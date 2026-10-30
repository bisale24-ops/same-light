"""Real-camera feasibility test: one person, one phone, three real lights, skin unchanged. Publish every result.

Take the photos (same phone, same pose, no filters, no beauty mode, no retakes of the ones you dislike):
    real_camera/set1/baseline.jpg   the light you normally take check-ins in (a window, daylight)
    real_camera/set1/light2.jpg     a clearly different real light (a warm lamp in the evening)
    real_camera/set1/light3.jpg     a third (a cool overhead or a phone torch from the side)
and, later, the same again as real_camera/set2/ without picking the best ones.

    python3 experiments/real_camera.py real_camera/set1 real_camera/set2     # scans: 5 per set, 9 units each
    python3 experiments/real_camera.py --no-scan real_camera/set1             # light reading only, spends nothing

Writes real_camera/RESULTS.md: per concern the score gap against the baseline as shot and after Same Light matches the light,
the total gap, the guard reading and the verdict each rule would give. Nothing is dropped.
"""
import io
import json
import pathlib
import sys

from PIL import Image, ImageOps

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import samelight as sl  # noqa: E402

NAMES = ("baseline", "light2", "light3")


def load(path):
    image = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    image.thumbnail((2000, 2000))
    return image


def jpeg(image):
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=92)
    return buffer.getvalue()


def scan(image):
    import youcam
    scores, _ = youcam.analyse(sl.CONCERNS, file_id=youcam.upload(jpeg(image)), forget=True)
    return {c: scores[c]["ui_score"] for c in sl.CONCERNS}


def run(folder, scanning):
    folder = pathlib.Path(folder)
    images = {n: load(next(folder.glob(n + ".*"))) for n in NAMES}
    base_fp = sl.fingerprint(images["baseline"])
    out = [f"## {folder.name}", "", f"Baseline light reading: {sl.light_reading(base_fp)}.", "",
           "| light | drift from baseline | reading | comparable | calibrated | scores as shot (wr/po/tx/ac) | gap as shot | gap matched | total gap as shot -> matched | verdict as shot | verdict matched |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    base_scores = scan(images["baseline"]) if scanning else None
    for name in NAMES[1:]:
        fp = sl.fingerprint(images[name])
        light = sl.drift(base_fp, fp)
        row = [name, sl.describe(light), sl.light_reading(base_fp, fp), str(sl.comparable(light)), str(sl.calibrated(light))]
        if scanning and sl.comparable(light):
            shot = scan(images[name])
            matched = scan(sl.match_light(images[name], base_fp))
            gs = {c: shot[c] - base_scores[c] for c in sl.CONCERNS}
            gm = {c: matched[c] - base_scores[c] for c in sl.CONCERNS}
            f = lambda d: "/".join(f"{d[c]:+d}" for c in sl.CONCERNS)
            vs = {r["concern"]: r["call"] for r in sl.verdict(base_scores, shot)}
            vm = {r["concern"]: r["call"] for r in sl.verdict(base_scores, matched, light)}
            row += ["/".join(str(shot[c]) for c in sl.CONCERNS), f(gs), f(gm),
                    f"{sum(abs(v) for v in gs.values())} -> {sum(abs(v) for v in gm.values())}",
                    ", ".join(f"{c}:{v}" for c, v in vs.items()), ", ".join(f"{c}:{v}" for c, v in vm.items())]
        else:
            row += ["not scanned" if not scanning else "retake: light too different"] + [""] * 5
        out.append("| " + " | ".join(row) + " |")
    return out


def main(args):
    scanning = "--no-scan" not in args
    folders = [a for a in args if not a.startswith("--")]
    lines = ["# Real-camera feasibility test", "",
             "One person, one phone, real lights, skin unchanged. Every photo is listed; none was dropped or retaken. "
             "A feasibility test on one person, not a validation: it says nothing about other skin, cameras or rooms.", ""]
    for folder in folders:
        lines += run(folder, scanning) + [""]
    (ROOT / "real_camera").mkdir(exist_ok=True)
    (ROOT / "real_camera" / "RESULTS.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1:])
