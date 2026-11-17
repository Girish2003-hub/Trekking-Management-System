import re

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user

from app.api.helpers import user_json
from app.extensions import db
from app.models import User


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
NAME_REGEX = re.compile(r"^[A-Za-z][A-Za-z .'-]*$")
CONTACT_REGEX = re.compile(r"^\+?[0-9\s-]{10,20}$")


@auth_bp.route("/login", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return jsonify({"user": user_json(current_user)}), 200

    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"message": "Request body must be a JSON object."}), 400
    email = data.get("email", "")
    password = data.get("password", "")
    if not isinstance(email, str) or not isinstance(password, str):
        return jsonify({"message": "Email and password must be text."}), 400
    email = email.strip().lower()

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"message": "Invalid email or password."}), 401

    if user.is_blacklisted:
        return jsonify({"message": "Your account is blacklisted. Contact admin."}), 403

    if not user.is_approved:
        return jsonify({"message": "Your account is deactivated. Contact admin."}), 403

    login_user(user)
    return jsonify({"user": user_json(user)}), 200


@auth_bp.route("/register", methods=["POST"])
def register():
    if current_user.is_authenticated:
        return jsonify({"message": "You are already logged in."}), 400

    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"message": "Request body must be a JSON object."}), 400
    name = data.get("name", "")
    email = data.get("email", "")
    contact = data.get("contact", "")
    password = data.get("password", "")
    confirm_password = data.get("confirm_password")

    if not all(isinstance(value, str) for value in (name, email, contact, password)):
        return jsonify({"message": "Registration fields must be text."}), 400
    if confirm_password is not None and not isinstance(confirm_password, str):
        return jsonify({"message": "Confirm password must be text."}), 400
    name = name.strip()
    email = email.strip().lower()
    contact = contact.strip()
    if not name or not email or not password:
        return jsonify({"message": "Name, email and password are required."}), 400
    if len(name) < 2 or len(name) > 120 or not NAME_REGEX.match(name):
        return jsonify({"message": "Enter a valid name (2-120 chars, letters/spaces only)."}), 400
    if len(email) > 255 or not EMAIL_REGEX.match(email):
        return jsonify({"message": "Enter a valid email address."}), 400
    if contact and (len(contact) > 50 or not CONTACT_REGEX.match(contact)):
        return jsonify({"message": "Enter a valid contact number."}), 400
    if len(password) < 8 or len(password) > 128:
        return jsonify({"message": "Password must be 8-128 characters long."}), 400
    if not re.search(r"[A-Z]", password):
        return jsonify({"message": "Password must include at least one uppercase letter."}), 400
    if not re.search(r"[a-z]", password):
        return jsonify({"message": "Password must include at least one lowercase letter."}), 400
    if not re.search(r"\d", password):
        return jsonify({"message": "Password must include at least one number."}), 400
    if not re.search(r"[^A-Za-z0-9]", password):
        return jsonify({"message": "Password must include at least one special character."}), 400
    if confirm_password is not None and password != confirm_password:
        return jsonify({"message": "Password and confirm password do not match."}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"message": "Email already registered."}), 409

    user = User(
        name=name,
        email=email,
        role="user",
        contact=contact,
        is_approved=True,
        is_blacklisted=False,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    login_user(user)
    return jsonify({
        "message": "Registration successful.",
        "user": user_json(user),
    }), 201


@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out successfully."}), 200


@auth_bp.get("/me")
def me():
    if not current_user.is_authenticated:
        return jsonify({"message": "Login required."}), 401
    return jsonify({"user": user_json(current_user)}), 200
