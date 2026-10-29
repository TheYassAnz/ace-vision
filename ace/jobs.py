import threading

from ace import store
from ace.pipeline import analyse


class JobRunner:
    """One analysis at a time, on a daemon thread."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self.running_id: str | None = None
        self._stop = threading.Event()

    def start(self, match_id: str) -> bool:
        with self._lock:
            if self.running_id is not None:
                return False
            t = threading.Thread(target=self._run, args=(match_id,), daemon=True)
            self.running_id = match_id  # before start(): _run clears it when done
            self._stop.clear()
            try:
                t.start()
            except Exception:
                self.running_id = None
                raise
            self._thread = t
            return True

    def stop(self, match_id: str) -> bool:
        with self._lock:
            if self.running_id != match_id:
                return False
            self._stop.set()
            return True

    def _run(self, match_id: str) -> None:
        try:
            analyse(match_id, self._stop.is_set)
        finally:
            self.running_id = None


runner = JobRunner()


def recover_interrupted() -> None:
    store.clear_incoming()
    for m in store.list_matches():
        if m.status == "running":
            m.status, m.error = "failed", "Analyse interrompue (l'app a été fermée)."
            store.save(m)
