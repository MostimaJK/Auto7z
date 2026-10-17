#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use std::{io::{BufRead, BufReader, Write}, process::{Child, Command, Stdio}, sync::Mutex};
use tauri::{Emitter, Manager};
struct Backend(Mutex<Child>);

#[tauri::command]
fn send(message: serde_json::Value, state: tauri::State<Backend>) -> Result<(), String> {
    let mut child = state.0.lock().map_err(|e| e.to_string())?;
    let input = child.stdin.as_mut().ok_or("引擎已關閉")?;
    writeln!(input, "{}", message).and_then(|_| input.flush()).map_err(|e| e.to_string())
}
fn main() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            let mut command;
            if cfg!(debug_assertions) {
                let root = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
                let python = root.join(".venv/Scripts/python.exe");
                command = Command::new(if python.exists() { python } else { "python".into() });
                command.arg(root.join("desktop/backend/bridge.py"));
            } else {
                command = Command::new(app.path().resource_dir()?.join("resources/auto7z-engine.exe"));
            }
            command.env("AUTO7Z_CONFIG_DIR", app.path().app_config_dir()?);
            #[cfg(windows)] {
                use std::os::windows::process::CommandExt;
                command.creation_flags(0x08000000);
            }
            let mut child = command.stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped()).spawn()?;
            let stdout = child.stdout.take().unwrap();
            let stderr = child.stderr.take().unwrap();
            let handle = app.handle().clone();
            std::thread::spawn(move || {
                for line in BufReader::new(stdout).lines().map_while(Result::ok) {
                    if let Ok(value) = serde_json::from_str::<serde_json::Value>(&line) { let _ = handle.emit("backend", value); }
                }
                let _ = handle.emit("backend-exit", "背景引擎已退出，請重新啟動應用程式");
            });
            let handle = app.handle().clone();
            std::thread::spawn(move || {
                for line in BufReader::new(stderr).lines().map_while(Result::ok) { let _ = handle.emit("backend-error", line); }
            });
            app.manage(Backend(Mutex::new(child)));
            // Reproducible layout checks without changing the user's display settings.
            if let Ok(value) = std::env::var("AUTO7Z_VERIFY_SIZE") {
                let dims: Vec<f64> = value.split('x').filter_map(|v| v.parse().ok()).collect();
                if dims.len() == 2 && dims[0] >= 640.0 && dims[1] >= 480.0 {
                    if let Some(window) = app.get_webview_window("main") {
                        window.set_size(tauri::LogicalSize::new(dims[0], dims[1]))?;
                    }
                }
            }
            if let Ok(value) = std::env::var("AUTO7Z_VERIFY_ZOOM") {
                if let Ok(zoom) = value.parse::<f64>() {
                    if (1.0..=2.0).contains(&zoom) {
                        if let Some(window) = app.get_webview_window("main") { window.set_zoom(zoom)?; }
                    }
                }
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![send])
        .build(tauri::generate_context!()).expect("無法啟動 Auto7z");
    app.run(|app, event| {
        if let tauri::RunEvent::Exit = event {
            // EOF requests cooperative cancellation; Python waits for its owned child.
            if let Some(state) = app.try_state::<Backend>() {
                if let Ok(mut child) = state.0.lock() {
                    child.stdin.take();
                    for _ in 0..60 {
                        if child.try_wait().ok().flatten().is_some() { return; }
                        std::thread::sleep(std::time::Duration::from_millis(50));
                    }
                    let _ = child.kill(); // backend job closes and kills its descendants on Windows
                    let _ = child.wait();
                }
            }
        }
    });
}
