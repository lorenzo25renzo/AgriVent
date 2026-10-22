
import sqlite3
from pathlib import Path

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.secret_key = "agrivent_secret_key_2026"

DATABASE_NAME = Path(__file__).resolve().parent / "agrivent.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def create_admin_account():
    connection = get_connection()

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

    connection.close()


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

    user = connection.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    connection.close()

    if user and check_password_hash(user["password_hash"], password):
        session["username"] = user["username"]
        session["role"] = user["role"]

        return redirect(url_for("dashboard"))

    return render_template(
        "login.html",
        error="Invalid username or password."
    )


@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("home"))

    connection = get_connection()

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

    connection.close()

    return render_template(
        "index.html",
        total_products=total_products,
        low_stock_items=low_stock_items,
        total_sales=total_sales,
        inventory_value=inventory_value
    )


# PRODUCTS PAGE
@app.route("/products")
def products():
    if "username" not in session:
        return redirect(url_for("home"))

    connection = get_connection()

    product_list = connection.execute(
        """
        SELECT *
        FROM products
        ORDER BY id DESC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "products.html",
        products=product_list
    )


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

            if (
                cost_price < 0
                or selling_price < 0
                or reorder_level < 0
            ):
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
                    sku,
                    name,
                    category,
                    unit,
                    cost_price,
                    selling_price,
                    reorder_level
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

            if (
                cost_price < 0
                or selling_price < 0
                or reorder_level < 0
            ):
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
                SET sku = ?,
                    name = ?,
                    category = ?,
                    unit = ?,
                    cost_price = ?,
                    selling_price = ?,
                    reorder_level = ?
                WHERE id = ?
                """,
                (
                    sku,
                    name,
                    category,
                    unit,
                    cost_price,
                    selling_price,
                    reorder_level,
                    product_id
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

    return render_template(
        "edit_product.html",
        product=product
    )


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


# INVENTORY PAGE
@app.route("/inventory")
def inventory():
    if "username" not in session:
        return redirect(url_for("home"))

    connection = get_connection()

    inventory_items = connection.execute(
        """
        SELECT
            p.id,
            p.sku,
            p.name,
            p.category,
            p.unit,
            p.reorder_level,
            COALESCE(SUM(ib.quantity), 0) AS stock_quantity
        FROM products AS p
        LEFT JOIN inventory_batches AS ib
            ON p.id = ib.product_id
        GROUP BY
            p.id,
            p.sku,
            p.name,
            p.category,
            p.unit,
            p.reorder_level
        ORDER BY p.name ASC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "inventory.html",
        inventory_items=inventory_items
    )


# BATCH EXPIRATION PAGE
@app.route("/batch-expiration")
def batch_expiration():
    if "username" not in session:
        return redirect(url_for("home"))

    connection = get_connection()

    batches = connection.execute(
        """
        SELECT
            ib.id,
            ib.batch_number,
            ib.quantity,
            ib.expiration_date,
            ib.received_at,
            p.sku,
            p.name AS product_name,
            p.category,
            p.unit,
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
        INNER JOIN products AS p
            ON ib.product_id = p.id
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

    connection.close()

    return render_template(
        "batch_expiration.html",
        batches=batches
    )


# SUPPLIERS PAGE
@app.route("/suppliers")
def suppliers():
    if "username" not in session:
        return redirect(url_for("home"))

    connection = get_connection()

    supplier_list = connection.execute(
        """
        SELECT *
        FROM suppliers
        ORDER BY name ASC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "suppliers.html",
        suppliers=supplier_list
    )


# ADD SUPPLIER
@app.route("/add-supplier", methods=["GET", "POST"])
def add_supplier():
    if "username" not in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        contact_person = request.form.get("contact_person", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()

        if not name:
            flash("Supplier name is required.", "error")
            return render_template("add_supplier.html")

        connection = get_connection()

        try:
            connection.execute(
                """
                INSERT INTO suppliers (
                    name, contact_person, phone, email, address
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    name,
                    contact_person or None,
                    phone or None,
                    email or None,
                    address or None
                )
            )

            connection.commit()
            flash("Supplier added successfully!", "success")

        except sqlite3.IntegrityError:
            flash("Unable to save the supplier.", "error")

        finally:
            connection.close()

        return redirect(url_for("suppliers"))

    return render_template("add_supplier.html")


# EDIT SUPPLIER
@app.route("/edit-supplier/<int:supplier_id>", methods=["GET", "POST"])
def edit_supplier(supplier_id):
    if "username" not in session:
        return redirect(url_for("home"))

    connection = get_connection()

    supplier = connection.execute(
        "SELECT * FROM suppliers WHERE id = ?",
        (supplier_id,)
    ).fetchone()

    if supplier is None:
        connection.close()
        flash("Supplier not found.", "error")
        return redirect(url_for("suppliers"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        contact_person = request.form.get("contact_person", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()

        if not name:
            connection.close()
            flash("Supplier name is required.", "error")
            return redirect(
                url_for("edit_supplier", supplier_id=supplier_id)
            )

        try:
            connection.execute(
                """
                UPDATE suppliers
                SET name = ?,
                    contact_person = ?,
                    phone = ?,
                    email = ?,
                    address = ?
                WHERE id = ?
                """,
                (
                    name,
                    contact_person or None,
                    phone or None,
                    email or None,
                    address or None,
                    supplier_id
                )
            )

            connection.commit()
            flash("Supplier updated successfully!", "success")

        except sqlite3.IntegrityError:
            flash("Unable to update the supplier.", "error")

        finally:
            connection.close()

        return redirect(url_for("suppliers"))

    connection.close()

    return render_template(
        "edit_supplier.html",
        supplier=supplier
    )


# DELETE SUPPLIER
@app.route("/delete-supplier/<int:supplier_id>", methods=["POST"])
def delete_supplier(supplier_id):
    if "username" not in session:
        return redirect(url_for("home"))

    connection = get_connection()

    supplier = connection.execute(
        "SELECT id FROM suppliers WHERE id = ?",
        (supplier_id,)
    ).fetchone()

    if supplier is None:
        connection.close()
        flash("Supplier not found.", "error")
        return redirect(url_for("suppliers"))

    try:
        connection.execute(
            "DELETE FROM suppliers WHERE id = ?",
            (supplier_id,)
        )

        connection.commit()
        flash("Supplier deleted successfully.", "success")

    except sqlite3.IntegrityError:
        connection.rollback()
        flash(
            "This supplier cannot be deleted because it is linked to existing purchase orders.",
            "error"
        )

    finally:
        connection.close()

    return redirect(url_for("suppliers"))

# PURCHASE ORDERS PAGE
@app.route("/purchase-orders")
def purchase_orders():
    if "username" not in session:
        return redirect(url_for("home"))

    connection = get_connection()

    purchase_order_list = connection.execute("""
        SELECT
            po.id,
            po.order_date,
            po.status,
            po.total_amount,
            s.name AS supplier_name
        FROM purchase_orders AS po
        INNER JOIN suppliers AS s
            ON po.supplier_id = s.id
        ORDER BY po.id DESC
    """).fetchall()

    connection.close()

    return render_template(
        "purchase_orders.html",
        purchase_orders=purchase_order_list
    )

# STOCK RECEIVING PAGE
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
                    product_id,
                    batch_number,
                    quantity,
                    expiration_date,
                    received_at
                )
                VALUES (
                    ?, ?, ?, ?,
                    datetime('now', 'localtime')
                )
                """,
                (
                    product_id,
                    batch_number,
                    quantity,
                    expiration_date
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

    product_list = connection.execute(
        """
        SELECT id, sku, name, unit
        FROM products
        ORDER BY name ASC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "stock_receiving.html",
        products=product_list
    )


# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    create_admin_account()
    app.run(debug=True)
