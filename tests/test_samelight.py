import pathlib
import sys

from PIL import Image, ImageEnhance

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import samelight as sl  # noqa: E402

FACE = pathlib.Path(__file__).resolve().parent.parent / "experiments" / "faceA.jpg"


def face():
    image = Image.open(FACE).convert("RGB")
    image.thumbnail((600, 600))
    return image


def tint(image, red, blue):
    r, g, b = image.split()
    return Image.merge("RGB", (r.point(lambda v: min(255, int(v * red))), g,
                               b.point(lambda v: min(255, int(v * blue)))))


def test_same_photo_has_no_drift():
    fp = sl.fingerprint(face())
    assert sl.drift(fp, fp) == {"exposure": 0.0, "warmth": 0.0}
    assert sl.describe(sl.drift(fp, fp)) == "same light as your baseline"


def test_darker_photo_reads_as_darker():
    base = face()
    light = sl.drift(sl.fingerprint(base), sl.fingerprint(ImageEnhance.Brightness(base).enhance(0.8)))
    assert -0.25 < light["exposure"] < -0.15
    assert sl.describe(light).startswith("2")
    assert "darker" in sl.describe(light)


def test_warm_and_cool_have_opposite_signs():
    base = face()
    fp = sl.fingerprint(base)
    assert sl.drift(fp, sl.fingerprint(tint(base, 1.08, 0.9)))["warmth"] > 0.02
    assert sl.drift(fp, sl.fingerprint(tint(base, 0.92, 1.08)))["warmth"] < -0.02


def test_matching_brings_the_light_back():
    base = face()
    fp = sl.fingerprint(base)
    shifted = tint(ImageEnhance.Brightness(base).enhance(0.8), 0.92, 1.08)
    before = sl.drift(fp, sl.fingerprint(shifted))
    after = sl.drift(fp, sl.fingerprint(sl.match_light(shifted, fp)))
    assert abs(after["exposure"]) < 0.02 and abs(after["warmth"]) < 0.01
    assert abs(before["exposure"]) > 10 * abs(after["exposure"])


def test_change_inside_the_band_is_noise():
    rows = sl.verdict({"wrinkle": 84, "pore": 92, "texture": 89, "acne": 98},
                      {"wrinkle": 86, "pore": 89, "texture": 87, "acne": 94})
    assert {r["concern"]: r["call"] for r in rows} == {
        "wrinkle": "noise", "pore": "noise", "texture": "noise", "acne": "noise"}


def test_change_beyond_the_band_counts_both_ways():
    rows = sl.verdict({"wrinkle": 80, "pore": 80, "texture": 80, "acne": 80},
                      {"wrinkle": 83, "pore": 76, "texture": 80, "acne": 85})
    calls = {r["concern"]: r["call"] for r in rows}
    assert calls == {"wrinkle": "better", "pore": "worse", "texture": "noise", "acne": "better"}


def test_light_too_different_means_retake_not_a_verdict():
    rows = sl.verdict({"wrinkle": 80}, {"wrinkle": 90}, light={"exposure": -0.5, "warmth": 0.0})
    assert all(r["call"] == "retake" for r in rows)
    assert all(r["delta"] is None for r in rows)


def test_light_explains_share():
    assert sl.light_explains(-7, 2) == 1.0      # all of it, and then some
    assert sl.light_explains(5, 0) == 1.0
    assert sl.light_explains(-6, -4) == 0.33
    assert sl.light_explains(0, 0) == 0.0
    assert sl.light_explains(4, 4) == 0.0
