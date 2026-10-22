
import sqlite3
from flask import (
    render_template, request, redirect, url_for,
    session, flash
)
from database import get_connection


def register_routes(app):

    @app.route("/suppliers")
    def suppliers():
        if "username" not in session:
            return redirect(url_for("home"))

        connection = get_connection()
        try:
            supplier_list = connection.execute(
                "SELECT * FROM suppliers ORDER BY name ASC"
            ).fetchall()
        finally:
            connection.close()

        return render_template("suppliers.html", suppliers=supplier_list)

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
                        name, contact_person or None, phone or None,
                        email or None, address or None
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
                    SET name = ?, contact_person = ?, phone = ?,
                        email = ?, address = ?
                    WHERE id = ?
                    """,
                    (
                        name, contact_person or None, phone or None,
                        email or None, address or None, supplier_id
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
        return render_template("edit_supplier.html", supplier=supplier)

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
