"""
Argon Book Studio - Application Launcher.
Starts the FastAPI publication server and opens the publishing workspace in the browser.
"""

import sys
import os
import webbrowser
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    
    print("=" * 72)
    print("   ARGON BOOK STUDIO — DRAG-AND-DROP PUBLISHING ENGINE")
    print(f"   Listening on: http://{host}:{port}")
    print("   Universal Typesetting Rules: 6x9\" Mirrored Margins Active")
    print("=" * 72)
    
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
