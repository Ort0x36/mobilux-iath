from datetime import datetime
import os
import sqlite3
from pathlib import Path
from flask import (Flask, render_template, request, redirect, url_for, flash,
                   g, session, abort, make_response)
from werkzeug.datastructures import MultiDict
from i18n import (LANGUAGES, DEFAULT_LANGUAGE, LANGUAGE_COOKIE, translate,
                  format_date)

app = Flask(__name__)
app.secret_key = "mobilux-demo"
# Public base URL used for canonical, hreflang and sitemap links,
# e.g. SITE_URL=https://www.example.com. Falls back to the request host.
app.config["SITE_URL"] = os.environ.get("SITE_URL", "").rstrip("/")
DB = Path(__file__).with_name("mobilux.db")

# Names are brand names and stay the same in every language. Themes,
# descriptions and stop names are translated in translations/*.json.
PACKAGES = {
    "city": {
        "name": "MOBILUX CITY",
        "image": "https://images.unsplash.com/photo-1499856871958-5b9627545d1a?auto=format&fit=crop&w=1100&q=80",
        "route": ["milan", "lyon", "paris", "amsterdam", "berlin", "prague", "vienna", "venice", "milan"],
    },
    "nature": {
        "name": "MOBILUX NATURE",
        "image": "https://images.unsplash.com/photo-1472396961693-142e6e269027?auto=format&fit=crop&w=1100&q=80",
        "route": ["milan", "chamonix", "annecy", "ortisei", "innsbruck", "salzburg", "hallstatt", "bled", "milan"],
    },
}

# Stored values stay in English so existing bookings remain readable;
# labels are translated at display time via the "service." and "pickup." keys.
SERVICES = [
    "Premium food and beverage service",
    "Special dietary requirements",
    "Private guided tours",
    "Additional wellness experiences",
    "Personalized concierge assistance",
    "Special celebrations",
    "Extra luggage requests",
]

PICKUP_OPTIONS = [
    "Nearest designated pick-up point (demonstration)",
    "Request home collection (subject to availability)",
]
DEFAULT_PICKUP = "Nearest designated pick-up point"

# Public pages listed in the sitemap.
SITEMAP_PAGES = [("home", {})] + [("package", {"code": code}) for code in PACKAGES] + [
    ("book", {}), ("my_journey", {})]

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

# --- Localization -----------------------------------------------------------
# Italian pages live at the root ("/book"), other languages under a prefix
# ("/en/book"). Each localized view is registered once per URL shape.

LOCALIZED_ENDPOINTS = set()
_PREFIXED = "/<any({}):lang_code>".format(
    ",".join(code for code in LANGUAGES if code != DEFAULT_LANGUAGE))

def localized_route(rule, **options):
    def decorator(view):
        endpoint = view.__name__
        LOCALIZED_ENDPOINTS.add(endpoint)
        app.add_url_rule(rule, endpoint, view, defaults={"lang_code": DEFAULT_LANGUAGE}, **options)
        app.add_url_rule(_PREFIXED + rule, endpoint, view, **options)
        return view
    return decorator

def current_lang():
    if "lang" not in g:
        prefix = request.path.strip("/").split("/", 1)[0]
        g.lang = prefix if prefix in LANGUAGES else DEFAULT_LANGUAGE
    return g.lang

def t(key, **params):
    return translate(current_lang(), key, **params)

@app.url_value_preprocessor
def pull_lang(endpoint, values):
    if values and "lang_code" in values:
        g.lang = values.pop("lang_code")

@app.url_defaults
def add_lang(endpoint, values):
    if endpoint in LOCALIZED_ENDPOINTS:
        values.setdefault("lang_code", current_lang())

def localized_url(lang, keep_query=True):
    """URL of the current page in another language (home page if not localized)."""
    if request.endpoint not in LOCALIZED_ENDPOINTS:
        return url_for("home", lang_code=lang)
    values = dict(request.view_args or {}, lang_code=lang)
    if keep_query:
        for key, items in request.args.lists():
            values.setdefault(key, items)
    return url_for(request.endpoint, **values)

def absolute(path):
    return (app.config["SITE_URL"] or request.host_url.rstrip("/")) + path

@app.before_request
def apply_saved_language():
    # An explicit choice made with the language selector wins over the URL.
    if request.method != "GET" or request.endpoint not in LOCALIZED_ENDPOINTS:
        return None
    saved = request.cookies.get(LANGUAGE_COOKIE)
    if saved in LANGUAGES and saved != current_lang():
        return redirect(localized_url(saved))
    return None

