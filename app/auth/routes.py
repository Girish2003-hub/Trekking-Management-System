import os
import re

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.models import User


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
NAME_REGEX = re.compile(r"^[A-Za-z][A-Za-z .'-]*$")
CONTACT_REGEX = re.compile(r"^\+?[0-9\s-]{10,20}$")


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
        confirm_password = request.form.get("confirm_password", "")

        if role not in {"user", "staff"}:
            flash("Invalid role selection.", "danger")
            return render_template("auth/register.html", trek_images=trek_images)

        if not name or not email or not password:
            flash("Name, email and password are required.", "danger")
            return render_template("auth/register.html", trek_images=trek_images)

        if len(name) < 2 or len(name) > 120 or not NAME_REGEX.match(name):
            flash("Enter a valid name (2-120 chars, letters/spaces only).", "danger")
            return render_template("auth/register.html", trek_images=trek_images)

        if len(email) > 255 or not EMAIL_REGEX.match(email):
            flash("Enter a valid email address.", "danger")
            return render_template("auth/register.html", trek_images=trek_images)

        if contact:
            if len(contact) > 50 or not CONTACT_REGEX.match(contact):
                flash("Enter a valid contact number.", "danger")
                return render_template("auth/register.html", trek_images=trek_images)

        if len(password) < 8 or len(password) > 128:
            flash("Password must be 8-128 characters long.", "danger")
            return render_template("auth/register.html", trek_images=trek_images)

        if not re.search(r"[A-Z]", password):
            flash("Password must include at least one uppercase letter.", "danger")
            return render_template("auth/register.html", trek_images=trek_images)

        if not re.search(r"[a-z]", password):
            flash("Password must include at least one lowercase letter.", "danger")
            return render_template("auth/register.html", trek_images=trek_images)

        if not re.search(r"\d", password):
            flash("Password must include at least one number.", "danger")
            return render_template("auth/register.html", trek_images=trek_images)

        if not re.search(r"[^A-Za-z0-9]", password):
            flash("Password must include at least one special character.", "danger")
            return render_template("auth/register.html", trek_images=trek_images)

        if password != confirm_password:
            flash("Password and confirm password do not match.", "danger")
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
