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

Redis must be reachable on port `6379` (WSL: `sudo service redis-server start`). If Windows cannot reach WSL Redis through `localhost`, set `REDIS_HOST` to the current WSL IP in each Flask/Celery terminal:

```powershell
$env:REDIS_HOST = (wsl.exe -e bash -lc "hostname -I").Trim().Split(' ')[0]
```

If Redis uses a password, set `REDIS_PASSWORD` before starting Flask and Celery; cache, broker, and result-backend URLs use the configured host and password.
Without Redis the public catalogue works uncached, but CSV export requests return 503 and scheduled jobs cannot run.
Mail is sent through the SMTP server in `MAIL_SERVER`/`MAIL_PORT`; for local demos, [MailHog](https://github.com/mailhog/MailHog/releases/latest) can listen on port 1025 with its inbox at `http://localhost:8025`.

Default admin: `admin@trek.local` / `admin123`

## Folder structure

```
app.py, config.py, requirements.txt
celery_worker.py   Flask-context Celery app and daily/monthly schedules
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
  mailer.py          SMTP plain-text + HTML email helper
  tasks.py           CSV export, daily reminders, monthly activity report
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
| POST | /api/auth/login | public | Log in and return the user |
| POST | /api/auth/register | public | Register a trekker account |
| POST | /api/auth/logout | authenticated | Log out |
| GET | /api/auth/me | any | Return current user or 401 |
| GET | /api/treks?q=&difficulty=&location=&min_days=&max_days= | any | Search/filter approved & open treks (cached) |
| GET | /api/treks/{id} | any | Trek detail (cached) |
| POST | /api/bookings | user | Book (Open only, no duplicates, no overbooking) |
| GET | /api/bookings?status= | user | Own trekking history |
| PATCH | /api/bookings/{id}/cancel | user | Cancel, slots returned, refund if paid |
| POST | /api/bookings/{id}/pay | user | Simulated payment |
| GET | /api/user/dashboard | user | Counts, upcoming bookings, available treks |
| POST | /api/user/export | user | Queue booking-history CSV export; completion is emailed |
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

## Background jobs

Celery beat sends trek reminders daily at 09:00 and the previous month's activity report on the first day of each month at 09:15 (Asia/Kolkata by default).

Run the API, a Celery worker, and Celery beat in separate terminals after starting Redis and the SMTP service:

```bash
flask --app app.py run
celery -A celery_worker.celery worker --loglevel=info --pool=solo
celery -A celery_worker.celery beat --loglevel=info
```

On Windows, `--pool=solo` is required for the worker. CSV files are written to `exports/` and are excluded from Git.

The project brief restricts AI use for some components; review the assignment rules and declare assistance accurately before submission.
