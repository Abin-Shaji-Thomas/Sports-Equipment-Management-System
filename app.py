import csv
import os
import sqlite3
from datetime import date, datetime

DB = "sports.db"
last_sql = ""

TODAY = "date('now', 'localtime')"
DUE = "date(i.issue_date, '+' || i.days_allowed || ' days')"
ISSUE_STATUS = ("CASE WHEN i.return_date IS NOT NULL THEN 'Returned' WHEN " + DUE + " < " + TODAY
                + " THEN 'Overdue' ELSE 'Issued' END")

EQUIPMENT_STOCK = """
SELECT equipment_id, name, brand, category, total_quantity, issued_now,
       total_quantity - issued_now AS available, condition,
       CASE WHEN condition = 'Under Repair' THEN 'Under Repair'
            WHEN total_quantity - issued_now = 0 THEN 'All Issued'
            ELSE 'Available' END AS status
FROM (SELECT e.*, c.name AS category,
             (SELECT COALESCE(SUM(i.quantity), 0) FROM issue_record i
              WHERE i.equipment_id = e.equipment_id AND i.return_date IS NULL) AS issued_now
      FROM equipment e JOIN categories c ON e.category_id = c.category_id)
"""

ISSUE_JOIN = """
FROM issue_record i
JOIN equipment e ON i.equipment_id = e.equipment_id
JOIN members m ON i.member_id = m.member_id
"""

LOOKUPS = {
    "category": "SELECT category_id, name, name FROM categories ORDER BY name",
    "equipment": "SELECT equipment_id, name, name FROM equipment ORDER BY name",
    "equipment_stock": "SELECT equipment_id, name || ' (' || available || ' available)', name FROM ("
                       + EQUIPMENT_STOCK + ") ORDER BY name",
    "member": "SELECT member_id, full_name, full_name FROM members ORDER BY full_name",
    "issue": "SELECT i.issue_id, '#' || i.issue_id || ' ' || e.name || ' - ' || m.full_name, i.issue_id "
             + ISSUE_JOIN + " ORDER BY i.issue_id DESC",
}


# Check an equipment update does not drop the total below what is issued
def check_equipment(values, record_id):
    if record_id is not None:
        item = get_stock(record_id)
        if values["total_quantity"] < item["issued_now"]:
            raise ValueError("Total quantity cannot be less than the " + str(item["issued_now"])
                             + " units currently issued.")


# Check an item can be issued in the requested quantity
def check_issue(values, record_id):
    item = get_stock(values["equipment_id"])
    if item["condition"] == "Under Repair":
        raise ValueError(item["name"] + " is under repair and cannot be issued.")
    if values["quantity"] > item["available"]:
        raise ValueError("Only " + str(item["available"]) + " " + item["name"] + " available.")


