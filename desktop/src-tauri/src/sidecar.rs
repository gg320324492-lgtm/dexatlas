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
//! - 收尾：应用退出时结束子进程——`RunEvent::Exit` 主动清理、`SidecarState::drop`
//!   兜底；Windows 上再加一道作业对象（Job Object）：宿主进程被 `taskkill /F`
//!   强杀时 Rust 一行也跑不了，由系统替我们收掉整棵后端进程树。
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
    /// 被托管的后端子进程；`None` 表示尚未启动或已被清理
    /// （主动清理，或本结构体的 `Drop` 收走）。
    child: Mutex<Option<ManagedChild>>,
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

impl Drop for SidecarState {
    /// 兜底：状态被丢弃时（应用退出、`run()` 返回）确保后端不留活口。
    ///
    /// `RunEvent::Exit` 里的主动清理是第一道，这里是第二道。旧版本**根本没有**
    /// 这个 `Drop`，而字段注释却写着"已由 Drop 收走"——注释声称的必须是代码
    /// 做的，所以要么补上实现，要么改注释；这里选了补实现，因为应用崩溃、
    /// 事件循环异常返回等路径上，主动清理那一条未必跑得到。
    ///
    /// 强杀（`taskkill /F`）时这个 `Drop` 同样跑不到——那一道由 Windows 的
    /// 作业对象兜：宿主进程一死，系统关闭它的句柄，作业里的后端进程随之终止。
    fn drop(&mut self) {
        // `get_mut` 不会上锁，也就不会和正拿着锁的日志线程互等。
        let Ok(slot) = self.child.get_mut() else {
            return;
        };
        if let Some(mut managed) = slot.take() {
            managed.terminate();
        }
    }
}

/// 被托管的后端子进程：进程本身 + "宿主一死它也得死"的托管句柄。
struct ManagedChild {
    /// 直接子进程；读日志线程与等待线程共用同一把锁。
    child: Arc<Mutex<Child>>,
    /// Windows：作业对象句柄。其他平台没有等价机制，恒为 `None`。
    ///
    /// 它与子进程同生共死：句柄一关（显式关闭，或宿主被强杀时由系统关闭），
    /// 作业里的整棵后端进程树随即被终止。
    job: Option<TreeGuard>,
}

/// 平台相关的"宿主一死，后端跟着死"的托管句柄。
#[cfg(windows)]
type TreeGuard = job::Job;
#[cfg(not(windows))]
type TreeGuard = ();

impl ManagedChild {
    /// 启动后端，但**不**纳入作业对象。
    ///
    /// 这是作业对象那条路走不通时的退路（作业建不起来、或主线程恢复失败）。
    /// 此时"宿主被强杀"就没有系统兜底，只剩应用自己收尾。
    fn spawn_unmanaged(
        program: &str,
        args: &[String],
        cwd: Option<&std::path::Path>,
    ) -> std::io::Result<Self> {
        let child = spawn_backend(program, args, cwd)?;
        Ok(Self {
            child: Arc::new(Mutex::new(child)),
            job: None,
        })
    }

    /// 启动后端，并把它纳入托管。
    ///
    /// Windows 上是"挂起创建 → 放进作业对象 → 放行"：子进程在进作业之前
    /// 一条指令也没执行，它自己拉起的后代（venv 的 `python.exe` 是个转发器，
    /// 会再拉起真正的解释器）必然继承作业身份。作业建不起来或恢复失败时
    /// 退回普通启动——功能不受影响，只是强杀宿主时少了系统兜底。
    fn spawn(
        program: &str,
        args: &[String],
        cwd: Option<&std::path::Path>,
    ) -> std::io::Result<Self> {
        #[cfg(windows)]
        {
            match job::Job::new() {
                Some(job) => {
                    let mut child = job::spawn_suspended(&mut backend_command(program, args, cwd))?;
                    let in_job = job.assign(&child) && job.contains(&child);
                    if !in_job {
                        // 进不了作业（或进去了却查不到）：照样把挂起的子进程放行，
                        // 别让它永远挂着；只是"宿主被强杀"时少了系统兜底。
                        eprintln!("[sidecar] 后端进程未进入作业对象，宿主被强杀时将失去系统兜底");
                        let _ = job::resume_primary_thread(&child);
                        return Ok(Self {
                            child: Arc::new(Mutex::new(child)),
                            job: None,
                        });
                    }
                    if let Err(err) = job::resume_primary_thread(&child) {
                        // 恢复失败 = 进程永远挂着 = 比孤儿更糟。杀掉重来，
                        // 这一回不带作业对象。
                        let _ = child.kill();
                        let _ = child.wait();
                        eprintln!(
                            "[sidecar] 恢复后端主线程失败（{err}），改用不带作业对象的启动方式"
                        );
                        return Self::spawn_unmanaged(program, args, cwd);
                    }
                    Ok(Self {
                        child: Arc::new(Mutex::new(child)),
                        job: Some(job),
                    })
                }
                None => Self::spawn_unmanaged(program, args, cwd),
            }
        }
        #[cfg(not(windows))]
        {
            Self::spawn_unmanaged(program, args, cwd)
        }
    }

