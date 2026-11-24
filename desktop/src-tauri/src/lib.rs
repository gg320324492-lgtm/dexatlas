//! DexAtlas Studio 的 Tauri 后端入口。
//!
//! 当前阶段仅提供应用窗口与最小命令面；分析编排、SQLite 工作区访问等
//! 将在后续里程碑中通过 Tauri command / event 接入。

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
        .invoke_handler(tauri::generate_handler![add, app_info])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[cfg(test)]
mod tests {
    #[test]
    fn add_works() {
        assert_eq!(super::add(2, 3), 5);
    }
}
