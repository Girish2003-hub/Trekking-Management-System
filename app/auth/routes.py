import os

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.models import User


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _get_trek_images():
    trek_images = []
    trek_images_dir = os.path.join(current_app.static_folder, "images", "treks")
    if os.path.isdir(trek_images_dir):
        allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
        for file_name in sorted(os.listdir(trek_images_dir)):
            ext = os.path.splitext(file_name)[1].lower()
            if ext in allowed_extensions:
                trek_images.append(f"images/treks/{file_name}")
    return trek_images


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    trek_images = _get_trek_images()

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html", trek_images=trek_images)

        if user.is_blacklisted:
            flash("Your account is blacklisted. Contact admin.", "danger")
            return render_template("auth/login.html", trek_images=trek_images)

        if user.role == "user" and not user.is_approved:
            flash("Your account is deactivated. Contact admin.", "danger")
            return render_template("auth/login.html", trek_images=trek_images)

        if user.role == "staff" and not user.is_approved:
            flash("Your staff account is pending admin approval or deactivated.", "warning")
            return render_template("auth/login.html", trek_images=trek_images)

        login_user(user)
        flash("Logged in successfully.", "success")
        return redirect(url_for("home"))

    return render_template("auth/login.html", trek_images=trek_images)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    trek_images = _get_trek_images()

    if request.method == "POST":
        role = request.form.get("role", "user")
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        contact = request.form.get("contact", "").strip()
        password = request.form.get("password", "")

        if role not in {"user", "staff"}:
            flash("Invalid role selection.", "danger")
            return render_template("auth/register.html", trek_images=trek_images)

        if not name or not email or not password:
            flash("Name, email and password are required.", "danger")
            return render_template("auth/register.html", trek_images=trek_images)

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("Email already registered.", "warning")
            return render_template("auth/register.html", trek_images=trek_images)

        user = User(
            name=name,
            email=email,
            role=role,
            contact=contact,
            is_approved=(role == "user"),
            is_blacklisted=False,
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        if role == "staff":
            flash("Staff registration submitted. Wait for admin approval.", "info")
            return redirect(url_for("home"))
        else:
            login_user(user)
            flash("Registration successful. You are now logged in.", "success")
            return redirect(url_for("user.dashboard"))

    return render_template("auth/register.html", trek_images=trek_images)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "success")
    return redirect(url_for("auth.login"))