    /// 结束这个后端：先按进程树杀，再等它收尸，最后关掉托管句柄兜底。
    fn terminate(&mut self) {
        let pid = self.child.lock().ok().map(|guard| guard.id());
        if let Some(pid) = pid {
            kill_process_tree(pid);
        }
        if let Ok(mut guard) = self.child.lock() {
            let _ = guard.kill();
            let _ = guard.wait();
        }
        // 关掉作业对象：Windows 上作业里剩下的进程随之被系统终止——
        // 直接子进程已经退出、只剩孙子进程时，`taskkill /T` 够不着它们，
        // 作业对象够得着。
        self.job = None;
    }
}

/// Windows 作业对象（Job Object）：把"宿主一死，后端跟着死"从 Rust 的善意
/// 变成操作系统的保证。
///
/// **为什么需要它。** 侧车后端是应用 spawn 出来的子进程。应用正常退出时
/// Rust 代码还能跑，可以主动结束它；被 `taskkill /F` 强杀时 Rust 一行也跑不了，
/// 剩下的只有操作系统。Windows 的作业对象正是为此准备的：把子进程放进一个
/// 带 `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` 的作业，宿主进程一死（正常退出、
/// 崩溃、被强杀都一样——系统会关闭它的全部句柄），作业里的进程随即被终止。
///
/// **为什么是"挂起创建"。** 子进程必须在**执行第一条指令之前**就进作业，
/// 否则它自己拉起的后代可能落在作业之外：venv 里的 `python.exe` 是个转发器，
/// 它会再拉起真正的解释器（实测进程树是 exe → venv python → 真解释器）。
/// 所以这里用 `CREATE_SUSPENDED` 创建子进程 → 放进作业 → 再恢复它的主线程。
/// 之后它 fork 出来的后代一律继承作业身份（作业没有开 breakaway）。
///
/// 其余平台没有等价机制，那里只剩"能主动收尾就主动收尾"（见 `ManagedChild`）。
#[cfg(windows)]
mod job {
    use std::ffi::c_void;
    use std::io;
    use std::mem::size_of;
    use std::os::windows::io::{AsRawHandle, RawHandle};
    use std::os::windows::process::CommandExt;
    use std::process::{Child, Command};
    use std::ptr;

    /// `CREATE_SUSPENDED`：进程创建后主线程挂起，不执行任何指令。
    const CREATE_SUSPENDED: u32 = 0x0000_0004;
    /// `THREAD_SUSPEND_RESUME`：打开线程只要"挂起/恢复"的权限。
    const THREAD_SUSPEND_RESUME: u32 = 0x0000_0002;
    /// `TH32CS_SNAPTHREAD`：线程快照。
    const TH32CS_SNAPTHREAD: u32 = 0x0000_0004;
    /// `INVALID_HANDLE_VALUE`
    const INVALID_HANDLE_VALUE: RawHandle = usize::MAX as RawHandle;
    /// `JobObjectExtendedLimitInformation`
    const JOB_OBJECT_EXTENDED_LIMIT_INFORMATION: i32 = 9;
    /// `JobObjectBasicAccountingInformation`
    const JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION: i32 = 1;
    /// `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`：作业的最后一个句柄关闭时，
    /// 终止作业里的全部进程。
    const JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE: u32 = 0x0000_2000;

    type Handle = *mut c_void;

    /// `JOBOBJECT_BASIC_LIMIT_INFORMATION`
    #[repr(C)]
    struct BasicLimitInformation {
        per_process_user_time_limit: i64,
        per_job_user_time_limit: i64,
        limit_flags: u32,
        minimum_working_set_size: usize,
        maximum_working_set_size: usize,
        active_process_limit: u32,
        affinity: usize,
        priority_class: u32,
        scheduling_class: u32,
    }

