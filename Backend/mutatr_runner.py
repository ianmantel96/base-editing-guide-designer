#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional


ROOT = Path(__file__).resolve().parent
RUNTIME_DIR = ROOT / ".mutatr-runtime"
RUNTIME_DIR.mkdir(exist_ok=True)

APP_HOST = "127.0.0.1"
APP_PORT = 8765
HELPER_HOST = "127.0.0.1"
HELPER_PORT = 8766
HELPER_HEALTH_URL = f"http://{HELPER_HOST}:{HELPER_PORT}/health"

APP_PID = RUNTIME_DIR / "app_server.pid"
HELPER_PID = RUNTIME_DIR / "automation_helper.pid"
APP_PORT_FILE = RUNTIME_DIR / "app_server.port"
APP_LOG = RUNTIME_DIR / "app_server.log"
HELPER_LOG = RUNTIME_DIR / "automation_helper.log"
LIBRARY_FILE = RUNTIME_DIR / "mutatr_library.json"

VENV_PY = ROOT / ".venv-browser" / "bin" / "python"
VENV_DIR = ROOT / ".venv-browser"
REQUIREMENTS_FILE = ROOT / "requirements-browser.txt"
AUTOMATION_SCRIPT = ROOT / "automation_server.py"
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SETUP_LOG = RUNTIME_DIR / "browser_runtime_setup.log"


def read_pid(path: Path) -> Optional[int]:
    try:
        return int(path.read_text().strip())
    except Exception:
        return None


def current_app_port() -> Optional[int]:
    try:
        return int(APP_PORT_FILE.read_text().strip())
    except Exception:
        return None


def write_app_port(port: int) -> None:
    APP_PORT_FILE.write_text(str(port))


def app_url(port: Optional[int] = None) -> str:
    target_port = port or current_app_port()
    return f"http://{APP_HOST}:{target_port}/mutatr.html" if target_port else ""


def app_health_url(port: Optional[int] = None) -> str:
    target_port = port or current_app_port()
    return f"http://{APP_HOST}:{target_port}/health" if target_port else ""


def pid_alive(pid: Optional[int]) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def clear_stale_pid(path: Path) -> None:
    pid = read_pid(path)
    if pid and not pid_alive(pid):
        path.unlink(missing_ok=True)
        if path == APP_PID:
            APP_PORT_FILE.unlink(missing_ok=True)


def write_pid(path: Path, pid: int) -> None:
    path.write_text(str(pid))


def terminate_pid(path: Path) -> bool:
    pid = read_pid(path)
    if not pid:
        path.unlink(missing_ok=True)
        if path == APP_PID:
            APP_PORT_FILE.unlink(missing_ok=True)
        return False
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        path.unlink(missing_ok=True)
        if path == APP_PID:
            APP_PORT_FILE.unlink(missing_ok=True)
        return False
    deadline = time.time() + 5
    while time.time() < deadline:
        if not pid_alive(pid):
            path.unlink(missing_ok=True)
            if path == APP_PID:
                APP_PORT_FILE.unlink(missing_ok=True)
            return True
        time.sleep(0.1)
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass
    path.unlink(missing_ok=True)
    if path == APP_PID:
        APP_PORT_FILE.unlink(missing_ok=True)
    return True


def json_bytes(payload: dict) -> bytes:
    return json.dumps(payload).encode("utf-8")


def load_library() -> list:
    try:
        data = json.loads(LIBRARY_FILE.read_text())
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_library(items: list) -> None:
    LIBRARY_FILE.write_text(json.dumps(items, indent=2))


def get_json(url: str, timeout: float = 2.0) -> Optional[dict]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return None


