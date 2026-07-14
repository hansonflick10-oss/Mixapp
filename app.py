import os
import sqlite3
from pathlib import Path
from flask import Flask, redirect, render_template, request, session, url_for, send_from_directory
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)


def get_db_connection(config=None):
    config = config or {}
    db_path = config.get("DATABASE_FILE") or str(BASE_DIR / "mixes.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(config=None):
    conn = get_db_connection(config)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mixes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            genre TEXT NOT NULL,
            filename TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def create_app(config=None):
    config = config or {}
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.update(
        SECRET_KEY=config.get("SECRET_KEY", "dev-secret-key"),
        UPLOAD_FOLDER=str(UPLOAD_FOLDER),
        DATABASE_FILE=config.get("DATABASE_FILE") or str(BASE_DIR / "mixes.db"),
        TESTING=config.get("TESTING", False),
    )

    init_db(app.config)

    @app.route("/")
    def index():
        conn = get_db_connection(app.config)
        mixes = conn.execute("SELECT * FROM mixes ORDER BY created_at DESC").fetchall()
        conn.close()
        return render_template("index.html", mixes=mixes)

    @app.route("/upload", methods=["GET", "POST"])
    def upload_mix():
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            genre = request.form.get("genre", "").strip()
            file = request.files.get("file")

            if not title or not description or not genre or not file or not file.filename:
                return render_template("index.html", error="Please complete all fields and choose a file."), 400

            filename = secure_filename(file.filename)
            path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(path)

            conn = get_db_connection(app.config)
            conn.execute(
                "INSERT INTO mixes (title, description, genre, filename) VALUES (?, ?, ?, ?)",
                (title, description, genre, filename),
            )
            conn.commit()
            conn.close()
            return redirect(url_for("index"))

        return redirect(url_for("index"))

    @app.route("/download/<filename>")
    def download(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=True)

    @app.route("/auth/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "").strip()
            if not username or not email or not password:
                return render_template("register.html", error="Please fill every field."), 400
            conn = get_db_connection(app.config)
            try:
                conn.execute(
                    "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                    (username, email, password),
                )
                conn.commit()
            except sqlite3.IntegrityError:
                conn.close()
                return render_template("register.html", error="That username or email already exists."), 400
            conn.close()
            session["user"] = username
            return redirect(url_for("dashboard"))
        return render_template("register.html")

    @app.route("/auth/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            conn = get_db_connection(app.config)
            user = conn.execute(
                "SELECT * FROM users WHERE username = ? AND password = ?",
                (username, password),
            ).fetchone()
            conn.close()
            if user:
                session["user"] = user["username"]
                return redirect(url_for("dashboard"))
            return render_template("login.html", error="Invalid username or password"), 401
        return render_template("login.html")

    @app.route("/dashboard")
    def dashboard():
        if not session.get("user"):
            return redirect(url_for("login"))
        conn = get_db_connection(app.config)
        mixes = conn.execute("SELECT * FROM mixes ORDER BY created_at DESC").fetchall()
        conn.close()
        return render_template("dashboard.html", mixes=mixes, username=session["user"])

    @app.route("/logout")
    def logout():
        session.pop("user", None)
        return redirect(url_for("index"))

    @app.route("/contact", methods=["GET", "POST"])
    def contact():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip()
            message = request.form.get("message", "").strip()
            if not name or not email or not message:
                return render_template("contact.html", error="Please fill every field."), 400
            conn = get_db_connection(app.config)
            conn.execute("INSERT INTO contacts (name, email, message) VALUES (?, ?, ?)", (name, email, message))
            conn.commit()
            conn.close()
            return render_template("contact.html", success="Thanks! Your message has been received.")
        return render_template("contact.html")

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")
            if username == "admin" and password == "password123":
                session["admin"] = True
                return redirect(url_for("admin_dashboard"))
            return render_template("admin_login.html", error="Invalid credentials"), 401
        return render_template("admin_login.html")

    @app.route("/admin")
    def admin_dashboard():
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        conn = get_db_connection(app.config)
        mixes = conn.execute("SELECT * FROM mixes ORDER BY created_at DESC").fetchall()
        conn.close()
        return render_template("admin_dashboard.html", mixes=mixes)

    @app.route("/admin/delete/<int:mix_id>", methods=["POST"])
    def delete_mix(mix_id):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        conn = get_db_connection(app.config)
        mix = conn.execute("SELECT filename FROM mixes WHERE id = ?", (mix_id,)).fetchone()
        if mix:
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], mix["filename"])
            if os.path.exists(file_path):
                os.remove(file_path)
            conn.execute("DELETE FROM mixes WHERE id = ?", (mix_id,))
            conn.commit()
        conn.close()
        return redirect(url_for("admin_dashboard"))

    @app.route("/admin/logout")
    def admin_logout():
        session.pop("admin", None)
        return redirect(url_for("admin_login"))

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(debug=False, host="0.0.0.0", port=port)
