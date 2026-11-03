import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
DB = "sports.db"
last_sql = ""


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    if not os.path.exists(DB):
        conn = get_db()
        with open("schema.sql") as f:
            conn.executescript(f.read())
        conn.close()


def show_value(v):
    if v is None:
        return "NULL"
    if isinstance(v, int):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def run(sql, params):
    global last_sql
    conn = get_db()
    conn.execute(sql, params)
    conn.commit()
    conn.close()
    for p in params:
        sql = sql.replace("?", show_value(p), 1)
    last_sql = sql


# Main page: list both tables
@app.route("/")
def index():
    conn = get_db()
    equipment = conn.execute("SELECT * FROM equipment").fetchall()
    issues = conn.execute(
        "SELECT issue_record.*, equipment.name FROM issue_record "
        "JOIN equipment ON issue_record.equipment_id = equipment.equipment_id"
    ).fetchall()
    conn.close()
    return render_template("index.html", equipment=equipment, issues=issues, last_sql=last_sql)


# Add equipment
@app.route("/equipment/add", methods=["POST"])
def add_equipment():
    f = request.form
    run("INSERT INTO equipment (name, category, quantity, condition) VALUES (?, ?, ?, ?)",
        (f["name"], f["category"], int(f["quantity"]), f["condition"]))
    return redirect(url_for("index"))


# Show edit form for equipment
@app.route("/equipment/edit/<int:id>")
def edit_equipment(id):
    conn = get_db()
    row = conn.execute("SELECT * FROM equipment WHERE equipment_id = ?", (id,)).fetchone()
    conn.close()
    return render_template("edit.html", table="equipment", row=row)


# Update equipment
@app.route("/equipment/update/<int:id>", methods=["POST"])
def update_equipment(id):
    f = request.form
    run("UPDATE equipment SET name = ?, category = ?, quantity = ?, condition = ? WHERE equipment_id = ?",
        (f["name"], f["category"], int(f["quantity"]), f["condition"], id))
    return redirect(url_for("index"))


# Delete equipment
@app.route("/equipment/delete/<int:id>", methods=["POST"])
def delete_equipment(id):
    run("DELETE FROM equipment WHERE equipment_id = ?", (id,))
    return redirect(url_for("index"))


# Add issue record
@app.route("/issue/add", methods=["POST"])
def add_issue():
    f = request.form
    run("INSERT INTO issue_record (equipment_id, issued_to, issue_date, return_date) VALUES (?, ?, ?, ?)",
        (int(f["equipment_id"]), f["issued_to"], f["issue_date"], f["return_date"] or None))
    return redirect(url_for("index"))


# Show edit form for issue record
@app.route("/issue/edit/<int:id>")
def edit_issue(id):
    conn = get_db()
    row = conn.execute("SELECT * FROM issue_record WHERE issue_id = ?", (id,)).fetchone()
    equipment = conn.execute("SELECT equipment_id, name FROM equipment").fetchall()
    conn.close()
    return render_template("edit.html", table="issue", row=row, equipment=equipment)


# Update issue record
@app.route("/issue/update/<int:id>", methods=["POST"])
def update_issue(id):
    f = request.form
    run("UPDATE issue_record SET equipment_id = ?, issued_to = ?, issue_date = ?, return_date = ? WHERE issue_id = ?",
        (int(f["equipment_id"]), f["issued_to"], f["issue_date"], f["return_date"] or None, id))
    return redirect(url_for("index"))


# Delete issue record
@app.route("/issue/delete/<int:id>", methods=["POST"])
def delete_issue(id):
    run("DELETE FROM issue_record WHERE issue_id = ?", (id,))
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
