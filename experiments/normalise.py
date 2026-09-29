"""Does matching the light to the baseline photo remove the fake change?

Take the frames from lighting.py that moved the most, match each one's colour statistics to the
baseline frame (exposure 1.0), scan again, and compare with both the baseline and the raw frame.

    python3 experiments/normalise.py
"""
import io
import json
import pathlib
import sys

from PIL import Image, ImageEnhance, ImageStat

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import youcam  # noqa: E402
from lighting import CONCERNS, jpeg, tint  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent


def match_light(image, reference):
    """Per-channel mean and spread matched to the reference — a crude white balance + exposure."""
    source, target = ImageStat.Stat(image), ImageStat.Stat(reference)
    bands = []
    for band, mean, std, t_mean, t_std in zip(image.split(), source.mean, source.stddev,
                                              target.mean, target.stddev):
        gain = t_std / std if std else 1.0
        bands.append(band.point(lambda v, m=mean, g=gain, tm=t_mean:
                                max(0, min(255, int(round((v - m) * g + tm))))))
    return Image.merge("RGB", bands)


CASES = [
    ("faceA", "cool light", lambda im: tint(im, 0.92, 1.08)),
    ("faceA", "exposure 0.8", lambda im: ImageEnhance.Brightness(im).enhance(0.8)),
    ("faceD", "exposure 1.2", lambda im: ImageEnhance.Brightness(im).enhance(1.2)),
    ("faceA", "warm light", lambda im: tint(im, 1.08, 0.90)),
]


def main():
    sweep = json.loads((HERE / "lighting.json").read_text())
    out = HERE / "normalise.json"
    rows = []
    for face, label, make in CASES:
        base = Image.open(HERE / f"{face}.jpg").convert("RGB")
        base.thumbnail((2000, 2000))
        fixed = match_light(make(base), base)
        file_id = youcam.upload(jpeg(fixed), name=face + ".jpg")
        scores, _ = youcam.analyse(CONCERNS, file_id=file_id)
        after = {c: scores[c]["ui_score"] for c in CONCERNS}
        before = next(r for r in sweep[face] if r["frame"] == label)
        baseline = next(r for r in sweep[face] if r["frame"] == "exposure 1.0")
        row = {"face": face, "frame": label,
               "raw_gap": {c: before[c] - baseline[c] for c in CONCERNS},
               "matched_gap": {c: after[c] - baseline[c] for c in CONCERNS}}
        rows.append(row)
        print(json.dumps(row), flush=True)
    out.write_text(json.dumps(rows, indent=1))
    print("balance now", youcam.balance())


if __name__ == "__main__":
    main()
