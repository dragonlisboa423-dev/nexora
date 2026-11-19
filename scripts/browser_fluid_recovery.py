"""Recovered original shader running, visual deformation and existing functional controls."""

import io
import json

from browser_support import PASSWORD, test_server
from PIL import Image, ImageChops
from playwright.sync_api import expect, sync_playwright

with test_server(port=8014) as base, sync_playwright() as p:
    b = p.chromium.launch(
        executable_path="/usr/bin/chromium",
        headless=True,
        args=[
            "--no-sandbox",
            "--enable-unsafe-swiftshader",
            "--use-fake-device-for-media-stream",
            "--use-fake-ui-for-media-stream",
        ],
    )
    c = b.new_context(viewport={"width": 1440, "height": 1000})
    c.add_init_script(
        "window.SpeechRecognition=undefined;window.webkitSpeechRecognition=undefined;"
    )
    page = c.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base)
    page.get_by_label("Senha privada", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Desbloquear", exact=True).click()
    page.locator("canvas[data-saly-rendered=true]").wait_for()
    core = page.locator(".core")
    expect(core).to_have_attribute("data-core-renderer", "webgl")
    assert core.locator("svg").count() == 0
    first = core.screenshot()
    page.wait_for_timeout(1250)
    second = core.screenshot()
    difference = ImageChops.difference(
        Image.open(io.BytesIO(first)).convert("RGB"), Image.open(io.BytesIO(second)).convert("RGB")
    )
    changed = sum(1 for pixel in difference.get_flattened_data() if max(pixel) > 12)
    assert changed > 1000, changed
    page.screenshot(path="/tmp/saly-restored-fluid-desktop.png", full_page=True)
    page.get_by_role("button", name="Ativar microfone", exact=True).click()
    page.get_by_role("button", name="Parar microfone", exact=True).wait_for()
    expect(core).to_have_class(__import__("re").compile("listening"))
    page.wait_for_function(
        "Number(document.querySelector('.core').style.getPropertyValue('--audio-energy'))>.01"
    )
    page.get_by_role("button", name="Parar microfone", exact=True).click()
    page.wait_for_function(
        "Number(document.querySelector('.core').style.getPropertyValue('--audio-energy'))===0"
    )
    page.set_viewport_size({"width": 390, "height": 844})
    page.locator("canvas[data-saly-rendered=true]").wait_for()
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
    page.screenshot(path="/tmp/saly-restored-fluid-mobile.png", full_page=True)
    page.emulate_media(reduced_motion="reduce")
    expect(core).to_have_attribute("data-motion", "reduced")
    page.wait_for_timeout(300)
    a = core.screenshot()
    page.wait_for_timeout(300)
    z = core.screenshot()
    assert (
        ImageChops.difference(Image.open(io.BytesIO(a)), Image.open(io.BytesIO(z))).getbbox()
        is None
    )
    assert page.get_by_role("navigation", name="Navegação móvel").get_by_role("link").count() == 4
    assert not errors, errors
    print(
        json.dumps(
            {
                "result": "passed",
                "changed_pixels": changed,
                "flows": [
                    "WebGL fluid deformation between actual frames",
                    "real test microphone energy and shutdown",
                    "desktop/mobile no overflow",
                    "reduced motion stable frames",
                    "four areas preserved",
                ],
                "page_errors": errors,
            }
        )
    )
    b.close()
