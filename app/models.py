from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")
    is_approved = db.Column(db.Boolean, nullable=False, default=False)
    is_blacklisted = db.Column(db.Boolean, nullable=False, default=False)
    contact = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    staff_treks = db.relationship("Trek", backref="assigned_staff", foreign_keys="Trek.assigned_staff_id")
    bookings = db.relationship("Booking", backref="trekker", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Trek(db.Model):
    __tablename__ = "treks"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(120), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    duration_days = db.Column(db.Integer, nullable=False)
    total_slots = db.Column(db.Integer, nullable=False)
    available_slots = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    assigned_staff_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_by_admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    bookings = db.relationship("Booking", backref="trek", lazy=True)


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    trek_id = db.Column(db.Integer, db.ForeignKey("treks.id"), nullable=False)
    booking_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    # booked / cancelled / completed
    status = db.Column(db.String(20), nullable=False, default="booked")
    # pending / paid / refunded (simulated payment)
    payment_status = db.Column(db.String(20), nullable=False, default="pending")
    participants = db.Column(db.Integer, nullable=False, default=1)
    cancelled_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "trek_id": self.trek_id,
            "trek_name": self.trek.name if self.trek else None,
            "location": self.trek.location if self.trek else None,
            "start_date": self.trek.start_date.isoformat() if self.trek else None,
            "end_date": self.trek.end_date.isoformat() if self.trek else None,
            "booking_date": self.booking_date.isoformat(),
            "status": self.status,
            "payment_status": self.payment_status,
            "participants": self.participants,
        }


class StaffProfile(db.Model):
    """Extra details for users whose role is 'staff' (one-to-one with User)."""

    __tablename__ = "staff_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    experience_years = db.Column(db.Integer, nullable=False, default=0)
    specialization = db.Column(db.String(120), nullable=True)  # e.g. "High altitude"
    # active / inactive / blacklisted
    status = db.Column(db.String(20), nullable=False, default="active")

    user = db.relationship("User", backref=db.backref("staff_profile", uselist=False))

    def to_dict(self):
        return {
            "staff_id": self.user_id,
            "name": self.user.name,
            "email": self.user.email,
            "phone": self.phone,
            "experience_years": self.experience_years,
            "specialization": self.specialization,
            "status": self.status,
            "assigned_treks": [t.name for t in self.user.staff_treks],
        }


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
