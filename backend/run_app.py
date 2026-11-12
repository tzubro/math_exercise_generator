import socket
import threading
import time
import webbrowser

import uvicorn

from backend.app.main import app


def _available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def main() -> None:
    port = _available_port()
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            log_level="info",
        )
    )
    thread = threading.Thread(target=server.run, name="math-test-api", daemon=True)
    thread.start()

    url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 30
    while thread.is_alive() and time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                webbrowser.open(url)
                print(f"Math Test Generator is running at {url}")
                print("Keep this window open while using the app. Press Ctrl+C to stop.")
                thread.join()
                return
        except OSError:
            time.sleep(0.2)

    server.should_exit = True
    thread.join(timeout=5)
    raise RuntimeError("The local server did not start within 30 seconds.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nMath Test Generator stopped.")
