"""Same Light: the part that decides whether a skin score changed, or only the light did.

Everything here is pure (Pillow in, numbers out) so it is testable without the API.

Measured on 29 September 2026 (experiments/): the scanner returns identical scores for an
identical file, but the same face under a warmer or cooler bulb moves the pore score by 11 points,
and ±20% exposure moves skin age by up to 3 years. Matching the new photo's light to the baseline
before scanning cut the fake change from 40 points to 13 across four cases.
"""
from PIL import Image, ImageStat

CONCERNS = ("wrinkle", "pore", "texture", "acne")

# How far a score moves with the light matched and the skin unchanged (max residual measured after
# matching, plus the ±2 acne jitter seen on re-encoded identical photos). A change inside the band
# is not evidence of anything.
NOISE_BAND = {"wrinkle": 2, "pore": 3, "texture": 2, "acne": 4}

# Leave-one-face-out (experiments/LEAVE_ONE_OUT.md) found 8 of 48 held-out readings outside a band fitted on the other two
# faces, never by more than 2 points. A change that clears the band by 2 points or less is therefore called borderline: it
# depends on where the band is drawn, so it is not reported as better or worse.
BORDERLINE_MARGIN = 2

# Beyond this the matching itself is a guess: the light is too different to compare at all.
MAX_EXPOSURE_DRIFT = 0.35
MAX_WARMTH_DRIFT = 0.25

# The largest light gaps the bands were measured on (experiments/calibrate.json: 3 faces, 12
# lights, residual after matching never above the band). Past this, matching still runs, but a
# change is never certified as real: a live pair with a 0.14 warmth gap left pores +6 after
# matching, twice the band, on skin that had not changed.
CALIBRATED_EXPOSURE = 0.27
CALIBRATED_WARMTH = 0.08

LABELS = {"wrinkle": "Wrinkles", "pore": "Pores", "texture": "Texture", "acne": "Blemishes"}


