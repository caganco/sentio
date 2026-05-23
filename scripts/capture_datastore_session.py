"""
BIST DataStore — headful Playwright login + session capture helper.

Usage:
    python scripts/capture_datastore_session.py

What it does:
  1. Opens a visible Chromium window at datastore.borsaistanbul.com.
  2. Waits for you to fill in email/password, solve the CAPTCHA, and click Login.
  3. Polls until the `token` cookie appears (login confirmed).
  4. Dumps all relevant cookies to datastore_session.json (gitignored).
  5. Prints the x-auth-token value so you can verify it.

D-130 Builder uses datastore_session.json to load x-auth-token for API calls.

SECURITY: datastore_session.json is gitignored via *_session.json pattern.
Never commit it. Never paste the token in chat.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DATASTORE_URL = "https://datastore.borsaistanbul.com/"
SESSION_FILE = Path(__file__).resolve().parents[1] / "datastore_session.json"
POLL_INTERVAL_S = 2
LOGIN_TIMEOUT_S = 300  # 5 minutes for human to complete login + captcha


def _require_playwright() -> None:
    try:
        import playwright  # noqa: F401
    except ImportError:
        sys.exit(
            "playwright not installed.\n"
            "Run: pip install playwright && python -m playwright install chromium"
        )


def capture() -> None:
    _require_playwright()
    from playwright.sync_api import sync_playwright

    print(f"[capture] Opening {DATASTORE_URL}")
    print("[capture] Fill in your credentials, solve the CAPTCHA, then click Login.")
    print(f"[capture] Waiting up to {LOGIN_TIMEOUT_S}s for login to complete…\n")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, slow_mo=0)
        context = browser.new_context()
        page = context.new_page()
        page.goto(DATASTORE_URL, wait_until="domcontentloaded")

        # Poll for the `token` cookie that the server sets on successful login.
        deadline = time.monotonic() + LOGIN_TIMEOUT_S
        token_cookie: str | None = None

        while time.monotonic() < deadline:
            time.sleep(POLL_INTERVAL_S)
            cookies = context.cookies(DATASTORE_URL)
            for c in cookies:
                if c["name"] == "token" and c["value"]:
                    token_cookie = c["value"]
                    break
            if token_cookie:
                break

        if not token_cookie:
            browser.close()
            sys.exit(
                "[capture] Timed out waiting for `token` cookie. "
                "Did you complete the login?"
            )

        print(f"[capture] Login detected — token cookie present.")

        # Post-login API calls may set additional cookies (sid, F5 BIG-IP, etc.)
        # Wait one extra poll cycle to ensure all cookies are settled.
        time.sleep(POLL_INTERVAL_S)

        # Collect all cookies from the domain.
        all_cookies = context.cookies(DATASTORE_URL)
        browser.close()

    # Build a clean dict keyed by cookie name, preserving all fields.
    cookie_map: dict[str, dict] = {c["name"]: c for c in all_cookies}

    # Identify F5 BIG-IP cookie (name starts with "TS").
    f5_key = next((k for k in cookie_map if k.startswith("TS")), None)

    session_data = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "x_auth_token": token_cookie,  # value to use in x-auth-token header
        "cookies": {
            "token": cookie_map.get("token", {}).get("value", ""),
            "datastoreCurrentUser": cookie_map.get("datastoreCurrentUser", {}).get("value", ""),
            "sid": cookie_map.get("sid", {}).get("value", ""),
            "f5_bigip": cookie_map.get(f5_key, {}).get("value", "") if f5_key else "",
            "f5_bigip_name": f5_key or "",
        },
        # Full cookie objects for debugging / future use.
        "_raw_cookies": all_cookies,
    }

    SESSION_FILE.write_text(
        json.dumps(session_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\n[capture] Session saved → {SESSION_FILE}")
    print(f"[capture] x-auth-token : {token_cookie[:12]}…{token_cookie[-6:]}")
    print(f"[capture] sid           : {'present' if session_data['cookies']['sid'] else 'absent'}")
    print(f"[capture] F5 cookie     : {f5_key or 'absent'}")
    print(
        "\n[capture] Done. D-130 connector can now load x_auth_token from "
        "datastore_session.json."
    )


if __name__ == "__main__":
    capture()
