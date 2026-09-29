"""Same Light web server: static app + three JSON endpoints. Standard library + Pillow.

    POST /api/scan   {image, baseline?}   one photo -> scores, light fingerprint, verdict vs baseline
    POST /api/pair   {before, after}      a before/after pair -> how much of the change was the light
    GET  /api/status                      whether live scans are available right now

The YouCam key never leaves the server. Photos are held in memory only, and each YouCam task is
deleted (with its uploaded photo) as soon as its scores are read.
"""
import base64
import io
import json
import os
import pathlib
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from PIL import Image, ImageOps

import samelight as sl
import youcam

ROOT = pathlib.Path(__file__).resolve().parent
WEB = ROOT / "web"
MAX_BODY = 12 * 1024 * 1024
UNIT_FLOOR = int(os.environ.get("UNIT_FLOOR", "150"))        # keep this many units in reserve
SCANS_PER_VISITOR = int(os.environ.get("SCANS_PER_VISITOR", "6"))  # per address per day
MAX_SIDE = 2000

_lock = threading.Lock()
_usage = {}          # (day, address) -> scans
_balance = {"value": None, "at": 0.0}


class Refused(Exception):
    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


FRIENDLY = {
    "error_src_face_too_small": ("face_too_small",
                                 "Move closer — your face needs to fill most of the frame."),
    "error_lighting_dark": ("too_dark", "Too dark to read skin. Face a window or a lamp."),
    "error_no_face": ("no_face", "No face found. Look straight at the camera."),
    "error_large_face_angle": ("angle", "Turn to face the camera straight on."),
    "error_multiple_people": ("many_faces", "Only one face in the photo, please."),
}


def balance(refresh=False):
    if refresh or _balance["value"] is None or time.time() - _balance["at"] > 60:
        _balance["value"], _balance["at"] = youcam.balance(), time.time()
    return _balance["value"]


def spend(address, scans):
    day = time.strftime("%Y-%m-%d")
    with _lock:
        used = _usage.get((day, address), 0)
        if used + scans > SCANS_PER_VISITOR:
            raise Refused("visitor_limit", "This demo allows a few live scans per visitor per "
                          "day. The sample faces below work without limits.", 429)
        if balance() - 9 * scans < UNIT_FLOOR:
            raise Refused("budget", "Live scans are paused to protect the API budget. The sample "
                          "faces below show real results.", 503)
        _usage[(day, address)] = used + scans


def decode(data_url):
    try:
        raw = base64.b64decode(data_url.split(",", 1)[-1])
        image = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    except Exception:
        raise Refused("bad_image", "That file is not a photo we can read.")
    if min(image.size) < 480:
        raise Refused("too_small", "The photo is too small — it needs at least 480 pixels on "
                      "its short side.")
    image.thumbnail((MAX_SIDE, MAX_SIDE))
    return image


def jpeg(image, quality=92):
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=quality)
    return buffer.getvalue()


def overlays(raw_zip):
    """The per-concern mask overlays from the result zip, shrunk to data URLs for the UI."""
    found = {}
    if not raw_zip:
        return found
    with zipfile.ZipFile(io.BytesIO(raw_zip)) as archive:
        for name in archive.namelist():
            stem = pathlib.Path(name).stem
            concern = stem.replace("_output", "")
            if concern in sl.CONCERNS:
                image = Image.open(io.BytesIO(archive.read(name))).convert("RGB")
                image.thumbnail((520, 520))
                found[concern] = "data:image/jpeg;base64," + base64.b64encode(
                    jpeg(image, 80)).decode()
    return found


def scan(image, with_overlays=True):
    file_id = youcam.upload(jpeg(image), name="samelight.jpg")
    try:
        info, raw = youcam.analyse(sl.CONCERNS, file_id=file_id, forget=True,
                                   overlay=with_overlays)
    except RuntimeError as error:
        code = str(error).split(":", 1)[0]
        friendly = FRIENDLY.get(code)
        if friendly:
            raise Refused(friendly[0], friendly[1], 422)
        raise Refused("scan_failed", "The skin scan failed on this photo. Try another one.", 502)
    scores = {c: info[c]["ui_score"] for c in sl.CONCERNS if c in info}
    return {"scores": scores, "overall": info.get("all", {}).get("score"),
            "skin_age": info.get("skin_age"),
            "overlays": overlays(raw) if with_overlays else {}}


