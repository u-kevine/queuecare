# Test Report — QueueCare

**Result:** 49 automated tests, all passing. 42 API, 7 UI.

---

## What I built

**Stack**

| Layer | Choice | Why |
|---|---|---|
| API | Python + FastAPI | Validation built into the request models, and free interactive docs |
| Storage | In-memory dictionaries | The assessment allows it; keeps setup at zero and tests fast and isolated |
| Auth | Opaque bearer tokens | Simpler than JWT and enough for this scope; sessions are server-side |
| UI | Plain HTML + JavaScript | The brief does not ask for a polished UI; a framework would add surface area without adding testable behaviour |
| API tests | Pytest + FastAPI TestClient | Runs in-process, so no server or port coordination |
| UI tests | Playwright | Auto-waiting removes the main source of flakiness |

**Architecture**

Routers hold HTTP concerns, `auth.py` holds authentication and authorization,
`schemas.py` holds validation, `store.py` holds state. Authorization is a
dependency (`get_current_user`, `require_staff`) rather than a repeated check
inside each handler, so a new endpoint cannot silently be left unprotected.

**Key decisions**

- **Cancel is a status change, not a delete.** A cancelled appointment stays in
  the store with `status: cancelled`. Deleting the row would have made
  "cancel an already-cancelled appointment" untestable, and clinics need the
  history.
- **Validation errors return 400, not 422.** FastAPI defaults to 422. The
  assessment expects 400 for malformed input, so a handler in `main.py`
  converts them and flattens the error into a single readable message.
- **409 for state conflicts.** Duplicate bookings, double cancellation and
  double serving are not malformed requests — the input is valid, it just
  conflicts with the current state. 409 says that precisely; 400 would blur it.
- **Queue numbers are per date.** Each day starts at 1, which is how a clinic
  actually queues.

---

## What I tested

| Area | Covered | Notes |
|---|---|---|
| Registration | Yes | Success, duplicates, case-insensitive email, bad format, missing fields |
| Login | Yes | Token issuance, wrong password, unknown email |
| Endpoint protection | Yes | No token, invalid token, valid token |
| Appointments CRUD | Yes | Create, list, fetch by ID, update, cancel |
| Role-based access | Yes | Patient isolation, staff visibility, staff-only serving |
| Queue logic | Yes | Numbering, per-date reset, ordering, exclusions, serving |
| Date rules | Yes | Past dates, invalid formats, rescheduling into the past |
| State conflicts | Yes | Double cancel, double serve, serving a cancelled booking, rebooking after cancellation |
| UI flows | Yes | Login (valid, invalid, empty), booking, form validation, cancellation, route guard |

**Deliberately not covered**

- **Password hashing strength.** Passwords use SHA-256 with no salt. This is not
  production-appropriate, but the fix is a library swap, not a design change,
  and testing the hash itself tests the library rather than my code.
- **Concurrency.** Two patients booking at the same instant could receive the
  same queue number. In-memory dictionaries with no locking cannot be made safe
  here, so the real fix belongs at the database layer. Documented rather than
  papered over with a test that would pass by luck.
- **Load and performance.** Out of scope for the assessment.
- **Cross-browser UI.** Chromium only. Playwright can run all three engines, but
  the UI uses no browser-specific APIs, so the added runtime would not buy
  much confidence.

---

## What I automated, and where I drew the line

Everything deterministic is automated. The line I drew was **behaviour vs
appearance**.

Automated: anything with a definite expected outcome — status codes, response
bodies, role filtering, queue ordering, state transitions, and the UI flows
where a specific element must show specific text.

Manual: layout, spacing, colour contrast, and whether an error message reads
clearly to a stressed patient. These need a human judgement, and asserting on
them produces tests that break every time the CSS changes without catching real
defects.

I also kept UI automation deliberately thin. Business rules are tested at the
API level, where tests are faster and failures point directly at the cause. The
UI tests only check that the interface is wired to the API correctly —
duplicating rule coverage in the browser would double the runtime and the
flakiness for no extra information.

**Selector strategy:** every UI test targets `data-testid` attributes. No CSS
classes, no element positions, no text-based lookups for structural elements.
The page can be restyled or reordered without touching a test.

---

