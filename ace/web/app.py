import hmac
import logging
import os
from pathlib import Path
from typing import Annotated, Literal

import numpy as np
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from ace import store
from ace.domain import Match, Settings, View
from ace.jobs import runner
from ace.notes import Note, score_detection

log = logging.getLogger(__name__)
app = FastAPI()
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])  # DNS rebinding


@app.middleware("http")
async def token_only(request: Request, call_next):  # the app passes a random token per launch; no other local process knows it
    sent = request.headers.get("authorization", "")
    if not hmac.compare_digest(sent.encode(), f"Bearer {os.environ.get('ACE_TOKEN', '')}".encode()) or not os.environ.get("ACE_TOKEN"):
        return JSONResponse({"detail": "Jeton manquant ou invalide."}, status_code=401)
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, exc: RequestValidationError):  # default body echoes the input, which breaks on NaN
    return JSONResponse({"detail": "Requête invalide."}, status_code=422)


class ImportBody(BaseModel):
    path: str
    view: View
    title: str = ""


def get_match(id: str) -> Match:
    try:
        return store.load(id)
    except (ValueError, FileNotFoundError):  # invalid id or no such match
        raise HTTPException(404, "Match introuvable.")


def live_status(m: Match) -> str:
    """The runner is the truth for "running": match.json lags at start and can stay stuck after a failed save."""
    if runner.running_id == m.id:
        return "running"
    return "failed" if m.status == "running" else m.status


def summary(m: Match) -> dict:
    return {"id": m.id, "title": m.title, "view": m.view, "status": live_status(m), "progress": m.progress, "error": m.error,
            "created": m.info.created if m.info else None, "duration_s": m.info.duration_s if m.info else None,
            "score": m.score.model_dump() if m.score else None, "defect_rates": store.defect_rates(m)}


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/matchs")
def history():
    return [summary(m) for m in store.list_matches()]


@app.post("/matchs", status_code=201)
def create(body: ImportBody):
    try:
        with open(body.path, "rb") as f:
            m = store.create_match(f, Path(body.path).name, body.view, body.title.strip())
    except (FileNotFoundError, IsADirectoryError):
        return JSONResponse({"detail": "Fichier introuvable."}, status_code=422)
    except store.UserError as e:
        return JSONResponse({"detail": str(e)}, status_code=422)
    except Exception:  # probe/ffprobe failure on a corrupt or non-video file; never show raw English text
        log.exception("import of %r failed", body.path)
        return JSONResponse({"detail": "Ce fichier n'est pas une vidéo lisible."}, status_code=422)
    return {"match": summary(m), "queued": not runner.start(m.id)}


@app.get("/matchs/{id}")
def match_detail(id: str):
    m = get_match(id)
    status = live_status(m)
    if status == "failed" and m.status == "running":
        m.error = "Analyse interrompue."
    m.status = status
    return m.model_dump(mode="json", exclude={"strokes": {"__all__": {"metrics"}}})


@app.post("/matchs/{id}/relancer")
def relaunch(id: str):
    return {"queued": not runner.start(get_match(id).id)}


@app.post("/matchs/{id}/arreter", status_code=202)
def stop(id: str):
    if not runner.stop(get_match(id).id):
        return JSONResponse({"detail": "Aucune analyse en cours pour ce match."}, status_code=409)
    return Response(status_code=202)


@app.delete("/matchs/{id}", status_code=204)
def delete(id: str):
    get_match(id)
    try:
        if runner.running_id == id:
            raise store.UserError("Ce match est en cours d'analyse.")
        store.delete_match(id)
    except store.UserError as e:
        return JSONResponse({"detail": str(e)}, status_code=409)
    return Response(status_code=204)


@app.get("/matchs/{id}/pose")
def pose(id: str):
    get_match(id)
    path = store.pose_path(id)
    if not path.exists():
        raise HTTPException(404, "Squelette indisponible : relance l'analyse.")
    with np.load(path) as z:
        body = z["kp"][:, :, :2].astype("<f4").tobytes()
    return Response(content=body, media_type="application/octet-stream")


@app.get("/matchs/{id}/notes")
def notes_list(id: str):
    get_match(id)
    return store.load_notes(id) or []


@app.post("/matchs/{id}/notes")
def notes_save(id: str, notes: Annotated[list[Note], Field(min_length=1, max_length=5000)]):
    m = get_match(id)
    if m.status == "running":
        return JSONResponse({"detail": "Une analyse est en cours : réessaie quand elle est terminée."}, status_code=409)
    limit = m.info.duration_s if m.info else 86400
    if any(n.t > limit for n in notes):
        return JSONResponse({"detail": "Une note dépasse la durée de la vidéo."}, status_code=422)
    store.save_notes(id, notes)
    m.score = score_detection(m.strokes, notes)
    store.save(m)
    return m.score


@app.get("/reglages")
def settings_get():
    return store.load_settings()


@app.put("/reglages")
def settings_put(s: Settings):
    store.save_settings(s)
    return s
