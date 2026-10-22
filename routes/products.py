
import sqlite3
from flask import (
    render_template, request, redirect, url_for,
    session, flash
)
from database import get_connection


def register_routes(app):

    @app.route("/products")
    def products():
        if "username" not in session:
            return redirect(url_for("home"))

        connection = get_connection()
        try:
            product_list = connection.execute(
                "SELECT * FROM products ORDER BY id DESC"
            ).fetchall()
        finally:
            connection.close()

        return render_template("products.html", products=product_list)

    @app.route("/add-product", methods=["GET", "POST"])
    def add_product():
        if "username" not in session:
            return redirect(url_for("home"))

        if request.method == "POST":
            sku = request.form.get("sku", "").strip()
            name = request.form.get("name", "").strip()
            category = request.form.get("category", "").strip()
            unit = request.form.get("unit", "").strip()

            try:
                cost_price = float(request.form.get("cost_price", ""))
                selling_price = float(request.form.get("selling_price", ""))
                reorder_level = int(request.form.get("reorder_level", "10"))

                if cost_price < 0 or selling_price < 0 or reorder_level < 0:
                    raise ValueError
            except ValueError:
                flash(
                    "Please enter valid, non-negative prices and reorder level.",
                    "error"
                )
                return render_template("add_product.html")

            if not sku or not name or not category or not unit:
                flash("Please fill in all required fields.", "error")
                return render_template("add_product.html")

            connection = get_connection()
            try:
                connection.execute(
                    """
                    INSERT INTO products (
                        sku, name, category, unit,
                        cost_price, selling_price, reorder_level
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sku, name, category, unit,
                        cost_price, selling_price, reorder_level
                    )
                )
                connection.commit()
                flash("Product added successfully!", "success")
            except sqlite3.IntegrityError:
                flash(
                    "This product code already exists. Please use a different one.",
                    "error"
                )
            finally:
                connection.close()

            return redirect(url_for("products"))

        return render_template("add_product.html")

    @app.route("/edit-product/<int:product_id>", methods=["GET", "POST"])
    def edit_product(product_id):
        if "username" not in session:
            return redirect(url_for("home"))

        connection = get_connection()

        product = connection.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()

        if product is None:
            connection.close()
            flash("Product not found.", "error")
            return redirect(url_for("products"))

        if request.method == "POST":
            sku = request.form.get("sku", "").strip()
            name = request.form.get("name", "").strip()
            category = request.form.get("category", "").strip()
            unit = request.form.get("unit", "").strip()

            try:
                cost_price = float(request.form.get("cost_price", ""))
                selling_price = float(request.form.get("selling_price", ""))
                reorder_level = int(request.form.get("reorder_level", ""))

                if cost_price < 0 or selling_price < 0 or reorder_level < 0:
                    raise ValueError
            except ValueError:
                connection.close()
                flash(
                    "Please enter valid, non-negative prices and reorder level.",
                    "error"
                )
                return redirect(
                    url_for("edit_product", product_id=product_id)
                )

            if not sku or not name or not category or not unit:
                connection.close()
                flash("Please fill in all required fields.", "error")
                return redirect(
                    url_for("edit_product", product_id=product_id)
                )

            try:
                connection.execute(
                    """
                    UPDATE products
                    SET sku = ?, name = ?, category = ?, unit = ?,
                        cost_price = ?, selling_price = ?, reorder_level = ?
                    WHERE id = ?
                    """,
                    (
                        sku, name, category, unit,
                        cost_price, selling_price, reorder_level, product_id
                    )
                )
                connection.commit()
                flash("Product updated successfully!", "success")
            except sqlite3.IntegrityError:
                flash(
                    "This product code is already being used by another product.",
                    "error"
                )
            finally:
                connection.close()

            return redirect(url_for("products"))

        connection.close()
        return render_template("edit_product.html", product=product)

    @app.route("/delete-product/<int:product_id>", methods=["POST"])
    def delete_product(product_id):
        if "username" not in session:
            return redirect(url_for("home"))

        connection = get_connection()

        product = connection.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()

        if product is None:
            connection.close()
            flash("Product not found.", "error")
            return redirect(url_for("products"))

        try:
            connection.execute(
                "DELETE FROM products WHERE id = ?",
                (product_id,)
            )
            connection.commit()
            flash("Product deleted successfully.", "success")
        except sqlite3.IntegrityError:
            flash(
                "This product cannot be deleted because it is linked to other records.",
                "error"
            )
        finally:
            connection.close()

        return redirect(url_for("products"))
