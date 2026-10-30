"""Frames from stock clips, cut the same fixed way for every clip, so nobody picks the flattering ones.

    python3 experiments/clip_frames.py OUTDIR ID [ID ...]      # Pexels video ids; downloads each clip (Pexels licence)

For each clip: frames at 10%, 50% and 90% of its length; each frame is cropped by a fixed automatic rule (the biggest
skin-coloured blob in the upper part of the frame, padded 10%, made square) to selfie framing. Writes OUTDIR/k<ID>/baseline.jpg
(10%), light2.jpg (50%) and light3.jpg (90%). Whether a frame is usable is decided by YouCam, not by a person.
"""
import pathlib
import subprocess
import sys
import urllib.request

import numpy as np
from PIL import Image


def crop_to_face(im):
    w, h = im.size
    ycc = np.asarray(im.resize((max(w // 8, 1), max(h // 8, 1))).convert("YCbCr")).astype(int)
    y, cb, cr = ycc[..., 0], ycc[..., 1], ycc[..., 2]
    mask = (y > 40) & (cb >= 77) & (cb <= 127) & (cr >= 133) & (cr <= 173)
    H, W = mask.shape
    mask[int(H * 0.85):] = False
    seen = np.zeros_like(mask)
    best = []
    for sy in range(H):
        for sx in range(W):
            if mask[sy, sx] and not seen[sy, sx]:
                stack, pts = [(sy, sx)], []
                seen[sy, sx] = True
                while stack:
                    a, b = stack.pop()
                    pts.append((a, b))
                    for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        na, nb = a + da, b + db
                        if 0 <= na < H and 0 <= nb < W and mask[na, nb] and not seen[na, nb]:
                            seen[na, nb] = True
                            stack.append((na, nb))
                if len(pts) > len(best):
                    best = pts
    if not best:
        return im
    ys, xs = [p[0] for p in best], [p[1] for p in best]
    cy, cx = int(np.median(ys)), int(np.median(xs))
    side = min(max(int(max(max(ys) - min(ys), max(xs) - min(xs)) * 1.1), 60), min(H, W))
    cx, cy = min(max(cx, side // 2), W - side // 2), min(max(cy, side // 2), H - side // 2)
    return im.crop(((cx - side // 2) * 8, (cy - side // 2) * 8, (cx + side // 2) * 8, (cy + side // 2) * 8))


def main(out, ids):
    out = pathlib.Path(out)
    for vid in ids:
        folder = out / f"k{vid}"
        folder.mkdir(parents=True, exist_ok=True)
        video = out / f"v{vid}.mp4"
        if not video.exists():
            req = urllib.request.Request(f"https://www.pexels.com/download/video/{vid}/", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=180) as r:
                video.write_bytes(r.read())
        duration = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)]))
        for name, pct in (("baseline", 10), ("light2", 50), ("light3", 90)):
            frame = folder / (name + "_raw.jpg")
            subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-ss", str(round(duration * pct / 100, 2)), "-i", str(video),
                                   "-frames:v", "1", "-vf", "scale='min(1600,iw)':-2", str(frame)])
            crop_to_face(Image.open(frame).convert("RGB")).save(folder / (name + ".jpg"), quality=95)
            frame.unlink()
        print("frames", vid, flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