@app.after_request
def vary_on_cookie(response):
    response.vary.add("Cookie")
    return response

@app.route("/lang/<code>")
def set_language(code):
    if code not in LANGUAGES:
        abort(404)
    target = request.args.get("next", "")
    if not target.startswith("/") or target.startswith("//") or "\\" in target:
        target = url_for("home", lang_code=code)
    response = redirect(target)
    response.set_cookie(LANGUAGE_COOKIE, code, max_age=365 * 24 * 3600, samesite="Lax")
    response.headers["X-Robots-Tag"] = "noindex"
    return response

@app.context_processor
def inject_i18n():
    lang = current_lang()
    localized = request.endpoint in LOCALIZED_ENDPOINTS
    switch = {code: url_for("set_language", code=code, next=localized_url(code))
              for code in LANGUAGES}
    alternates = {}
    if localized:
        alternates = {LANGUAGES[code]["hreflang"]: absolute(localized_url(code, keep_query=False))
                      for code in LANGUAGES}
    return {
        "t": t,
        "lang": lang,
        "languages": LANGUAGES,
        "switch_urls": switch,
        "alternates": alternates,
        "default_alternate": alternates.get(LANGUAGES[DEFAULT_LANGUAGE]["hreflang"]),
        "canonical": absolute(localized_url(lang, keep_query=False)) if localized else None,
        "absolute": absolute,
        "service_label": lambda value: translate(lang, f"service.{value}") if value in SERVICES else value,
        "format_date": lambda value: format_date(lang, value),
    }

# --- Pages ------------------------------------------------------------------

@localized_route("/")
def home():
    return render_template("index.html", packages=PACKAGES)

@localized_route("/package/<code>")
def package(code):
    item = PACKAGES.get(code)
    if not item:
        return redirect(url_for("home"))
    return render_template("package.html", package=item, code=code)

@localized_route("/book", methods=["GET", "POST"])
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
        preference = request.form.get("pickup_preference", DEFAULT_PICKUP)
        if preference not in PICKUP_OPTIONS:
            preference = DEFAULT_PICKUP
        services = [s for s in request.form.getlist("services") if s in SERVICES]
        notes = request.form.get("notes", "").strip()

        error = None
        if not name or not email or not address:
            error = t("book.error_required")
        elif "@" not in email:
            error = t("book.error_email")
        if error:
            flash(error, "error")
            return render_template("book.html", packages=PACKAGES, selected=package_code,
                                   services=SERVICES, pickup_options=PICKUP_OPTIONS, form=request.form)

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
            session["booking_id"] = cursor.lastrowid

        # Redirect so a refresh does not resubmit and the page can be viewed in either language.
        return redirect(url_for("confirmation"))

    return render_template("book.html", packages=PACKAGES, selected=selected,
                           services=SERVICES, pickup_options=PICKUP_OPTIONS, form=MultiDict())

@localized_route("/book/confirmation")
def confirmation():
    booking = None
    if "booking_id" in session:
        with connect() as db:
            booking = db.execute("SELECT * FROM bookings WHERE id = ?", (session["booking_id"],)).fetchone()
    if not booking:
        return redirect(url_for("book"))
    return render_template("confirmation.html", booking=booking, noindex=True)

@localized_route("/my-journey", methods=["GET", "POST"])
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
            flash(t("journey.not_found"), "error")
    return render_template("my_journey.html", booking=booking, form=request.form)

# --- SEO and errors ---------------------------------------------------------

@app.route("/sitemap.xml")
def sitemap():
    entries = [{LANGUAGES[code]["hreflang"]: absolute(url_for(endpoint, lang_code=code, **values))
                for code in LANGUAGES} for endpoint, values in SITEMAP_PAGES]
    response = make_response(render_template("sitemap.xml", entries=entries,
                                             default=LANGUAGES[DEFAULT_LANGUAGE]["hreflang"]))
    response.mimetype = "application/xml"
    return response

@app.route("/robots.txt")
def robots():
    body = f"User-agent: *\nDisallow: /lang/\n\nSitemap: {absolute(url_for('sitemap'))}\n"
    response = make_response(body)
    response.mimetype = "text/plain"
    return response

@app.errorhandler(404)
def not_found(error):
    return render_template("404.html", noindex=True), 404

if __name__ == "__main__":
    init_db()
    # Also restart the dev server when translation files change; they are read once at startup.
    app.run(debug=True, extra_files=[str(p) for p in Path(__file__).with_name("translations").glob("*.json")])
