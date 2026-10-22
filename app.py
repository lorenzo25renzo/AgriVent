
from flask import Flask
from werkzeug.security import generate_password_hash

from database import get_connection
from routes.auth import register_routes as register_auth_routes
from routes.dashboard import register_routes as register_dashboard_routes
from routes.products import register_routes as register_product_routes
from routes.inventory import register_routes as register_inventory_routes
from routes.suppliers import register_routes as register_supplier_routes
from routes.purchase_orders import register_routes as register_purchase_order_routes
from routes.stock_receiving import register_routes as register_stock_receiving_routes


app = Flask(__name__)
app.secret_key = "agrivent_secret_key_2026"


def create_admin_account():
    connection = get_connection()

    try:
        user = connection.execute(
            "SELECT id FROM users WHERE username = ?",
            ("admin",)
        ).fetchone()

        if user is None:
            password_hash = generate_password_hash("admin123")

            connection.execute(
                """
                INSERT INTO users (username, password_hash, role)
                VALUES (?, ?, ?)
                """,
                ("admin", password_hash, "admin")
            )

            connection.commit()
            print("Default admin account created.")
    finally:
        connection.close()


register_auth_routes(app)
register_dashboard_routes(app)
register_product_routes(app)
register_inventory_routes(app)
register_supplier_routes(app)
register_purchase_order_routes(app)
register_stock_receiving_routes(app)


if __name__ == "__main__":
    create_admin_account()
    app.run(debug=True)
