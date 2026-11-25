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
}