    /// `IO_COUNTERS`
    #[repr(C)]
    struct IoCounters {
        read_operation_count: u64,
        write_operation_count: u64,
        other_operation_count: u64,
        read_transfer_count: u64,
        write_transfer_count: u64,
        other_transfer_count: u64,
    }

    /// `JOBOBJECT_EXTENDED_LIMIT_INFORMATION`
    #[repr(C)]
    struct ExtendedLimitInformation {
        basic_limit_information: BasicLimitInformation,
        io_info: IoCounters,
        process_memory_limit: usize,
        job_memory_limit: usize,
        peak_process_memory_used: usize,
        peak_job_memory_used: usize,
    }

    /// `JOBOBJECT_BASIC_ACCOUNTING_INFORMATION`
    #[cfg(test)]
    #[repr(C)]
    struct BasicAccountingInformation {
        total_user_time: i64,
        total_kernel_time: i64,
        this_period_total_user_time: i64,
        this_period_total_kernel_time: i64,
        total_page_fault_count: u32,
        total_processes: u32,
        active_processes: u32,
        total_terminated_processes: u32,
    }

    /// `THREADENTRY32`
    #[repr(C)]
    struct ThreadEntry32 {
        dw_size: u32,
        cnt_usage: u32,
        thread_id: u32,
        owner_process_id: u32,
        base_priority: i32,
        delta_priority: i32,
        flags: u32,
    }

    // 结构体布局写歪时 `SetInformationJobObject` 会失败，但失败原因看不直观；
    // 与 Windows SDK 的文档尺寸对齐，能在编译期就发现写歪。
    #[cfg(target_pointer_width = "64")]
    const _: () = assert!(size_of::<ExtendedLimitInformation>() == 144);
    #[cfg(target_pointer_width = "32")]
    const _: () = assert!(size_of::<ExtendedLimitInformation>() == 112);

    #[link(name = "kernel32")]
    extern "system" {
        fn CreateJobObjectW(attributes: *const c_void, name: *const u16) -> Handle;
        fn SetInformationJobObject(
            job: Handle,
            info_class: i32,
            info: *const c_void,
            info_length: u32,
        ) -> i32;
        fn AssignProcessToJobObject(job: Handle, process: RawHandle) -> i32;
        #[cfg(test)]
        fn QueryInformationJobObject(
            job: Handle,
            info_class: i32,
            info: *mut c_void,
            info_length: u32,
            return_length: *mut u32,
        ) -> i32;
        fn IsProcessInJob(process: RawHandle, job: Handle, result: *mut i32) -> i32;
        fn CloseHandle(object: Handle) -> i32;
        fn CreateToolhelp32Snapshot(flags: u32, process_id: u32) -> Handle;
        fn Thread32First(snapshot: Handle, entry: *mut ThreadEntry32) -> i32;
        fn Thread32Next(snapshot: Handle, entry: *mut ThreadEntry32) -> i32;
        fn OpenThread(access: u32, inherit_handle: i32, thread_id: u32) -> Handle;
        fn ResumeThread(thread: Handle) -> u32;
    }

    /// 一个作业对象句柄：句柄一关，作业里的进程就被终止。
    pub struct Job {
        handle: Handle,
    }

    // 作业句柄是内核对象，交给多个线程用与交给一个线程用没有区别；但裸指针
    // 不带 `Send`/`Sync`，得自己说明这一点。本模块只在持锁的情况下用它。
    unsafe impl Send for Job {}
    unsafe impl Sync for Job {}

    impl Job {
        /// 建一个"关闭即终止"的作业。
        pub fn new() -> Option<Self> {
            let handle = unsafe { CreateJobObjectW(ptr::null(), ptr::null()) };
            if handle.is_null() {
                eprintln!("[sidecar] 创建作业对象失败：{:?}", io::Error::last_os_error());
                return None;
            }
            let job = Self { handle };
            let info = ExtendedLimitInformation {
                basic_limit_information: BasicLimitInformation {
                    per_process_user_time_limit: 0,
                    per_job_user_time_limit: 0,
                    limit_flags: 0,
                    minimum_working_set_size: 0,
                    maximum_working_set_size: 0,
                    active_process_limit: 0,
                    affinity: 0,
                    priority_class: 0,
                    scheduling_class: 0,
                },
                io_info: IoCounters {
                    read_operation_count: 0,
                    write_operation_count: 0,
                    other_operation_count: 0,
                    read_transfer_count: 0,
                    write_transfer_count: 0,
                    other_transfer_count: 0,
                },
                process_memory_limit: 0,
                job_memory_limit: 0,
                peak_process_memory_used: 0,
                peak_job_memory_used: 0,
            };
            let ok = unsafe {
                SetInformationJobObject(
                    job.handle,
                    JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                    ptr::from_ref(&info).cast::<c_void>(),
                    size_of::<ExtendedLimitInformation>() as u32,
                )
            };
            if ok == 0 {
                eprintln!("[sidecar] 设置作业对象属性失败：{:?}", io::Error::last_os_error());
                // job 在这里被 drop ⇒ CloseHandle；此刻作业里没有成员，没有副作用。
                return None;
            }
            Some(job)
        }

