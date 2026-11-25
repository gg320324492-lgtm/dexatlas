//! DexAtlas 后端侧车进程管理。
//!
//! 设计规范（docs/architecture/desktop-app.md §178）：桌面应用通过 Tauri
//! 侧车进程运行现有 DexAtlas，前端只经侧车的本地通道取数；不复制分析逻辑，
//! 不新增公共契约。本模块只负责把现有后端（`python -m dexatlas.workbench`
//! 或用户在设置里指定的命令）作为子进程拉起来，并把它的实际端口告诉前端。
//!
//! 职责边界：
//! - 启动：应用启动时（`setup`）按配置 spawn 后端，端口由系统分配（`--port 0`）。
//! - 观测：转发子进程 stdout/stderr 到应用日志（透传，不解析、不造数据）。
//! - 通知：子进程退出/被杀时向前端发 `sidecar://exited` 事件，UI 如实呈现。
//! - 收尾：应用退出时结束子进程（Drop + RunEvent::ExitRequested 双保险）。
//! - 放行：拿到实际端口后给 http 插件补一条动态 capability，前端 fetch 才
//!   能通过 ACL（`Manager::add_capability` 的 global scope 是增量合并的）。

use std::io::{BufRead, BufReader};
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicU16, AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;

use serde::Serialize;
use tauri::{AppHandle, Emitter, Manager, Runtime, State};

/// 前端通过 `getSidecarStatus` / `sidecar:status` 事件拿到的状态。
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SidecarStatus {
    /// 侧车是否活着（进程仍在运行）。
    pub running: bool,
    /// 后端实际监听的端口；尚未拿到时为 null。
    pub port: Option<u16>,
    /// 后端启动命令（ argv[0] ），用于设置页展示与排障。
    pub program: Option<String>,
    /// 人能读的状态说明（启动中 / 已就绪 / 已退出 + 退出码等）。
    pub message: String,
    /// 后端**根本没起来**（spawn 失败，如命令不在 PATH）。
    ///
    /// 前端据此不必空等端口：这是"确定不会来了"，与"还在启动中"不同。
    /// 运行过之后退出的侧车不算 `failed`——端口仍然知道，UI 如实显示退出即可。
    #[serde(default)]
    pub failed: bool,
}

impl SidecarStatus {
    fn starting(program: &str) -> Self {
        Self {
            running: false,
            port: None,
            program: Some(program.to_string()),
            message: "正在启动 DexAtlas 后端…".into(),
            failed: false,
        }
    }

    fn ready(port: u16, program: &str) -> Self {
        Self {
            running: true,
            port: Some(port),
            program: Some(program.to_string()),
            message: format!("DexAtlas 后端已就绪（127.0.0.1:{port}）"),
            failed: false,
        }
    }

    fn exited(&self, code: Option<i32>) -> Self {
        Self {
            running: false,
            port: self.port,
            program: self.program.clone(),
            message: match code {
                Some(0) => "DexAtlas 后端已退出（正常结束）。".into(),
                Some(code) => format!("DexAtlas 后端已异常退出（exit code {code}）。请检查后端命令与 Python 环境，或在设置页修改后端命令。"),
                None => "DexAtlas 后端进程已终止（被杀或因错误中断）。请检查后端命令与 Python 环境，或在设置页修改后端命令。".into(),
            },
            failed: false,
        }
    }

    fn spawn_failed(program: &str, reason: &str) -> Self {
        Self {
            running: false,
            port: None,
            program: Some(program.to_string()),
            message: format!("未能启动 DexAtlas 后端：{reason}。未检测到 DexAtlas 后端：请在设置页把后端命令写成已装好 dexatlas 包的 Python 绝对路径。"),
            failed: true,
        }
    }
}

/// 全局共享的侧车状态。
#[derive(Default)]
pub struct SidecarState {
    /// 最近一次状态（供命令查询与事件载荷）。
    status: Mutex<Option<SidecarStatus>>,
    /// 子进程句柄；`None` 表示尚未启动或已由 Drop 收走。
    child: Mutex<Option<Arc<Mutex<Child>>>>,
    /// 已向 http 插件放行的端口，避免重复注入 capability。
    allowed_port: AtomicU16,
    /// 侧车实例序号：每次 spawn 自增。
    ///
    /// 只有**当前实例**的线程能改状态。旧实例的退出/日志线程若继续改写，
    /// 会把新实例的状态覆盖掉——例如"保存设置 → 重启 → 新命令起不来"时，
    /// 旧进程的退出码会把"未能启动：找不到后端命令"盖成"已异常退出"。
    instance: AtomicU64,
}