## Bugs found

Eight issues surfaced while building and testing. Five were fixed, three are
documented and deliberately left.

### 1. Email addresses were case-sensitive — fixed

`aline@queuecare.io` and `ALINE@queuecare.io` were treated as different people.
Two accounts could exist for the same address, and a patient who capitalised
their email at sign-in would be locked out of their own bookings. Emails are now
normalised to lowercase on registration and login.
Covered by `test_email_is_case_insensitive`.

### 2. UI tests were sharing state — fixed

The UI tests run against one live server, so the in-memory store persisted
between them. A test asserting "no appointments are listed" failed because an
earlier test's booking was still there. This is exactly the flakiness the brief
warns about: the test passed or failed depending on execution order. Each UI
test now registers its own account with a unique email, so no test can see
another's data.

### 3. A `date` field shadowed the `date` type — fixed

In the update model, the field named `date` shadowed the imported `date` type in
the class namespace, so Pydantic resolved the annotation to `None` and rejected
every valid reschedule with 400. Caught by
`test_patient_can_reschedule_their_appointment`. Fixed by importing the module
as `dt` and annotating `dt.date`.

### 4. Cancelled appointments could still be edited — fixed

Nothing stopped a patient updating an appointment they had already cancelled,
which would have left a cancelled booking with a fresh date and queue number.
`update_appointment` now rejects non-active appointments with 409.
Covered by `test_updating_a_cancelled_appointment_is_rejected`.

### 5. Booking form was shown to staff — fixed

Found during manual exploratory testing while signed in as a staff account.
Staff were shown the "Book an appointment" form, which would have created a
booking with the staff member as the patient. That contradicts the purpose of
the system: staff manage the queue, patients book. The form is now hidden for
non-patient roles, and the appointment list heading is role-aware ("Your
appointments" for patients, "All appointments" for staff) with a patient column
so staff can see whose booking each row is.

### 6. Hiding the form does not enforce the rule — known, not fixed

After hiding the form I called `POST /appointments` directly with a staff token,
and the booking still succeeded. Removing a control from the interface is not
authorization. I left the API behaviour as it is, because a staff member may
legitimately be a patient at their own clinic, but the interface should not
imply a rule the API does not enforce. If the rule is meant to hold, it belongs
in the endpoint, not the template.

### 7. Queue numbers leave gaps after cancellation — known, not fixed

Numbers are assigned by counting active bookings for that date. If patient 2 of
3 cancels, the queue reads 1 and 3. Renumbering would be worse: patient 3 would
silently move up while holding a printed ticket saying 3. The gap is honest
about what happened. Worth raising with a product owner rather than deciding
alone.

### 8. Date rules use the server's local date — known, not fixed

"Past" and "today" are evaluated against the server clock. A patient in a
different timezone can have a same-day booking rejected as being in the past,
and `/queue/today` rolls over at the server's midnight rather than the clinic's.
For a single-clinic deployment this is fine; for anything wider, the clinic's
timezone needs to be explicit rather than inherited from the host.

---

## What I would improve with more time

**Security**
- Replace SHA-256 with bcrypt or argon2, with a per-user salt.
- Add token expiry. Tokens currently live until the process restarts, so a
  leaked token is valid indefinitely.
- Rate-limit `/auth/login`. Nothing currently slows down a brute-force attempt.
- Prevent open registration of `staff` and `admin` accounts. Anyone can register
  as staff right now and read every patient's appointments — the most serious
  issue in the system. It is a deliberate scope decision for an assessment with
  no seeded users, but it would be unacceptable in production.

**Testing**
- Freeze time with `freezegun` so date-boundary behaviour can be tested
  deterministically instead of relying on the real clock.
- Add property-based tests for the date validator to cover input shapes I did
  not think to enumerate.
- Run the suite in CI on every push, and add coverage reporting to find gaps I
  have not noticed.
- Add a concurrency test once storage moves to a real database with locking.

**Engineering**
- Move to SQLite or PostgreSQL. In-memory storage loses everything on restart
  and cannot enforce uniqueness constraints at the data layer.
- Extract booking rules from the router into a service layer, so they can be
  unit-tested without going through HTTP.
- Add structured logging so failures in production can be traced.
