from ace.domain import Match, Stroke


def test_match_roundtrip_json():
    m = Match(id="x", view="net", video_file="v.mov",
              strokes=[Stroke(t=1.0, frame=30, kind="forehand", defects=["late_prep"])])
    assert Match.model_validate_json(m.model_dump_json()) == m


def test_rallies_none_by_default():
    assert Match(id="x", view="net", video_file="v.mov").rallies is None