def wait_for_health(url: str, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        data = get_json(url, timeout=1.5)
        if data and data.get("ok"):
            return True
        time.sleep(0.25)
    return False


def port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def spawn_background(cmd: list[str], pid_path: Path, log_path: Path, cwd: Path) -> int:
    with log_path.open("ab") as log:
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            stdout=log,
            stderr=log,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    write_pid(pid_path, proc.pid)
    return proc.pid


def browser_runtime_ready() -> bool:
    if not VENV_PY.exists():
        return False
    try:
        check = subprocess.run(
            [str(VENV_PY), "-c", "import pyppeteer"],
            cwd=str(ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
            check=False,
        )
        return check.returncode == 0
    except Exception:
        return False


def ensure_browser_runtime() -> None:
    if browser_runtime_ready():
        return
    if not REQUIREMENTS_FILE.exists():
        raise RuntimeError(f"Missing browser-helper requirements at {REQUIREMENTS_FILE}")
    RUNTIME_DIR.mkdir(exist_ok=True)
    with SETUP_LOG.open("ab") as log:
        log.write(b"\nSetting up the MUTATR browser helper...\n")
        create = subprocess.run(
            [sys.executable, "-m", "venv", "--clear", str(VENV_DIR)],
            cwd=str(ROOT),
            stdout=log,
            stderr=log,
            timeout=120,
            check=False,
        )
        if create.returncode != 0 or not VENV_PY.exists():
            raise RuntimeError(f"Could not create the browser-helper environment. See {SETUP_LOG}")
        install = subprocess.run(
            [
                str(VENV_PY),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-input",
                "-r",
                str(REQUIREMENTS_FILE),
            ],
            cwd=str(ROOT),
            stdout=log,
            stderr=log,
            timeout=300,
            check=False,
        )
        if install.returncode != 0 or not browser_runtime_ready():
            raise RuntimeError(f"Could not install the browser-helper requirements. See {SETUP_LOG}")


class MutatrHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self) -> None:
        if self.path == "/health":
            payload = json_bytes({"ok": True, "service": "mutatr-app"})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if self.path == "/runtime/status":
            payload = json_bytes(status_payload())
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if self.path == "/api/library":
            payload = json_bytes({"ok": True, "items": load_library()})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        super().do_GET()

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_POST(self) -> None:
        if self.path not in {"/runtime/start", "/runtime/restart-helper", "/runtime/stop-helper", "/api/library"}:
            self.send_error(404, "not found")
            return
        try:
            if self.path == "/api/library":
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length else b"{}"
                parsed = json.loads(raw.decode("utf-8"))
                items = parsed.get("items", [])
                if not isinstance(items, list):
                    raise ValueError("items must be a list")
                save_library(items)
                payload = {"ok": True, "items": items}
            elif self.path == "/runtime/start":
                ensure_helper()
                payload = {"ok": True, "message": "MUTATR services are ready.", "status": status_payload()}
            elif self.path == "/runtime/restart-helper":
                terminate_pid(HELPER_PID)
                ensure_helper()
                payload = {"ok": True, "message": "Automation helper restarted.", "status": status_payload()}
            else:
                terminate_pid(HELPER_PID)
                payload = {"ok": True, "message": "Automation helper stopped.", "status": status_payload()}
            body = json_bytes(payload)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as error:
            body = json_bytes({"ok": False, "error": str(error), "status": status_payload()})
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)


def run_server(port: int) -> None:
    server = ThreadingHTTPServer((APP_HOST, port), MutatrHandler)
    print(f"MUTATR app server running on http://{APP_HOST}:{port}", flush=True)
    server.serve_forever()


def ensure_helper() -> None:
    clear_stale_pid(HELPER_PID)
    if get_json(HELPER_HEALTH_URL):
        return
    ensure_browser_runtime()
    if not AUTOMATION_SCRIPT.exists():
        raise RuntimeError(f"Missing automation helper at {AUTOMATION_SCRIPT}")
    spawn_background([str(VENV_PY), str(AUTOMATION_SCRIPT)], HELPER_PID, HELPER_LOG, ROOT)
    if not wait_for_health(HELPER_HEALTH_URL, timeout=20):
        raise RuntimeError("Automation helper failed to start.")


def ensure_app_server() -> None:
    clear_stale_pid(APP_PID)
    existing_port = current_app_port()
    if existing_port and get_json(app_health_url(existing_port)):
        return
    port = APP_PORT
    while port_in_use(APP_HOST, port):
        port += 1
    write_app_port(port)
    spawn_background([sys.executable, str(ROOT / "mutatr_runner.py"), "serve", "--port", str(port)], APP_PID, APP_LOG, ROOT)
    if not wait_for_health(app_health_url(port), timeout=10):
        raise RuntimeError("App server failed to start.")


def open_app_window() -> None:
    url = app_url()
    if not url:
        raise RuntimeError("App server URL is unavailable.")
    if Path(CHROME_PATH).exists():
        subprocess.Popen(
            [CHROME_PATH, f"--app={url}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    else:
        webbrowser.open(url)


def status_payload() -> dict:
    clear_stale_pid(APP_PID)
    clear_stale_pid(HELPER_PID)
    port = current_app_port()
    app_pid = read_pid(APP_PID)
    helper_pid = read_pid(HELPER_PID)
    app_health = get_json(app_health_url(port)) if port else None
    helper_health = get_json(HELPER_HEALTH_URL)
    return {
        "ok": bool(app_health and helper_health),
        "app": {
            "pid": app_pid,
            "pid_alive": pid_alive(app_pid),
            "health": bool(app_health),
            "url": app_url(port) if port else "",
            "port": port,
        },
        "automation": {
            "pid": helper_pid,
            "pid_alive": pid_alive(helper_pid),
            "health": bool(helper_health),
            "url": HELPER_HEALTH_URL,
        },
        "browser_runtime": {
            "ready": browser_runtime_ready(),
            "python": str(VENV_PY),
        },
    }


def cmd_start(open_window: bool) -> None:
    ensure_helper()
    ensure_app_server()
    if open_window:
        open_app_window()
    print(json.dumps(status_payload(), indent=2))


def cmd_stop() -> None:
    terminate_pid(APP_PID)
    terminate_pid(HELPER_PID)
    print(json.dumps(status_payload(), indent=2))


def cmd_status() -> None:
    print(json.dumps(status_payload(), indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MUTATR local app services.")
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("start")
    start.add_argument("--no-open", action="store_true")
    sub.add_parser("stop")
    sub.add_parser("status")
    serve = sub.add_parser("serve")
    serve.add_argument("--port", type=int, required=True)
    args = parser.parse_args()

    if args.command == "serve":
        run_server(args.port)
        return
    if args.command == "start":
        cmd_start(open_window=not args.no_open)
        return
    if args.command == "stop":
        cmd_stop()
        return
    if args.command == "status":
        cmd_status()
        return


if __name__ == "__main__":
    main()
