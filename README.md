# Trekking Management Application

Flask-based role-driven trekking management app for MAD-I project.

## Tech Stack

- Flask
- Jinja2 + HTML + CSS + Bootstrap
- SQLite

## Setup

1. Create virtual environment and activate it.
2. Install dependencies:
   pip install -r requirements.txt
3. Initialize database and pre-create admin:
   flask --app app.py init-db
4. Run application:
   flask --app app.py run

## Default Admin Credentials

- Email: admin@trek.local
- Password: admin123

## Roles

- Admin (pre-existing)
- Trek Staff (self-register, requires admin approval)
- User/Trekker (self-register)
