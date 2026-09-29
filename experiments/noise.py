"""How much does a skin score move when the skin does not change?

Same face, same day: the identical file three times, then small changes a weekly selfie would
really have — brighter room, slightly different framing, a different JPEG encoder, a smaller
photo. Whatever the scores do here is the noise floor; a week-on-week change smaller than it
says nothing about the skin.

    python3 experiments/noise.py photo.jpg     (~9 units per scan)
"""
import io
import json
import pathlib
import sys

from PIL import Image, ImageEnhance

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import youcam  # noqa: E402

CONCERNS = ["wrinkle", "pore", "texture", "acne"]


def jpeg(image, quality=92):
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=quality)
    return buffer.getvalue()


def variants(original):
    width, height = original.size
    yield "same file #1", jpeg(original)
    yield "same file #2", jpeg(original)
    yield "same file #3", jpeg(original)
    yield "brighter +12%", jpeg(ImageEnhance.Brightness(original).enhance(1.12))
    yield "darker -12%", jpeg(ImageEnhance.Brightness(original).enhance(0.88))
    dx, dy = width // 25, height // 25
    yield "reframed 4%", jpeg(original.crop((dx, dy, width, height)))
    yield "jpeg q70", jpeg(original, 70)
    yield "smaller 75%", jpeg(original.resize((width * 3 // 4, height * 3 // 4)))


def main(path):
    original = Image.open(path).convert("RGB")
    start = youcam.balance()
    rows = []
    for label, data in variants(original):
        file_id = youcam.upload(data, name="noise.jpg")
        scores, _ = youcam.analyse(CONCERNS, file_id=file_id)
        row = {"variant": label, "all": scores["all"]["score"], "skin_age": scores.get("skin_age")}
        for concern in CONCERNS:
            row[concern] = scores[concern]["ui_score"]
            row[concern + "_raw"] = round(scores[concern]["raw_score"], 3)
        rows.append(row)
        print(json.dumps(row), flush=True)
    out = pathlib.Path(__file__).with_name("noise-" + pathlib.Path(path).stem + ".json")
    out.write_text(json.dumps({"image": pathlib.Path(path).name, "rows": rows,
                               "units_spent": start - youcam.balance()}, indent=1))
    print("units spent:", start - youcam.balance(), "->", out)


if __name__ == "__main__":
    main(sys.argv[1])