def handle_scan(body, address):
    image = decode(body.get("image") or "")
    measured = sl.fingerprint(image)
    baseline = body.get("baseline")
    result = {"fingerprint": measured}
    if baseline and baseline.get("fingerprint"):
        light = sl.drift(baseline["fingerprint"], measured)
        result["light"] = light
        result["light_words"] = sl.describe(light)
        if not sl.comparable(light):
            result["verdict"] = sl.verdict(baseline.get("scores", {}), {}, light)
            result["retake"] = True
            return result
        spend(address, 1)
        image = sl.match_light(image, baseline["fingerprint"])
        result["matched"] = True
        result.update(scan(image))
        result["verdict"] = sl.verdict(baseline.get("scores", {}), result["scores"], light)
    else:
        spend(address, 1)
        result.update(scan(image))
    return result


def handle_plain(body, address):
    """What an ordinary app would report: the check-in scanned as shot, no light matching."""
    image = decode(body.get("image") or "")
    baseline = body.get("baseline") or {}
    spend(address, 1)
    result = scan(image, with_overlays=False)
    result["verdict"] = sl.verdict(baseline.get("scores", {}), result["scores"])
    return result


def handle_pair(body, address):
    before, after = decode(body.get("before") or ""), decode(body.get("after") or "")
    before_fp, after_fp = sl.fingerprint(before), sl.fingerprint(after)
    light = sl.drift(before_fp, after_fp)
    spend(address, 3)
    with ThreadPoolExecutor(max_workers=3) as pool:     # three independent tasks: run together
        jobs = [pool.submit(scan, image, False)
                for image in (before, after, sl.match_light(after, before_fp))]
        first, raw, matched = [job.result() for job in jobs]
    rows = []
    for concern in sl.CONCERNS:
        claimed = raw["scores"][concern] - first["scores"][concern]
        real = matched["scores"][concern] - first["scores"][concern]
        rows.append({"concern": concern, "label": sl.LABELS[concern], "claimed": claimed,
                     "same_light": real, "band": sl.NOISE_BAND[concern],
                     "light_share": sl.light_explains(claimed, real),
                     "real": abs(real) > sl.NOISE_BAND[concern]})
    return {"light": light, "light_words": sl.describe(light).replace("your baseline",
                                                                       "the before photo"),
            "rows": rows, "before": first, "after": raw, "after_same_light": matched}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)

    def end_headers(self):
        if not self.path.startswith("/api/"):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def address(self):
        forwarded = self.headers.get("X-Forwarded-For", "")
        return forwarded.split(",")[0].strip() or self.client_address[0]

    def send_json(self, status, payload):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/api/status":
            try:
                live = balance() - 9 >= UNIT_FLOOR
            except Exception:
                live = False
            return self.send_json(200, {"live": live, "scans_per_visitor": SCANS_PER_VISITOR})
        return super().do_GET()

    def do_POST(self):
        routes = {"/api/scan": handle_scan, "/api/plain": handle_plain, "/api/pair": handle_pair}
        route = routes.get(self.path)
        if not route:
            return self.send_json(404, {"error": "not_found"})
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            return self.send_json(413, {"error": "too_large", "message": "Photos up to 8 MB."})
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            return self.send_json(200, route(body, self.address()))
        except Refused as refused:
            return self.send_json(refused.status, {"error": refused.code,
                                                   "message": refused.message})
        except Exception as error:  # never leak internals, never the key
            self.log_error("scan error: %s", type(error).__name__)
            return self.send_json(500, {"error": "server", "message": "Something went wrong. "
                                        "Try again in a minute."})

    def log_message(self, fmt, *args):
        if "/api/" in (args[0] if args else ""):
            super().log_message(fmt, *args)


def main():
    port = int(os.environ.get("PORT", "8790"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
