import json
from collections import Counter, defaultdict
from pathlib import Path

from ace.domain import DefectId, Finding, Stroke

MIN_COUNT, MIN_SHARE, MAX_FINDINGS = 5, 0.4, 3


def load_advice() -> dict[DefectId, dict[str, str]]:
    return json.loads((Path(__file__).parent / "advice.fr.json").read_text(encoding="utf-8"))


def build_findings(strokes: list[Stroke], advice: dict) -> list[Finding]:
    totals = Counter(s.kind for s in strokes)
    hits: dict[tuple, list[float]] = defaultdict(list)
    for s in sorted(strokes, key=lambda s: s.t):
        for d in s.defects:
            hits[(s.kind, d)].append(s.t)
    eligible = [(k, d, ts) for (k, d), ts in hits.items() if len(ts) >= MIN_COUNT and len(ts) / totals[k] >= MIN_SHARE]
    eligible.sort(key=lambda e: -len(e[2]))
    return [Finding(kind=k, defect=d, count=len(ts), total=totals[k], clip_times=ts[:5], **advice[d])
            for k, d, ts in eligible[:MAX_FINDINGS]]
