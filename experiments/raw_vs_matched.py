"""The missing half of calibrate.json: the same 12 light changes scanned WITHOUT matching.

calibrate.json holds the score gap left after matching (residual). This scans the same shifted photos as they come,
so every case has both numbers and the table shows where matching helped, where it did nothing and where it hurt.

    python3 experiments/raw_vs_matched.py      (3 faces x 4 lights, ~108 units)
"""
import json
import pathlib
import sys

from PIL import Image, ImageEnhance

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import samelight as sl  # noqa: E402
import youcam  # noqa: E402
from lighting import jpeg, tint  # noqa: E402
from calibrate import LIGHTS  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent


def main():
    base_scores = json.loads((HERE / "lighting.json").read_text())
    out = HERE / "raw.json"
    rows = json.loads(out.read_text()) if out.exists() else []
    done = {(r["face"], r["light"]) for r in rows}
    for face in ("faceA", "faceC", "faceD"):
        image = Image.open(HERE / f"{face}.jpg").convert("RGB")
        image.thumbnail((2000, 2000))
        base = next(r for r in base_scores[face] if r["frame"] == "exposure 1.0")
        for label, exposure, (red, blue) in LIGHTS:
            if (face, label) in done:
                continue
            shifted = tint(ImageEnhance.Brightness(image).enhance(exposure), red, blue)
            try:
                scores, _ = youcam.analyse(sl.CONCERNS, file_id=youcam.upload(jpeg(shifted)), forget=True)
            except RuntimeError as error:
                print(face, label, "ERROR", error)
                continue
            row = {"face": face, "light": label,
                   "raw": {c: scores[c]["ui_score"] - base[c] for c in sl.CONCERNS}}
            rows.append(row)
            out.write_text(json.dumps(rows, indent=1))
            print(json.dumps(row), flush=True)
    print("balance", youcam.balance())


if __name__ == "__main__":
    main()