        /// 把一个（此刻还挂着的）子进程收进作业。
        pub fn assign(&self, child: &Child) -> bool {
            let ok = unsafe { AssignProcessToJobObject(self.handle, child.as_raw_handle()) };
            if ok == 0 {
                eprintln!("[sidecar] 后端进程加入作业对象失败：{:?}", io::Error::last_os_error());
                return false;
            }
            true
        }

        /// 这个进程是不是在作业里。
        pub fn contains(&self, child: &Child) -> bool {
            let mut inside = 0i32;
            let ok = unsafe { IsProcessInJob(child.as_raw_handle(), self.handle, &mut inside) };
            ok != 0 && inside != 0
        }

        /// 作业里活着的进程数（含它们自己 fork 出来的后代）。
        #[cfg(test)]
        pub fn active_process_count(&self) -> u32 {
            let mut info = BasicAccountingInformation {
                total_user_time: 0,
                total_kernel_time: 0,
                this_period_total_user_time: 0,
                this_period_total_kernel_time: 0,
                total_page_fault_count: 0,
                total_processes: 0,
                active_processes: 0,
                total_terminated_processes: 0,
            };
            let ok = unsafe {
                QueryInformationJobObject(
                    self.handle,
                    JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION,
                    ptr::from_mut(&mut info).cast::<c_void>(),
                    size_of::<BasicAccountingInformation>() as u32,
                    ptr::null_mut(),
                )
            };
            if ok == 0 {
                0
            } else {
                info.active_processes
            }
        }
    }

    impl Drop for Job {
        fn drop(&mut self) {
            unsafe { CloseHandle(self.handle) };
        }
    }

    /// 以"挂起"方式创建进程：主线程不执行任何指令，直到我们显式恢复它。
    ///
    /// 挂起创建的意义只有一个：让调用方能在子进程跑第一条指令之前，先把它
    /// 安置进作业对象。否则它 fork 出来的后代可能落在作业之外。
    pub fn spawn_suspended(command: &mut Command) -> io::Result<Child> {
        command.creation_flags(CREATE_SUSPENDED);
        command.spawn()
    }

