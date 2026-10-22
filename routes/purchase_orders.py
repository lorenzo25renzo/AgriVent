
from flask import render_template, redirect, url_for, session
from database import get_connection


def register_routes(app):

    @app.route("/purchase-orders")
    def purchase_orders():
        if "username" not in session:
            return redirect(url_for("home"))

        connection = get_connection()
        try:
            purchase_order_list = connection.execute(
                """
                SELECT
                    po.id,
                    po.order_date,
                    po.status,
                    po.total_amount,
                    s.name AS supplier_name
                FROM purchase_orders AS po
                INNER JOIN suppliers AS s ON po.supplier_id = s.id
                ORDER BY po.id DESC
                """
            ).fetchall()
        finally:
            connection.close()

        return render_template(
            "purchase_orders.html",
            purchase_orders=purchase_order_list
        )
