# #!/usr/bin/env python3
# """
# main_api.py - Fetch raw SmartCredit report data via Playwright
# """

# import os
# from flask import Flask, request, jsonify
# from dotenv import load_dotenv
# from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
# from functools import wraps

# load_dotenv()

# PLAYWRIGHT_HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"
# REQUEST_TIMEOUT_MS = int(os.getenv("PLAYWRIGHT_TIMEOUT_MS", "30000"))
# API_KEY = os.getenv("API_KEY")  # Add your API_KEY in .env

# app = Flask(__name__)

# # -----------------------------
# # API key protection
# # -----------------------------
# def require_api_key(func):
#     @wraps(func)
#     def wrapper(*args, **kwargs):
#         client_key = request.headers.get("X-API-KEY")
#         if not client_key or client_key != API_KEY:
#             return jsonify({"ok": False, "error": "Unauthorized"}), 401
#         return func(*args, **kwargs)
#     return wrapper

# # -----------------------------
# # Endpoints
# # -----------------------------
# ENDPOINTS = {
#     "search_results": "https://www.smartcredit.com/member/privacy/search-results",
#     "statistics": "https://www.smartcredit.com/member/privacy/search-result-statistics",
#     "trades": "https://www.smartcredit.com/member/money-manager/law/trades",
#     "credit_report_json": "https://www.smartcredit.com/member/credit-report/3b/simple.htm?format=JSON"
# }
# CREDIT_REPORT_HTML = "https://www.smartcredit.com/member/credit-report/smart-3b/"


# def fetch_report_for_credentials(email: str, password: str, headless: bool = PLAYWRIGHT_HEADLESS, timeout_ms: int = REQUEST_TIMEOUT_MS):
#     aggregated = {}
#     scores = {}

#     with sync_playwright() as p:
#         browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
#         context = browser.new_context()
#         page = context.new_page()

#         # --- Login ---
#         page.goto("https://www.smartcredit.com/login", wait_until="domcontentloaded", timeout=timeout_ms)
#         page.fill("input#j_username", email, timeout=timeout_ms)
#         page.fill("input#j_password", password, timeout=timeout_ms)
#         page.click("button[name='loginbttn']", timeout=timeout_ms)

#         try:
#             page.wait_for_url("**/member/**", timeout=timeout_ms)
#         except PWTimeout:
#             raise ValueError("Login failed or CAPTCHA required.")

#         # --- Fetch JSON endpoints ---
#         for key, url in ENDPOINTS.items():
#             try:
#                 resp = page.request.get(url, headers={"Accept": "application/json"})
#                 if resp.ok:
#                     try:
#                         aggregated[key] = resp.json()
#                     except Exception:
#                         aggregated[key] = {"__raw_text": resp.text()}
#                 else:
#                     aggregated[key] = {"__http_status": resp.status, "__error": resp.text()}
#             except Exception as e:
#                 aggregated[key] = {"__error_exception": str(e)}

#         # --- Scrape HTML scores ---
#         try:
#             page.goto(CREDIT_REPORT_HTML, wait_until="domcontentloaded", timeout=timeout_ms)
#             tu = None
#             exp = None
#             eqf = None
#             try:
#                 tu = page.inner_text("div.border-transunion h1.fw-bold", timeout=3000).strip()
#             except Exception:
#                 pass
#             try:
#                 exp = page.inner_text("div.border-experian h1.fw-bold", timeout=3000).strip()
#             except Exception:
#                 pass
#             try:
#                 eqf = page.inner_text("div.border-equifax h1.fw-bold", timeout=3000).strip()
#             except Exception:
#                 pass

#             if tu:
#                 scores["TransUnion"] = tu
#             if exp:
#                 scores["Experian"] = exp
#             if eqf:
#                 scores["Equifax"] = eqf
#         except Exception:
#             pass

#         browser.close()

#     return {"aggregated": aggregated, "scores": scores}


