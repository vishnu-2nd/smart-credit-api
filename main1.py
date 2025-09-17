# #!/usr/bin/env python3
# """
# main.py — SmartCredit Prototype (Step 1: Login)

# - Loads SMARTCREDIT_EMAIL / SMARTCREDIT_PASSWORD from .env
# - Logs into SmartCredit using Playwright
# - Confirms login success by checking /member/ dashboard URL
# """

# import os
# import time
# from playwright.sync_api import sync_playwright
# from dotenv import load_dotenv

# # Load environment variables
# load_dotenv()
# EMAIL = os.getenv("SMARTCREDIT_EMAIL")
# PASSWORD = os.getenv("SMARTCREDIT_PASSWORD")
# HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"

# if not EMAIL or not PASSWORD:
#     raise SystemExit("❌ Please set SMARTCREDIT_EMAIL and SMARTCREDIT_PASSWORD in .env")

# LOGIN_URL = "https://www.smartcredit.com/login"
# DASHBOARD_URL_PATTERN = "**/member/**"

# def main():
#     with sync_playwright() as p:
#         browser = p.chromium.launch(headless=HEADLESS)
#         context = browser.new_context()
#         page = context.new_page()

#         print("🌐 Opening login page...")
#         page.goto(LOGIN_URL, wait_until="domcontentloaded")

#         print("✍️ Filling credentials...")
#         page.fill("input#j_username", EMAIL)      # email field
#         page.fill("input#j_password", PASSWORD)   # password field

#         print("🔑 Submitting login form...")
#         page.click("button[name='loginbttn']")    # login button

#         try:
#             page.wait_for_url(DASHBOARD_URL_PATTERN, timeout=15000)
#             print("✅ Login successful! Landed on:", page.url)
#         except Exception:
#             print("❌ Login failed or CAPTCHA required. Check browser output.")

#         time.sleep(2)  # wait for debug
#         browser.close()

# if __name__ == "__main__":
#     main()

#!/usr/bin/env python3
"""
main.py — SmartCredit Prototype (Complete)

Features:
1. Logs into SmartCredit using Playwright (headless by default, set via .env)
2. Fetches JSON data from protected endpoints
3. Extracts scores from /member/credit-report/smart-3b/ page
4. Saves raw JSON to data/smartcredit_raw.json
5. Normalizes accounts and scores into CSV/XLSX
"""

import os
import json
import pandas as pd
from pathlib import Path
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
EMAIL = os.getenv("SMARTCREDIT_EMAIL")
PASSWORD = os.getenv("SMARTCREDIT_PASSWORD")
HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"

if not EMAIL or not PASSWORD:
    raise SystemExit("❌ Please set SMARTCREDIT_EMAIL and SMARTCREDIT_PASSWORD in .env")

# URLs
LOGIN_URL = "https://www.smartcredit.com/login"
DASHBOARD_URL_PATTERN = "**/member/**"
CREDIT_REPORT_URL = "https://www.smartcredit.com/member/credit-report/smart-3b/"

# Output paths
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
RAW_JSON = DATA_DIR / "smartcredit_raw.json"
ACCOUNTS_CSV = DATA_DIR / "smartcredit_accounts.csv"
SCORES_CSV = DATA_DIR / "smartcredit_scores.csv"

# JSON endpoints (trades, privacy, etc.)
ENDPOINTS = {
    "search_results": "https://www.smartcredit.com/member/privacy/search-results",
    "statistics": "https://www.smartcredit.com/member/privacy/search-result-statistics",
    "trades": "https://www.smartcredit.com/member/money-manager/law/trades",
}

def normalize_and_export(raw: dict, scores: dict):
    """Normalize JSON into accounts.csv and scores.csv"""

    accounts = []

    # Extract accounts from credit_report JSON (per bureau split)
    credit_report = raw.get("credit_report", {})
    if "accounts" in credit_report and isinstance(credit_report["accounts"], list):
        for acct in credit_report["accounts"]:
            account_name = acct.get("creditorName") or acct.get("subscriberCode") or "Unknown"
            bureau = acct.get("report_type")  # should be 'equifax' / 'experian' / 'transunion'
            balance = acct.get("balance_owed")
            limit = acct.get("credit_limit")
            status = acct.get("account_status")

            # Find or create row for this account
            existing = next((a for a in accounts if a["account_name"] == account_name), None)
            if not existing:
                existing = {"account_name": account_name}
                accounts.append(existing)

            # Fill in bureau-specific columns
            if bureau:
                b = bureau.capitalize()
                existing[f"balance_{b}"] = balance
                existing[f"limit_{b}"] = limit
                existing[f"status_{b}"] = status

    # Save accounts (pivoted per bureau)
    if accounts:
        df = pd.DataFrame(accounts)
        df.to_csv(ACCOUNTS_CSV, index=False)
        try:
            df.to_excel(str(ACCOUNTS_CSV.with_suffix(".xlsx")), index=False)
        except Exception as e:
            print("⚠️ Could not save XLSX for accounts:", e)

    # Save scores
    if scores:
        sdf = pd.DataFrame([scores])
        sdf.to_csv(SCORES_CSV, index=False)
        try:
            sdf.to_excel(str(SCORES_CSV.with_suffix(".xlsx")), index=False)
        except Exception as e:
            print("⚠️ Could not save XLSX for scores:", e)

        print("📊 Credit Scores:", scores)
    else:
        print("⚠️ No scores found")


def main():
    aggregated = {}
    scores = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context()
        page = context.new_page()

        print("🌐 Opening login page...")
        page.goto(LOGIN_URL, wait_until="domcontentloaded")

        print("✍️ Filling credentials...")
        page.fill("input#j_username", EMAIL)
        page.fill("input#j_password", PASSWORD)

        print("🔑 Submitting login form...")
        page.click("button[name='loginbttn']")

        try:
            page.wait_for_url(DASHBOARD_URL_PATTERN, timeout=15000)
            print("✅ Login successful! Landed on:", page.url)
        except Exception:
            print("❌ Login failed or CAPTCHA required.")
            browser.close()
            return

        # Fetch JSON endpoints
        for key, url in ENDPOINTS.items():
            try:
                resp = page.request.get(url, headers={"Accept": "application/json"})
                if resp.ok:
                    aggregated[key] = resp.json()
                    print(f"📥 Fetched {key} from {url}")
                else:
                    print(f"⚠️ Failed to fetch {url}: {resp.status}")
            except Exception as e:
                print(f"⚠️ Error fetching {url}: {e}")

        # Navigate to credit report page for scores
        print("🌐 Navigating to credit report page for scores...")
        page.goto(CREDIT_REPORT_URL, wait_until="domcontentloaded")

        try:
            tu = page.inner_text("div.border-transunion h1.fw-bold")
            exp = page.inner_text("div.border-experian h1.fw-bold")
            eqf = page.inner_text("div.border-equifax h1.fw-bold")

            scores = {
                "TransUnion": tu.strip(),
                "Experian": exp.strip(),
                "Equifax": eqf.strip()
            }
        except Exception as e:
            print("⚠️ Could not extract scores:", e)

        browser.close()

    # Save raw JSON
    with open(RAW_JSON, "w", encoding="utf-8") as f:
        json.dump(aggregated, f, indent=2)
    print(f"💾 Saved raw JSON to {RAW_JSON}")

    # Normalize and export
    normalize_and_export(aggregated, scores)
    print(f"📊 Wrote {ACCOUNTS_CSV} and {SCORES_CSV}")

if __name__ == "__main__":
    main()
