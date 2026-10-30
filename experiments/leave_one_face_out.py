"""Leave-one-face-out: do noise bands fitted on two faces hold on the third?

    python3 experiments/leave_one_face_out.py        (no API units: uses raw.json and calibrate.json)

The shipped bands were set from the largest matched gap seen, which is in-sample. Here the band for each concern is the largest
absolute matched residual on two faces, and it is scored on the held-out face: how many of its 16 matched readings
(4 lights x 4 concerns) fall outside, how big the worst miss is, and the same count for the readings as shot.
"""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
C = ["wrinkle", "pore", "texture", "acne"]
cal = json.loads((HERE / "calibrate.json").read_text())
raw = {(r["face"], r["light"]): r["raw"] for r in json.loads((HERE / "raw.json").read_text())}
faces = sorted({c["face"] for c in cal})
lines = ["# Leave one face out", "",
         "Band per concern = the largest absolute matched residual on the other two faces (the same way the shipped bands were set, without the acne jitter allowance). Scored on the held-out face: 4 lights x 4 concerns = 16 readings. Nothing removed.", "",
         "| held-out face | band (wr/po/tx/ac) | matched readings outside the band | worst miss | readings as shot outside the band |", "|---|---|---|---|---|"]
total_out = total = 0
for held in faces:
    train = [c for c in cal if c["face"] != held]
    band = {x: max(abs(c["residual"][x]) for c in train) for x in C}
    test = [c for c in cal if c["face"] == held]
    out = [(c["light"], x, c["residual"][x]) for c in test for x in C if abs(c["residual"][x]) > band[x]]
    worst = max([abs(v) - band[x] for _, x, v in out], default=0)
    shot_out = sum(abs(raw[(c["face"], c["light"])][x]) > band[x] for c in test for x in C)
    total_out += len(out); total += len(test) * len(C)
    lines.append(f"| {held[-1]} | {'/'.join(str(band[x]) for x in C)} | {len(out)} of {len(test) * len(C)}"
                 + (" (" + ", ".join(f"{l} {x} {v:+d}" for l, x, v in out) + ")" if out else "") + f" | {worst} | {shot_out} |")
lines += ["", f"Across the three folds {total_out} of {total} held-out matched readings fall outside a band fitted on the other two faces. "
          "That is the honest out-of-sample number: a band fitted on two faces is not guaranteed on a third, and with three faces the bands are only a rough guide. "
          "The shipped bands (wrinkle 2, pore 3, texture 2, acne 4) also include the acne jitter allowance, which is why they are a little wider than a pure two-face fit."]
(HERE / "LEAVE_ONE_OUT.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
