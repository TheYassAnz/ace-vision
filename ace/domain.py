from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

StrokeKind = Literal["forehand", "backhand", "serve", "other"]
View = Literal["net", "rear"]
Status = Literal["pending", "running", "done", "failed"]
DefectId = Literal["late_prep", "small_turn", "straight_legs", "narrow_stance"]
Outcome = Literal["net", "long", "wide", "in", "unknown"]
RallyEnd = Literal["net", "long", "wide", "not_returned", "unknown"]

STROKE_LABELS: dict[StrokeKind, str] = {
    "forehand": "Coup droit",
    "backhand": "Revers",
    "serve": "Service",
    "other": "Autre",
}


class Settings(BaseModel):
    handedness: Literal["right", "left"] = "right"
    backhand_hands: Literal[1, 2] = 2


class VideoInfo(BaseModel):
    width: int  # already rotation-corrected
    height: int
    fps: float
    duration_s: float
    n_frames: int
    rotation: int
    created: str | None


class Stroke(BaseModel):
    model_config = ConfigDict(ser_json_inf_nan="constants")  # unmeasurable metrics are NaN; JSON null would not reload
    t: float
    frame: int
    kind: StrokeKind
    metrics: dict[str, float] = Field(default_factory=dict)
    defects: list[DefectId] = Field(default_factory=list)
    outcome: Outcome = "unknown"


class Rally(BaseModel):
    start_t: float
    end_t: float
    n_hits: int
    end: RallyEnd
    last_stroke: StrokeKind | None
    user_hit_last: bool
    is_serve_fault: bool = False


class Finding(BaseModel):
    kind: StrokeKind
    defect: DefectId
    count: int
    total: int
    title: str
    text: str
    drill: str
    clip_times: list[float]


class Score(BaseModel):
    n_notes: int
    n_detected: int
    found_rate: float
    class_rate: float
    false_hits: int


class Match(BaseModel):
    id: str
    title: str = ""
    view: View
    status: Status = "pending"
    progress: float = 0.0
    error: str | None = None
    video_file: str
    info: VideoInfo | None = None
    settings: Settings = Field(default_factory=Settings)
    strokes: list[Stroke] = Field(default_factory=list)
    rallies: list[Rally] | None = None
    findings: list[Finding] = Field(default_factory=list)
    score: Score | None = None
    coverage: float | None = None  # share of frames where the player's hips were found
    n_unmeasured: int = 0  # forehands/backhands/serves without any usable metric
