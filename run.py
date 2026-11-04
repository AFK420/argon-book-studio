"""
Argon Book Studio Pro - Application Launcher.
Starts the FastAPI publication server and automatically opens
the publishing workspace in your default web browser.
"""

import sys
import os
import time
import threading
import webbrowser
import subprocess
import urllib.request
import shutil
import socket
import uvicorn

def is_port_free(port: int, host: str = "127.0.0.1") -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return True
    except OSError:
        return False

def find_available_port(preferred_port: int = 8000, host: str = "127.0.0.1") -> int:
    if is_port_free(preferred_port, host):
        return preferred_port
    
    candidate_ports = [8000, 8080, 8081, 8082, 8083, 8084, 8085, 8088, 8090, 8888]
    for p in candidate_ports:
        if is_port_free(p, host):
            return p
            
    for p in range(8001, 8150):
        if is_port_free(p, host):
            return p
            
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]

def is_ollama_running(url: str = "http://127.0.0.1:11434") -> bool:
    try:
        with urllib.request.urlopen(f"{url}/api/tags", timeout=1.5) as r:
            return r.status == 200
    except Exception:
        return False

def ensure_ollama_server() -> bool:
    if is_ollama_running():
        print("[*] Local AI Engine: Ollama is running and ready on port 11434.")
        return True
    
    print("[*] Local AI Engine: Launching Ollama background daemon...")
    ollama_exe = shutil.which("ollama") or r"C:\Users\albre\AppData\Local\Programs\Ollama\ollama.exe"
    if not os.path.exists(ollama_exe) and not shutil.which("ollama"):
        print("[!] Notice: ollama executable not found in PATH; skipping auto-launch.")
        return False
        
    try:
        creationflags = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW
        subprocess.Popen(
            [ollama_exe, "serve"],
            creationflags=creationflags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        t0 = time.time()
        while time.time() - t0 < 8:
            if is_ollama_running():
                print(f"[OK] Ollama server started in background ({time.time() - t0:.1f}s).")
                return True
            time.sleep(0.5)
        print("[*] Ollama server launched in background.")
        return True
    except Exception as e:
        print(f"[!] Notice: Could not auto-launch Ollama ({e}).")
        return False

def open_browser(url: str):
    time.sleep(1.2)
    try:
        webbrowser.open(url)
    except Exception:
        pass

if __name__ == "__main__":
    requested_port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    port = find_available_port(preferred_port=requested_port, host=host)
    if port != requested_port:
        print(f"[!] Notice: Port {requested_port} is already in use.")
        print(f"[*] Automatically selected next available port: {port}")
    url = f"http://{host}:{port}"
    
    print("=" * 74)
    print("   ARGON BOOK STUDIO PRO -- DESKTOP TYPESETTING AND PUBLISHING ENGINE")
    print(f"   Server Address: {url}")
    print("   Live Geometry Inspector: Active (6x9, 5.5x8.5, Custom)")
    print("   Opening browser studio workspace...")
    print("   Press CTRL+C anytime to stop the server.")
    print("=" * 74)
    
    # Auto-ensure Ollama daemon is active
    ensure_ollama_server()

    # Auto-open browser in background thread
    threading.Thread(target=open_browser, args=(url,), daemon=True).start()
    
    print(f"[*] Studio server is live at {url}")
    print("[*] Waiting for incoming requests...\n")
    uvicorn.run("app.main:app", host=host, port=port, reload=False, log_level="info")
