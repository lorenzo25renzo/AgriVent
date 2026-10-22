
from flask import render_template, redirect, url_for, session
from database import get_connection


def register_routes(app):

    @app.route("/dashboard")
    def dashboard():
        if "username" not in session:
            return redirect(url_for("home"))

        connection = get_connection()

        try:
            total_products = connection.execute(
                "SELECT COUNT(*) AS total FROM products"
            ).fetchone()["total"]

            low_stock_items = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM products AS p
                LEFT JOIN (
                    SELECT product_id, SUM(quantity) AS total_quantity
                    FROM inventory_batches
                    GROUP BY product_id
                ) AS stock ON p.id = stock.product_id
                WHERE COALESCE(stock.total_quantity, 0) <= p.reorder_level
                """
            ).fetchone()["total"]

            total_sales = connection.execute(
                """
                SELECT COALESCE(SUM(total_amount), 0) AS total
                FROM sales
                """
            ).fetchone()["total"]

            inventory_value = connection.execute(
                """
                SELECT COALESCE(SUM(
                    COALESCE(stock.total_quantity, 0) * p.cost_price
                ), 0) AS total
                FROM products AS p
                LEFT JOIN (
                    SELECT product_id, SUM(quantity) AS total_quantity
                    FROM inventory_batches
                    GROUP BY product_id
                ) AS stock ON p.id = stock.product_id
                """
            ).fetchone()["total"]
        finally:
            connection.close()

        return render_template(
            "index.html",
            total_products=total_products,
            low_stock_items=low_stock_items,
            total_sales=total_sales,
            inventory_value=inventory_value
        )
