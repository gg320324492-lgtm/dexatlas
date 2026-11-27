//! DexAtlas Studio 的 Tauri 后端入口。
//!
//! Phase 5 W1（侧车进程真接入）：应用启动时由 [`sidecar::spawn_sidecar`]
//! 拉起现有 DexAtlas 后端（默认 `python -m dexatlas.workbench --port 0`），
//! 前端通过 `get_sidecar_status` 命令与 `sidecar:status` 事件拿到实际端口；
//! 侧车退出/崩溃时前端收到事件如实呈现。分析能力全部来自现有 Python 核心，
//! 这里不复制分析逻辑，也不新增公共契约。

mod sidecar;

use sidecar::{shutdown_sidecar, spawn_sidecar, SidecarState};

/// 计算两个整数的和。作为前后端命令链路的连通性样例保留。
#[tauri::command]
fn add(a: i64, b: i64) -> i64 {
    a + b
}

/// 返回应用的基本信息，供前端“关于”页使用。
#[tauri::command]
fn app_info() -> serde_json::Value {
    serde_json::json!({
        "name": "DexAtlas Studio",
        "version": env!("CARGO_PKG_VERSION"),
    })
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_http::init())
        .manage(SidecarState::default())
        .invoke_handler(tauri::generate_handler![
            add,
            app_info,
            sidecar::get_sidecar_status,
            sidecar::get_backend_command,
            sidecar::set_backend_command,
            sidecar::restart_sidecar
        ])
        .setup(|app| {
            // 应用启动即拉起侧车；失败不 panic——状态与原因已写入
            // SidecarState，前端会如实显示"未检测到 DexAtlas 后端"。
            spawn_sidecar(app.handle().clone());
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            // 应用退出时结束侧车子进程，避免留下孤儿后端。
            //
            // 这里等的是 `RunEvent::Exit`（"即将退出"），不是
            // `RunEvent::ExitRequested`（"请求退出"，还可以被 veto 掉）——
            // 两者不是一回事，注释里写哪个就得是哪个。另外两层兜底：状态被
            // 丢弃时 `SidecarState::drop` 收尾；宿主被 `taskkill /F` 强杀时
            // 这两层都跑不了，由 Windows 的作业对象接手（见 sidecar.rs）。
            if let tauri::RunEvent::Exit = event {
                shutdown_sidecar(app_handle);
            }
        });
}

#[cfg(test)]
mod tests {
    #[test]
    fn add_works() {
        assert_eq!(super::add(2, 3), 5);
    }

    /// 应用自己报的版本号必须与 `tauri.conf.json` 里的那个一致。
    ///
    /// 设置页「应用版本」显示的就是 `app_info` 返回的值，而 MSI 的
    /// `ProductVersion` 取的是 `tauri.conf.json` 的 `version`——两者是同一个
    /// 数字，读者看到的版本号才是这个安装包的版本号。crate 版本
    /// （`Cargo.toml`）与它的一致性由 `tests/test_desktop_version.py` 断言。
    #[test]
    fn app_version_matches_the_tauri_config() {
        let config: serde_json::Value =
            serde_json::from_str(include_str!("../tauri.conf.json")).expect("tauri.conf.json 读不出来");
        let configured = config["version"]
            .as_str()
            .expect("tauri.conf.json 里没有 version 字段");
        let reported = super::app_info();
        assert_eq!(
            reported["version"].as_str(),
            Some(configured),
            "app_info 报的版本与 tauri.conf.json 不一致"
        );
    }
}