impl SidecarState {
    /// 当前状态；从未启动过时返回一个"未启动"的占位。
    pub fn status(&self) -> SidecarStatus {
        self.status
            .lock()
            .expect("sidecar status mutex poisoned")
            .clone()
            .unwrap_or_else(|| SidecarStatus {
                running: false,
                port: None,
                program: None,
                message: "DexAtlas 后端尚未启动。".into(),
                failed: false,
            })
    }

    fn set_status(&self, status: SidecarStatus) {
        *self.status.lock().expect("sidecar status mutex poisoned") = Some(status);
    }

    /// 开启一个新的侧车实例，返回它的序号。
    fn begin_instance(&self) -> u64 {
        self.instance.fetch_add(1, Ordering::SeqCst) + 1
    }

    /// 这个线程是否仍在负责当前那一个侧车实例。
    fn is_current_instance(&self, instance: u64) -> bool {
        self.instance.load(Ordering::SeqCst) == instance
    }
}

/// 设置项：后端命令与参数（来自 Tauri 本地配置 backend.json）。
#[derive(Debug, Clone)]
pub struct BackendCommand {
    pub program: String,
    pub args: Vec<String>,
}

impl Default for BackendCommand {
    fn default() -> Self {
        Self {
            program: "python".into(),
            args: vec!["-m".into(), "dexatlas.workbench".into()],
        }
    }
}

/// 从 Tauri 应用配置目录读 `backend.json`；没有或解析失败就用默认命令。
///
/// 文件形如 `{ "command": "python", "args": ["-m", "dexatlas.workbench"] }`。
/// 解析失败不 panic：带着坏配置起不来后端只会让 UI 如实报错，而崩掉整个
/// 桌面应用会让用户失去"在设置页改回来"的机会。
pub fn backend_config_path(app: &AppHandle<impl Runtime>) -> Option<std::path::PathBuf> {
    app.path().app_config_dir().ok().map(|dir| dir.join("backend.json"))
}

/// 读 `backend.json`；没有或解析失败就用默认命令。
fn read_backend_command(path: &std::path::Path) -> BackendCommand {
    let default = BackendCommand::default();
    let Ok(raw) = std::fs::read_to_string(path) else {
        return default;
    };
    let Ok(value) = serde_json::from_str::<serde_json::Value>(&raw) else {
        eprintln!("[sidecar] {path:?} 不是合法 JSON，使用默认后端命令");
        return default;
    };
    parse_backend_command(&value).unwrap_or(default)
}

/// 从 JSON 值解析后端命令；形状不合法时返回 None（调用方回退默认）。
fn parse_backend_command(value: &serde_json::Value) -> Option<BackendCommand> {
    let program = value
        .get("command")
        .and_then(|v| v.as_str())
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(str::to_string)?;
    let args = value
        .get("args")
        .and_then(|v| v.as_array())
        .map(|items| {
            items
                .iter()
                .filter_map(|item| item.as_str().map(str::to_string))
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();
    Some(BackendCommand { program, args })
}

/// 把后端命令写入 `backend.json`（设置页保存时调用）。
pub fn store_backend_command(app: &AppHandle<impl Runtime>, command: &BackendCommand) -> Result<(), String> {
    let path = backend_config_path(app).ok_or_else(|| "无法定位应用配置目录".to_string())?;
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("创建配置目录失败：{e}"))?;
    }
    let value = serde_json::json!({ "command": command.program, "args": command.args });
    std::fs::write(&path, serde_json::to_string_pretty(&value).expect("json serialize"))
        .map_err(|e| format!("写入 {path:?} 失败：{e}"))
}

/// 从 Tauri 应用配置目录读 `backend.json`；没有或解析失败就用默认命令。
pub fn load_backend_command(app: &AppHandle<impl Runtime>) -> BackendCommand {
    match backend_config_path(app) {
        Some(path) => read_backend_command(&path),
        None => BackendCommand::default(),
    }
}

