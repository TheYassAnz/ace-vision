import os
import socket
import sys
import threading

os.environ.setdefault("YOLO_OFFLINE", "1")  # before ultralytics loads: no analytics or online checks

import uvicorn

from ace.jobs import recover_interrupted
from ace.web.app import app


def announce(port: int) -> None:
    print(f"ACE_READY {port}", flush=True)
    # nobody reads stdout after this line: a full pipe would block the next print (ultralytics logs)
    os.dup2(2, 1)


def main() -> None:
    if not os.environ.get("ACE_TOKEN"):
        sys.exit(2)
    recover_interrupted()
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))  # local only, free port reported to the app
    announce(sock.getsockname()[1])
    # the app owns this process: when it dies or closes our stdin, stop at once
    threading.Thread(target=lambda: (sys.stdin.read(), os._exit(0)), daemon=True).start()
    uvicorn.Server(uvicorn.Config(app, log_level="warning")).run(sockets=[sock])


if __name__ == "__main__":
    main()
