import os
import sqlite3
from datetime import date, datetime

DB = "sports.db"
CONDITIONS = ("Good", "Fair", "Poor", "Under Repair")
last_sql = ""

EQUIPMENT_QUERY = """
SELECT equipment_id, name, category, total_quantity, issued_now,
       total_quantity - issued_now AS available, condition,
       CASE WHEN condition = 'Under Repair' THEN 'Under Repair'
            WHEN total_quantity - issued_now <= 0 THEN 'All Issued'
            ELSE 'Available' END AS status
FROM (SELECT e.*,
             (SELECT COALESCE(SUM(i.quantity), 0) FROM issue_record i
              WHERE i.equipment_id = e.equipment_id AND i.return_date IS NULL) AS issued_now
      FROM equipment e)
"""

ISSUE_QUERY = """
SELECT i.issue_id, e.name, i.issued_to, i.quantity, i.issue_date, i.days_allowed,
       date(i.issue_date, '+' || i.days_allowed || ' days') AS due_date, i.return_date,
       CASE WHEN i.return_date IS NOT NULL THEN 'Returned'
            WHEN date(i.issue_date, '+' || i.days_allowed || ' days') < date('now', 'localtime') THEN 'Overdue'
            ELSE 'Issued' END AS status
FROM issue_record i JOIN equipment e ON i.equipment_id = e.equipment_id
"""


# Open a connection with foreign keys turned on
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# Create the database from schema.sql if it does not exist
def init_db():
    if not os.path.exists(DB):
        conn = get_db()
        with open("schema.sql") as f:
            conn.executescript(f.read())
        conn.close()


# Format a value the way it would appear in an SQL statement
def show_value(v):
    if v is None:
        return "NULL"
    if isinstance(v, int):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


# Run a change statement and remember it with its values filled in
def run(sql, params):
    global last_sql
    conn = get_db()
    conn.execute(sql, params)
    conn.commit()
    conn.close()
    for p in params:
        sql = sql.replace("?", show_value(p), 1)
    last_sql = sql


# Run a SELECT and return all rows
def query(sql, params=()):
    conn = get_db()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


# All equipment with issued, available and status
def fetch_equipment():
    return query(EQUIPMENT_QUERY + " ORDER BY equipment_id")


# One equipment row with issued, available and status
def get_equipment(equipment_id):
    rows = query("SELECT * FROM (" + EQUIPMENT_QUERY + ") WHERE equipment_id = ?", (equipment_id,))
    return rows[0] if rows else None


# All issue records with due date and status
def fetch_issues():
    return query(ISSUE_QUERY + " ORDER BY i.issue_id")


# Totals for the summary line
def fetch_summary():
    equipment = fetch_equipment()
    issues = fetch_issues()
    total = sum(e["total_quantity"] for e in equipment)
    issued = sum(e["issued_now"] for e in equipment)
    overdue = sum(1 for i in issues if i["status"] == "Overdue")
    return total, issued, overdue


# Check a text field is not empty
def require_text(value, field):
    value = value.strip()
    if not value:
        raise ValueError(field + " cannot be empty.")
    return value


# Check a field is a whole number (positive, or zero if allowed)
def require_int(value, field, allow_zero=False):
    value = value.strip()
    if not value.isdigit() or (int(value) == 0 and not allow_zero):
        raise ValueError(field + " must be a " + ("whole number." if allow_zero else "positive whole number."))
    return int(value)


# Check a date is in YYYY-MM-DD format
def require_date(value, field):
    value = value.strip()
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise ValueError(field + " must be a valid date in YYYY-MM-DD format.")
    return value


# Check the condition is one of the allowed values
def require_condition(value):
    if value not in CONDITIONS:
        raise ValueError("Please choose a condition.")
    return value


# Add a new equipment item
def add_equipment(name, category, total, condition):
    name = require_text(name, "Name")
    category = require_text(category, "Category")
    total = require_int(total, "Total Quantity", allow_zero=True)
    condition = require_condition(condition)
    run("INSERT INTO equipment (name, category, total_quantity, condition) VALUES (?, ?, ?, ?)",
        (name, category, total, condition))


# Update an equipment item
def update_equipment(equipment_id, name, category, total, condition):
    name = require_text(name, "Name")
    category = require_text(category, "Category")
    total = require_int(total, "Total Quantity", allow_zero=True)
    condition = require_condition(condition)
    current = get_equipment(equipment_id)
    if total < current["issued_now"]:
        raise ValueError("Total quantity cannot be less than the " + str(current["issued_now"]) + " currently issued.")
    run("UPDATE equipment SET name = ?, category = ?, total_quantity = ?, condition = ? WHERE equipment_id = ?",
        (name, category, total, condition, equipment_id))


# Delete an equipment item (its issue records are removed by cascade)
def delete_equipment(equipment_id):
    run("DELETE FROM equipment WHERE equipment_id = ?", (equipment_id,))


# Issue equipment to a person
def issue_equipment(equipment_id, issued_to, quantity, issue_date, days):
    if equipment_id is None:
        raise ValueError("Please choose an equipment item.")
    issued_to = require_text(issued_to, "Issued To")
    quantity = require_int(quantity, "Quantity")
    days = require_int(days, "Days Allowed")
    issue_date = require_date(issue_date, "Issue Date")
    item = get_equipment(equipment_id)
    if item["condition"] == "Under Repair":
        raise ValueError(item["name"] + " is under repair and cannot be issued.")
    if quantity > item["available"]:
        raise ValueError("Only " + str(item["available"]) + " " + item["name"] + " available.")
    run("INSERT INTO issue_record (equipment_id, issued_to, quantity, issue_date, days_allowed) VALUES (?, ?, ?, ?, ?)",
        (equipment_id, issued_to, quantity, issue_date, days))


# Set the return date of an issue record to today
def mark_returned(issue_id):
    row = query("SELECT return_date FROM issue_record WHERE issue_id = ?", (issue_id,))[0]
    if row["return_date"] is not None:
        raise ValueError("This record is already marked as returned.")
    run("UPDATE issue_record SET return_date = ? WHERE issue_id = ?", (date.today().isoformat(), issue_id))


# Delete an issue record
def delete_issue(issue_id):
    run("DELETE FROM issue_record WHERE issue_id = ?", (issue_id,))


if __name__ == "__main__":
    init_db()