/// 把端口写回后端参数：替换/追加 `--port`，随后追加 `--port 0` 由系统选端口。
fn with_dynamic_port(mut args: Vec<String>) -> Vec<String> {
    let mut cleaned = Vec::with_capacity(args.len() + 2);
    let mut skip_next = false;
    for arg in args.drain(..) {
        if skip_next {
            skip_next = false;
            continue;
        }
        if arg == "--port" {
            skip_next = true;
            continue;
        }
        if arg.starts_with("--port=") {
            continue;
        }
        cleaned.push(arg);
    }
    cleaned.push("--port".into());
    cleaned.push("0".into());
    cleaned
}

/// 给 http 插件动态放行 `http://127.0.0.1:<port>/*`。
///
/// capability 的 global scope 是增量合并的（runtime_authority.add_capability
/// 只 extend），所以每次拿到新端口补一条即可，不影响既有放行。
fn allow_backend_port(app: &AppHandle<impl Runtime>, port: u16) {
    let identifier = format!("backend-port-{port}");
    let url = format!("http://127.0.0.1:{port}/*");
    let capability = format!(
        r#"{{ "identifier": "{identifier}", "windows": ["main"], "permissions": [{{ "identifier": "http:default", "allow": [{{ "url": "{url}" }}] }}] }}"#
    );
    if let Err(err) = app.add_capability(capability.as_str()) {
        eprintln!("[sidecar] 放行 {url} 失败：{err}");
    }
}

/// 启动后端命令。
///
/// `cwd` 是**可选**的工作目录：`None` 表示"推断不到仓库根"（安装形态）。
/// 推断不到**不是**拒绝启动的理由——那样绝对路径的后端命令永远不会被执行。
/// 旧实现把两件事用 `and_then` 串死：cwd 推断失败 ⇒ 短路 ⇒ `Command::new`
/// 从未被调用 ⇒ 安装形态下侧车从未被拉起。
fn spawn_backend(
    program: &str,
    args: &[String],
    cwd: Option<&std::path::Path>,
) -> std::io::Result<Child> {
    let mut command = Command::new(program);
    command.args(args);
    if let Some(dir) = cwd {
        command.current_dir(dir);
    }
    command
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
}

/// 命令里是否带了目录部分（`python` 与 `E:\venv\Scripts\python.exe` 的区别）。
fn has_directory_component(program: &str) -> bool {
    std::path::Path::new(program).components().count() > 1
}

/// spawn 失败的原因（人话）。
///
/// 分两种最常见的情况：
/// - 命令是个裸名字（`python`）而 PATH 里没有它 ⇒ 让用户去设置页写绝对路径；
/// - 命令本身带了路径但那个路径不存在 ⇒ 直接点名那个路径。
fn spawn_failure_reason(program: &str, err: &std::io::Error) -> String {
    if err.kind() == std::io::ErrorKind::NotFound {
        if has_directory_component(program) {
            format!("找不到后端命令 `{program}`：路径不存在或不可执行")
        } else {
            format!("命令 `{program}` 不是绝对路径，且不在 PATH 中（找不到该可执行文件）")
        }
    } else {
        format!("启动后端命令 `{program}` 失败：{err}")
    }
}

