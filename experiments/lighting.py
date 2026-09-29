"""The lighting sweep: how far do skin scores move when only the light changes?

Each face is scanned at five exposures and two colour temperatures. The skin is identical in every
frame, so any score change is the light, not the skincare.

    python3 experiments/lighting.py faceA.jpg faceB.jpg ...     (~9 units per scan, 7 per face)
"""
import io
import json
import pathlib
import sys

from PIL import Image, ImageEnhance

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import youcam  # noqa: E402

CONCERNS = ["wrinkle", "pore", "texture", "acne"]
EXPOSURES = [0.8, 0.9, 1.0, 1.1, 1.2]


def jpeg(image):
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=92)
    return buffer.getvalue()


def tint(image, red, blue):
    r, g, b = image.split()
    return Image.merge("RGB", (r.point(lambda v: min(255, int(v * red))), g,
                               b.point(lambda v: min(255, int(v * blue)))))


def frames(image):
    for exposure in EXPOSURES:
        yield f"exposure {exposure:.1f}", ImageEnhance.Brightness(image).enhance(exposure)
    yield "warm light", tint(image, 1.08, 0.90)
    yield "cool light", tint(image, 0.92, 1.08)


def main(paths):
    out = pathlib.Path(__file__).with_name("lighting.json")
    done = json.loads(out.read_text()) if out.exists() else {}
    for path in paths:
        name = pathlib.Path(path).stem
        if name in done:
            continue
        image = Image.open(path).convert("RGB")
        if max(image.size) > 2000:
            image.thumbnail((2000, 2000))
        rows = []
        for label, frame in frames(image):
            file_id = youcam.upload(jpeg(frame), name=name + ".jpg")
            try:
                scores, _ = youcam.analyse(CONCERNS, file_id=file_id)
            except RuntimeError as error:
                rows.append({"frame": label, "error": str(error)})
                print(name, label, "ERROR", error, flush=True)
                continue
            row = {"frame": label, "all": scores["all"]["score"], "skin_age": scores.get("skin_age")}
            row.update({c: scores[c]["ui_score"] for c in CONCERNS})
            rows.append(row)
            print(name, json.dumps(row), flush=True)
        done[name] = rows
        out.write_text(json.dumps(done, indent=1))
    print("balance now", youcam.balance())


if __name__ == "__main__":
    main(sys.argv[1:])
