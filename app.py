import os
import secrets
import sqlite3
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("IRONHUB_DB_PATH", BASE_DIR / "ironhub.db"))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("IRONHUB_SECRET_KEY", "ironhub-sivagangai-dev-key")
app.config["ADMIN_USERNAME"] = os.environ.get("IRONHUB_ADMIN_USER", "admin")
app.config["ADMIN_PASSWORD"] = os.environ.get("IRONHUB_ADMIN_PASSWORD", "ironhub-admin")

PLANS = [
    {
        "id": "trial",
        "name": "7-Day Trial",
        "price": "₹299",
        "period": "one week",
        "points": ["Full gym access", "1 trainer intro session", "Locker use"],
    },
    {
        "id": "monthly",
        "name": "Monthly",
        "price": "₹999",
        "period": "/ month",
        "featured": True,
        "points": ["Unlimited training hours", "Group classes", "Diet starter plan"],
    },
    {
        "id": "quarterly",
        "name": "Quarterly",
        "price": "₹2,699",
        "period": "/ 3 months",
        "points": ["Save vs monthly", "Body assessment", "Priority class slots"],
    },
    {
        "id": "yearly",
        "name": "Iron Year",
        "price": "₹8,999",
        "period": "/ year",
        "points": ["Best value", "2 PT sessions / month", "Guest pass each quarter"],
    },
]

CLASSES = [
    {
        "title": "Strength Forge",
        "time": "6:00 – 7:00 AM",
        "blurb": "Compound lifts, progressive overload, and real iron work.",
    },
    {
        "title": "HIIT Burn",
        "time": "7:15 – 8:00 AM",
        "blurb": "Short, intense intervals to cut fat and raise stamina.",
    },
    {
        "title": "Functional Fit",
        "time": "6:00 – 7:00 PM",
        "blurb": "Kettlebells, sled, and bodyweight for everyday strength.",
    },
    {
        "title": "Core & Mobility",
        "time": "7:15 – 8:00 PM",
        "blurb": "Spine health, hips, and recovery so you can train harder.",
    },
]

DEFAULT_SETTINGS = {
    "gym_phone": "+91 98765 43210",
    "gym_email": "hello@ironhub.sivagangai",
    "gym_address": "Near New Bus Stand, Sivagangai, Tamil Nadu 630561",
    "hours_week": "Mon–Sat 5:30 AM – 10:00 PM",
    "hours_sunday": "Sun 6:00 AM – 1:00 PM",
    "tagline": "Strength gym in the heart of Sivagangai. Train hard. Stay consistent.",
    "plan_trial_price": "₹299",
    "plan_monthly_price": "₹999",
    "plan_quarterly_price": "₹2,699",
    "plan_yearly_price": "₹8,999",
}

SETTING_FIELDS = [
    ("gym_phone", "Phone"),
    ("gym_email", "Email"),
    ("gym_address", "Address"),
    ("hours_week", "Weekday hours"),
    ("hours_sunday", "Sunday hours"),
    ("tagline", "Footer tagline"),
    ("plan_trial_price", "7-day trial price"),
    ("plan_monthly_price", "Monthly price"),
    ("plan_quarterly_price", "Quarterly price"),
    ("plan_yearly_price", "Yearly price"),
]


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS enquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            plan TEXT NOT NULL,
            preferred_slot TEXT NOT NULL,
            message TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS site_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )
    username = app.config["ADMIN_USERNAME"]
    existing = db.execute("SELECT id FROM admins WHERE username = ?", (username,)).fetchone()
    if existing is None:
        db.execute(
            "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(app.config["ADMIN_PASSWORD"])),
        )
    for key, value in DEFAULT_SETTINGS.items():
        db.execute(
            "INSERT OR IGNORE INTO site_settings (key, value) VALUES (?, ?)",
            (key, value),
        )
    db.commit()
    db.close()


def get_settings():
    if "settings" not in g:
        rows = get_db().execute("SELECT key, value FROM site_settings").fetchall()
        data = dict(DEFAULT_SETTINGS)
        data.update({row["key"]: row["value"] for row in rows})
        g.settings = data
    return g.settings


def get_plans():
    settings = get_settings()
    prices = {
        "trial": settings["plan_trial_price"],
        "monthly": settings["plan_monthly_price"],
        "quarterly": settings["plan_quarterly_price"],
        "yearly": settings["plan_yearly_price"],
    }
    plans = []
    for plan in PLANS:
        item = dict(plan)
        item["price"] = prices.get(plan["id"], plan["price"])
        plans.append(item)
    return plans


