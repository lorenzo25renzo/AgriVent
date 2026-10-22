
from flask import render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash
from database import get_connection


def register_routes(app):

    @app.route("/")
    def home():
        if "username" in session:
            return redirect(url_for("dashboard"))

        return render_template("login.html")

    @app.route("/login", methods=["POST"])
    def login():
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        connection = get_connection()

        try:
            user = connection.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,)
            ).fetchone()
        finally:
            connection.close()

        if user and check_password_hash(user["password_hash"], password):
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            error="Invalid username or password."
        )

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("home"))
