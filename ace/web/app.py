from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from pydantic import Field
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ace import store
from ace.domain import STROKE_LABELS, Match, Settings
from ace.jobs import runner
from ace.notes import Note, score_detection

HERE = Path(__file__).parent
app = FastAPI()
ORIGINS = ("http://127.0.0.1:8765", "http://localhost:8765")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])  # DNS rebinding


@app.middleware("http")
async def same_origin_only(request: Request, call_next):  # CSRF: browsers always send Origin/Referer on cross-site POSTs
    if request.method not in ("GET", "HEAD"):
        src = request.headers.get("origin") or request.headers.get("referer") or ""
        if not any(src == o or src.startswith(o + "/") for o in ORIGINS):
            return JSONResponse({"detail": "Origine refusée."}, status_code=403)
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, exc: RequestValidationError):  # default body echoes the input, which breaks on NaN
    return JSONResponse({"detail": "Requête invalide."}, status_code=422)


app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
templates = Jinja2Templates(directory=HERE / "templates")
VIEW_LABELS = {"net": "Vue filet", "rear": "Vue arrière"}
STATUS_LABELS = {"pending": "Pas encore analysé", "running": "En cours", "done": "Terminé", "failed": "Échec"}
QUEUED_MSG = "Une analyse est déjà en cours. Celle-ci démarrera quand tu cliqueras sur Relancer."


PLURALS = {"forehand": "coups droits", "backhand": "revers", "serve": "services", "other": "autres"}
SINGULARS = {"forehand": "coup droit", "backhand": "revers", "serve": "service", "other": "autre"}
DEFECT_LABELS = {"late_prep": "Préparation tardive", "small_turn": "Épaules peu tournées",
                 "straight_legs": "Jambes tendues", "narrow_stance": "Appuis serrés"}


def of_total(count: int, total: int, kind: str) -> str:
    return f"{count} {(SINGULARS if count < 2 else PLURALS)[kind]} sur {total}"


def rally_summary(m: Match) -> dict | None:
    if m.view != "rear" or m.rallies is None:
        return None
    long = [r.n_hits for r in m.rallies if r.n_hits >= 2]  # a lone hit is not an exchange length
    return {"n": len(m.rallies), "mean": f"{sum(long) / len(long):.1f}".replace(".", ",") if long else "—", "max": max(long, default="—")}


def render(request: Request, name: str, **ctx):
    return templates.TemplateResponse(request, name, {"view_labels": VIEW_LABELS, "stroke_labels": STROKE_LABELS, **ctx})


def get_match(id: str) -> Match:
    try:
        return store.load(id)
    except (ValueError, FileNotFoundError):  # invalid id or no such match
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
    except Exception:  # probe/ffprobe failure on a corrupt or non-video file
        return render(request, "add.html", error="Ce fichier n'est pas une vidéo lisible.")
    if not runner.start(m.id):
        return RedirectResponse(f"/matchs/{m.id}?attente=1", status_code=303)
    return see(m.id)


@app.get("/matchs/{id}")
def match_page(request: Request, id: str, attente: int = 0):
    m = get_match(id)
    page = {"running": "match_running.html", "done": "match_report.html"}.get(m.status, "match_failed.html")
    counts = {k: sum(s.kind == k for s in m.strokes) for k in STROKE_LABELS}
    return render(request, page, m=m, queued_msg=QUEUED_MSG if attente else None, counts=counts,
                  rallies=rally_summary(m), of_total=of_total, defect_labels=DEFECT_LABELS)


@app.get("/matchs/{id}/statut")
def status(id: str):
    m = get_match(id)
    return JSONResponse({"status": m.status, "progress": m.progress, "error": m.error})


@app.post("/matchs/{id}/relancer")
def relaunch(id: str):
    m = get_match(id)
    if not runner.start(m.id):
        return RedirectResponse(f"/matchs/{m.id}?attente=1", status_code=303)
    return see(m.id)


@app.get("/matchs/{id}/video")
def video(id: str):
    m = get_match(id)
    path = store.match_dir(id) / m.video_file
    if not path.is_file():
        raise HTTPException(404, "Vidéo introuvable.")
    # Starlette's FileResponse answers Range requests with 206 (needed by Safari).
    return FileResponse(path, media_type="video/quicktime" if path.suffix.lower() == ".mov" else "video/mp4")


@app.get("/matchs/{id}/noter")
def notes_form(request: Request, id: str):
    return render(request, "notes.html", m=get_match(id))


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
def settings_form(request: Request, saved: int = 0):
    return render(request, "settings.html", s=store.load_settings(), saved=saved)


@app.post("/reglages")
def settings_save(handedness: Literal["right", "left"] = Form(...), backhand_hands: Literal["1", "2"] = Form(...)):
    store.save_settings(Settings(handedness=handedness, backhand_hands=int(backhand_hands)))
    return RedirectResponse("/reglages?saved=1", status_code=303)
