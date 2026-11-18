from flask import Flask, abort, jsonify, render_template, request
from sqlalchemy import inspect, text

from config import Config
from app.models import User
from app.extensions import db, init_redis, login_manager


def create_app():
    # Jinja is only used for the single Vue entry page (templates/index.html).
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    init_redis(app.config["REDIS_URL"])

    # ---- JSON API (Vue talks only to these) ----
    from app.api import api_bp

    app.register_blueprint(api_bp)
    from app.auth.routes import auth_bp

    app.register_blueprint(auth_bp)

    # ---- Vue entry point ----
    # Vue Router uses HTML5 history mode, so a refresh on /admin/treks must also
    # return index.html; the catch-all route below handles that.
    @app.route("/")
    @app.route("/<path:_any>")
    def home(_any=None):
        if _any and _any.startswith(("api/", "static/")):
            abort(404)
        return render_template("index.html")

    # ---- Errors: JSON for /api/*, Vue page for everything else ----
    def _wants_json():
        return request.path.startswith("/api/")

    @app.errorhandler(401)
    def unauthorized(_error):
        if _wants_json():
            return jsonify({"message": "Login required"}), 401
        return render_template("index.html"), 401

    @app.errorhandler(403)
    def forbidden(_error):
        if _wants_json():
            return jsonify({"message": "You are not allowed to do this"}), 403
        return render_template("index.html"), 403

    @app.errorhandler(404)
    def not_found(_error):
        if _wants_json():
            return jsonify({"message": "Not found"}), 404
        return render_template("index.html"), 404

    # ---- Your existing admin seeding command (unchanged from V1) ----
    @app.cli.command("init-db")
    def init_db_command():
        db.create_all()
        _migrate_legacy_bookings()

        admin = User.query.filter_by(role="admin").first()
        if not admin:
            admin = User(
                name="System Admin",
                email="admin@trek.local",
                role="admin",
                is_approved=True,
                is_blacklisted=False,
            )
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()
            print("Database initialized and default admin created.")
        else:
            print("Database initialized. Admin already exists.")

    return app


def _migrate_legacy_bookings():
    """Add fields introduced after the original V1 bookings table."""
    inspector = inspect(db.engine)
    if not inspector.has_table("bookings"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("bookings")}
    new_columns = {
        "payment_status": "VARCHAR(20) NOT NULL DEFAULT 'pending'",
        "participants": "INTEGER NOT NULL DEFAULT 1",
        "cancelled_at": "DATETIME",
    }
    with db.engine.begin() as connection:
        for column, definition in new_columns.items():
            if column not in existing_columns:
                connection.execute(text(f"ALTER TABLE bookings ADD COLUMN {column} {definition}"))
