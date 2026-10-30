# Same Light

**Did your skincare work — or did the light change?**

AI skin analysis reads the photo, not the face. Before building anything, this project measured
how far YouCam's AI Skin Analysis scores move when the skin does not change at all. The answer is
far enough to invent a result. Same Light is the tool that follows from that:

- **Track a routine.** Take a baseline selfie, then check in weekly. Every check-in's light is
  measured against the baseline and matched to it *before* the YouCam scan. Each concern then
  gets a plain verdict: *better beyond light noise*, *worse beyond light noise*, *within noise*, or *retake — the
  light is too different to compare*. At the end you get a shareable proof card.
- **Check a before & after.** Two photos from an ad, a clinic post or your own camera roll. Same
  Light scans both, then scans the "after" again with its light matched to the "before", and shows
  how much of each claimed improvement the light alone accounts for.

**Live: https://same-light.onrender.com** (free instance — the first load after a quiet spell takes up to a minute) · Demo video: https://youtu.be/hvygpxSM6fo

## What was measured first

YouCam AI Skin Analysis V2.1, SD, concerns `wrinkle`, `pore`, `texture`, `acne`. Faces under the
Unsplash License ([experiments/SOURCES.md](experiments/SOURCES.md)). Every light change is applied
to the *same photo*, so the skin is identical in every frame. Raw results are committed next to
the scripts that produced them.

**1. The scanner is deterministic.** The identical file scanned three times gave identical scores
on every concern ([experiments/noise-faceA.json](experiments/noise-faceA.json)).

**2. The light is not.** Exposure −20% … +20% and a warm/cool colour shift
([experiments/lighting.json](experiments/lighting.json)):

| face | concern | range with the skin unchanged |
|---|---|---|
| A | pore | **85 – 96** (warm vs cool: 11 points) |
| A | wrinkle | 82 – 89 |
| A | texture | 85 – 92 |
| D | acne | 93 – 99 |
| D | skin age | 22 – 25 years |
| C | pore | 70 – 76 |

A fourth face (B) was refused by the API as too small in frame, and face C at −20% was refused as
too dark — both are now handled as capture advice in the app.

**3. Matching the light removes most of it.** All 12 light changes (3 faces x 4 lights, skin unchanged) scanned as
shot and after matching ([experiments/RESULTS.md](experiments/RESULTS.md), [raw.json](experiments/raw.json),
[calibrate.json](experiments/calibrate.json), and the same table on the site at /evidence.html): the total score gap
falls from **84 to 33 points** (61% less). Seven single readings got slightly worse (all inside their band, mostly
blemishes) and they are listed. The bands were set from the largest matched gap, so "none outside the band after
matching" is by construction and is not claimed as a result. An earlier headline, 40 to 13, came from the first
four cases measured and is superseded by this table. What remains sets the noise band per concern
(`samelight.NOISE_BAND`: wrinkle ±2, pore ±3, texture ±2, acne ±4): a change inside the band is reported as noise,
never as a result.

**4. How far matching can be trusted.** A live before/after pair with a large light gap (29%
brighter and 0.14 warmer — "before" pushed cool, "after" pushed warm) still left pores +6 after
matching: twice the band, on skin that had not changed. So the residual was measured across
larger single-sided gaps too — 3 faces × 4 lights up to 26% exposure and 0.07 warmth
([experiments/calibrate.json](experiments/calibrate.json)): it never exceeded the band. Same Light
therefore certifies a change only inside that measured range (`CALIBRATED_EXPOSURE = 0.27`,
`CALIBRATED_WARMTH = 0.08`). Beyond it, the change is shown with how much the light explains, and
marked **can't certify** — it does not guess. Beyond 35% / 0.25 it asks for a retake.

## How the YouCam API is used

- **AI Skin Analysis V2.1** (`/s2s/v2.1/file/skin-analysis` → upload to the signed URL →
  `/s2s/v2.1/task/skin-analysis` → poll → result zip with `score_info.json` and per-concern mask
  overlays, `enable_mask_overlay`). The overlays are shown on every result.
- **Task deletion** (`/s2s/v2.0/task/delete`) right after the scores are read, so the photo does
  not stay on the scanner. History stays in the browser (`localStorage`); the server keeps nothing.
- **JS Camera Kit** (`v2.2-camera-kit/sdk.js`, `faceDetectionMode: 'skincare'`) as the guided
  camera: it waits for a steady, well-lit, frontal face and captures by itself — the same
  conditions the API rejects photos for.
- API errors (`error_src_face_too_small`, `error_lighting_dark`, `error_no_face`, …) are turned
  into one-line capture advice.

Cost: one SD scan with 4 concerns is 9 units. A check-in is one scan; a before/after check is
three. The server holds the key, caps scans per visitor per day and stops live scans above a unit
floor; the sample face and sample pair are real recorded results
([demo/build_samples.py](demo/build_samples.py)) and cost nothing.

## Run it

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
echo "YOUR_YOUCAM_API_KEY" > ~/.config/youcam.key     # or export YOUCAM_API_KEY
.venv/bin/python server.py                               # http://localhost:8790
.venv/bin/python -m pytest -q                            # 20 tests, no network, no units
```

Re-run the measurements (they spend units): `experiments/noise.py`, `experiments/lighting.py`,
`experiments/normalise.py`.

## Layout

| path | what |
|---|---|
| `samelight.py` | light fingerprint, drift in plain words, light matching, verdicts — pure, tested |
| `youcam.py` | minimal YouCam V2 client (standard library) |
| `server.py` | static site + `/api/scan`, `/api/pair`, `/api/status`; budget and per-visitor caps |
| `web/` | the app: vanilla HTML/CSS/JS, no build step |
| `experiments/` | the measurements and their raw results |

Same Light is not a medical device. It says whether a score moved beyond what the light and the
scanner move on their own — nothing about why.
