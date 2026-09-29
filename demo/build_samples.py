"""Record the sample results the site shows without spending API units.

Every number in web/samples.json comes from a real YouCam scan made by this script — nothing is
typed in by hand. Face A (Unsplash License, experiments/SOURCES.md), six scans, ~54 units.

    .venv/bin/python demo/build_samples.py
"""
import base64
import io
import json
import pathlib
import sys

from PIL import Image, ImageEnhance

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import samelight as sl  # noqa: E402
import server  # noqa: E402


def tint(image, red, blue):
    r, g, b = image.split()
    return Image.merge("RGB", (r.point(lambda v: min(255, int(v * red))), g,
                               b.point(lambda v: min(255, int(v * blue)))))


def data_url(image, side=720):
    small = image.copy()
    small.thumbnail((side, side))
    buffer = io.BytesIO()
    small.save(buffer, "JPEG", quality=82)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()


def main():
    face = Image.open(ROOT / "experiments" / "faceA.jpg").convert("RGB")
    face.thumbnail((2000, 2000))

    # Tracker: baseline in daylight, a check-in four weeks later under a cooler bulb.
    baseline = server.scan(face)
    baseline["fingerprint"] = sl.fingerprint(face)
    checkin_photo = tint(face, 0.92, 1.08)
    fp = sl.fingerprint(checkin_photo)
    light = sl.drift(baseline["fingerprint"], fp)
    matched = server.scan(sl.match_light(checkin_photo, baseline["fingerprint"]))
    raw = server.scan(checkin_photo, with_overlays=False)
    checkin = {"fingerprint": fp, "light": light, "light_words": sl.describe(light),
               "matched": True, **matched,
               "verdict": sl.verdict(baseline["scores"], matched["scores"], light)}
    track = {"baseline": {k: baseline[k] for k in ("fingerprint", "scores", "overall",
                                                    "skin_age", "overlays")},
             "checkin": checkin, "checkin_photo": data_url(checkin_photo),
             "raw_scores": raw["scores"],
             "raw_verdict": sl.verdict(baseline["scores"], raw["scores"])}

    # Pair: the classic ad — "before" dim and cool, "after" bright and warm. Same skin.
    # Kept inside the calibrated light gap (samelight.CALIBRATED_*), where a verdict is certified.
    before = tint(ImageEnhance.Brightness(face).enhance(0.92), 0.97, 1.03)
    after = tint(ImageEnhance.Brightness(face).enhance(1.12), 1.04, 0.97)
    before_fp = sl.fingerprint(before)
    first = server.scan(before, with_overlays=False)
    as_shown = server.scan(after, with_overlays=False)
    same = server.scan(sl.match_light(after, before_fp), with_overlays=False)
    rows = []
    for concern in sl.CONCERNS:
        claimed = as_shown["scores"][concern] - first["scores"][concern]
        real = same["scores"][concern] - first["scores"][concern]
        rows.append({"concern": concern, "label": sl.LABELS[concern], "claimed": claimed,
                     "same_light": real, "band": sl.NOISE_BAND[concern],
                     "light_share": sl.light_explains(claimed, real),
                     "real": abs(real) > sl.NOISE_BAND[concern], "uncertain": False})
    pair_light = sl.drift(before_fp, sl.fingerprint(after))
    assert sl.calibrated(pair_light), pair_light
    pair = {"before_photo": data_url(before), "after_photo": data_url(after),
            "result": {"light": pair_light, "calibrated": True,
                       "light_words": sl.describe(pair_light).replace("your baseline",
                                                                      "the before photo"),
                       "rows": rows, "before": first, "after": as_shown,
                       "after_same_light": same}}

    out = ROOT / "web" / "samples.json"
    out.write_text(json.dumps({"track": track, "pair": pair}))
    print(json.dumps({"baseline": baseline["scores"], "checkin_matched": matched["scores"],
                      "checkin_raw": raw["scores"], "pair_rows": rows}, indent=1))
    print(out, out.stat().st_size // 1024, "KB; balance", server.balance(refresh=True))


if __name__ == "__main__":
    main()