/// 启动侧车。返回是否真的 spawn 出了进程（失败时已把原因写进状态）。
pub fn spawn_sidecar(app: AppHandle<impl Runtime>) -> bool {
    let command = load_backend_command(&app);
    let program = command.program.clone();
    let args = with_dynamic_port(command.args);
    // 换一个实例序号：上一个实例的线程从此不再有资格改状态。
    let instance = app.state::<SidecarState>().begin_instance();
    let status = SidecarStatus::starting(&program);
    app.state::<SidecarState>().set_status(status);

    let cwd = backend_cwd(&app);
    let child = match spawn_backend(&program, &args, cwd.as_deref()) {
        Ok(child) => child,
        Err(err) => {
            let reason = spawn_failure_reason(&program, &err);
            let failure = SidecarStatus::spawn_failed(&program, &reason);
            app.state::<SidecarState>().set_status(failure);
            // 前端可能还没就绪，启动失败也要补发一次事件
            let _ = app.emit("sidecar:status", app.state::<SidecarState>().status());
            return false;
        }
    };

    let child = Arc::new(Mutex::new(child));
    *app.state::<SidecarState>()
        .child
        .lock()
        .expect("sidecar child mutex poisoned") = Some(child.clone());

    // stdout 线程：透传日志 + 从启动行抓实际端口
    let stdout_app = app.clone();
    let stdout_child = child.clone();
    thread::spawn(move || {
        let mut reader = BufReader::new(stdout_child.lock().expect("child mutex poisoned").stdout.take().expect("stdout piped"));
        let mut line = String::new();
        loop {
            line.clear();
            match reader.read_line(&mut line) {
                Ok(0) => break,
                Ok(_) => {
                    let trimmed = line.trim_end();
                    eprintln!("[backend-stdout] {trimmed}");
                    note_backend_line(&stdout_app, instance, trimmed);
                }
                Err(err) => {
                    eprintln!("[backend-stdout] 读取失败：{err}");
                    break;
                }
            }
        }
    });

    // stderr 线程：透传日志（uvicorn 的 "Uvicorn running on" 行在 stderr，
    // 实际端口主要从这里抓——stdout 的 banner 在 --port 0 下不含数字）
    let stderr_app = app.clone();
    let stderr_child = child.clone();
    thread::spawn(move || {
        let mut reader = BufReader::new(stderr_child.lock().expect("child mutex poisoned").stderr.take().expect("stderr piped"));
        let mut line = String::new();
        loop {
            line.clear();
            match reader.read_line(&mut line) {
                Ok(0) => break,
                Ok(_) => {
                    let trimmed = line.trim_end();
                    eprintln!("[backend-stderr] {trimmed}");
                    note_backend_line(&stderr_app, instance, trimmed);
                }
                Err(err) => {
                    eprintln!("[backend-stderr] 读取失败：{err}");
                    break;
                }
            }
        }
    });

    // 等待线程：进程退出时更新状态并通知前端。
    // 直接 wait() 会一直阻塞到直接子进程退出；workbench 可能经由中间
    // python 进程再 spawn uvicorn，所以这里轮询 PID：直接子进程已消失
    // （或其后端进程树已整体消失）即视为侧车退出。
    let wait_app = app.clone();
    let wait_child = child.clone();
    thread::spawn(move || loop {
        {
            let mut guard = wait_child.lock().expect("child mutex poisoned");
            match guard.try_wait() {
                Ok(Some(status)) => {
                    let code = status.code();
                    let state = wait_app.state::<SidecarState>();
                    // 已有更新的实例接管 ⇒ 这个旧实例不该再改状态。
                    if state.is_current_instance(instance) {
                        let current = state.status();
                        state.set_status(current.exited(code));
                        let _ = wait_app.emit("sidecar:status", state.status());
                    }
                    break;
                }
                Ok(None) => {}
                Err(err) => {
                    eprintln!("[sidecar] try_wait 失败：{err}");
                    break;
                }
            }
        }
        if !backend_process_alive() {
            let state = wait_app.state::<SidecarState>();
            // 同上：旧实例的退出不覆盖新实例的状态。
            if state.is_current_instance(instance) {
                let current = state.status();
                // kill 的退出码拿不到（进程树已散），按异常终止如实报告
                state.set_status(current.exited(None));
                let _ = wait_app.emit("sidecar:status", state.status());
            }
            break;
        }
        thread::sleep(std::time::Duration::from_millis(500));
    });

    true
}

/// 侧车后端进程树是否仍有活口（按本进程的直接子进程里有没有 python 探测）。
///
/// 不依赖具体 PID：`--port 0` 下后端可能经中间进程再 spawn uvicorn，只有
/// "本应用名下还有没有 python 进程" 这个事实是稳定的。
fn backend_process_alive() -> bool {
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        // tasklist /FO CSV /NH 输出： "python.exe","1234","Console",...
        if let Ok(output) = Command::new("tasklist")
            .args(["/FI", "IMAGENAME eq python.exe", "/FO", "CSV", "/NH"])
            .creation_flags(0x0800_0000) // CREATE_NO_WINDOW
            .output()
        {
            let text = String::from_utf8_lossy(&output.stdout);
            return text.contains("python.exe");
        }
        // tasklist 不可用时保守返回 true（宁可晚报退出也不误报崩溃）
        true
    }
    #[cfg(not(windows))]
    {
        // 非 Windows：没有直接子进程探测的轻量办法，保守返回 true，
        // 由 Child::try_wait 的直接退出路径负责状态更新。
        true
    }
}

