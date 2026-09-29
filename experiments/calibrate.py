"""How much does a score still move after matching, as the light gap grows?

The first noise bands came from gaps of about 20% exposure. A live before/after pair with a 29%
gap plus a warm shift left pores +6 after matching — beyond the ±3 band, so Same Light called a
change "real" on skin that had not changed. This measures the residual across larger gaps so the
band can grow with the gap instead of pretending matching is perfect.

    python3 experiments/calibrate.py      (3 faces × 4 lights, ~108 units)
"""
import json
import pathlib
import sys

from PIL import Image, ImageEnhance

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import samelight as sl  # noqa: E402
import youcam  # noqa: E402
from lighting import jpeg, tint  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
LIGHTS = [("0.85 warm", 0.85, (1.07, 0.92)), ("1.2 cool", 1.2, (0.93, 1.07)),
          ("1.25 warm", 1.25, (1.07, 0.92)), ("0.8 cool", 0.8, (0.93, 1.07))]


def main():
    base_scores = json.loads((HERE / "lighting.json").read_text())
    out = HERE / "calibrate.json"
    rows = json.loads(out.read_text()) if out.exists() else []
    done = {(r["face"], r["light"]) for r in rows}
    for face in ("faceA", "faceC", "faceD"):
        image = Image.open(HERE / f"{face}.jpg").convert("RGB")
        image.thumbnail((2000, 2000))
        fp = sl.fingerprint(image)
        base = next(r for r in base_scores[face] if r["frame"] == "exposure 1.0")
        for label, exposure, (red, blue) in LIGHTS:
            if (face, label) in done:
                continue
            shifted = tint(ImageEnhance.Brightness(image).enhance(exposure), red, blue)
            gap = sl.drift(fp, sl.fingerprint(shifted))
            matched = sl.match_light(shifted, fp)
            try:
                scores, _ = youcam.analyse(sl.CONCERNS, file_id=youcam.upload(jpeg(matched)),
                                           forget=True)
            except RuntimeError as error:
                print(face, label, "ERROR", error)
                continue
            row = {"face": face, "light": label, "gap": gap,
                   "residual": {c: scores[c]["ui_score"] - base[c] for c in sl.CONCERNS}}
            rows.append(row)
            out.write_text(json.dumps(rows, indent=1))
            print(json.dumps(row), flush=True)
    print("balance", youcam.balance())


if __name__ == "__main__":
    main()
