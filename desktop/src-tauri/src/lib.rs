use std::mem;
use std::os::windows::io::AsRawHandle;
use std::os::windows::process::CommandExt;
use std::path::PathBuf;
use std::ptr;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Manager, WindowEvent,
};
use uuid::Uuid;
use windows_sys::Win32::Foundation::{CloseHandle, HANDLE};
use windows_sys::Win32::System::JobObjects::{
    AssignProcessToJobObject, CreateJobObjectW, SetInformationJobObject,
    JobObjectExtendedLimitInformation, JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
};

// ============================================================================
// 1. Win32 Job Object Supervisor (Guarantees zero-orphan process lifecycle)
// ============================================================================

pub struct JobObjectGuard {
    handle: HANDLE,
}

impl JobObjectGuard {
    pub fn new() -> Option<Self> {
        unsafe {
            let handle = CreateJobObjectW(ptr::null(), ptr::null());
            if handle.is_null() {
                return None;
            }
            let mut info: JOBOBJECT_EXTENDED_LIMIT_INFORMATION = mem::zeroed();
            info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
            let ok = SetInformationJobObject(
                handle,
                JobObjectExtendedLimitInformation,
                &info as *const _ as *const _,
                mem::size_of::<JOBOBJECT_EXTENDED_LIMIT_INFORMATION>() as u32,
            );
            if ok == 0 {
                CloseHandle(handle);
                return None;
            }
            Some(Self { handle })
        }
    }

    pub fn assign_process(&self, process: &std::process::Child) -> bool {
        unsafe {
            let proc_handle = process.as_raw_handle() as HANDLE;
            let ok = AssignProcessToJobObject(self.handle, proc_handle);
            ok != 0
        }
    }
}

impl Drop for JobObjectGuard {
    fn drop(&mut self) {
        unsafe {
            if !self.handle.is_null() {
                CloseHandle(self.handle);
            }
        }
    }
}

unsafe impl Send for JobObjectGuard {}
unsafe impl Sync for JobObjectGuard {}

// ============================================================================
// 2. Application State & IPC Payloads
// ============================================================================

#[derive(Clone, serde::Serialize, serde::Deserialize)]
pub struct BackendConfig {
    pub port: u16,
    pub token: String,
}

pub struct BackendState {
    pub config: Mutex<BackendConfig>,
    pub _job_guard: Option<Arc<JobObjectGuard>>,
    pub _child: Mutex<Option<std::process::Child>>,
}

#[tauri::command]
fn get_backend_config(state: tauri::State<BackendState>) -> BackendConfig {
    state.config.lock().unwrap().clone()
}

// ============================================================================
// 3. Helpers: Port Selection & Backend Spawning
// ============================================================================

fn find_available_port() -> u16 {
    // Try preferred port 8765 first
    if let Ok(listener) = std::net::TcpListener::bind("127.0.0.1:8765") {
        drop(listener);
        return 8765;
    }
    // Bind to 0 for ephemeral port allocation
    std::net::TcpListener::bind("127.0.0.1:0")
        .and_then(|l| l.local_addr())
        .map(|a| a.port())
        .unwrap_or(8765)
}

