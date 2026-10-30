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
import uvicorn

def open_browser(url: str):
    time.sleep(1.2)
    try:
        webbrowser.open(url)
    except Exception:
        pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    url = f"http://{host}:{port}"
    
    print("=" * 74)
    print("   ARGON BOOK STUDIO PRO -- DESKTOP TYPESETTING AND PUBLISHING ENGINE")
    print(f"   Server Address: {url}")
    print("   Live Geometry Inspector: Active (6x9, 5.5x8.5, Custom)")
    print("   Opening browser studio workspace...")
    print("   Press CTRL+C anytime to stop the server.")
    print("=" * 74)
    
    # Auto-open browser in background thread
    threading.Thread(target=open_browser, args=(url,), daemon=True).start()
    
    uvicorn.run("app.main:app", host=host, port=port, reload=False, log_level="warning")
