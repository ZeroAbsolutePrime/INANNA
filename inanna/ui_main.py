from __future__ import annotations

import asyncio
import os
import threading
import time
import webbrowser

from ui.server import InterfaceServer, run_http_server


def main() -> None:
    print("Starting INANNA NYX interface...")
    http_port = int(os.getenv("INANNA_HTTP_PORT", "8080"))
    ws_port = int(os.getenv("INANNA_WS_PORT", "8081"))

    t0 = time.monotonic()
    server = InterfaceServer()
    startup_ms = (time.monotonic() - t0) * 1000.0
    http_thread = threading.Thread(target=run_http_server, args=(server,), daemon=True)
    http_thread.start()

    time.sleep(0.5)

    webbrowser.open(f"http://localhost:{http_port}")
    print(f"INANNA NYX ready in {startup_ms:.0f}ms")
    print(f"HTTP: http://localhost:{http_port}")
    print(f"WS:   ws://localhost:{ws_port}")
    print(f"Model: {'connected' if server.engine._connected else 'fallback mode'}")
    print("Press Ctrl+C to stop.")

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\nSession closed.")


if __name__ == "__main__":
    main()
