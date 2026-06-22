import os

from flask import Flask, flash, redirect, render_template, url_for
from flask_login import current_user

from config import Config
from app.extensions import db, login_manager
from app.models import User


def _get_trek_images(static_folder):
    trek_images = []
    trek_images_dir = os.path.join(static_folder, "images", "treks")
    if os.path.isdir(trek_images_dir):
        allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
        for file_name in sorted(os.listdir(trek_images_dir)):
            ext = os.path.splitext(file_name)[1].lower()
            if ext in allowed_extensions:
                trek_images.append(f"images/treks/{file_name}")
    return trek_images


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    from app.auth.routes import auth_bp
    from app.admin.routes import admin_bp
    from app.staff.routes import staff_bp
    from app.user.routes import user_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(user_bp)

    @app.route("/")
    def home():
        if current_user.is_authenticated:
            if current_user.role == "admin":
                return redirect(url_for("admin.dashboard"))
            if current_user.role == "staff":
                return redirect(url_for("staff.dashboard"))
            return redirect(url_for("user.dashboard"))

        trek_images = _get_trek_images(app.static_folder)

        return render_template("shared/index.html", trek_images=trek_images)

    @app.route("/about")
    def about():
        trek_images = _get_trek_images(app.static_folder)
        return render_template("shared/about.html", trek_images=trek_images)

    @app.errorhandler(401)
    def unauthorized(_error):
        flash("Please log in first.", "warning")
        return redirect(url_for("auth.login"))

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("shared/forbidden.html"), 403

    @app.cli.command("init-db")
    def init_db_command():
        db.create_all()

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