# # -----------------------------
# # Routes
# # -----------------------------
# @app.route("/fetch_report", methods=["POST"])
# @require_api_key
# def fetch_report():
#     """Return RAW SmartCredit data + scores (no normalization)."""
#     data = request.get_json(silent=True)
#     if not data:
#         return jsonify({"ok": False, "error": "Invalid JSON body"}), 400

#     email = data.get("email")
#     password = data.get("password")
#     headless = data.get("headless", PLAYWRIGHT_HEADLESS)

#     if not email or not password:
#         return jsonify({"ok": False, "error": "email and password required"}), 422

#     try:
#         result = fetch_report_for_credentials(email, password, headless=bool(headless))
#     except ValueError as e:
#         return jsonify({"ok": False, "error": str(e)}), 401
#     except Exception as e:
#         return jsonify({"ok": False, "error": f"internal error: {e}"}), 500

#     # 🚨 Return raw aggregated + scores directly
#     return jsonify({"ok": True, "raw": result["aggregated"], "scores": result["scores"]}), 200


# @app.route("/")
# @require_api_key
# def index():
#     return jsonify({"ok": True, "msg": "SmartCredit RAW fetch API. POST /fetch_report with {email,password}"}), 200


# # -----------------------------
# # Run
# # -----------------------------
# if __name__ == "__main__":
#     port = int(os.getenv("PORT", "5000"))
#     app.run(host="0.0.0.0", port=port)
## Above is with raw JSON
#!/usr/bin/env python3
"""
main_api.py - Fetch SmartCredit report data via Playwright
Returns both RAW and NORMALIZED JSON in the response.
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


# -----------------------------
# Fetch report
# -----------------------------
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
            try:
                tu = page.inner_text("div.border-transunion h1.fw-bold", timeout=3000).strip()
            except Exception:
                tu = None
            try:
                exp = page.inner_text("div.border-experian h1.fw-bold", timeout=3000).strip()
            except Exception:
                exp = None
            try:
                eqf = page.inner_text("div.border-equifax h1.fw-bold", timeout=3000).strip()
            except Exception:
                eqf = None

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
# Normalization
# -----------------------------
def normalize_report(raw: dict, scores: dict):
    """
    Normalize raw SmartCredit JSON into the structure expected by the client.
    """
    def safe_number(val):
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    normalized = {
        "personal_info": {},
        "scores": scores or {},
        "summary": {},
        "accounts": [],
        "inquiries": [],
        "public_records": [],
        "employers": []
    }

    # Personal info
    cr_json = raw.get("credit_report_json", {})
    if isinstance(cr_json, dict):
        borrower = cr_json.get("Borrower", {}) or {}
        addr = (borrower.get("BorrowerAddress") or {}).get("CreditAddress", {}) or {}
        normalized["personal_info"] = {
            "name": borrower.get("BorrowerName"),
            "ssn": (borrower.get("SocialPartition") or {}).get("Social"),
            "date_of_birth": (borrower.get("Birth") or {}).get("date"),
            "address": ", ".join(filter(None, [
                addr.get("Street"),
                addr.get("City"),
                addr.get("State"),
                addr.get("PostalCode"),
            ]))
        }

    # Scores (fallback)
    if not normalized["scores"] and isinstance(cr_json, dict):
        comps = (cr_json.get("BundleComponents") or {}).get("BundleComponent", [])
        if isinstance(comps, dict):
            comps = [comps]
        for comp in comps:
            bureau = comp.get("Type")
            cs = comp.get("CreditScoreType") or {}
            score = cs.get("riskScore") or cs.get("score")
            if score and bureau:
                if "TUC" in bureau:
                    normalized["scores"]["TransUnion"] = score
                elif "EQF" in bureau:
                    normalized["scores"]["Equifax"] = score
                elif "EXP" in bureau:
                    normalized["scores"]["Experian"] = score

    # Summary
    stats = raw.get("statistics", {})
    if isinstance(stats, dict):
        normalized["summary"] = {
            "total_accounts": safe_number(stats.get("totalAccounts")),
            "open_accounts": safe_number(stats.get("openAccounts")),
            "closed_accounts": safe_number(stats.get("closedAccounts")),
            "delinquent_accounts": safe_number(stats.get("delinquentAccounts")),
            "derogatory_accounts": safe_number(stats.get("derogatoryAccounts")),
            "total_balances": safe_number(stats.get("totalBalances")),
            "total_payments": safe_number(stats.get("totalPayments")),
            "public_records": safe_number(stats.get("publicRecords")),
            "inquiries_2yrs": safe_number(stats.get("inquiriesLast2Years")),
        }

    # Accounts
    trades = (raw.get("trades") or {}).get("trades", [])
    if isinstance(trades, dict):
        trades = [trades]
    for trade in trades:
        inst = trade.get("institution") or {}
        acct = {
            "institution": {"name": inst.get("name") or trade.get("creditorName")},
            "account_type": (
                (trade.get("accountTypeObj") or {}).get("description")
                or trade.get("accountTypeDescription")
                or trade.get("accountType")
                or trade.get("type")
            ),
            "bureau": trade.get("creditorContactSource") or trade.get("bureau") or trade.get("source"),
            "status": (
                trade.get("accountStatus")
                or trade.get("currentAccountRatingDisplay")
                or trade.get("accountRating")
            ),
            "balance": safe_number(trade.get("currentBalanceAmount") or trade.get("balance")),
            "credit_limit": safe_number(trade.get("creditLimitAmount")),
            "high_balance": safe_number(trade.get("highCreditAmount")),
            "open_date": trade.get("openDateFormatted"),
            "closed_date": trade.get("dateClosed"),
            "last_payment_date": trade.get("dateLastPayment"),
            "payment_amount": safe_number(trade.get("termsMonthlyPayment")),
            "past_due": safe_number(trade.get("amountPastDue")),
            "account_number": trade.get("maskedAccountNumber"),
            "payment_history": trade.get("paymentHistory"),
            "times_30_late": safe_number(trade.get("times30Late")),
            "times_60_late": safe_number(trade.get("times60Late")),
            "times_90_late": safe_number(trade.get("times90Late")),
            "remarks": trade.get("accountRemark"),
            "last_reported": trade.get("lastReported"),
            "account_age": trade.get("accountAge"),
        }
        normalized["accounts"].append(acct)

    # Inquiries
    inqs = (raw.get("search_results") or {}).get("inquiries", [])
    if isinstance(inqs, dict):
        inqs = [inqs]
    for iq in inqs:
        normalized["inquiries"].append({
            "bureau": iq.get("bureau"),
            "business_name": iq.get("subscriberName"),
            "inquiry_date": iq.get("inquiryDate"),
            "type": iq.get("inquiryType"),
        })

    # Public records
    prs = (raw.get("search_results") or {}).get("publicRecords", [])
    if isinstance(prs, dict):
        prs = [prs]
    for pr in prs:
        normalized["public_records"].append({
            "type": pr.get("type"),
            "date_filed": pr.get("dateFiled"),
            "status": pr.get("status"),
            "amount": safe_number(pr.get("amount")),
        })

    # Employers
    employers = (cr_json.get("Borrower") or {}).get("Employer", []) or []
    if isinstance(employers, dict):
        employers = [employers]
    for emp in employers:
        normalized["employers"].append({
            "name": emp.get("employerName"),
            "date_reported": emp.get("dateReported") or emp.get("dateUpdated"),
            "bureau": emp.get("bureau"),
        })

    return normalized


# -----------------------------
# Routes
# -----------------------------
@app.route("/fetch_report", methods=["POST"])
@require_api_key
def fetch_report():
    """Return RAW and NORMALIZED SmartCredit data + scores."""
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
        normalized = normalize_report(result["aggregated"], result["scores"])
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 401
    except Exception as e:
        return jsonify({"ok": False, "error": f"internal error: {e}"}), 500

    return jsonify({
        "ok": True,
        "raw": result["aggregated"],
        "normalized": normalized,
        "scores": result["scores"]
    }), 200


@app.route("/")
@require_api_key
def index():
    return jsonify({"ok": True, "msg": "SmartCredit API. POST /fetch_report with {email,password}"}), 200


# -----------------------------
# Run
# -----------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
