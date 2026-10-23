from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ace import store
from ace.domain import STROKE_LABELS, Match, Settings
from ace.jobs import runner

HERE = Path(__file__).parent
app = FastAPI()
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
templates = Jinja2Templates(directory=HERE / "templates")
VIEW_LABELS = {"net": "Vue filet", "rear": "Vue arrière"}
STATUS_LABELS = {"pending": "Pas encore analysé", "running": "En cours", "done": "Terminé", "failed": "Échec"}
QUEUED_MSG = "Une analyse est déjà en cours. Celle-ci démarrera quand tu cliqueras sur Relancer."


def render(request: Request, name: str, **ctx):
    return templates.TemplateResponse(request, name, {"view_labels": VIEW_LABELS, "stroke_labels": STROKE_LABELS, **ctx})


def get_match(id: str) -> Match:
    try:
        return store.load(id)
    except (ValueError, OSError):  # invalid id or no such match
        raise HTTPException(404, "Match introuvable.")


def see(id: str) -> RedirectResponse:
    return RedirectResponse(f"/matchs/{id}", status_code=303)


@app.get("/")
def history(request: Request):
    return render(request, "history.html", matches=store.list_matches(), status_labels=STATUS_LABELS)


@app.get("/ajouter")
def add_form(request: Request, error: str | None = None):
    return render(request, "add.html", error=error)


@app.post("/matchs")
def create(request: Request, video: UploadFile = File(...), view: Literal["net", "rear"] = Form(...), title: str = Form("")):
    try:
        m = store.create_match(video.file, video.filename or "", view, title.strip())
    except ValueError as e:
        return render(request, "add.html", error=str(e))
    if not runner.start(m.id):
        return RedirectResponse(f"/matchs/{m.id}?attente=1", status_code=303)
    return see(m.id)


@app.get("/matchs/{id}")
def match_page(request: Request, id: str, attente: int = 0):
    m = get_match(id)
    # Single status dispatch: Task 10 swaps the "done" template.
    page = {"running": "match_running.html", "done": "match_done.html"}.get(m.status, "match_failed.html")
    return render(request, page, m=m, queued_msg=QUEUED_MSG if attente else None)


@app.get("/matchs/{id}/statut")
def status(id: str):
    m = get_match(id)
    return JSONResponse({"status": m.status, "progress": m.progress, "error": m.error})


@app.post("/matchs/{id}/relancer")
def relaunch(id: str):
    m = get_match(id)
    runner.start(m.id)
    return see(m.id)


@app.get("/matchs/{id}/video")
def video(id: str):
    m = get_match(id)
    path = store.match_dir(id) / m.video_file
    if not path.is_file():
        raise HTTPException(404, "Vidéo introuvable.")
    # Starlette's FileResponse answers Range requests with 206 (needed by Safari).
    return FileResponse(path, media_type="video/quicktime" if path.suffix.lower() == ".mov" else "video/mp4")


@app.get("/reglages")
def settings_form(request: Request, saved: int = 0):
    return render(request, "settings.html", s=store.load_settings(), saved=saved)


@app.post("/reglages")
def settings_save(handedness: Literal["right", "left"] = Form(...), backhand_hands: Literal["1", "2"] = Form(...)):
    store.save_settings(Settings(handedness=handedness, backhand_hands=int(backhand_hands)))
    return RedirectResponse("/reglages?saved=1", status_code=303)