/// 侧车后端的工作目录：仓库根（保证 `python -m dexatlas.workbench` 能找到包）。
///
/// **推断不到仓库根不是错误**：安装形态下 exe 位于安装目录，反推不出仓库，
/// 此时后端命令应当是绝对路径（如 venv 的 python.exe），workbench 自带前端，
/// cwd 无关紧要。返回 `None` 的含义是"不设 cwd"，**不是"不启动"**。
fn backend_cwd(_app: &AppHandle<impl Runtime>) -> Option<std::path::PathBuf> {
    repo_root_from_exe(&std::env::current_exe().ok()?)
}

/// 从 exe 路径反推仓库根。
///
/// dev 形态：`target/debug`（或 `target/release`）的上四级是 `desktop/`，
/// 再上一级是仓库根——该目录下确有 `src/dexatlas` 才认。
/// 打包形态：exe 在安装目录，祖先链里没有 `src/dexatlas` ⇒ `None`。
fn repo_root_from_exe(exe: &std::path::Path) -> Option<std::path::PathBuf> {
    let dir = exe.parent()?.ancestors().nth(4)?;
    if dir.join("src").join("dexatlas").exists() {
        Some(dir.to_path_buf())
    } else {
        None
    }
}

/// 从 workbench/uvicorn 的启动行里抓实际端口。
///
/// 两种已知形态（src/dexatlas/workbench/__main__.py 打印 + uvicorn 默认行）：
/// - `serving the workbench on http://127.0.0.1:<port>`
/// - `Uvicorn running on http://127.0.0.1:<port>`
/// `--port 0` 时第一条是 `<system-chosen port>`（抓不到，等 uvicorn 那条）。
fn parse_serving_port(line: &str) -> Option<u16> {
    let marker = "http://127.0.0.1:";
    let idx = line.find(marker)?;
    let rest = &line[idx + marker.len()..];
    let digits: String = rest.chars().take_while(char::is_ascii_digit).collect();
    digits.parse().ok()
}

/// 后端每行输出统一处理：抓到端口就放行 + 更新状态 + 广播。
///
/// `instance` 是这个输出属于哪一次侧车：旧实例的迟到输出不得覆盖
/// 新实例的状态（旧端口会把刚启动好的新侧车盖成"另一个端口已就绪"）。
fn note_backend_line(app: &AppHandle<impl Runtime>, instance: u64, line: &str) {
    if let Some(port) = parse_serving_port(line) {
        allow_backend_port(app, port);
        let state = app.state::<SidecarState>();
        if !state.is_current_instance(instance) {
            return;
        }
        if state.allowed_port.load(Ordering::SeqCst) != port {
            state.allowed_port.store(port, Ordering::SeqCst);
            let program = state.status().program.unwrap_or_else(|| "dexatlas".into());
            state.set_status(SidecarStatus::ready(port, &program));
            let _ = app.emit("sidecar:status", state.status());
        }
    }
}

/// 前端查询侧车状态（启动中 / 已就绪 / 已退出 / 启动失败）。
#[tauri::command]
pub fn get_sidecar_status(state: State<'_, SidecarState>) -> SidecarStatus {
    state.status()
}

/// 前端读取后端命令配置（设置页展示当前值）。
#[tauri::command]
pub fn get_backend_command(app: AppHandle<impl Runtime>) -> serde_json::Value {
    let command = load_backend_command(&app);
    serde_json::json!({ "command": command.program, "args": command.args })
}

/// 前端保存后端命令配置（写 backend.json；重启由 restart_sidecar 触发）。
#[tauri::command]
pub fn set_backend_command(
    app: AppHandle<impl Runtime>,
    command: String,
    args: Vec<String>,
) -> Result<(), String> {
    let command = command.trim().to_string();
    if command.is_empty() {
        return Err("后端命令不能为空".into());
    }
    store_backend_command(&app, &BackendCommand { program: command, args })
}

