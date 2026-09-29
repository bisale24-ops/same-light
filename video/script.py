"""Same Light — demo video for the YouCam API hackathon. 1–3 minutes, narrated, no presenter.

    ~/.venvs/video/bin/python video/record.py            # records the clips on the live site
    ~/.venvs/video/bin/python ~/Desktop/KHLab/hack-nation/kit/video/render.py \
        video/script.py --out video/demo.mp4 --max-seconds 175

Every number spoken here is in experiments/ or came from the scans recorded in the clips.
"""
VOICE = "en-US-AvaNeural"
W, H = 1280, 720
BACKGROUND = "0xfdfcfc"

SCENES = [
    ("card:title",
     "Same Light. Did your skincare work, or did the light change? An AI skin scan reads the "
     "photo, not your face. So before building anything, I measured how far YouCam's AI Skin "
     "Analysis moves when the skin does not change at all."),

    ("clip:home",
     "Scanned three times, the identical photo gives identical scores. The scanner is exact. "
     "Then I changed only the light on that same photo. Warm: pores ninety six. Cool: eighty five. "
     "Same skin."),

    ("card:measured",
     "Across three faces, light alone moved a single concern by up to eleven points, and skin age "
     "by three years. But matching the light back to a baseline before scanning cut the fake change "
     "from forty points to thirteen. That is the product."),

    ("clip:baseline",
     "Track a routine. Name what you're testing and add a baseline photo. The server uploads it to "
     "the YouCam Skin Analysis API, runs the task, reads four concerns with their mask overlays, "
     "and then deletes the task and the photo from YouCam. History stays on your device."),

    ("clip:checkin",
     "A week later, in a cooler room. Same Light measures how the light moved, matches it to the "
     "baseline, and only then scans. Every concern is judged against its measured noise band. "
     "Here: nothing changed beyond noise. Scanned as shot, without matching, the same photo reads "
     "pores down eight and texture down four, for skin that did not change."),

    ("clip:pair",
     "Check a before and after, like a product ad: dim and cool before, bright and warm after. "
     "As shown, pores improve by twelve and texture by four. In the before photo's light, "
     "texture's gain is gone. Pores keep six, but this light gap is bigger than anything I "
     "calibrated, so Same Light says it can't certify it, instead of guessing."),

    ("clip:proof",
     "When a routine does work, you get a proof card that only counts changes beyond the noise. "
     "Photos that the API would reject, too dark, too small, turned away, come back as one line of "
     "capture advice, and the YouCam Camera Kit guides the selfie itself."),

    ("card:end",
     "For people spending money on skincare, for clinics, and for brands whose results should "
     "survive a fair photo. Open source, with every measurement in the repository. Same Light, "
     "same light dot on render dot com."),
]

CARDS = {
    "title": """<h1 style="font-weight:300;font-size:64px;letter-spacing:-.03em">Same Light</h1>
      <p class="sub" style="font-size:30px">Did your skincare work — or did the light change?</p>
      <p class="foot">Built on YouCam AI Skin Analysis · YouCam API Skin AI &amp; eCommerce VTO Hackathon</p>""",

    "measured": """<h1 style="font-weight:300">What the light does to a skin score</h1>
      <p class="sub">YouCam AI Skin Analysis V2.1 · same photo, only the light changed · 29 Sep 2026</p>
      <table>
        <tr><th>measurement</th><th>result</th></tr>
        <tr><td>identical photo, scanned 3×</td><td class="ok">0 points difference</td></tr>
        <tr><td>warm vs cool light, one face</td><td class="no">pores 96 vs 85</td></tr>
        <tr><td>exposure ±20%, one face</td><td class="no">skin age 22 → 25</td></tr>
        <tr><td>fake change, 4 worst cases, as shot</td><td class="no">40 points</td></tr>
        <tr><td>same cases, light matched to baseline</td><td class="ok">13 points</td></tr>
      </table>
      <p class="foot">Raw results and scripts: github.com/bisale24-ops/same-light/tree/main/experiments</p>""",

    "end": """<h1 style="font-weight:300;font-size:56px;letter-spacing:-.03em">Same Light</h1>
      <p class="sub" style="font-size:26px">same-light.onrender.com</p>
      <table>
        <tr><td>YouCam API</td><td>AI Skin Analysis V2.1 · mask overlays · task delete · JS Camera Kit</td></tr>
        <tr><td>source</td><td>github.com/bisale24-ops/same-light</td></tr>
      </table>
      <p class="foot">Not a medical device. It says whether a score moved beyond what the light and the scanner move on their own.</p>""",
}

CLIPS = {
    "home": "clips/home.webm",
    "baseline": "clips/baseline.webm",
    "checkin": ("clips/checkin.webm", 3),
    "pair": "clips/pair.webm",
    "proof": "clips/proof.webm",
}
