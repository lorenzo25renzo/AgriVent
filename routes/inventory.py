
from flask import render_template, redirect, url_for, session
from database import get_connection


def register_routes(app):

    @app.route("/inventory")
    def inventory():
        if "username" not in session:
            return redirect(url_for("home"))

        connection = get_connection()
        try:
            inventory_items = connection.execute(
                """
                SELECT
                    p.id, p.sku, p.name, p.category, p.unit,
                    p.reorder_level,
                    COALESCE(SUM(ib.quantity), 0) AS stock_quantity
                FROM products AS p
                LEFT JOIN inventory_batches AS ib
                    ON p.id = ib.product_id
                GROUP BY
                    p.id, p.sku, p.name, p.category, p.unit, p.reorder_level
                ORDER BY p.name ASC
                """
            ).fetchall()
        finally:
            connection.close()

        return render_template(
            "inventory.html",
            inventory_items=inventory_items
        )

    @app.route("/batch-expiration")
    def batch_expiration():
        if "username" not in session:
            return redirect(url_for("home"))

        connection = get_connection()
        try:
            batches = connection.execute(
                """
                SELECT
                    ib.id, ib.batch_number, ib.quantity,
                    ib.expiration_date, ib.received_at,
                    p.sku, p.name AS product_name, p.category, p.unit,
                    CASE
                        WHEN ib.expiration_date IS NULL
                             OR TRIM(ib.expiration_date) = ''
                            THEN 'No Expiration Date'
                        WHEN date(ib.expiration_date) < date('now', 'localtime')
                            THEN 'Expired'
                        WHEN date(ib.expiration_date)
                             <= date('now', 'localtime', '+30 days')
                            THEN 'Expiring Soon'
                        ELSE 'Good'
                    END AS expiration_status
                FROM inventory_batches AS ib
                INNER JOIN products AS p ON ib.product_id = p.id
                ORDER BY
                    CASE
                        WHEN ib.expiration_date IS NULL
                             OR TRIM(ib.expiration_date) = ''
                            THEN 1
                        ELSE 0
                    END,
                    date(ib.expiration_date) ASC,
                    p.name ASC
                """
            ).fetchall()
        finally:
            connection.close()

        return render_template("batch_expiration.html", batches=batches)
