from __future__ import annotations

import threading
import time
import webbrowser

from ui.server import run_http_server, InterfaceServer
import asyncio


def main() -> None:
    print("Starting INANNA NYX interface...")

    # HTTP server on port 8080
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()

    # Give HTTP server a moment to bind
    time.sleep(0.5)

    # Open browser
    webbrowser.open("http://localhost:8080")
    print("INANNA NYX is running at http://localhost:8080")
    print("WebSocket on ws://localhost:8081")
    print("Press Ctrl+C to stop.")

    # WebSocket server runs on main thread via asyncio
    server = InterfaceServer()
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\nSession closed.")


if __name__ == "__main__":
    main()
