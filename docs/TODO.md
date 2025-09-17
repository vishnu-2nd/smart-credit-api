# TODO (Step-by-Step Roadmap)

## Phase 1: Environment Setup

- [✅] Create project structure (`setup.sh` / `setup.py`)
- [✅] Create virtual environment (`.venv`)
- [✅] Add `requirements.txt`
- [✅] Add `.env.example`

## Phase 2: Authentication

- [ ✅] Implement Playwright login script (`src/login.py`)
  - [✅ ] Load credentials from `.env` (`SMARTCREDIT_EMAIL`, `SMARTCREDIT_PASSWORD`)
  - [ ✅] Use Playwright in **headless mode** (default)
  - [ ✅] Verify login success by reaching `/member/home`

## Phase 3: Data Fetching

- [ ] Capture JSON endpoints (accounts, scores, trades, etc.)
- [ ] Save combined raw JSON → `data/smartcredit_raw.json`

## Phase 4: Normalization & Export

- [ ] Transform JSON → `smartcredit_accounts.csv`
- [ ] Transform JSON → `smartcredit_scores.csv`
- [ ] Optional: add inquiries & public records export

## Phase 5: Testing & CI

- [ ] Basic login test
- [ ] Data fetch test
- [ ] Run in Replit / Lovable.dev successfully

installing and setting up

Venv:
python -m venv .venv
.venv\Scripts\activate

packages :

pip install --upgrade pip
pip install -r requirements.txt

Install Playwright browsers:
python -m playwright install

Run the script
python main.py
