import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

import requests


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_HOST = "127.0.0.1"
API_PORT = "8001"


def read_env_value(name: str, default: str = "") -> str:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return default

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        if key.strip() == name:
            return value.strip().strip("'\"")

    return default


def can_run_uvicorn(python_exe: str) -> bool:
    try:
        result = subprocess.run(
            [python_exe, "-c", "import uvicorn"],
            cwd=BASE_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False

    return result.returncode == 0


def find_api_python() -> str | None:
    candidates = [
        sys.executable,
        str(BASE_DIR / "venv" / "Scripts" / "python.exe"),
    ]

    path_python = shutil.which("python")
    if path_python:
        candidates.append(path_python)

    py_launcher = shutil.which("py")
    if py_launcher:
        candidates.append(py_launcher)

    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)

        if can_run_uvicorn(candidate):
            return candidate

    return None


class WhatsAppApiGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Local WhatsApp API")
        self.geometry("760x620")
        self.minsize(760, 600)

        self.process: subprocess.Popen[str] | None = None
        self.log_queue: queue.Queue[str] = queue.Queue()

        self.host_var = tk.StringVar(value=DEFAULT_HOST)
        self.api_key_var = tk.StringVar(value=read_env_value("API_KEY"))
        self.masked_api_key_var = tk.StringVar(value=self._masked_api_key())
        self.number_var = tk.StringVar()
        self.status_var = tk.StringVar(value="API stopped")
        self.endpoint_var = tk.StringVar(value=f"http://{DEFAULT_HOST}:{API_PORT}")

        self._build_ui()
        self.after(150, self._drain_log_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    @property
    def base_url(self) -> str:
        return f"http://{DEFAULT_HOST}:{API_PORT}"

    def _build_ui(self) -> None:
        self.configure(bg="#eef3f0")

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("App.TFrame", background="#eef3f0")
        style.configure("Panel.TFrame", background="#ffffff", relief="flat")
        style.configure("Muted.TLabel", background="#ffffff", foreground="#63736d")
        style.configure("Title.TLabel", background="#eef3f0", foreground="#17201c", font=("Segoe UI", 18, "bold"))
        style.configure("PanelTitle.TLabel", background="#ffffff", foreground="#17201c", font=("Segoe UI", 11, "bold"))
        style.configure("Status.TLabel", background="#ffffff", foreground="#118c5b", font=("Segoe UI", 10, "bold"))
        style.configure("Primary.TButton", background="#118c5b", foreground="#ffffff", padding=(14, 8))
        style.configure("Secondary.TButton", background="#24342e", foreground="#ffffff", padding=(12, 8))
        style.map("Primary.TButton", background=[("active", "#0d744b")])
        style.map("Secondary.TButton", background=[("active", "#17201c")])

        root = ttk.Frame(self, padding=18, style="App.TFrame")
        root.pack(fill=tk.BOTH, expand=True)

        ttk.Label(root, text="WhatsApp Sender", style="Title.TLabel").pack(anchor="w")

        body = ttk.Frame(root, style="App.TFrame")
        body.pack(fill=tk.BOTH, expand=True, pady=(14, 0))
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        server = ttk.Frame(body, padding=16, style="Panel.TFrame")
        server.grid(row=0, column=0, sticky="ns", padx=(0, 14))

        ttk.Label(server, text="Server", style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Label(server, textvariable=self.status_var, style="Status.TLabel").pack(anchor="w", pady=(4, 14))

        ttk.Label(server, text="Endpoint", style="Muted.TLabel").pack(anchor="w")
        ttk.Label(server, textvariable=self.endpoint_var, background="#ffffff").pack(anchor="w", pady=(2, 14))

        ttk.Label(server, text="API Key", style="Muted.TLabel").pack(anchor="w")
        ttk.Label(server, textvariable=self.masked_api_key_var, background="#ffffff").pack(anchor="w", pady=(2, 8))
        ttk.Button(server, text="Show API Key", command=self.show_api_key).pack(fill=tk.X, pady=(0, 16))

        self.start_button = ttk.Button(server, text="Start API", style="Primary.TButton", command=self.start_api)
        self.start_button.pack(fill=tk.X)

        self.stop_button = ttk.Button(server, text="Stop API", style="Secondary.TButton", command=self.stop_api)
        self.stop_button.pack(fill=tk.X, pady=(8, 0))

        self.status_button = ttk.Button(server, text="Check Status", command=self.check_status)
        self.status_button.pack(fill=tk.X, pady=(8, 0))

        self.web_button = ttk.Button(server, text="Open Web UI", command=self.open_web_ui)
        self.web_button.pack(fill=tk.X, pady=(8, 0))

        sender = ttk.Frame(body, padding=16, style="Panel.TFrame")
        sender.grid(row=0, column=1, sticky="nsew")
        sender.columnconfigure(0, weight=1)
        sender.rowconfigure(7, weight=1)

        ttk.Label(sender, text="Send Message", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")

        ttk.Label(sender, text="Phone Number", style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(14, 0))
        ttk.Entry(sender, textvariable=self.number_var).grid(row=2, column=0, sticky="ew", pady=(4, 10))

        ttk.Label(sender, text="Message", style="Muted.TLabel").grid(row=3, column=0, sticky="w")
        self.message_text = tk.Text(sender, height=5, wrap=tk.WORD)
        self.message_text.grid(row=4, column=0, sticky="ew", pady=(4, 10))

        self.send_button = ttk.Button(sender, text="Send Message", style="Primary.TButton", command=self.send_message)
        self.send_button.grid(
            row=5,
            column=0,
            sticky="ne",
        )

        ttk.Label(sender, text="Activity", style="PanelTitle.TLabel").grid(row=6, column=0, sticky="w", pady=(14, 0))
        self.log_text = scrolledtext.ScrolledText(
            sender,
            height=13,
            state=tk.DISABLED,
            wrap=tk.WORD,
            borderwidth=1,
            relief=tk.SOLID,
        )
        self.log_text.grid(row=7, column=0, sticky="nsew", pady=(6, 0))
        self._set_controls_for_running(False)

    def start_api(self) -> None:
        if self.process and self.process.poll() is None:
            self._append_log("API is already running.")
            return

        api_python = find_api_python()
        if not api_python:
            messagebox.showerror(
                "Missing uvicorn",
                "Could not find a Python installation with uvicorn installed. "
                "Run: python -m pip install -r requirements.txt",
            )
            return

        command = [
            api_python,
            "-m",
            "uvicorn",
            "whatsapp_api.main:app",
            "--host",
            DEFAULT_HOST,
            "--port",
            API_PORT,
        ]

        env = os.environ.copy()
        env["PYTHONPATH"] = str(BASE_DIR)

        try:
            self.process = subprocess.Popen(
                command,
                cwd=BASE_DIR,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            messagebox.showerror("Could not start API", str(exc))
            return

        self.status_var.set("Starting API...")
        self._set_controls_for_starting()
        self._append_log("Starting WhatsApp API on port 8001...")
        self._append_log(f"Using Python: {api_python}")
        threading.Thread(target=self._read_process_output, daemon=True).start()
        threading.Thread(target=self._wait_for_startup, daemon=True).start()

    def stop_api(self) -> None:
        if not self.process or self.process.poll() is not None:
            self.status_var.set("API stopped")
            self._append_log("API is not running.")
            return

        self._append_log("Stopping API...")
        self.process.terminate()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self._append_log("API did not stop in time; forcing shutdown.")
            self.process.kill()
            self.process.wait(timeout=5)

        self.status_var.set("API stopped")
        self._set_controls_for_running(False)
        self._append_log("API stopped.")

    def open_web_ui(self) -> None:
        webbrowser.open(self.base_url)

    def show_api_key(self) -> None:
        api_key = self.api_key_var.get().strip()
        if not api_key:
            messagebox.showwarning("API Key", "No API key is set in .env.")
            return

        messagebox.showinfo("Current API Key", api_key)

    def check_status(self) -> None:
        self._run_request("Checking WhatsApp login status...", self._check_status_request)

    def send_message(self) -> None:
        number = self.number_var.get().strip()
        message = self.message_text.get("1.0", tk.END).strip()

        if not number:
            messagebox.showerror("Missing phone number", "Enter a WhatsApp phone number.")
            return

        if not message:
            messagebox.showerror("Missing message", "Enter a message to send.")
            return

        self._run_request("Sending message...", lambda: self._send_message_request(number, message))

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key_var.get().strip()}",
            "Content-Type": "application/json",
        }

    def _masked_api_key(self) -> str:
        api_key = self.api_key_var.get().strip()
        if not api_key:
            return "Not set"

        if len(api_key) <= 4:
            return "*" * len(api_key)

        return f"{api_key[:2]}{'*' * max(len(api_key) - 4, 4)}{api_key[-2:]}"

    def _check_status_request(self) -> str:
        response = requests.get(f"{self.base_url}/status", headers=self._headers(), timeout=20)
        return self._format_response(response)

    def _send_message_request(self, number: str, message: str) -> str:
        response = requests.post(
            f"{self.base_url}/send-message",
            headers=self._headers(),
            json={"number": number, "message": message},
            timeout=90,
        )
        return self._format_response(response)

    def _run_request(self, label: str, task) -> None:
        self._append_log(label)
        threading.Thread(target=self._request_worker, args=(task,), daemon=True).start()

    def _request_worker(self, task) -> None:
        try:
            result = task()
        except requests.RequestException as exc:
            result = f"Request failed: {exc}"
        except Exception as exc:
            result = f"Unexpected error: {exc}"

        self.log_queue.put(result)

    def _wait_for_startup(self) -> None:
        for _ in range(45):
            if not self.process or self.process.poll() is not None:
                self.log_queue.put("API process exited during startup.")
                self._set_status("API stopped")
                self._set_controls_for_running(False)
                return

            try:
                requests.get(f"{self.base_url}/status", headers=self._headers(), timeout=2)
                self.log_queue.put("API is running. Scan the WhatsApp QR code if prompted.")
                self._set_status("API running")
                self._set_controls_for_running(True)
                return
            except requests.RequestException:
                time.sleep(1)

        self.log_queue.put("API did not respond within 45 seconds. Check the logs above.")
        self._set_status("Startup timeout")
        self._set_controls_for_running(False)

    def _read_process_output(self) -> None:
        if not self.process or not self.process.stdout:
            return

        for line in self.process.stdout:
            clean_line = self._simplify_process_log(line.rstrip())
            if clean_line:
                self.log_queue.put(clean_line)

    def _simplify_process_log(self, line: str) -> str | None:
        if not line:
            return None

        if "Uvicorn running on" in line:
            return "API server is listening on port 8001."

        if "Application startup complete" in line:
            return "API startup completed."

        if "Started server process" in line:
            return None

        if "INFO:" in line and 'GET /status' in line:
            return None

        if "INFO:" in line and 'POST /send-message' in line:
            return "Send request received by API."

        if "WhatsApp Web opened" in line:
            return "WhatsApp Web opened. Scan the QR code if needed."

        if "Starting WhatsApp browser session" in line:
            return "Opening WhatsApp Web browser session..."

        if "Stopping WhatsApp browser session" in line:
            return "Closing WhatsApp Web browser session..."

        return line

    def _format_response(self, response: requests.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            body = {}

        if response.status_code == 401:
            return "API key is wrong. Check the API key from your .env file."

        if response.status_code >= 400:
            detail = body.get("detail") if isinstance(body, dict) else None
            if isinstance(detail, dict):
                return detail.get("error", f"Request failed with status {response.status_code}.")
            return f"Request failed with status {response.status_code}."

        if isinstance(body, dict):
            if body.get("success") is True:
                return body.get("message", "Done.")

            if body.get("success") is False:
                return body.get("error", "Request failed.")

            if body.get("logged_in") is True:
                return "WhatsApp is logged in and ready."

            if body.get("logged_in") is False:
                return body.get("message", "WhatsApp is not logged in. Scan the QR code.")

        return response.text.strip() or "Done."

    def _drain_log_queue(self) -> None:
        self._refresh_process_state()

        while True:
            try:
                line = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self._append_log(line)

        self.after(150, self._drain_log_queue)

    def _refresh_process_state(self) -> None:
        if self.process and self.process.poll() is not None and self.status_var.get() != "API stopped":
            self.status_var.set("API stopped")
            self._set_controls_for_running(False)

    def _append_log(self, text: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{text}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _set_status(self, text: str) -> None:
        self.after(0, self.status_var.set, text)

    def _set_button_state(self, button: ttk.Button, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED
        self.after(0, button.configure, {"state": state})

    def _set_controls_for_starting(self) -> None:
        self._set_button_state(self.start_button, False)
        self._set_button_state(self.stop_button, True)
        self._set_button_state(self.status_button, False)
        self._set_button_state(self.web_button, False)
        self._set_button_state(self.send_button, False)

    def _set_controls_for_running(self, running: bool) -> None:
        self._set_button_state(self.start_button, not running)
        self._set_button_state(self.stop_button, running)
        self._set_button_state(self.status_button, running)
        self._set_button_state(self.web_button, running)
        self._set_button_state(self.send_button, running)

    def _on_close(self) -> None:
        if self.process and self.process.poll() is None:
            if not messagebox.askyesno("Quit", "Stop the API and close the app?"):
                return
            self.stop_api()

        self.destroy()


if __name__ == "__main__":
    app = WhatsAppApiGui()
    app.mainloop()
