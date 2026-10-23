import uvicorn

from ace.jobs import recover_interrupted
from ace.web.app import app

HOST, PORT = "127.0.0.1", 8765  # local only, never exposed on the network


def main() -> None:
    recover_interrupted()
    uvicorn.run(app, host=HOST, port=PORT)


if __name__ == "__main__":
    main()
