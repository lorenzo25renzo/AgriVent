
import sqlite3
from flask import (
    render_template, request, redirect, url_for,
    session, flash
)
from database import get_connection


def register_routes(app):

    @app.route("/stock-receiving", methods=["GET", "POST"])
    def stock_receiving():
        if "username" not in session:
            return redirect(url_for("home"))

        connection = get_connection()

        if request.method == "POST":
            try:
                product_id = int(request.form.get("product_id", ""))
                batch_number = request.form.get("batch_number", "").strip()
                quantity = int(request.form.get("quantity", ""))
                expiration_date = (
                    request.form.get("expiration_date", "").strip() or None
                )

                if product_id <= 0 or quantity <= 0 or not batch_number:
                    raise ValueError
            except ValueError:
                connection.close()
                flash(
                    "Please select a product and enter a batch number and a quantity greater than zero.",
                    "error"
                )
                return redirect(url_for("stock_receiving"))

            product = connection.execute(
                "SELECT id FROM products WHERE id = ?",
                (product_id,)
            ).fetchone()

            if product is None:
                connection.close()
                flash("The selected product does not exist.", "error")
                return redirect(url_for("stock_receiving"))

            try:
                connection.execute(
                    """
                    INSERT INTO inventory_batches (
                        product_id, batch_number, quantity,
                        expiration_date, received_at
                    )
                    VALUES (?, ?, ?, ?, datetime('now', 'localtime'))
                    """,
                    (
                        product_id, batch_number, quantity, expiration_date
                    )
                )
                connection.commit()
                flash("Stock received successfully!", "success")
            except sqlite3.IntegrityError:
                flash(
                    "This batch number is already registered for this product. Please use a different batch number.",
                    "error"
                )
            finally:
                connection.close()

            return redirect(url_for("stock_receiving"))

        try:
            product_list = connection.execute(
                """
                SELECT id, sku, name, unit
                FROM products
                ORDER BY name ASC
                """
            ).fetchall()
        finally:
            connection.close()

        return render_template(
            "stock_receiving.html",
            products=product_list
        )
