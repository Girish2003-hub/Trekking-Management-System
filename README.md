# Trekking Management Application - V2

Flask JSON API + VueJS (CDN) single-page UI, SQLite, Redis cache, Celery jobs.

## Tech stack

| Layer | Used |
|---|---|
| API | Flask, Flask-SQLAlchemy, Flask-Login |
| UI | VueJS 3 + Vue Router (CDN, ES modules, no build step), Bootstrap 5, Chart.js |
| Entry page | Jinja2 - only `templates/index.html` |
| Database | SQLite, tables created in code (`flask init-db`) |
| Cache | Redis (`app/cache.py`, 5 min expiry, cleared on every trek change) |
| Jobs | Celery + Redis |

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
flask --app app.py init-db       # creates tables + the single admin
flask --app app.py run
```

Redis must run on `localhost:6379` (WSL: `sudo service redis-server start`).
Without Redis the app still works, just uncached.

Default admin: `admin@trek.local` / `admin123`

## Folder structure

```
app.py, config.py, requirements.txt
app/
  __init__.py        create_app, Vue entry route, JSON error handlers, init-db
  extensions.py      db, login_manager, redis client
  cache.py           Redis get/set/delete-by-prefix helpers
  models.py          User, Trek, Booking, StaffProfile
  decorators.py      role_required
  api/
    __init__.py      /api blueprint, /api/health
    helpers.py       JSON conversion, validation, cache clearing
    treks.py         public catalogue (cached)
    user.py          bookings, history, dashboard, profile
    staff.py         assigned treks, slots/status, participants
    admin.py         treks, staff, users, bookings, search, stats
  templates/index.html
  static/js/
    main.js          router + role guard
    api.js           fetch wrapper
    store.js         logged-in user state
    components.js    navbar, badges, stat cards, filters
    pages/           public.js, user.js, staff.js, admin.js
```

## Trek lifecycle

`pending` (admin created) -> `approved` (admin) -> `open` (bookings allowed) <-> `closed`
-> `ongoing` (staff: mark started) -> `completed` (staff: all bookings become completed)

## API endpoints

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | /api/health | any | Flask + Redis status |
| GET | /api/treks?q=&difficulty=&location=&min_days=&max_days= | any | Search/filter approved & open treks (cached) |
| GET | /api/treks/{id} | any | Trek detail (cached) |
| POST | /api/bookings | user | Book (Open only, no duplicates, no overbooking) |
| GET | /api/bookings?status= | user | Own trekking history |
| PATCH | /api/bookings/{id}/cancel | user | Cancel, slots returned, refund if paid |
| POST | /api/bookings/{id}/pay | user | Simulated payment |
| GET | /api/user/dashboard | user | Counts, upcoming bookings, available treks |
| GET/PUT | /api/user/profile | all | View / edit name and contact |
| GET | /api/staff/dashboard | staff | Assigned treks + registered count per trek |
| GET | /api/staff/treks/{id} | staff (assigned) | Trek + participant list |
| PATCH | /api/staff/treks/{id} | staff (assigned) | Update total slots / status |
| POST | /api/staff/treks/{id}/start | staff (assigned) | Mark started |
| POST | /api/staff/treks/{id}/complete | staff (assigned) | Mark completed |
| PATCH | /api/staff/bookings/{id} | staff (assigned) | Remove / restore participant |
| GET | /api/admin/stats | admin | Dashboard counts + chart data |
| GET/POST | /api/admin/treks | admin | List all (history) / create |
| PUT/DELETE | /api/admin/treks/{id} | admin | Edit / delete (blocked if it has bookings) |
| PATCH | /api/admin/treks/{id}/status | admin | Approve / set any status |
| PUT | /api/admin/treks/{id}/assign | admin | Assign or unassign staff |
| GET/POST | /api/admin/staff | admin | List / create staff accounts |
| PUT | /api/admin/staff/{id} | admin | Edit staff profile |
| GET | /api/admin/users | admin | List trekkers |
| PATCH | /api/admin/accounts/{id} | admin | activate / deactivate / blacklist / unblacklist |
| GET | /api/admin/bookings?status=&trek_id= | admin | All bookings |
| GET | /api/admin/search?q=&type= | admin | Search users, staff, treks |

## Still to be written by the student (AI not permitted by the problem statement)

- **Trek model (V2)** - `app/models.py`
- **Authentication** - `POST /api/auth/login`, `POST /api/auth/register`, `POST /api/auth/logout`, `GET /api/auth/me`
  (contract in `app/api/__init__.py`; old V1 page-based auth kept in `app/auth/` for reference, not registered)
- **Celery jobs** - daily reminders, monthly HTML report to admin, `POST /api/user/export` CSV export
  (the dashboard's "Export history (CSV)" button already calls it)