/// 前端保存设置后要求按新配置重启侧车（杀旧进程，重新 spawn）。
#[tauri::command]
pub fn restart_sidecar(app: AppHandle<impl Runtime>) -> SidecarStatus {
    shutdown_sidecar(&app);
    spawn_sidecar(app.clone());
    app.state::<SidecarState>().status()
}

/// 应用退出时结束子进程（kill 整棵进程树再 wait，避免留下孤儿后端）。
pub fn shutdown_sidecar(app: &AppHandle<impl Runtime>) {
    let child = app
        .state::<SidecarState>()
        .child
        .lock()
        .expect("sidecar child mutex poisoned")
        .take();
    if let Some(child) = child {
        let pid = child.lock().expect("child mutex poisoned").id();
        kill_process_tree(pid);
        let mut guard = child.lock().expect("child mutex poisoned");
        let _ = guard.kill();
        let _ = guard.wait();
    }
}

/// 结束一整棵进程树（taskkill /T，Windows；其他平台只杀直接进程）。
fn kill_process_tree(pid: u32) {
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        let _ = Command::new("taskkill")
            .args(["/PID", &pid.to_string(), "/T", "/F"])
            .creation_flags(0x0800_0000) // CREATE_NO_WINDOW
            .output();
    }
    #[cfg(not(windows))]
    {
        let _ = pid;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn dynamic_port_replaces_existing_flag() {
        let args = with_dynamic_port(vec![
            "python".into(),
            "-m".into(),
            "dexatlas.workbench".into(),
            "--port".into(),
            "8618".into(),
        ]);
        assert_eq!(args, vec!["python", "-m", "dexatlas.workbench", "--port", "0"]);
    }

    #[test]
    fn dynamic_port_appends_when_missing() {
        let args = with_dynamic_port(vec!["dexatlas-workbench".into()]);
        assert_eq!(args, vec!["dexatlas-workbench", "--port", "0"]);
    }

    #[test]
    fn parses_workbench_banner_port() {
        let line = "serving the workbench on http://127.0.0.1:53123";
        assert_eq!(parse_serving_port(line), Some(53123));
    }

    #[test]
    fn parses_uvicorn_banner_port() {
        let line = "INFO:     Uvicorn running on http://127.0.0.1:53123 (Press CTRL+C to quit)";
        assert_eq!(parse_serving_port(line), Some(53123));
    }

    #[test]
    fn system_chosen_placeholder_yields_none() {
        let line = "serving the workbench on http://127.0.0.1:<system-chosen port>";
        assert_eq!(parse_serving_port(line), None);
    }

    #[test]
    fn non_loopback_line_yields_none() {
        assert_eq!(parse_serving_port("serving on http://example.com:80"), None);
    }

    #[test]
    fn exited_status_names_the_exit_code() {
        let ready = SidecarStatus::ready(1234, "python");
        let exited = ready.exited(Some(1));
        assert!(!exited.running);
        assert_eq!(exited.port, Some(1234));
        assert!(exited.message.contains("exit code 1"));
    }

    #[test]
    fn parses_backend_command_from_json() {
        let value = serde_json::json!({ "command": " E:\\venv\\python.exe ", "args": ["-m", "dexatlas.workbench"] });
        let parsed = parse_backend_command(&value).expect("should parse");
        assert_eq!(parsed.program, "E:\\venv\\python.exe");
        assert_eq!(parsed.args, vec!["-m", "dexatlas.workbench"]);
    }

    #[test]
    fn blank_command_yields_none() {
        let value = serde_json::json!({ "command": "   " });
        assert!(parse_backend_command(&value).is_none());
    }

    #[test]
    fn read_backend_command_falls_back_on_garbage() {
        let dir = std::env::temp_dir().join(format!("dexatlas-sidecar-test-{}", std::process::id()));
        std::fs::create_dir_all(&dir).expect("mkdir");
        std::fs::write(dir.join("backend.json"), "not json{").expect("write");
        let command = read_backend_command(&dir.join("backend.json"));
        assert_eq!(command.program, BackendCommand::default().program);
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn read_backend_command_missing_file_uses_default() {
        let dir = std::env::temp_dir().join(format!("dexatlas-sidecar-absent-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).expect("mkdir");
        let command = read_backend_command(&dir.join("absent.json"));
        assert_eq!(command.program, "python");
        assert_eq!(command.args, vec!["-m", "dexatlas.workbench"]);
        let _ = std::fs::remove_dir_all(&dir);
    }

    /// 一个必定能启动的跨平台命令（用来证明 spawn 确实被尝试过）。
    fn noop_command() -> (String, Vec<String>) {
        if cfg!(windows) {
            ("cmd".into(), vec!["/C".into(), "exit".into()])
        } else {
            ("sh".into(), vec!["-c".into(), "exit".into()])
        }
    }

    #[test]
    fn install_directory_is_not_mistaken_for_the_repo_root() {
        // 打包形态：exe 在安装目录，祖先链里没有 src/dexatlas。
        let exe = std::path::Path::new(r"C:\Users\pc\AppData\Local\DexAtlas Studio\dexatlas-desktop.exe");
        assert_eq!(repo_root_from_exe(exe), None);
    }

    #[test]
    fn spawn_is_attempted_even_when_the_repo_root_cannot_be_inferred() {
        // 回归：旧实现把 cwd 推断与 spawn 用 and_then 串起来，推断失败 ⇒ 短路
        // ⇒ Command::new 从未被调用 ⇒ 安装形态下侧车永远起不来。
        let exe = std::path::Path::new(r"C:\Users\pc\AppData\Local\DexAtlas Studio\dexatlas-desktop.exe");
        let cwd = repo_root_from_exe(exe);
        assert!(cwd.is_none(), "安装目录不该被当成仓库根");
        let (program, args) = noop_command();
        let mut child = spawn_backend(&program, &args, cwd.as_deref())
            .expect("推断不出仓库根时也必须尝试启动后端命令");
        let _ = child.wait();
    }

    #[test]
    fn spawn_failure_reason_explains_a_bare_command_name() {
        let err = std::io::Error::new(
            std::io::ErrorKind::NotFound,
            "The system cannot find the file specified.",
        );
        let reason = spawn_failure_reason("python", &err);
        assert!(reason.contains("不是绝对路径"), "原因要说清命令不是绝对路径：{reason}");
        assert!(reason.contains("PATH"), "原因要说清 PATH 里也没有：{reason}");
    }

    #[test]
    fn spawn_failure_reason_explains_a_missing_absolute_path() {
        let err = std::io::Error::new(
            std::io::ErrorKind::NotFound,
            "The system cannot find the file specified.",
        );
        let reason = spawn_failure_reason(r"E:\missing\python.exe", &err);
        assert!(reason.contains(r"E:\missing\python.exe"), "原因要点名那个路径：{reason}");
        assert!(!reason.contains("不是绝对路径"), "绝对路径不该被说成缺 PATH：{reason}");
    }

    #[test]
    fn only_a_spawn_failure_marks_the_backend_as_failed() {
        // 前端靠 failed 区分"还在启动中"与"确定起不来"，别把两者混为一谈。
        assert!(SidecarStatus::spawn_failed("python", "原因").failed);
        assert!(!SidecarStatus::starting("python").failed);
        assert!(!SidecarStatus::ready(1234, "python").failed);
        assert!(!SidecarStatus::ready(1234, "python").exited(Some(1)).failed);
    }

    #[test]
    fn an_old_sidecar_instance_may_not_overwrite_the_new_status() {
        // 回归：重启侧车时，旧进程的退出线程会把"未能启动：找不到后端命令"
        // 盖成"已异常退出（exit code 1）"，新实例的真实原因就丢了。
        let state = SidecarState::default();
        let first = state.begin_instance();
        state.set_status(SidecarStatus::starting("python"));
        let second = state.begin_instance();

        assert_ne!(first, second, "每次 spawn 都该换一个实例序号");
        assert!(!state.is_current_instance(first), "旧实例不得再改状态");
        assert!(state.is_current_instance(second), "新实例才该改状态");

        // 旧实例的退出状态不该被写进去
        if state.is_current_instance(first) {
            state.set_status(state.status().exited(Some(1)));
        }
        assert!(!state.status().failed);
        assert!(state.status().message.contains("正在启动"), "状态仍是新实例的：{}", state.status().message);
    }
}
