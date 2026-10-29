import os
import socket
import sys
import threading

os.environ.setdefault("YOLO_OFFLINE", "1")  # before ultralytics loads: no analytics or online checks

import uvicorn

from ace.jobs import recover_interrupted
from ace.web.app import app


def main() -> None:
    if not os.environ.get("ACE_TOKEN"):
        sys.exit(2)
    recover_interrupted()
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))  # local only, free port reported to the app
    print(f"ACE_READY {sock.getsockname()[1]}", flush=True)
    # the app owns this process: when it dies or closes our stdin, stop at once
    threading.Thread(target=lambda: (sys.stdin.read(), os._exit(0)), daemon=True).start()
    uvicorn.Server(uvicorn.Config(app, log_level="warning")).run(sockets=[sock])


if __name__ == "__main__":
    main()
