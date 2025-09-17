#!/usr/bin/env python3
"""
main_api.py - Fetch raw SmartCredit report data via Playwright
"""

import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from functools import wraps

load_dotenv()

PLAYWRIGHT_HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"
REQUEST_TIMEOUT_MS = int(os.getenv("PLAYWRIGHT_TIMEOUT_MS", "30000"))
API_KEY = os.getenv("API_KEY")  # Add your API_KEY in .env

app = Flask(__name__)

# -----------------------------
# API key protection
# -----------------------------
def require_api_key(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        client_key = request.headers.get("X-API-KEY")
        if not client_key or client_key != API_KEY:
            return jsonify({"ok": False, "error": "Unauthorized"}), 401
        return func(*args, **kwargs)
    return wrapper

# -----------------------------
# Endpoints
# -----------------------------
ENDPOINTS = {
    "search_results": "https://www.smartcredit.com/member/privacy/search-results",
    "statistics": "https://www.smartcredit.com/member/privacy/search-result-statistics",
    "trades": "https://www.smartcredit.com/member/money-manager/law/trades",
    "credit_report_json": "https://www.smartcredit.com/member/credit-report/3b/simple.htm?format=JSON"
}
CREDIT_REPORT_HTML = "https://www.smartcredit.com/member/credit-report/smart-3b/"


def fetch_report_for_credentials(email: str, password: str, headless: bool = PLAYWRIGHT_HEADLESS, timeout_ms: int = REQUEST_TIMEOUT_MS):
    aggregated = {}
    scores = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context()
        page = context.new_page()

        # --- Login ---
        page.goto("https://www.smartcredit.com/login", wait_until="domcontentloaded", timeout=timeout_ms)
        page.fill("input#j_username", email, timeout=timeout_ms)
        page.fill("input#j_password", password, timeout=timeout_ms)
        page.click("button[name='loginbttn']", timeout=timeout_ms)

        try:
            page.wait_for_url("**/member/**", timeout=timeout_ms)
        except PWTimeout:
            raise ValueError("Login failed or CAPTCHA required.")

        # --- Fetch JSON endpoints ---
        for key, url in ENDPOINTS.items():
            try:
                resp = page.request.get(url, headers={"Accept": "application/json"})
                if resp.ok:
                    try:
                        aggregated[key] = resp.json()
                    except Exception:
                        aggregated[key] = {"__raw_text": resp.text()}
                else:
                    aggregated[key] = {"__http_status": resp.status, "__error": resp.text()}
            except Exception as e:
                aggregated[key] = {"__error_exception": str(e)}

        # --- Scrape HTML scores ---
        try:
            page.goto(CREDIT_REPORT_HTML, wait_until="domcontentloaded", timeout=timeout_ms)
            tu = None
            exp = None
            eqf = None
            try:
                tu = page.inner_text("div.border-transunion h1.fw-bold", timeout=3000).strip()
            except Exception:
                pass
            try:
                exp = page.inner_text("div.border-experian h1.fw-bold", timeout=3000).strip()
            except Exception:
                pass
            try:
                eqf = page.inner_text("div.border-equifax h1.fw-bold", timeout=3000).strip()
            except Exception:
                pass

            if tu:
                scores["TransUnion"] = tu
            if exp:
                scores["Experian"] = exp
            if eqf:
                scores["Equifax"] = eqf
        except Exception:
            pass

        browser.close()

    return {"aggregated": aggregated, "scores": scores}


# -----------------------------
# Routes
# -----------------------------
@app.route("/fetch_report", methods=["POST"])
@require_api_key
def fetch_report():
    """Return RAW SmartCredit data + scores (no normalization)."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"ok": False, "error": "Invalid JSON body"}), 400

    email = data.get("email")
    password = data.get("password")
    headless = data.get("headless", PLAYWRIGHT_HEADLESS)

    if not email or not password:
        return jsonify({"ok": False, "error": "email and password required"}), 422

    try:
        result = fetch_report_for_credentials(email, password, headless=bool(headless))
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 401
    except Exception as e:
        return jsonify({"ok": False, "error": f"internal error: {e}"}), 500

    # 🚨 Return raw aggregated + scores directly
    return jsonify({"ok": True, "raw": result["aggregated"], "scores": result["scores"]}), 200


@app.route("/")
@require_api_key
def index():
    return jsonify({"ok": True, "msg": "SmartCredit RAW fetch API. POST /fetch_report with {email,password}"}), 200


# -----------------------------
# Run
# -----------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
