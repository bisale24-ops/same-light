"""Server logic against a fake YouCam: no network, no units."""
import base64
import io
import pathlib
import sys

import pytest
from PIL import Image, ImageEnhance

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import samelight as sl  # noqa: E402
import server  # noqa: E402


def data_url(image):
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()


@pytest.fixture
def face():
    image = Image.open(ROOT / "experiments" / "faceA.jpg").convert("RGB")
    image.thumbnail((900, 900))
    return image


@pytest.fixture(autouse=True)
def fake_youcam(monkeypatch):
    calls = {"uploads": 0, "analyses": 0, "forgot": 0, "balance": 1000}

    images = {}

    def upload(data, name="x.jpg"):
        calls["uploads"] += 1
        file_id = f"file-{calls['uploads']}"
        images[file_id] = Image.open(io.BytesIO(data)).convert("RGB")
        return file_id

    def analyse(concerns, file_id=None, forget=False, overlay=False, **_):
        calls["analyses"] += 1
        calls["forgot"] += int(forget)
        # Score follows brightness, like the real scanner does: darker photo, "better" pores.
        light = sl.luminance(sl.fingerprint(images[file_id]))
        pore = int(round(120 - light / 3))
        info = {c: {"ui_score": 80, "raw_score": 80.0} for c in concerns}
        info["pore"] = {"ui_score": pore, "raw_score": float(pore)}
        info["all"] = {"score": 80.0}
        info["skin_age"] = 30
        return info, None

    monkeypatch.setattr(server.youcam, "upload", upload)
    monkeypatch.setattr(server.youcam, "analyse", analyse)
    monkeypatch.setattr(server.youcam, "balance", lambda: calls["balance"])
    monkeypatch.setattr(server, "_usage", {})
    monkeypatch.setattr(server, "_balance", {"value": None, "at": 0.0})
    return calls


def test_baseline_scan_returns_scores_and_fingerprint(face, fake_youcam):
    result = server.handle_scan({"image": data_url(face)}, "1.1.1.1")
    assert set(result["scores"]) == set(sl.CONCERNS)
    assert len(result["fingerprint"]["mean"]) == 3
    assert fake_youcam["forgot"] == 1          # the photo is deleted from YouCam after reading


def test_checkin_is_matched_so_a_darker_room_is_not_an_improvement(face, fake_youcam):
    base = server.handle_scan({"image": data_url(face)}, "1.1.1.1")
    darker = ImageEnhance.Brightness(face).enhance(0.8)
    result = server.handle_scan({"image": data_url(darker), "baseline": base}, "1.1.1.1")
    assert result["matched"] is True
    assert "darker" in result["light_words"]
    pore = next(r for r in result["verdict"] if r["concern"] == "pore")
    assert pore["call"] == "noise", pore


def test_unmatched_darker_photo_would_have_fooled_the_scanner(face, fake_youcam):
    base = server.scan(face)
    raw = server.scan(ImageEnhance.Brightness(face).enhance(0.8))
    assert raw["scores"]["pore"] - base["scores"]["pore"] > sl.NOISE_BAND["pore"]


def test_light_too_different_asks_for_a_retake_without_spending(face, fake_youcam):
    base = server.handle_scan({"image": data_url(face)}, "1.1.1.1")
    spent = fake_youcam["analyses"]
    dark = ImageEnhance.Brightness(face).enhance(0.4)
    result = server.handle_scan({"image": data_url(dark), "baseline": base}, "1.1.1.1")
    assert result["retake"] is True
    assert fake_youcam["analyses"] == spent


def test_visitor_cap(face, fake_youcam, monkeypatch):
    monkeypatch.setattr(server, "SCANS_PER_VISITOR", 2)
    for _ in range(2):
        server.handle_scan({"image": data_url(face)}, "2.2.2.2")
    with pytest.raises(server.Refused) as refused:
        server.handle_scan({"image": data_url(face)}, "2.2.2.2")
    assert refused.value.code == "visitor_limit"
    server.handle_scan({"image": data_url(face)}, "3.3.3.3")   # another visitor is fine


def test_budget_floor_stops_live_scans(face, fake_youcam):
    fake_youcam["balance"] = server.UNIT_FLOOR + 5
    with pytest.raises(server.Refused) as refused:
        server.handle_scan({"image": data_url(face)}, "4.4.4.4")
    assert refused.value.code == "budget"
    assert fake_youcam["analyses"] == 0


def test_small_or_broken_photos_are_refused_before_any_call(fake_youcam):
    tiny = Image.new("RGB", (300, 300), (200, 150, 120))
    with pytest.raises(server.Refused):
        server.handle_scan({"image": data_url(tiny)}, "5.5.5.5")
    with pytest.raises(server.Refused):
        server.handle_scan({"image": "data:image/jpeg;base64,bm90IGFuIGltYWdl"}, "5.5.5.5")
    assert fake_youcam["uploads"] == 0


def test_youcam_errors_become_plain_advice(face, fake_youcam, monkeypatch):
    def refuse(*_a, **_k):
        raise RuntimeError("error_src_face_too_small: The face in the input image is too small.")
    monkeypatch.setattr(server.youcam, "analyse", refuse)
    with pytest.raises(server.Refused) as refused:
        server.handle_scan({"image": data_url(face)}, "6.6.6.6")
    assert refused.value.code == "face_too_small"
    assert "closer" in refused.value.message


def test_pair_reports_the_share_the_light_explains(face, fake_youcam):
    before = ImageEnhance.Brightness(face).enhance(1.15)
    after = ImageEnhance.Brightness(face).enhance(0.85)
    result = server.handle_pair({"before": data_url(before), "after": data_url(after)}, "7.7.7.7")
    pore = next(r for r in result["rows"] if r["concern"] == "pore")
    assert pore["claimed"] > sl.NOISE_BAND["pore"]
    assert pore["real"] is False
    assert pore["light_share"] > 0.7
    assert fake_youcam["analyses"] == 3


def test_plain_scan_shows_what_an_unmatched_app_would_claim(face, fake_youcam):
    base = server.handle_scan({"image": data_url(face)}, "8.8.8.8")
    darker = ImageEnhance.Brightness(face).enhance(0.8)
    plain = server.handle_plain({"image": data_url(darker), "baseline": base}, "8.8.8.8")
    pore = next(r for r in plain["verdict"] if r["concern"] == "pore")
    assert pore["call"] == "better"            # the fake improvement a plain scan reports