TABLES = {
    "categories": {
        "table": "categories", "pk": "category_id",
        "columns": ("ID", "Name", "Description", "Storage Location", "Equipment Count"),
        "select": """SELECT c.category_id, c.name, c.description, c.storage_location,
                            (SELECT COUNT(*) FROM equipment e WHERE e.category_id = c.category_id)
                     FROM categories c ORDER BY c.category_id""",
        "fields": [("Name", "name", "text", None),
                   ("Description", "description", "text", None),
                   ("Storage Location", "storage_location", "text", None)],
        "blocked": "This category still has equipment. Move or delete that equipment first.",
    },
    "equipment": {
        "table": "equipment", "pk": "equipment_id",
        "columns": ("ID", "Name", "Brand", "Category", "Total", "Issued", "Available", "Condition", "Status"),
        "select": EQUIPMENT_STOCK + " ORDER BY equipment_id",
        "fields": [("Name", "name", "text", None),
                   ("Brand", "brand", "text", None),
                   ("Category", "category_id", "fk", "category"),
                   ("Total Quantity", "total_quantity", "int", (0, None)),
                   ("Condition", "condition", "choice", ("Good", "Fair", "Poor", "Under Repair")),
                   ("Purchase Date", "purchase_date", "date", None)],
        "check": check_equipment,
    },
    "members": {
        "table": "members", "pk": "member_id",
        "columns": ("ID", "Full Name", "Department", "Year", "Phone", "Email", "Primary Sport", "Total Issues"),
        "select": """SELECT m.member_id, m.full_name, m.department, m.year_of_study, m.phone, m.email,
                            m.primary_sport,
                            (SELECT COUNT(*) FROM issue_record i WHERE i.member_id = m.member_id)
                     FROM members m ORDER BY m.member_id""",
        "fields": [("Full Name", "full_name", "text", None),
                   ("Department", "department", "text", None),
                   ("Year of Study", "year_of_study", "int", (1, 4)),
                   ("Phone", "phone", "phone", None),
                   ("Email", "email", "email", None),
                   ("Primary Sport", "primary_sport", "text", None)],
    },
    "issue": {
        "table": "issue_record", "pk": "issue_id",
        "columns": ("ID", "Equipment", "Member", "Qty", "Issue Date", "Days", "Due Date", "Return Date", "Status"),
        "select": "SELECT i.issue_id, e.name, m.full_name, i.quantity, i.issue_date, i.days_allowed, "
                  + DUE + ", COALESCE(i.return_date, ''), " + ISSUE_STATUS + ISSUE_JOIN + " ORDER BY i.issue_id",
        "fields": [("Equipment", "equipment_id", "fk", "equipment_stock"),
                   ("Member", "member_id", "fk", "member"),
                   ("Quantity", "quantity", "int", (1, None)),
                   ("Days Allowed", "days_allowed", "int", (1, None)),
                   ("Issue Date", "issue_date", "date", None)],
        "check": check_issue,
    },
    "maintenance": {
        "table": "maintenance", "pk": "maintenance_id",
        "columns": ("ID", "Equipment", "Problem", "Sent Date", "Cost", "Status"),
        "select": """SELECT mt.maintenance_id, e.name, mt.problem, mt.sent_date, mt.cost, mt.status
                     FROM maintenance mt JOIN equipment e ON mt.equipment_id = e.equipment_id
                     ORDER BY mt.maintenance_id""",
        "fields": [("Equipment", "equipment_id", "fk", "equipment"),
                   ("Problem", "problem", "text", None),
                   ("Sent Date", "sent_date", "date", None),
                   ("Cost", "cost", "money", 0),
                   ("Status", "status", "choice", ("Pending", "In Progress", "Completed"))],
    },
    "fines": {
        "table": "fines", "pk": "fine_id",
        "columns": ("ID", "Issue ID", "Equipment", "Member", "Amount", "Reason", "Date", "Status"),
        "select": "SELECT f.fine_id, i.issue_id, e.name, m.full_name, f.amount, f.reason, f.fine_date, f.status "
                  "FROM fines f JOIN issue_record i ON f.issue_id = i.issue_id "
                  "JOIN equipment e ON i.equipment_id = e.equipment_id "
                  "JOIN members m ON i.member_id = m.member_id ORDER BY f.fine_id",
        "fields": [("Issue", "issue_id", "fk", "issue"),
                   ("Amount", "amount", "money", 0.01),
                   ("Reason", "reason", "text", None),
                   ("Date", "fine_date", "date", None),
                   ("Status", "status", "choice", ("Pending", "Paid"))],
    },
}


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
        with open("schema.sql", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.close()


# Run a SELECT and return all rows
def query(sql, params=()):
    conn = get_db()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


# Format a value the way it would appear in an SQL statement
def show_value(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


# Run a change statement, remember it with its values, and turn constraint errors into messages
def run(sql, params, blocked=None):
    global last_sql
    conn = get_db()
    try:
        conn.execute(sql, params)
        conn.commit()
    except sqlite3.IntegrityError as e:
        if "FOREIGN KEY" in str(e):
            raise ValueError(blocked or "This record is linked to other records and cannot be changed.")
        if "UNIQUE" in str(e):
            raise ValueError("A record with that name already exists.")
        raise ValueError("The database rejected this change: " + str(e))
    finally:
        conn.close()
    for p in params:
        sql = sql.replace("?", show_value(p), 1)
    last_sql = sql


# Rows for a screen's table
def fetch(name):
    return [tuple(r) for r in query(TABLES[name]["select"])]


# One raw table row by its primary key
def get_record(name, record_id):
    cfg = TABLES[name]
    rows = query("SELECT * FROM " + cfg["table"] + " WHERE " + cfg["pk"] + " = ?", (record_id,))
    return dict(rows[0]) if rows else None


# One equipment row with issued, available and status
def get_stock(equipment_id):
    return query("SELECT * FROM (" + EQUIPMENT_STOCK + ") WHERE equipment_id = ?", (equipment_id,))[0]


# Choices for a foreign-key combo as (id, label, key) rows
def lookup(name):
    return [tuple(r) for r in query(LOOKUPS[name])]


# Turn a foreign-key value (an id from a combo, or a name from CSV) into an id
def resolve(lookup_name, value, label):
    rows = lookup(lookup_name)
    if isinstance(value, int):
        if any(r[0] == value for r in rows):
            return value
    elif str(value).strip():
        key = str(value).strip().lstrip("#").lower()
        for r in rows:
            if str(r[2]).lower() == key:
                return r[0]
        raise ValueError(label + " '" + str(value).strip() + "' was not found.")
    raise ValueError("Please choose a " + label + ".")


# Check one field value and convert it to the type stored in the table
def clean_value(label, kind, option, value):
    value = str(value).strip()
    if not value:
        raise ValueError(label + " cannot be empty.")
    if kind == "int":
        low, high = option
        if not value.isdigit() or int(value) < low or (high is not None and int(value) > high):
            if high is not None:
                raise ValueError(label + " must be a whole number from " + str(low) + " to " + str(high) + ".")
            raise ValueError(label + " must be a whole number of " + str(low) + " or more.")
        return int(value)
    if kind == "money":
        try:
            amount = round(float(value), 2)
        except ValueError:
            raise ValueError(label + " must be a number.")
        if amount < option:
            raise ValueError(label + (" cannot be negative." if option == 0 else " must be more than 0."))
        return amount
    if kind == "date":
        try:
            if datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d") != value:
                raise ValueError
        except ValueError:
            raise ValueError(label + " must be a valid date in YYYY-MM-DD format.")
    if kind == "phone" and not (value.isdigit() and len(value) == 10):
        raise ValueError(label + " must be exactly 10 digits.")
    if kind == "email" and "@" not in value:
        raise ValueError(label + " must contain '@'.")
    if kind == "choice" and value not in option:
        raise ValueError(label + " must be one of: " + ", ".join(option) + ".")
    return value


# Validate a whole form (keyed by field label) and return values keyed by column
def clean(name, raw, record_id=None):
    cfg = TABLES[name]
    values = {}
    for label, column, kind, option in cfg["fields"]:
        value = raw.get(label, "")
        if kind == "fk":
            values[column] = resolve(option, value, label)
        else:
            values[column] = clean_value(label, kind, option, value)
    if "check" in cfg:
        cfg["check"](values, record_id)
    return values


# Insert a new record after validation
def add_record(name, raw):
    cfg = TABLES[name]
    values = clean(name, raw)
    run("INSERT INTO " + cfg["table"] + " (" + ", ".join(values) + ") VALUES ("
        + ", ".join("?" for _ in values) + ")", tuple(values.values()))


# Update a record after validation
def update_record(name, record_id, raw):
    cfg = TABLES[name]
    values = clean(name, raw, record_id)
    run("UPDATE " + cfg["table"] + " SET " + ", ".join(c + " = ?" for c in values) + " WHERE "
        + cfg["pk"] + " = ?", tuple(values.values()) + (record_id,))


# Delete a record, with a friendly message if other records depend on it
def delete_record(name, record_id):
    cfg = TABLES[name]
    run("DELETE FROM " + cfg["table"] + " WHERE " + cfg["pk"] + " = ?", (record_id,), cfg.get("blocked"))


# Set the return date of an issue record to today
def mark_returned(issue_id):
    row = get_record("issue", issue_id)
    if row["return_date"] is not None:
        raise ValueError("This record is already marked as returned.")
    today = date.today().isoformat()
    if today < row["issue_date"]:
        raise ValueError("Return date cannot be before the issue date (" + row["issue_date"] + ").")
    run("UPDATE issue_record SET return_date = ? WHERE issue_id = ?", (today, issue_id))


# Numbers for the dashboard cards
def dashboard_stats():
    one = lambda sql: query(sql)[0][0]
    return {
        "equipment": one("SELECT COUNT(*) FROM equipment"),
        "members": one("SELECT COUNT(*) FROM members"),
        "issued": one("SELECT COALESCE(SUM(quantity), 0) FROM issue_record WHERE return_date IS NULL"),
        "overdue": one("SELECT COUNT(*) FROM issue_record i WHERE i.return_date IS NULL AND " + DUE + " < " + TODAY),
        "repair": one("SELECT COUNT(*) FROM equipment WHERE condition = 'Under Repair'"),
        "fines": one("SELECT COALESCE(SUM(amount), 0) FROM fines WHERE status = 'Pending'"),
    }


# Overdue issues for the dashboard table
def fetch_overdue():
    return [tuple(r) for r in query(
        "SELECT e.name, m.full_name, m.phone, " + DUE + " AS due_date, "
        "CAST(julianday(" + TODAY + ") - julianday(" + DUE + ") AS INTEGER) AS days_late, i.quantity "
        + ISSUE_JOIN + " WHERE i.return_date IS NULL AND " + DUE + " < " + TODAY + " ORDER BY days_late DESC")]


# Read the sample queries (title comment + SQL) from queries.sql
def load_sample_queries():
    with open("queries.sql", encoding="utf-8") as f:
        text = f.read()
    queries = []
    for block in text.split(";"):
        lines = block.strip().splitlines()
        titles = [line[2:].strip() for line in lines if line.startswith("--")]
        sql = "\n".join(line for line in lines if not line.startswith("--")).strip()
        if sql:
            queries.append((titles[-1] if titles else "Query", sql + ";"))
    return queries


# Run a sample query and return its column names and rows
def run_sample_query(sql):
    conn = get_db()
    cursor = conn.execute(sql)
    rows = [tuple(r) for r in cursor.fetchall()]
    headings = [d[0] for d in cursor.description]
    conn.close()
    return headings, rows


# Write table columns and rows to a CSV file
def export_csv(path, headings, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headings)
        writer.writerows(rows)


# Insert every valid row of a CSV file and report how many were skipped
def import_csv(name, path):
    labels = [f[0] for f in TABLES[name]["fields"]]
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
    except (OSError, UnicodeDecodeError, csv.Error) as e:
        return 0, 0, "Could not read the file: " + str(e)
    header = [h.strip().lower() for h in rows[0]] if rows else []
    missing = [label for label in labels if label.lower() not in header]
    if missing:
        return 0, 0, "The header row must contain: " + ", ".join(labels)
    imported = skipped = 0
    reason = ""
    for number, row in enumerate(rows[1:], start=2):
        if not any(cell.strip() for cell in row):
            continue
        raw = {}
        for label in labels:
            position = header.index(label.lower())
            raw[label] = row[position] if position < len(row) else ""
        try:
            add_record(name, raw)
            imported += 1
        except ValueError as e:
            skipped += 1
            reason = reason or "Row " + str(number) + ": " + str(e)
    return imported, skipped, reason


if __name__ == "__main__":
    init_db()
