from __future__ import annotations

import threading
import time
import webbrowser

from ui.server import start_server


def main() -> None:
    print("Starting INANNA NYX interface...")
    thread = threading.Thread(target=start_server, daemon=True)
    thread.start()
    time.sleep(1.0)
    webbrowser.open("http://localhost:8080")
    print("INANNA NYX is running at http://localhost:8080")
    print("Press Ctrl+C to stop.")
    try:
        thread.join()
    except KeyboardInterrupt:
        print("\nSession closed.")


if __name__ == "__main__":
    main()
