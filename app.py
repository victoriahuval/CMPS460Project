from functools import wraps
import os
import secrets
import sqlite3

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "sims4_catalog.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def initialize_database():
    db = sqlite3.connect(DATABASE)
    with open(os.path.join(BASE_DIR, "schema.sql"), "r", encoding="utf-8") as schema_file:
        db.executescript(schema_file.read())

    admin_exists = db.execute("SELECT 1 FROM users WHERE username = ?", ("admin",)).fetchone()
    if not admin_exists:
        db.execute(
            """
            INSERT INTO users (username, password_hash, role)
            VALUES (?, ?, ?)
            """,
            ("admin", generate_password_hash("admin123"), "admin"),
        )
    db.commit()
    db.close()


if not os.path.exists(DATABASE):
    initialize_database()


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(**kwargs)

    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if session.get("role") != "admin":
            abort(403)
        return view(**kwargs)

    return wrapped_view


def get_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]


def validate_csrf():
    if request.form.get("csrf_token") != session.get("csrf_token"):
        abort(400, "Invalid CSRF token.")


@app.context_processor
def inject_globals():
    return {"csrf_token": get_csrf_token()}


@app.route("/")
def index():
    db = get_db()
    stats = {
        "packs": db.execute("SELECT COUNT(*) AS count FROM skin_packs").fetchone()["count"],
        "creators": db.execute("SELECT COUNT(*) AS count FROM creators").fetchone()["count"],
        "categories": db.execute("SELECT COUNT(*) AS count FROM categories").fetchone()["count"],
        "downloads": db.execute("SELECT COUNT(*) AS count FROM downloads").fetchone()["count"],
    }
    featured_packs = db.execute(
        """
        SELECT sp.pack_id, sp.pack_name, c.creator_name, cat.category_name, sp.price
        FROM skin_packs sp
        JOIN creators c ON sp.creator_id = c.creator_id
        JOIN categories cat ON sp.category_id = cat.category_id
        ORDER BY sp.pack_id DESC
        LIMIT 4
        """
    ).fetchall()
    return render_template("index.html", stats=stats, featured_packs=featured_packs)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        validate_csrf()
        username = request.form["username"].strip()
        password = request.form["password"]
        user = get_db().execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            session["csrf_token"] = secrets.token_hex(16)
            flash("Welcome back. You are now logged in.", "success")
            return redirect(url_for("index"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    validate_csrf()
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/skin-packs")
def skin_packs():
    search = request.args.get("search", "").strip()
    db = get_db()

    base_query = """
        SELECT
            sp.pack_id,
            sp.pack_name,
            c.creator_name,
            cat.category_name,
            cv.version_name,
            sp.price,
            sp.release_date,
            COALESCE(SUM(d.download_count), 0) AS total_downloads
        FROM skin_packs sp
        JOIN creators c ON sp.creator_id = c.creator_id
        JOIN categories cat ON sp.category_id = cat.category_id
        JOIN compatibility_versions cv ON sp.compatibility_id = cv.compatibility_id
        LEFT JOIN downloads d ON sp.pack_id = d.pack_id
    """
    params = ()
    if search:
        base_query += """
            WHERE sp.pack_name LIKE ?
               OR c.creator_name LIKE ?
               OR cat.category_name LIKE ?
        """
        like_search = f"%{search}%"
        params = (like_search, like_search, like_search)

    packs = db.execute(
        base_query
        + """
        GROUP BY sp.pack_id
        ORDER BY sp.pack_name
        """,
        params,
    ).fetchall()
    return render_template("skin_packs.html", packs=packs, search=search)


def load_pack_form_options():
    db = get_db()
    return {
        "creators": db.execute("SELECT * FROM creators ORDER BY creator_name").fetchall(),
        "categories": db.execute("SELECT * FROM categories ORDER BY category_name").fetchall(),
        "compatibility_versions": db.execute(
            "SELECT * FROM compatibility_versions ORDER BY version_name DESC"
        ).fetchall(),
        "tags": db.execute("SELECT * FROM tags ORDER BY tag_name").fetchall(),
    }


def save_pack(form, pack_id=None):
    db = get_db()
    selected_tags = request.form.getlist("tag_ids")
    pack_data = (
        form["pack_name"].strip(),
        form["creator_id"],
        form["category_id"],
        form["compatibility_id"],
        float(form["price"]),
        form["release_date"],
        form["description"].strip(),
        1 if form.get("is_default") == "on" else 0,
    )

    if pack_id is None:
        cursor = db.execute(
            """
            INSERT INTO skin_packs
            (pack_name, creator_id, category_id, compatibility_id, price, release_date, description, is_default)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            pack_data,
        )
        pack_id = cursor.lastrowid
    else:
        db.execute(
            """
            UPDATE skin_packs
            SET pack_name = ?, creator_id = ?, category_id = ?, compatibility_id = ?,
                price = ?, release_date = ?, description = ?, is_default = ?
            WHERE pack_id = ?
            """,
            pack_data + (pack_id,),
        )
        db.execute("DELETE FROM skin_pack_tags WHERE pack_id = ?", (pack_id,))

    for tag_id in selected_tags:
        db.execute(
            "INSERT INTO skin_pack_tags (pack_id, tag_id) VALUES (?, ?)",
            (pack_id, tag_id),
        )

    db.commit()


@app.route("/skin-packs/add", methods=["GET", "POST"])
@login_required
@admin_required
def add_skin_pack():
    options = load_pack_form_options()
    if request.method == "POST":
        validate_csrf()
        save_pack(request.form)
        flash("Skin pack added successfully.", "success")
        return redirect(url_for("skin_packs"))
    return render_template("skin_pack_form.html", pack=None, selected_tags=[], **options)


@app.route("/skin-packs/<int:pack_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_skin_pack(pack_id):
    db = get_db()
    pack = db.execute("SELECT * FROM skin_packs WHERE pack_id = ?", (pack_id,)).fetchone()
    if pack is None:
        abort(404)

    options = load_pack_form_options()
    selected_tags = [
        row["tag_id"]
        for row in db.execute(
            "SELECT tag_id FROM skin_pack_tags WHERE pack_id = ?",
            (pack_id,),
        ).fetchall()
    ]

    if request.method == "POST":
        validate_csrf()
        save_pack(request.form, pack_id)
        flash("Skin pack updated successfully.", "success")
        return redirect(url_for("skin_packs"))

    return render_template(
        "skin_pack_form.html",
        pack=pack,
        selected_tags=selected_tags,
        **options,
    )


@app.route("/skin-packs/<int:pack_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_skin_pack(pack_id):
    validate_csrf()
    db = get_db()
    db.execute("DELETE FROM skin_packs WHERE pack_id = ?", (pack_id,))
    db.commit()
    flash("Skin pack deleted.", "success")
    return redirect(url_for("skin_packs"))


@app.route("/creators", methods=["GET", "POST"])
@login_required
@admin_required
def creators():
    db = get_db()
    if request.method == "POST":
        validate_csrf()
        db.execute(
            """
            INSERT INTO creators (creator_name, platform_name, country_name)
            VALUES (?, ?, ?)
            """,
            (
                request.form["creator_name"].strip(),
                request.form["platform_name"].strip(),
                request.form["country_name"].strip(),
            ),
        )
        db.commit()
        flash("Creator added successfully.", "success")
        return redirect(url_for("creators"))

    creator_rows = db.execute(
        """
        SELECT c.*, COUNT(sp.pack_id) AS pack_count
        FROM creators c
        LEFT JOIN skin_packs sp ON c.creator_id = sp.creator_id
        GROUP BY c.creator_id
        ORDER BY c.creator_name
        """
    ).fetchall()
    return render_template("creators.html", creators=creator_rows)


@app.route("/creators/<int:creator_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_creator(creator_id):
    validate_csrf()
    db = get_db()
    pack_count = db.execute(
        "SELECT COUNT(*) AS count FROM skin_packs WHERE creator_id = ?",
        (creator_id,),
    ).fetchone()["count"]
    if pack_count > 0:
        flash("That creator still has skin packs assigned and cannot be deleted yet.", "danger")
    else:
        db.execute("DELETE FROM creators WHERE creator_id = ?", (creator_id,))
        db.commit()
        flash("Creator deleted.", "success")
    return redirect(url_for("creators"))


@app.route("/categories", methods=["GET", "POST"])
@login_required
@admin_required
def categories():
    db = get_db()
    if request.method == "POST":
        validate_csrf()
        db.execute(
            "INSERT INTO categories (category_name, mood_style) VALUES (?, ?)",
            (
                request.form["category_name"].strip(),
                request.form["mood_style"].strip(),
            ),
        )
        db.commit()
        flash("Category added successfully.", "success")
        return redirect(url_for("categories"))

    category_rows = db.execute(
        """
        SELECT cat.*, COUNT(sp.pack_id) AS pack_count
        FROM categories cat
        LEFT JOIN skin_packs sp ON cat.category_id = sp.category_id
        GROUP BY cat.category_id
        ORDER BY cat.category_name
        """
    ).fetchall()
    return render_template("categories.html", categories=category_rows)


@app.route("/reports/creators")
def creator_report():
    rows = get_db().execute(
        """
        SELECT c.creator_name, c.platform_name, COUNT(sp.pack_id) AS total_packs,
               ROUND(AVG(sp.price), 2) AS average_price
        FROM creators c
        LEFT JOIN skin_packs sp ON c.creator_id = sp.creator_id
        GROUP BY c.creator_id
        ORDER BY total_packs DESC, c.creator_name
        """
    ).fetchall()
    return render_template("report_creators.html", rows=rows)


@app.route("/reports/categories")
def category_report():
    rows = get_db().execute(
        """
        SELECT cat.category_name, cat.mood_style, COUNT(sp.pack_id) AS total_packs
        FROM categories cat
        LEFT JOIN skin_packs sp ON cat.category_id = sp.category_id
        GROUP BY cat.category_id
        ORDER BY total_packs DESC, cat.category_name
        """
    ).fetchall()
    return render_template("report_categories.html", rows=rows)


@app.route("/reports/downloads")
def download_report():
    rows = get_db().execute(
        """
        SELECT sp.pack_name, c.creator_name, COALESCE(SUM(d.download_count), 0) AS total_downloads
        FROM skin_packs sp
        JOIN creators c ON sp.creator_id = c.creator_id
        LEFT JOIN downloads d ON sp.pack_id = d.pack_id
        GROUP BY sp.pack_id
        ORDER BY total_downloads DESC, sp.pack_name
        """
    ).fetchall()
    return render_template("report_downloads.html", rows=rows)


@app.route("/reset-database", methods=["POST"])
@login_required
@admin_required
def reset_database():
    validate_csrf()
    initialize_database()
    flash("Database was reset and sample data was reloaded.", "warning")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
