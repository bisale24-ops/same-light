"""Build web/evidence.html and web/audit-sample.html from the measured data, so the page cannot drift from the files.

    python3 experiments/build_pages.py
"""
import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
HERE = ROOT / "experiments"
BAND = {"wrinkle": 2, "pore": 3, "texture": 2, "acne": 4}
C = list(BAND)
LABEL = {"wrinkle": "Wrinkles", "pore": "Pores", "texture": "Texture", "acne": "Blemishes"}
GITHUB = "https://github.com/bisale24-ops/same-light/blob/main/"

HEAD = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><link rel="stylesheet" href="style.css">
<style>
 .page{{max-width:980px;margin:0 auto;padding:28px 24px 80px}} .page h1{{font-size:clamp(30px,4vw,44px);margin:12px 0}} .page h2{{margin:40px 0 10px}}
 table.m{{width:100%;border-collapse:collapse;font-size:14px}} table.m th,table.m td{{padding:8px 10px;border-bottom:1px solid #ebe8e4;text-align:left;vertical-align:top}}
 table.m th{{font-weight:600;color:#44403b}} .tri{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}} @media(max-width:760px){{.tri{{grid-template-columns:1fr}}}}
 .tri .card{{padding:18px}} .tri h3{{margin:0 0 8px}} .tri ul{{margin:0;padding-left:18px}} .tri li{{margin:5px 0;font-size:14px}}
 .wrapx{{overflow-x:auto}} a.back{{display:inline-block;margin-bottom:6px}}
</style></head><body><div class="page"><a class="back" href="index.html">← Same Light</a>
"""
FOOT = "</div></body></html>"


def e(x):
    return html.escape(str(x))


def evidence():
    raw = {(r["face"], r["light"]): r["raw"] for r in json.loads((HERE / "raw.json").read_text())}
    cal = json.loads((HERE / "calibrate.json").read_text())
    rows, tr, tm, orr, worse = [], 0, 0, 0, []
    fmt = lambda d: " / ".join(f"{d[c]:+d}" for c in C)
    for c in cal:
        r, m = raw[(c["face"], c["light"])], c["residual"]
        sr, sm = sum(abs(r[x]) for x in C), sum(abs(m[x]) for x in C)
        tr, tm = tr + sr, tm + sm
        orr += sum(abs(r[x]) > BAND[x] for x in C)
        worse += [(c["face"], c["light"], x, r[x], m[x]) for x in C if abs(m[x]) > abs(r[x])]
        rows.append(f"<tr><td>{e(c['face'][-1])}</td><td>{e(c['light'])}</td><td>{c['gap']['exposure']:+.2f} / {c['gap']['warmth']:+.2f}</td>"
                    f"<td>{fmt(r)}</td><td>{fmt(m)}</td><td>{sr} → {sm}</td></tr>")
    loo_lines = [l for l in (HERE / "LEAVE_ONE_OUT.md").read_text().split("\n") if l.startswith("|")]
    loo = "<table class=\"m\"><thead><tr>" + "".join(f"<th>{e(c.strip())}</th>" for c in loo_lines[0].strip("|").split("|")) + "</tr></thead><tbody>" + "".join(
        "<tr>" + "".join(f"<td>{e(c.strip())}</td>" for c in l.strip("|").split("|")) + "</tr>" for l in loo_lines[2:]) + "</tbody></table>"
    worse_li = "".join(f"<li>Face {e(f[-1])}, {e(l)}, {LABEL[x].lower()}: {a:+d} as shot, {b:+d} after matching</li>" for f, l, x, a, b in worse)
    return HEAD.format(title="Evidence: Same Light") + f"""
<p class="eyebrow">Evidence</p><h1>What we measured, and what we did not.</h1>
<p class="lede">Every number on the site comes from this page's data. It is a small experiment and it says so.</p>

<div class="tri">
 <div class="card"><h3>Measured</h3><ul>
  <li>The YouCam scanner returns identical scores for an identical file: 0 points of difference over three scans.</li>
  <li>Changing only the light moves scores: up to 11 points on one concern, up to 3 years of skin age.</li>
  <li>Matching the light to the baseline cut the total gap from {tr} to {tm} points across the {len(cal)} cases below.</li></ul></div>
 <div class="card"><h3>Assumed</h3><ul>
  <li>That the light can be read from the middle of the frame (a fixed crop), as a mean and spread per colour channel.</li>
  <li>That a score change smaller than the noise band for its concern is not evidence of anything.</li>
  <li>That the bands measured on a programmatic light change carry over to a real bulb.</li></ul></div>
 <div class="card"><h3>Not validated</h3><ul>
  <li>Out of sample: bands fitted on two faces failed on the third in 8 of 48 held-out readings (see below); a change within 2 points of the band is shown as borderline, not better or worse.</li>
  <li>Real camera light: every controlled measurement here was applied by software to one photo. On real footage one clip could be compared, and there matching made things worse (see below).</li>
  <li>Whether a score change is a real change in skin: Same Light says a change beats the light noise, not that skincare worked.</li>
  <li>More than 3 faces, and darker skin tones (the 3 faces include one; the skin-colour guard was looked at on four faces only).</li></ul></div>
</div>

<h2>All {len(cal)} cases, nothing removed</h2>
<p class="muted">3 faces × 4 lights; the skin is identical in every frame, only the light changed. Score gap against the same face at its original light, as wrinkle / pore / texture / blemish. Noise bands: ±2, ±3, ±2, ±4.</p>
<div class="card white wrapx"><table class="m"><thead><tr><th>Face</th><th>Light</th><th>Exposure / warmth gap</th><th>As shot</th><th>After matching</th><th>Total gap</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p style="margin-top:14px"><strong>Totals:</strong> {tr} points of gap as shot, {tm} after matching ({round((1-tm/tr)*100)}% less). {orr} of 48 readings were outside their band as shot.</p>
<p class="muted">The bands were set from the largest matched gaps, so "0 outside the band after matching" is true by construction and is not offered as a result. The fair comparison is the totals.</p>

<h2>Out of sample: leave one face out</h2>
<p class="muted">The shipped noise bands were fitted on these same faces, so they are in-sample. Fitting the band for each concern on two faces and scoring the third:</p>
<div class="card white wrapx">{loo}</div>
<p class="muted">So a band fitted on two faces does not always hold on the third: 8 of 48 held-out matched readings fell outside (acne on face D by 1 point, wrinkle and pore on face A by up to 2). With three faces the bands are a rough guide. <a href="{GITHUB}experiments/LEAVE_ONE_OUT.md">Method and table</a>.</p>

<h2>On real camera footage</h2>
<p class="muted">Frames from 18 free stock clips (one person, one camera, light changing), cut by a fixed rule, with YouCam deciding what was usable. Only two clips produced a comparison, and neither shows matching helping: on a face split by strong blue and orange light the total gap went <strong>24 to 39</strong>; on an evenly lit clip (the second pass asked for even light, eligibility fixed before scanning) it stayed <strong>14 to 14</strong>, with one confident \"better\" after matching on unchanged skin, though expression and pose also changed. Sixteen clips were refused outright (angle, face size, out of frame) or gave no second frame. So: two cases, not a validation; matching is shown to help on three faces with software-applied light and not shown to help on real footage. <a href="{GITHUB}real_camera/FOOTAGE.md">Every clip, every refusal, and the guard I tried and did not ship</a>.</p>

<h2>Where matching did not help</h2>
<p class="muted">Readings where the matched gap is larger than the gap as shot (all inside their band; mostly blemishes, which jitter by about 2 on identical re-encoded photos):</p>
<ul>{worse_li}</ul>

<h2>How the light is read, and when Same Light refuses</h2>
<ul>
 <li>The light is read from a fixed crop of the middle of the frame (the middle 50% by 60%). Hair, makeup, shadows and a changed pose can contaminate it.</li>
 <li>If almost nothing in that crop looks like skin, no verdict is given and the photo is rejected as unreadable. If under a third looks like skin, the result carries a warning. The colour test is loose on purpose and is not applied to very dark crops, where it cannot tell skin from dark hair: <a href="{GITHUB}experiments/SKIN_GUARD_CHECK.md">a check on all ten Monk Skin Tone swatches</a> found it refused the darkest tone before that fix, and none now. Flat swatches are not faces, so this is a diagnostic, not a fairness validation.</li>
 <li>A light gap beyond the measured range (exposure ±27%, warmth ±0.08) is shown with how much the light explains and marked "can't certify". Beyond 35% / 0.25 it asks for a retake.</li>
</ul>

<h2>Raw data and scripts</h2>
<ul>
 <li><a href="{GITHUB}experiments/raw.json">raw.json</a>: the 12 light changes scanned as shot</li>
 <li><a href="{GITHUB}experiments/calibrate.json">calibrate.json</a>: the same 12 after matching</li>
 <li><a href="{GITHUB}experiments/lighting.json">lighting.json</a> and <a href="{GITHUB}experiments/noise-faceA.json">noise-faceA.json</a>: the first measurements</li>
 <li><a href="{GITHUB}experiments/RESULTS.md">RESULTS.md</a>: this table as text; <a href="{GITHUB}experiments/SOURCES.md">SOURCES.md</a>: the three test faces (Unsplash License)</li>
</ul>
""" + FOOT


def audit():
    s = json.loads((ROOT / "web" / "samples.json").read_text())["pair"]["result"]
    rows = []
    for r in s["rows"]:
        shown = abs(r["claimed"]) > r["band"]
        verdict = "can't certify" if r.get("uncertain") else "beyond light noise" if r["real"] else "removed by light matching" if shown else "no change"
        share = f"{round((r['light_share'] or 0) * 100)}%" if shown else "n/a"
        rows.append(f"<tr><td>{e(r['label'])}</td><td>{r['claimed']:+d}</td><td>{r['same_light']:+d}</td><td>±{r['band']}</td><td>{share}</td><td><strong>{verdict}</strong></td></tr>")
    return HEAD.format(title="Sample claim audit: Same Light") + f"""
<p class="eyebrow">Sample claim audit · demonstration</p><h1>Before and after: how much did the light do?</h1>
<p class="lede">What a brand, a retailer or a clinic gets for a before/after photo pair: each claimed change, and how much of it the light alone produces. This one is generated from the recorded sample pair; it is not a real merchant's claim and not a clinical, regulatory or advertising-standards finding.</p>
<p>The after photo is {e(s['light_words'])}.</p>
<div class="card white wrapx"><table class="m"><thead><tr><th>Concern</th><th>Change as shown</th><th>Change in the same light</th><th>Noise band</th><th>Share removed by light matching</th><th>Verdict</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<h2>How to read it</h2>
<ul><li>Scores are YouCam AI Skin Analysis ui_scores; higher is better.</li>
<li>The after photo is scanned twice: as it is, and with its light matched to the before photo. The difference is what the light alone produced.</li>
<li>A change counts only if it exceeds the noise band for that concern, measured on 3 faces (<a href="evidence.html">evidence</a>).</li></ul>
<h2>What it does not establish</h2>
<ul><li>That the product caused, or did not cause, any change in skin.</li><li>Anything about different poses, makeup, shadows or cameras.</li><li>Anything outside the light gap measured; beyond it the verdict is withheld.</li></ul>
<p class="muted">Your own pair: <a href="index.html#pair">Check a before &amp; after</a>, then "Download the claim audit".</p>
""" + FOOT


(ROOT / "web" / "evidence.html").write_text(evidence())
(ROOT / "web" / "audit-sample.html").write_text(audit())
print("built")
