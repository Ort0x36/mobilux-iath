from datetime import datetime
import sqlite3
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "mobilux-demo"
DB = Path(__file__).with_name("mobilux.db")

PACKAGES = {
    "city": {
        "name": "MOBILUX CITY",
        "theme": "Luxury European City Experience",
        "description": "Explore Europe's most iconic cities through art, architecture, gastronomy and culture.",
        "route": ["Milan", "Lyon", "Paris", "Amsterdam", "Berlin", "Prague", "Vienna", "Venice", "Milan"],
    },
    "nature": {
        "name": "MOBILUX NATURE",
        "theme": "Luxury Nature & Wellness Experience",
        "description": "Discover Europe's natural destinations through wellness, landscapes and exclusive outdoor experiences.",
        "route": ["Milan", "Chamonix", "Annecy", "Ortisei / Dolomites", "Innsbruck", "Salzburg", "Hallstatt", "Lake Bled", "Milan"],
    },
}

SERVICES = [
    "Premium food and beverage service",
    "Special dietary requirements",
    "Private guided tours",
    "Additional wellness experiences",
    "Personalized concierge assistance",
    "Special celebrations",
    "Extra luggage requests",
]

def connect():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference TEXT NOT NULL,
                package TEXT NOT NULL,
                departure_date TEXT,
                passengers INTEGER NOT NULL,
                customer_name TEXT NOT NULL,
                email TEXT NOT NULL,
                pickup_address TEXT NOT NULL,
                pickup_preference TEXT NOT NULL,
                services TEXT,
                notes TEXT,
                created_at TEXT NOT NULL
            )
        """)

@app.route("/")
def home():
    return render_template("index.html", packages=PACKAGES)

@app.route("/package/<code>")
def package(code):
    item = PACKAGES.get(code)
    if not item:
        return redirect(url_for("home"))
    return render_template("package.html", package=item, code=code)

@app.route("/book", methods=["GET", "POST"])
def book():
    selected = request.args.get("package", "city")
    if selected not in PACKAGES:
        selected = "city"

    if request.method == "POST":
        package_code = request.form.get("package", "city")
        if package_code not in PACKAGES:
            package_code = "city"

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()
        passengers = request.form.get("passengers", "1")
        date = request.form.get("departure_date", "")
        preference = request.form.get("pickup_preference", "Nearest designated pick-up point")
        services = request.form.getlist("services")
        notes = request.form.get("notes", "").strip()

        if not name or not email or not address:
            flash("Please complete your name, email and pick-up address.")
            return render_template("book.html", packages=PACKAGES, selected=package_code, services=SERVICES)

        try:
            passengers = max(1, min(8, int(passengers)))
        except ValueError:
            passengers = 1

        with connect() as db:
            cursor = db.execute("""
                INSERT INTO bookings
                (reference, package, departure_date, passengers, customer_name, email,
                 pickup_address, pickup_preference, services, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "MLX-" + datetime.now().strftime("%y%m%d%H%M%S"),
                PACKAGES[package_code]["name"], date, passengers, name, email,
                address, preference, ", ".join(services), notes,
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ))
            booking_id = cursor.lastrowid
            booking = db.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()

        return render_template("confirmation.html", booking=booking)

    return render_template("book.html", packages=PACKAGES, selected=selected, services=SERVICES)

@app.route("/my-journey", methods=["GET", "POST"])
def my_journey():
    booking = None
    if request.method == "POST":
        reference = request.form.get("reference", "").strip()
        email = request.form.get("email", "").strip()
        with connect() as db:
            booking = db.execute(
                "SELECT * FROM bookings WHERE reference = ? AND email = ? ORDER BY id DESC LIMIT 1",
                (reference, email)
            ).fetchone()
        if not booking:
            flash("No demonstration booking found. Check the reference and email.")
    return render_template("my_journey.html", booking=booking)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