    /// 恢复刚创建（挂起）的子进程主线程。
    ///
    /// 挂起创建的进程只有一个线程（主线程），所以按属主 PID 找到它并恢复即可。
    /// 找不到或恢复失败时返回错误：调用方必须杀掉这个挂起的进程——让它一直
    /// 挂着比留下一个孤儿更糟（占着内存却什么都不做）。
    pub fn resume_primary_thread(child: &Child) -> io::Result<()> {
        let pid = child.id();
        let snapshot = unsafe { CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0) };
        if snapshot == INVALID_HANDLE_VALUE {
            return Err(io::Error::last_os_error());
        }
        let mut entry = ThreadEntry32 {
            dw_size: size_of::<ThreadEntry32>() as u32,
            cnt_usage: 0,
            thread_id: 0,
            owner_process_id: 0,
            base_priority: 0,
            delta_priority: 0,
            flags: 0,
        };
        let mut outcome = Err(io::Error::new(
            io::ErrorKind::NotFound,
            "找不到挂起进程的主线程",
        ));
        unsafe {
            if Thread32First(snapshot, &mut entry) != 0 {
                loop {
                    if entry.owner_process_id == pid {
                        let thread = OpenThread(THREAD_SUSPEND_RESUME, 0, entry.thread_id);
                        if thread.is_null() {
                            outcome = Err(io::Error::last_os_error());
                        } else {
                            let previous = ResumeThread(thread);
                            CloseHandle(thread);
                            outcome = if previous == u32::MAX {
                                Err(io::Error::last_os_error())
                            } else {
                                Ok(())
                            };
                        }
                        break;
                    }
                    if Thread32Next(snapshot, &mut entry) == 0 {
                        break;
                    }
                }
            }
            CloseHandle(snapshot);
        }
        outcome
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

/// 拼好后端命令（启动与测试共用）。
fn backend_command(program: &str, args: &[String], cwd: Option<&std::path::Path>) -> Command {
    let mut command = Command::new(program);
    command.args(args);
    if let Some(dir) = cwd {
        command.current_dir(dir);
    }
    command.stdout(Stdio::piped()).stderr(Stdio::piped());
    command
}

/// 启动后端命令。
///
/// `cwd` 是**可选**的工作目录：`None` 表示"推断不到仓库根"（安装形态）。
/// 推断不到**不是**拒绝启动的理由——那样绝对路径的后端命令永远不会被执行。
/// 旧实现把两件事用 `and_then` 串死：cwd 推断失败 ⇒ 短路 ⇒ `Command::new`
/// 从未被调用 ⇒ 安装形态下侧车从未被拉起。
///
/// 这条路径**不做**进程托管：托管在 [`ManagedChild::spawn`] 里（Windows 上
/// 还要"挂起创建 → 进作业对象 → 放行"）。
fn spawn_backend(
    program: &str,
    args: &[String],
    cwd: Option<&std::path::Path>,
) -> std::io::Result<Child> {
    backend_command(program, args, cwd).spawn()
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
    let managed = match ManagedChild::spawn(&program, &args, cwd.as_deref()) {
        Ok(managed) => managed,
        Err(err) => {
            let reason = spawn_failure_reason(&program, &err);
            let failure = SidecarStatus::spawn_failed(&program, &reason);
            app.state::<SidecarState>().set_status(failure);
            // 前端可能还没就绪，启动失败也要补发一次事件
            let _ = app.emit("sidecar:status", app.state::<SidecarState>().status());
            return false;
        }
    };

    let child = managed.child.clone();
    *app.state::<SidecarState>()
        .child
        .lock()
        .expect("sidecar child mutex poisoned") = Some(managed);

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
///
/// 这是**主动**清理；`SidecarState::drop` 是兜底；宿主被强杀时两者都跑不到，
/// 由 Windows 的作业对象接手（见 `job` 模块）。
pub fn shutdown_sidecar(app: &AppHandle<impl Runtime>) {
    let managed = app
        .state::<SidecarState>()
        .child
        .lock()
        .expect("sidecar child mutex poisoned")
        .take();
    if let Some(mut managed) = managed {
        managed.terminate();
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

    // ---------------------------------------------------------------- 收尾

    use std::time::{Duration, Instant};

    /// 一个必定会一直跑着的后端命令（用来观察"谁还活着"）。
    fn long_running_command() -> Vec<String> {
        if cfg!(windows) {
            // ping -t 一直跑；输出丢进 nul，免得测试的管道被填满。
            vec!["/C".into(), "ping -t 127.0.0.1 > nul".into()]
        } else {
            vec!["-c".into(), "sleep 300".into()]
        }
    }

    /// 等一个进程收工；超时返回 false。
    fn wait_until_exited(child: &Arc<Mutex<Child>>, timeout: Duration) -> bool {
        let deadline = Instant::now() + timeout;
        loop {
            if child
                .lock()
                .expect("child mutex poisoned")
                .try_wait()
                .expect("try_wait")
                .is_some()
            {
                return true;
            }
            if Instant::now() >= deadline {
                return false;
            }
            std::thread::sleep(Duration::from_millis(50));
        }
    }

    #[test]
    fn dropping_the_sidecar_state_stops_the_backend() {
        // 回归：旧实现里**根本没有** Drop，字段注释却写着"已由 Drop 收走"——
        // 注释声称的必须是代码做的。状态被丢弃（应用退出）时后端必须跟着走。
        //
        // 这里刻意用**没有作业对象**的后端：否则作业对象会替 Drop 把进程收走，
        // 测到的就不是 Drop 了。
        let managed = ManagedChild::spawn_unmanaged("cmd", &long_running_command(), None)
            .or_else(|_| ManagedChild::spawn_unmanaged("sh", &long_running_command(), None))
            .expect("启动后端");
        let child = managed.child.clone();
        {
            let state = SidecarState::default();
            *state.child.lock().expect("sidecar child mutex poisoned") = Some(managed);
        } // state 在这里被 drop
        assert!(
            wait_until_exited(&child, Duration::from_secs(15)),
            "状态被丢弃后，后端进程必须一起走"
        );
    }

    #[test]
    fn terminate_stops_the_backend() {
        let managed = ManagedChild::spawn_unmanaged("cmd", &long_running_command(), None)
            .or_else(|_| ManagedChild::spawn_unmanaged("sh", &long_running_command(), None))
            .expect("启动后端");
        let child = managed.child.clone();
        let mut managed = managed;
        managed.terminate();
        assert!(
            wait_until_exited(&child, Duration::from_secs(15)),
            "主动清理后，后端进程必须收工"
        );
    }

    #[cfg(windows)]
    #[test]
    fn a_suspended_process_has_not_run_yet() {
        // 挂起创建的意义：子进程在进作业对象之前**一条指令也没执行**。
        // 否则它 fork 出来的后代可能落在作业之外（venv 的 python.exe 就是
        // 转发器，它会再拉起真正的解释器）。
        let marker = std::env::temp_dir().join(format!("dexatlas-suspend-{}.txt", std::process::id()));
        let _ = std::fs::remove_file(&marker);
        let mut child = job::spawn_suspended(&mut backend_command(
            "cmd",
            &["/C".into(), format!("echo hi > {}", marker.display())],
            None,
        ))
        .expect("挂起创建");

        std::thread::sleep(Duration::from_millis(300));
        assert!(
            !marker.exists(),
            "挂起创建的进程在恢复之前不该执行任何指令"
        );

        job::resume_primary_thread(&child).expect("恢复主线程");
        let deadline = Instant::now() + Duration::from_secs(15);
        while !marker.exists() && Instant::now() < deadline {
            std::thread::sleep(Duration::from_millis(50));
        }
        assert!(marker.exists(), "恢复之后进程应当照常执行");
        let _ = std::fs::remove_file(&marker);
    }

    #[cfg(windows)]
    #[test]
    fn closing_the_job_object_terminates_the_process_inside_it() {
        // 回归：宿主被 `taskkill /F` 强杀时 Rust 代码一行也跑不了，收尾只能
        // 靠作业对象——句柄被系统关闭，作业里的进程随之终止。
        let mut child = job::spawn_suspended(&mut backend_command(
            "cmd",
            &long_running_command(),
            None,
        ))
        .expect("挂起创建");
        let job = job::Job::new().expect("作业对象");
        assert!(job.assign(&child), "子进程应当能进作业对象");
        job::resume_primary_thread(&child).expect("恢复主线程");
        assert!(
            child.try_wait().expect("try_wait").is_none(),
            "恢复之后进程应当还活着"
        );

        drop(job);

        let deadline = Instant::now() + Duration::from_secs(15);
        loop {
            if child.try_wait().expect("try_wait").is_some() {
                break;
            }
            assert!(
                Instant::now() < deadline,
                "作业对象的句柄关闭后，作业里的进程必须被终止"
            );
            std::thread::sleep(Duration::from_millis(50));
        }
    }

    #[cfg(windows)]
    #[test]
    fn the_spawned_backend_runs_inside_the_job_object() {
        let managed = ManagedChild::spawn("cmd", &long_running_command(), None).expect("启动后端");
        let guard = managed.child.lock().expect("child mutex poisoned");
        let job = managed.job.as_ref().expect("作业对象");
        assert!(job.contains(&guard), "后端进程必须在作业对象里");
    }

    #[cfg(windows)]
    #[test]
    fn the_grandchild_inherits_the_job_object() {
        // 回归：venv 里的 `python.exe` 是个转发器，它会再拉起真正的解释器。
        // 后端的后代必须继承作业身份——否则强杀宿主时留下的是"孙进程"，
        // 而它才是真正在监听端口的那个。
        let managed = ManagedChild::spawn(
            "cmd",
            &[
                "/C".into(),
                "ping -t 127.0.0.1 > nul & start /B ping -t 127.0.0.1 > nul".into(),
            ],
            None,
        )
        .expect("启动后端");
        let job = managed.job.as_ref().expect("作业对象");

        let deadline = Instant::now() + Duration::from_secs(15);
        loop {
            if job.active_process_count() >= 2 {
                break;
            }
            assert!(
                Instant::now() < deadline,
                "后端自己拉出来的后代也应当继承作业身份（作业里活着的进程数：{}）",
                job.active_process_count()
            );
            std::thread::sleep(Duration::from_millis(50));
        }
    }
}
