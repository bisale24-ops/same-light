"""Does the skin-share guard refuse faces it should not? A diagnostic, not a fairness validation.

    python3 experiments/skin_guard_check.py

Flat colour swatches stand in for faces: the ten Monk Skin Tone Scale colours (published by Google, #f6ede4 to #292420),
a set of colours that are not skin, and the four test faces. Flat swatches have no shadows, highlights, makeup or hair, so
passing here only shows the colour test does not call a skin tone "not skin"; it says nothing about real photos.
"""
import pathlib
import sys

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import samelight as sl  # noqa: E402

MONK = ["#f6ede4", "#f3e7db", "#f7ead0", "#eadaba", "#d7bd96", "#a07e56", "#825c43", "#604134", "#3a312a", "#292420"]
OTHER = [("grey wall", (128, 128, 128)), ("white wall", (240, 240, 235)), ("blue", (30, 60, 200)), ("green", (40, 160, 60)),
         ("red shirt", (190, 30, 40)), ("black hair", (20, 18, 18))]


def row(name, image):
    share = sl.skin_share(image)
    return f"| {name} | {'not applied (dark crop)' if share is None else f'{share:.2f}'} | {sl.light_reading(sl.fingerprint(image))} |"


L = ["# Skin-share guard check", "",
     "Flat swatches, not faces: this checks that the colour test never calls a skin tone 'not skin', not that it works on real photos. Reading = what the app would do with the photo (ok / weak = warning / unreadable = no verdict).", "",
     "| input | skin share of the crop | reading |", "|---|---|---|"]
for i, h in enumerate(MONK, 1):
    c = tuple(int(h[k:k + 2], 16) for k in (1, 3, 5))
    L.append(row(f"Monk {i} {h}", Image.new("RGB", (400, 500), c)))
for n, c in OTHER:
    L.append(row(n, Image.new("RGB", (400, 500), c)))
for f in ("faceA", "faceB", "faceC", "faceD"):
    im = Image.open(HERE / f"{f}.jpg")
    im.thumbnail((800, 800))
    L.append(row(f"{f} (photo)", im))
L += ["", "Known limits: the darkest Monk tones (9 and 10) sit where colour cannot tell skin from dark hair, so the test is not applied there rather than allowed to refuse a face (the API itself refuses frames that are too dark). Bright non-skin colours near the skin hue (beige, wood) would pass as skin; the guard is a loose check, not a face detector."]
(HERE / "SKIN_GUARD_CHECK.md").write_text("\n".join(L) + "\n")
print("\n".join(L))
