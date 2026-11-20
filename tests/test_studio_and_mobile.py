import time
from pathlib import Path
from playwright.sync_api import sync_playwright

docs_dir = Path("docs/screenshots")
docs_dir.mkdir(parents=True, exist_ok=True)

console_errors = []

def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # -------------------------------------------------------------
        # Test 1: Desktop Studio (1280x800)
        # -------------------------------------------------------------
        context_desktop = browser.new_context(viewport={"width": 1280, "height": 850})
        page_desktop = context_desktop.new_page()

        def on_console(msg):
            if msg.type == "error":
                console_errors.append(f"[Desktop Error] {msg.text}")
        page_desktop.on("console", on_console)

        print("[Test 1] Loading Desktop Studio: http://127.0.0.1:8000/")
        page_desktop.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        time.sleep(1.0)

        # Take initial desktop screenshot
        desktop_screenshot_path = docs_dir / "desktop_studio.png"
        page_desktop.screenshot(path=str(desktop_screenshot_path), full_page=True)
        print(f"  -> Saved desktop screenshot: {desktop_screenshot_path}")

        # Open settings modal
        page_desktop.click("text=설정 (API 키)")
        time.sleep(0.5)
        settings_screenshot_path = docs_dir / "desktop_settings_modal.png"
        page_desktop.screenshot(path=str(settings_screenshot_path))
        print(f"  -> Saved settings modal screenshot: {settings_screenshot_path}")

        # Close modal
        page_desktop.click("#settings-modal button:has(.fa-xmark)")
        time.sleep(0.5)

        # -------------------------------------------------------------
        # Test 2: Mobile Web Exam (390x844 - iPhone 12/13/14)
        # -------------------------------------------------------------
        context_mobile = browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
        )
        page_mobile = context_mobile.new_page()

        def on_mobile_console(msg):
            if msg.type == "error":
                console_errors.append(f"[Mobile Error] {msg.text}")
        page_mobile.on("console", on_mobile_console)

        print("[Test 2] Loading Mobile Web Exam: http://127.0.0.1:8000/web-sample/index.html")
        page_mobile.goto("http://127.0.0.1:8000/web-sample/index.html", wait_until="networkidle")
        time.sleep(1.0)

        # Select answers: 1->5, 2->2, 3->2, 4->3
        page_mobile.check('input[name="answer-q1"][value="5"]')
        page_mobile.check('input[name="answer-q2"][value="2"]')
        page_mobile.check('input[name="answer-q3"][value="2"]')
        page_mobile.check('input[name="answer-q4"][value="3"]')
        time.sleep(0.5)

        mobile_before_path = docs_dir / "mobile_exam_390px_selected.png"
        page_mobile.screenshot(path=str(mobile_before_path), full_page=False)
        print(f"  -> Saved mobile selected screenshot: {mobile_before_path}")

        # Click audio play on Q1
        page_mobile.click("#btn-play-q1")
        time.sleep(0.8)
        page_mobile.click("#btn-play-q1") # pause

        # Click submit button
        print("  -> Submitting exam...")
        page_mobile.click("#btn-submit")
        time.sleep(1.0)

        # Verify score
        score_text = page_mobile.inner_text("#final-score")
        print(f"  -> Scored: {score_text} / 12.9 points")

        res_q1 = page_mobile.inner_text("#res-q1")
        res_q2 = page_mobile.inner_text("#res-q2")
        res_q3 = page_mobile.inner_text("#res-q3")
        res_q4 = page_mobile.inner_text("#res-q4")
        print(f"  -> Item results: Q1={res_q1}, Q2={res_q2}, Q3={res_q3}, Q4={res_q4}")

        mobile_after_path = docs_dir / "mobile_exam_390px_graded.png"
        page_mobile.screenshot(path=str(mobile_after_path), full_page=False)
        print(f"  -> Saved mobile graded screenshot: {mobile_after_path}")

        browser.close()

    print("\n--- Verification Summary ---")
    print(f"Console errors detected: {len(console_errors)}")
    for err in console_errors:
        print("  !", err)

    assert len(console_errors) == 0, f"Expected 0 console errors, got {len(console_errors)}"
    assert score_text == "12.9", f"Expected perfect score 12.9, got {score_text}"
    print("ALL TESTS PASSED! (Console errors: 0, Score: 12.9/12.9)")

if __name__ == "__main__":
    run_tests()
