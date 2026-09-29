"""Record the demo clips on the live site with a headless browser — no desktop, no Dock, no files.

Real scans on https://same-light.onrender.com: baseline 1, check-in 1, plain comparison 1,
pair 3 — about 54 units. Each clip is paced to its narration line in script.py.

    ~/.venvs/video/bin/python video/record.py [home baseline checkin pair proof]
"""
import asyncio
import pathlib
import shutil
import sys

from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
SITE = "https://same-light.onrender.com/"
CLIPS = HERE / "clips"
VIEW = {"width": 1280, "height": 720}
STATE = HERE / "build" / "storage.json"


async def smooth(page, to, ms=1200):
    """Scroll to an element or a pixel offset the way a person would."""
    await page.evaluate("""([to, ms]) => new Promise(done => {
        const target = typeof to === 'number' ? to
            : document.querySelector(to).getBoundingClientRect().top + scrollY - 24;
        const from = scrollY, start = performance.now();
        const step = t => { const k = Math.min(1, (t - start) / ms);
            scrollTo(0, from + (target - from) * (1 - Math.pow(1 - k, 3)));
            k < 1 ? requestAnimationFrame(step) : done(); };
        requestAnimationFrame(step); })""", [to, ms])


async def wait_result(page, sel, timeout=90000):
    await page.wait_for_function(f"!document.querySelector('{sel}').hidden && "
                                 f"document.querySelector('{sel}').innerText.length > 20",
                                 timeout=timeout)


async def home(page):
    await page.goto(SITE)
    await page.wait_for_timeout(5200)
    await smooth(page, ".facts", 1600)
    await page.wait_for_timeout(3800)
    await smooth(page, "table.measured", 1200)
    await page.wait_for_timeout(5000)


async def baseline(page):
    await page.goto(SITE + "#track")
    await page.evaluate("localStorage.clear()")
    await page.reload()
    await page.wait_for_timeout(800)
    await page.click("#product")
    await page.keyboard.type("Niacinamide serum, twice a day", delay=45)
    await page.set_input_files("#drop input[type=file]", str(ROOT / "experiments" / "faceA.jpg"))
    await page.wait_for_timeout(900)
    await page.click("#scan-btn")
    await wait_result(page, "#result")
    await page.wait_for_timeout(600)
    await smooth(page, "#result", 900)
    await page.wait_for_timeout(1600)
    await smooth(page, "#result .overlays", 1100)
    await page.wait_for_timeout(3000)


async def checkin(page):
    await page.goto(SITE + "#track")
    await page.wait_for_timeout(900)
    await page.set_input_files("#drop input[type=file]", str(HERE / "shots" / "checkin-cool.jpg"))
    await page.wait_for_timeout(700)
    await page.click("#scan-btn")
    await wait_result(page, "#result")
    await page.wait_for_timeout(400)
    await smooth(page, "#result", 900)
    await page.wait_for_timeout(5000)
    button = page.get_by_role("button", name="What would a plain scan say?")
    await button.click()
    await page.wait_for_function("document.querySelector('#result').innerText.includes('Scanned as shot')",
                                 timeout=90000)
    await smooth(page, "#result .card.white", 900)
    await page.wait_for_timeout(5000)


async def pair(page):
    await page.goto(SITE + "#pair")
    await page.wait_for_timeout(1200)
    await page.set_input_files("#drop-before input[type=file]", str(HERE / "shots" / "ad-before.jpg"))
    await page.wait_for_timeout(700)
    await page.set_input_files("#drop-after input[type=file]", str(HERE / "shots" / "ad-after.jpg"))
    await page.wait_for_timeout(1000)
    await page.click("#pair-btn")
    await wait_result(page, "#pair-result")
    await page.wait_for_timeout(300)
    await smooth(page, "#pair-result", 900)
    await page.wait_for_timeout(6500)


async def proof(page):
    await page.goto(SITE + "#track")
    await page.wait_for_timeout(1000)
    await smooth(page, "#history", 1000)
    await page.wait_for_timeout(1200)
    await page.click("#proof-btn")
    await page.wait_for_timeout(5000)
    await page.keyboard.press("Escape")
    await page.wait_for_timeout(600)
    await smooth(page, 0, 800)
    tiny = HERE / "build" / "tiny.jpg"
    from PIL import Image
    Image.open(ROOT / "experiments" / "faceA.jpg").resize((300, 450)).save(tiny)
    await page.set_input_files("#drop input[type=file]", str(tiny))
    await page.wait_for_timeout(500)
    await page.click("#scan-btn")
    await page.wait_for_function("document.querySelector('#alert').classList.contains('on')")
    await page.wait_for_timeout(4500)


async def record(name, run, browser):
    CLIPS.mkdir(exist_ok=True)
    temp = HERE / "build" / ("rec-" + name)
    shutil.rmtree(temp, ignore_errors=True)
    kwargs = {"viewport": VIEW, "record_video_dir": str(temp), "record_video_size": VIEW,
              "device_scale_factor": 1}
    if STATE.exists() and name in ("checkin", "proof"):
        kwargs["storage_state"] = str(STATE)
    context = await browser.new_context(**kwargs)
    page = await context.new_page()
    await run(page)
    if name in ("baseline", "checkin"):
        await context.storage_state(path=str(STATE))
    video = page.video
    await context.close()
    target = CLIPS / (name + ".webm")
    shutil.move(await video.path(), target)
    shutil.rmtree(temp, ignore_errors=True)
    print("recorded", target)


async def main(names):
    runs = {"home": home, "baseline": baseline, "checkin": checkin, "pair": pair, "proof": proof}
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        warm = await browser.new_page()
        await warm.goto(SITE + "api/status", timeout=120000)     # wake the free instance first
        await warm.close()
        for name in names or runs:
            await record(name, runs[name], browser)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