fn spawn_backend(port: u16, token: &str, job_guard: &JobObjectGuard) -> Option<std::process::Child> {
    const CREATE_NO_WINDOW: u32 = 0x08000000;

    let exe_dir = std::env::current_exe().ok().and_then(|p| p.parent().map(|p| p.to_path_buf()));
    let sidecar_candidates = [
        exe_dir.as_ref().map(|d| d.join("reeta-backend.exe")),
        exe_dir.as_ref().map(|d| d.join("reeta-backend-x86_64-pc-windows-msvc.exe")),
        exe_dir.as_ref().map(|d| d.join("reeta-backend").join("reeta-backend.exe")),
        exe_dir.as_ref().map(|d| d.join("resources").join("binaries").join("reeta-backend").join("reeta-backend.exe")),
        exe_dir.as_ref().map(|d| d.join("resources").join("reeta-backend").join("reeta-backend.exe")),
        exe_dir.as_ref().map(|d| d.join("resources").join("reeta-backend.exe")),
        exe_dir.as_ref().map(|d| d.join("binaries").join("reeta-backend").join("reeta-backend.exe")),
        exe_dir.as_ref().map(|d| d.join("binaries").join("reeta-backend.exe")),
        Some(PathBuf::from("desktop/src-tauri/binaries/reeta-backend/reeta-backend.exe")),
        Some(PathBuf::from("src-tauri/binaries/reeta-backend/reeta-backend.exe")),
        Some(PathBuf::from("binaries/reeta-backend/reeta-backend.exe")),
        Some(PathBuf::from("backend/dist/reeta-backend/reeta-backend.exe")),
    ];

    // 1. Production sidecar check
    for candidate in sidecar_candidates.iter().flatten() {
        if candidate.exists() {
            log::info!("Spawning standalone frozen backend sidecar: {:?}", candidate);
            let mut cmd = std::process::Command::new(candidate);
            cmd.creation_flags(CREATE_NO_WINDOW);
            cmd.env("PORT", port.to_string());
            cmd.env("REETA_LAUNCH_TOKEN", token);
            cmd.env("REETA_STANDALONE", "1");
            cmd.env("USE_SQLITE", "1");
            if let Ok(child) = cmd.spawn() {
                job_guard.assign_process(&child);
                return Some(child);
            }
        }
    }

    // 2. Development mode fallback: local venv Python
    let venv_python_candidates = [
        PathBuf::from("backend/venv/Scripts/python.exe"),
        PathBuf::from("../backend/venv/Scripts/python.exe"),
        PathBuf::from("E:/PROJECTS/reeta — responsive executive engine for tasks and automation/backend/venv/Scripts/python.exe"),
    ];

    for py in &venv_python_candidates {
        if py.exists() {
            log::info!("Spawning development backend using virtualenv Python: {:?}", py);
            let mut cmd = std::process::Command::new(py);
            cmd.creation_flags(CREATE_NO_WINDOW);
            cmd.arg("-m");
            cmd.arg("app.main");

            if let Some(backend_dir) = py.parent().and_then(|p| p.parent()) {
                cmd.current_dir(backend_dir);
            }

            cmd.env("PORT", port.to_string());
            cmd.env("REETA_LAUNCH_TOKEN", token);
            cmd.env("REETA_STANDALONE", "1");
            cmd.env("USE_SQLITE", "1");
            if let Ok(child) = cmd.spawn() {
                job_guard.assign_process(&child);
                return Some(child);
            }
        }
    }

    log::warn!("Could not find frozen sidecar or virtualenv Python to launch backend.");
    None
}

// ============================================================================
// 4. Tauri Application Run Entrypoint
// ============================================================================

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let port = find_available_port();
    let token = format!("{:x}{:x}", Uuid::new_v4().as_u128(), Uuid::new_v4().as_u128());

    // Initialize Win32 Job Object supervisor
    let job_guard = JobObjectGuard::new().map(Arc::new);
    let child_process = if let Some(guard) = &job_guard {
        spawn_backend(port, &token, guard)
    } else {
        None
    };

    let backend_state = BackendState {
        config: Mutex::new(BackendConfig {
            port,
            token: token.clone(),
        }),
        _job_guard: job_guard,
        _child: Mutex::new(child_process),
    };

    // Wait for backend health probe in background
    let probe_port = port;
    thread::spawn(move || {
        let probe_url = format!("http://127.0.0.1:{}/api/v1/system/health", probe_port);
        let mut healthy = false;
        for _ in 0..60 {
            if let Ok(stream) = std::net::TcpStream::connect(format!("127.0.0.1:{}", probe_port)) {
                drop(stream);
                healthy = true;
                break;
            }
            thread::sleep(Duration::from_millis(250));
        }
        if healthy {
            log::info!("Backend health verified at {}", probe_url);
        } else {
            log::warn!("Backend health probe timed out after 15 seconds.");
        }
    });

    tauri::Builder::default()
        .manage(backend_state)
        .invoke_handler(tauri::generate_handler![get_backend_config])
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            // System Tray Menu
            let show_item = MenuItem::with_id(app, "show", "Show REETA", true, None::<&str>)?;
            let hide_item = MenuItem::with_id(app, "hide", "Hide to Tray", true, None::<&str>)?;
            let quit_item = MenuItem::with_id(app, "quit", "Quit REETA", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show_item, &hide_item, &quit_item])?;

            let _tray = TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .tooltip("REETA — Autonomous Personal AI Operating System")
                .menu(&menu)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "show" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                    "hide" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.hide();
                        }
                    }
                    "quit" => {
                        app.exit(0);
                    }
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        let app = tray.app_handle();
                        if let Some(window) = app.get_webview_window("main") {
                            if window.is_visible().unwrap_or(false) {
                                let _ = window.hide();
                            } else {
                                let _ = window.show();
                                let _ = window.set_focus();
                            }
                        }
                    }
                })
                .build(app)?;

            // Window close interception -> hide to tray
            if let Some(window) = app.get_webview_window("main") {
                let win_clone = window.clone();
                window.on_window_event(move |event| {
                    if let WindowEvent::CloseRequested { api, .. } = event {
                        api.prevent_close();
                        let _ = win_clone.hide();
                    }
                });
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running REETA desktop application");
}
