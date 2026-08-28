# queuecare

**Live application:** https://queuecare-ntk7.onrender.com

**API documentation:** https://queuecare-ntk7.onrender.com/docs

> Hosted on Render's free tier. The instance sleeps after inactivity, so the
> first request may take up to a minute to respond.
A clinic appointment and queue management system: a REST API with a small HTML
interface, plus an automated test suite covering API and UI.

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.10 or newer |
| pip | Any recent version |
| Browser | Installed automatically by Playwright (Chromium) |

No database is required. Data is held in memory and resets when the app restarts.

---

## Install

```bash
git clone <https://github.com/s-gasaro/queuecare.git>
cd queuecare

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium
```

`playwright install chromium` is only needed for the UI tests.

---

## Run the application

```bash
uvicorn app.main:app --reload
```

| URL | What it is |
|---|---|
| http://localhost:8000 | Sign in / register page |
| http://localhost:8000/static/dashboard.html | Appointments dashboard (after sign in) |
| http://localhost:8000/docs | Interactive API documentation |
| http://localhost:8000/health | Health check |

### Environment variables

None. The application runs with no configuration.

---

## Test credentials

The store starts empty, so no accounts exist by default. Create them from the
sign-in page, or from the terminal:

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Aline","email":"patient@queuecare.io","password":"Passw0rd!","role":"patient"}'

curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Chantal","email":"staff@queuecare.io","password":"Passw0rd!","role":"staff"}'
```

| Role | Email | Password |
|---|---|---|
| Patient | patient@queuecare.io | Passw0rd! |
| Staff | staff@queuecare.io | Passw0rd! |

The tests create their own accounts and do not depend on these.

---

## Run the tests

```bash
pytest                          # everything (49 tests)
pytest tests/test_auth_api.py tests/test_appointments_api.py tests/test_queue_api.py   # API only
pytest tests/test_ui.py         # UI only
pytest -v                       # verbose, one line per test
pytest --headed tests/test_ui.py   # watch the browser run
```

The UI tests start the application themselves on port 8001, so the app does not
need to be running first. Port 8001 must be free.

---

## API reference

Every endpoint except `/auth/register`, `/auth/login` and `/health` requires an
`Authorization: Bearer <token>` header.

### Auth

| Method | Path | Description |
|---|---|---|
| POST | `/auth/register` | Create an account (`patient`, `staff` or `admin`) |
| POST | `/auth/login` | Exchange credentials for a token |
| GET | `/auth/me` | Return the signed-in user |

### Appointments

| Method | Path | Description |
|---|---|---|
| POST | `/appointments` | Book an appointment; a queue number is assigned |
| GET | `/appointments` | List appointments (patients see only their own) |
| GET | `/appointments/{id}` | Fetch one appointment |
| PUT | `/appointments/{id}` | Update date, doctor or reason |
| DELETE | `/appointments/{id}` | Cancel an appointment |

### Queue

| Method | Path | Description |
|---|---|---|
| GET | `/queue/today` | Today's queue, ordered by queue number |
| POST | `/queue/{id}/serve` | Mark a patient as served (staff and admin only) |

### Status codes

| Code | Meaning in QueueCare |
|---|---|
| 200 | Request succeeded |
| 201 | Account or appointment created |
| 400 | Malformed or invalid input |
| 401 | Missing, invalid or unrecognised token; bad credentials |
| 403 | Authenticated but not permitted to perform the action |
| 404 | Appointment does not exist |
| 409 | Conflicts with current state (duplicate booking, already cancelled, already served) |

---

## Project structure

```
queuecare/
├── app/
│   ├── main.py                    application entrypoint and error handling
│   ├── store.py                   in-memory data store
│   ├── auth.py                    hashing, tokens, role dependencies
│   ├── schemas.py                 request and response validation
│   ├── routers/
│   │   ├── auth.py                register, login, current user
│   │   └── appointments.py        appointments CRUD and queue
│   └── static/                    sign-in page, dashboard, styles, fetch helper
├── tests/
│   ├── conftest.py                shared fixtures and auth helpers
│   ├── test_auth_api.py           registration, login, protected endpoints
│   ├── test_appointments_api.py   CRUD, authorization, edge cases
│   ├── test_queue_api.py          queue ordering and serving
│   └── test_ui.py                 browser tests (Playwright)
├── requirements.txt
├── README.md
└── TEST_REPORT.md
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: app` | Run commands from the project root, not from `app/` |
| UI tests fail to start | Free port 8001, or change `BASE_URL` in `tests/test_ui.py` |
| `Executable doesn't exist` from Playwright | Run `playwright install chromium` |
| Data disappeared | Expected: the store is in memory and clears on restart |