def phone_to_tel(phone):
    digits = "".join(ch for ch in phone if ch.isdigit())
    if not digits:
        return "#"
    if digits.startswith("91"):
        return f"+{digits}"
    if len(digits) == 10:
        return f"+91{digits}"
    return f"+{digits}"


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]


def validate_csrf():
    token = request.form.get("csrf_token", "")
    if not token or token != session.get("csrf_token"):
        abort(400)


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_user"):
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


@app.context_processor
def inject_globals():
    settings = get_settings()
    return {
        "gym_name": "IRONHUB",
        "gym_city": "Sivagangai",
        "gym_phone": settings["gym_phone"],
        "gym_email": settings["gym_email"],
        "gym_address": settings["gym_address"],
        "hours_week": settings["hours_week"],
        "hours_sunday": settings["hours_sunday"],
        "tagline": settings["tagline"],
        "gym_tel": phone_to_tel(settings["gym_phone"]),
        "plans": get_plans(),
        "year": datetime.now().year,
        "csrf_token": csrf_token,
        "admin_user": session.get("admin_user"),
    }


@app.route("/")
def home():
    return render_template("index.html", classes=CLASSES)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/training")
def training():
    return render_template("training.html", classes=CLASSES)


@app.route("/membership")
def membership():
    return render_template("membership.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    plans = get_plans()
    if request.method == "POST":
        full_name = (request.form.get("full_name") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        email = (request.form.get("email") or "").strip()
        plan = (request.form.get("plan") or "").strip()
        preferred_slot = (request.form.get("preferred_slot") or "").strip()
        message = (request.form.get("message") or "").strip()

        errors = []
        if len(full_name) < 2:
            errors.append("Please enter your full name.")
        if len(phone) < 10:
            errors.append("Please enter a valid mobile number.")
        if plan not in {p["id"] for p in plans}:
            errors.append("Please choose a membership plan.")
        if preferred_slot not in {"morning", "evening", "flexible"}:
            errors.append("Please choose a preferred time.")

        if errors:
            for item in errors:
                flash(item, "error")
            return render_template(
                "contact.html",
                form={
                    "full_name": full_name,
                    "phone": phone,
                    "email": email,
                    "plan": plan,
                    "preferred_slot": preferred_slot,
                    "message": message,
                },
            )

        db = get_db()
        db.execute(
            """
            INSERT INTO enquiries
                (full_name, phone, email, plan, preferred_slot, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                full_name,
                phone,
                email,
                plan,
                preferred_slot,
                message,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        db.commit()
        flash("Thanks. The IRONHUB team in Sivagangai will call you shortly.", "success")
        return redirect(url_for("contact"))

    selected = request.args.get("plan", "")
    return render_template("contact.html", form={"plan": selected})


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_user"):
        return redirect(url_for("admin_cms"))

    if request.method == "POST":
        validate_csrf()
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        row = get_db().execute(
            "SELECT username, password_hash FROM admins WHERE username = ?",
            (username,),
        ).fetchone()
        if row and check_password_hash(row["password_hash"], password):
            session["admin_user"] = row["username"]
            session.permanent = True
            flash("Signed in to IRONHUB CMS.", "success")
            nxt = request.args.get("next") or url_for("admin_cms")
            if not nxt.startswith("/admin"):
                nxt = url_for("admin_cms")
            return redirect(nxt)
        flash("Invalid username or password.", "error")

    return render_template("admin/login.html")


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    validate_csrf()
    session.pop("admin_user", None)
    flash("Signed out.", "success")
    return redirect(url_for("admin_login"))


@app.route("/admin", methods=["GET", "POST"])
@admin_required
def admin_cms():
    db = get_db()
    if request.method == "POST":
        validate_csrf()
        for key, _label in SETTING_FIELDS:
            value = (request.form.get(key) or "").strip()
            if not value:
                flash(f"{_label} cannot be empty.", "error")
                return redirect(url_for("admin_cms"))
            db.execute(
                "INSERT INTO site_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
        db.commit()
        g.pop("settings", None)
        flash("Website content updated.", "success")
        return redirect(url_for("admin_cms"))

    enquiries = db.execute(
        "SELECT * FROM enquiries ORDER BY id DESC"
    ).fetchall()
    return render_template(
        "admin/cms.html",
        enquiries=enquiries,
        settings=get_settings(),
        setting_fields=SETTING_FIELDS,
    )


init_db()


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