def face_region(image):
    """The middle of a framed selfie — where the face is when the capture guide was followed."""
    width, height = image.size
    return image.crop((width // 4, height // 5, width * 3 // 4, height * 4 // 5))


# The light is read from a fixed crop, so a crop that is mostly not skin (hair, a hat, a wall behind a
# small face) is reading something else. The skin share is a loose check on that, deliberately low: the
# colour range below was looked at on four faces only and favours lighter skin, so it must not refuse a
# darker face. Below UNREADABLE nothing in the crop looks like skin at all; below WEAK the reading is
# shown with a warning.
SKIN_UNREADABLE = 0.12
SKIN_WEAK = 0.30


DARK_CROP = 70


def skin_share(image):
    """Share of the face crop whose colour is in a broad skin range (YCbCr), 0..1; None when the crop
    is too dark to tell skin from dark hair by colour (the darkest Monk skin tones sit there: the colour
    test would call them hair, so it is not applied rather than being allowed to refuse a face)."""
    crop = face_region(image.convert("RGB")).convert("YCbCr")
    crop.thumbnail((160, 160))
    data = crop.tobytes()
    if sum(data[0::3]) / max(len(data) // 3, 1) < DARK_CROP:
        return None
    pixels = len(data) // 3
    hit = sum(1 for i in range(0, pixels * 3, 3)
              if data[i] > 40 and 77 <= data[i + 1] <= 127 and 133 <= data[i + 2] <= 173)
    return hit / max(pixels, 1)


def fingerprint(image):
    """Per-channel mean and spread of the face region: the light, as the camera saw it."""
    stat = ImageStat.Stat(face_region(image.convert("RGB")))
    return {"mean": [round(v, 2) for v in stat.mean], "std": [round(v, 2) for v in stat.stddev],
            "skin": None if (share := skin_share(image)) is None else round(share, 2)}


def light_reading(*fingerprints):
    """'ok', 'weak' or 'unreadable': can the light be read from these photos? Older fingerprints without
    a skin share count as ok."""
    shares = [fp["skin"] for fp in fingerprints if fp.get("skin") is not None]
    if shares and min(shares) < SKIN_UNREADABLE:
        return "unreadable"
    if shares and min(shares) < SKIN_WEAK:
        return "weak"
    # a very dark crop skips the colour test: the light is read, but not checked
    return "unchecked" if any("skin" in fp and fp["skin"] is None for fp in fingerprints) else "ok"


def luminance(fp):
    r, g, b = fp["mean"]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def warmth(fp):
    r, _, b = fp["mean"]
    return (r - b) / max(r + b, 1.0)


def drift(baseline, current):
    """How the light moved, as two signed numbers: exposure (relative) and warmth (difference)."""
    exposure = luminance(current) / max(luminance(baseline), 1.0) - 1.0
    return {"exposure": round(exposure, 3), "warmth": round(warmth(current) - warmth(baseline), 3)}


def describe(light):
    """Plain words for a drift, the way the result screen says it."""
    parts = []
    exposure, warm = light["exposure"], light["warmth"]
    if abs(exposure) >= 0.05:
        parts.append(f"{abs(exposure) * 100:.0f}% {'brighter' if exposure > 0 else 'darker'}")
    if abs(warm) >= 0.02:
        parts.append("warmer" if warm > 0 else "cooler")
    return " and ".join(parts) + " than your baseline" if parts else "same light as your baseline"


def comparable(light):
    return abs(light["exposure"]) <= MAX_EXPOSURE_DRIFT and abs(light["warmth"]) <= MAX_WARMTH_DRIFT


def calibrated(light):
    """Inside the light gaps the noise bands were actually measured on."""
    return abs(light["exposure"]) <= CALIBRATED_EXPOSURE and abs(light["warmth"]) <= CALIBRATED_WARMTH


def match_light(image, reference_fp):
    """Map each channel of the whole photo so the face region has the baseline's mean and spread."""
    image = image.convert("RGB")
    current = fingerprint(image)
    bands = []
    for band, mean, std, t_mean, t_std in zip(image.split(), current["mean"], current["std"],
                                              reference_fp["mean"], reference_fp["std"]):
        gain = t_std / std if std else 1.0
        bands.append(band.point(lambda v, m=mean, g=gain, tm=t_mean:
                                max(0, min(255, int(round((v - m) * g + tm))))))
    return Image.merge("RGB", bands)


def verdict(baseline_scores, current_scores, light=None):
    """Per concern: did it move beyond what the light and the scanner move on their own?

    Scores are YouCam `ui_score`s, higher is better. Returns a list of rows the UI renders as-is.
    """
    if light is not None and not comparable(light):
        return [{"concern": c, "label": LABELS[c], "before": baseline_scores.get(c),
                 "after": current_scores.get(c), "delta": None, "band": NOISE_BAND[c],
                 "call": "retake"} for c in CONCERNS]
    certain = light is None or calibrated(light)
    rows = []
    for concern in CONCERNS:
        before, after = baseline_scores.get(concern), current_scores.get(concern)
        if before is None or after is None:
            continue
        delta = after - before
        band = NOISE_BAND[concern]
        if abs(delta) <= band:
            call = "noise"
        elif abs(delta) <= band + BORDERLINE_MARGIN:
            call = "borderline"
        else:
            call = "better" if delta > 0 else "worse"
        if call in ("better", "worse", "borderline") and not certain:
            call = "uncertain"
        rows.append({"concern": concern, "label": LABELS[concern], "before": before, "after": after,
                     "delta": delta, "band": band, "call": call})
    return rows


def light_explains(raw_delta, matched_delta):
    """For a before/after pair: how much of the claimed change was the light (0..1), per concern."""
    if raw_delta == 0:
        return 0.0
    share = (raw_delta - matched_delta) / raw_delta
    return round(max(0.0, min(1.0, share)), 2)
