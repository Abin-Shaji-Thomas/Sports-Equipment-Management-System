import csv
import os
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter import font as tkfont
from datetime import date, datetime

DB = "sports.db"
last_sql = ""

BG = "#F7F5F0"
WHITE = "#FFFFFF"
TEXT = "#2B2B2B"
MUTED = "#6B6B6B"
GREEN = "#2E7D5B"
GREEN_HOVER = "#256B4C"
SIDEBAR = "#1F3A2E"
SIDEBAR_HOVER = "#294C3C"
SIDEBAR_TEXT = "#F2EFE8"
SIDEBAR_MUTED = "#A9BDB2"
GREY_BUTTON = "#ECEAE4"
GREY_HOVER = "#DEDBD3"
RED_BUTTON = "#FBE3E3"
RED_HOVER = "#F5CFCF"
RED_TEXT = "#9B2C2C"
HEADING = "#E6EEE9"
SELECT = "#DCEFE4"
BORDER = "#DAD6CD"
ZEBRA = "#FAF9F6"
STATUS_COLOURS = {
    "Available": "#E6F4EA", "Returned": "#E6F4EA", "Completed": "#E6F4EA", "Paid": "#E6F4EA",
    "Issued": "#FFF3D6", "In Progress": "#FFF3D6", "Pending": "#FFF3D6",
    "Overdue": "#F8DADA", "All Issued": "#F8DADA",
    "Under Repair": "#E4E4E4",
}

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


# Apply the clam theme with the project colours and fonts
def setup_theme(root):
    family = "Segoe UI" if "Segoe UI" in tkfont.families() else "Arial"
    for name in ("TkDefaultFont", "TkTextFont", "TkHeadingFont"):
        tkfont.nametofont(name).configure(family=family, size=10)
    root.option_add("*TCombobox*Listbox.background", WHITE)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", SELECT)
    root.option_add("*TCombobox*Listbox.selectForeground", TEXT)

    s = ttk.Style()
    s.theme_use("clam")
    s.configure(".", background=BG, foreground=TEXT, font=(family, 10), focuscolor=BORDER)
    s.configure("TFrame", background=BG)
    s.configure("Panel.TFrame", background=WHITE)
    s.configure("TLabel", background=BG, foreground=TEXT)
    s.configure("Panel.TLabel", background=WHITE)
    s.configure("PanelTitle.TLabel", background=WHITE, font=(family, 12, "bold"))
    s.configure("Hint.TLabel", background=WHITE, foreground=MUTED, font=(family, 9))
    s.configure("Title.TLabel", font=(family, 20, "bold"))
    s.configure("Section.TLabel", font=(family, 12, "bold"))
    s.configure("Owner.TLabel", foreground=GREEN, font=(family, 10, "bold"))

    def button(name, bg, fg, hover):
        s.configure(name, background=bg, foreground=fg, borderwidth=0, relief="flat", padding=(14, 7),
                    bordercolor=bg, lightcolor=bg, darkcolor=bg, focuscolor=bg)
        s.map(name, background=[("active", hover), ("pressed", hover)],
              lightcolor=[("active", hover)], darkcolor=[("active", hover)], bordercolor=[("active", hover)])

    button("TButton", GREEN, WHITE, GREEN_HOVER)
    button("Secondary.TButton", GREY_BUTTON, TEXT, GREY_HOVER)
    button("Danger.TButton", RED_BUTTON, RED_TEXT, RED_HOVER)
    button("Nav.TButton", SIDEBAR, SIDEBAR_TEXT, SIDEBAR_HOVER)
    button("NavActive.TButton", GREEN, WHITE, GREEN)
    for name in ("Nav.TButton", "NavActive.TButton"):
        s.configure(name, anchor="w", padding=(22, 10), font=(family, 10))

    for widget in ("TEntry", "TCombobox"):
        s.configure(widget, fieldbackground=WHITE, foreground=TEXT, bordercolor=BORDER, lightcolor=WHITE,
                    darkcolor=WHITE, selectbackground=SELECT, selectforeground=TEXT, padding=5,
                    insertcolor=TEXT)
        s.map(widget, bordercolor=[("focus", GREEN)], lightcolor=[("focus", GREEN)])
    s.configure("TCombobox", background=WHITE, arrowcolor=TEXT)
    s.map("TCombobox", fieldbackground=[("readonly", WHITE)], selectbackground=[("readonly", WHITE)],
          selectforeground=[("readonly", TEXT)], background=[("active", SELECT)])

    s.configure("Treeview", background=WHITE, fieldbackground=WHITE, foreground=TEXT, rowheight=28,
                bordercolor=BORDER, lightcolor=WHITE, darkcolor=WHITE)
    s.map("Treeview", background=[("selected", SELECT)], foreground=[("selected", TEXT)])
    s.configure("Treeview.Heading", background=HEADING, foreground=TEXT, font=(family, 10, "bold"),
                relief="flat", bordercolor=BORDER, lightcolor=HEADING, darkcolor=HEADING, padding=(6, 5))
    s.map("Treeview.Heading", background=[("active", SELECT)])
    for bar in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
        s.configure(bar, background=GREY_BUTTON, troughcolor=BG, bordercolor=BG, lightcolor=GREY_BUTTON,
                    darkcolor=GREY_BUTTON, arrowcolor=MUTED)
        s.map(bar, background=[("active", GREY_HOVER)])
    return family


# Create a table with both scrollbars and status colour tags inside a frame
def make_table(parent, columns):
    frame = ttk.Frame(parent)
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)
    tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
    vbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    hbar = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vbar.grid(row=0, column=1, sticky="ns")
    hbar.grid(row=1, column=0, sticky="ew")
    set_columns(tree, columns)
    for tag, colour in STATUS_COLOURS.items():
        tree.tag_configure(tag, background=colour)
    tree.tag_configure("odd", background=ZEBRA)
    return frame, tree


# Set the headings and widths of a table
def set_columns(tree, columns):
    tree["columns"] = columns
    for col in columns:
        tree.heading(col, text=col, anchor="w")
        tree.column(col, width=60 if col == "ID" else 130, minwidth=50, anchor="w", stretch=True)


# Fill a table with rows, colouring each row by its Status column if there is one
def fill_table(tree, rows):
    tree.delete(*tree.get_children())
    columns = list(tree["columns"])
    status = columns.index("Status") if "Status" in columns else None
    for n, row in enumerate(rows):
        shown = tuple(f"{v:.2f}" if isinstance(v, float) else ("" if v is None else v) for v in row)
        tag = row[status] if status is not None else ("odd" if n % 2 else "")
        tree.insert("", "end", iid=str(n), values=shown, tags=(tag,))


class DashboardPage(ttk.Frame):
    title = "Dashboard"

    # Build the stat cards, quick actions and overdue table
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)

        cards = ttk.Frame(self)
        cards.grid(row=0, column=0, sticky="ew")
        self.numbers = {}
        for col, (key, label, colour) in enumerate((
                ("equipment", "Equipment Items", GREEN), ("members", "Members", "#3F6B4F"),
                ("issued", "Currently Issued (units)", "#B7791F"), ("overdue", "Overdue Returns", "#B23B3B"),
                ("repair", "Under Repair", MUTED), ("fines", "Pending Fines (total amount)", "#A35A12"))):
            cards.columnconfigure(col, weight=1, uniform="card")
            card = tk.Frame(cards, bg=WHITE, highlightthickness=1, highlightbackground=BORDER)
            card.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 12, 0))
            self.numbers[key] = tk.Label(card, bg=WHITE, fg=colour, font=(app.family, 26, "bold"))
            self.numbers[key].pack(anchor="w", padx=16, pady=(14, 0))
            tk.Label(card, text=label, bg=WHITE, fg=MUTED, font=(app.family, 10)).pack(anchor="w", padx=16, pady=(0, 14))

        ttk.Label(self, text="Quick actions", style="Section.TLabel").grid(row=1, column=0, sticky="w", pady=(22, 8))
        actions = ttk.Frame(self)
        actions.grid(row=2, column=0, sticky="w")
        for text, page in (("Add equipment", "equipment"), ("Register a member", "members"),
                           ("Issue equipment", "issue"), ("Record maintenance", "maintenance")):
            ttk.Button(actions, text=text, command=lambda p=page: app.show(p, new=True)).pack(side="left", padx=(0, 10))

        ttk.Label(self, text="Overdue returns", style="Section.TLabel").grid(row=3, column=0, sticky="w", pady=(22, 8))
        frame, self.tree = make_table(self, ("Equipment", "Member", "Phone", "Due Date", "Days Late", "Qty"))
        frame.grid(row=4, column=0, sticky="nsew")
        self.rows = []

    # Reload the card numbers and the overdue table
    def refresh(self):
        stats = dashboard_stats()
        for key, label in self.numbers.items():
            label.configure(text=("₹ %.2f" % stats[key]) if key == "fines" else str(stats[key]))
        self.rows = fetch_overdue()
        fill_table(self.tree, self.rows)
        for iid in self.tree.get_children():
            self.tree.item(iid, tags=("Overdue",))

    # Number of rows shown in the table
    def shown_count(self):
        return len(self.rows)


class TablePage(ttk.Frame):
    hint = "Select a row to edit it, or fill the fields to create a new record."

    # Build the toolbar, table and record details panel for one table
    def __init__(self, parent, app, name, title):
        super().__init__(parent)
        self.app = app
        self.name = name
        self.title = title
        self.rows = []
        self.shown = []
        self.selected_id = None
        self.widgets = {}
        self.choices = {}
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, minsize=320)
        self.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(self)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self.search = ttk.Entry(toolbar, width=32)
        self.search.pack(side="left")
        self.search.bind("<Return>", lambda e: self.apply_filter())
        ttk.Button(toolbar, text="Search", style="Secondary.TButton", command=self.apply_filter).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="Clear", style="Secondary.TButton", command=self.clear_search).pack(side="left", padx=(8, 0))
        self.toolbar_right = ttk.Frame(toolbar)
        self.toolbar_right.pack(side="right")
        ttk.Button(self.toolbar_right, text="Refresh", style="Secondary.TButton",
                   command=app.refresh_all).pack(side="right", padx=(8, 0))
        ttk.Button(self.toolbar_right, text="Export CSV", command=self.export).pack(side="right", padx=(8, 0))
        ttk.Button(self.toolbar_right, text="Import CSV", command=self.import_file).pack(side="right")

        frame, self.tree = make_table(self, TABLES[name]["columns"])
        frame.grid(row=1, column=0, sticky="nsew", padx=(0, 16))
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        panel = tk.Frame(self, bg=WHITE, highlightthickness=1, highlightbackground=BORDER, padx=18, pady=16)
        panel.grid(row=1, column=1, sticky="nsew")
        panel.columnconfigure(0, weight=1)
        panel.columnconfigure(1, weight=1)
        ttk.Label(panel, text="Record details", style="PanelTitle.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(panel, text=self.hint, style="Hint.TLabel", wraplength=270,
                  justify="left").grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 10))
        row = 2
        for label, column, kind, option in TABLES[name]["fields"]:
            ttk.Label(panel, text=label, style="Panel.TLabel").grid(row=row, column=0, columnspan=2, sticky="w", pady=(6, 2))
            if kind in ("fk", "choice"):
                widget = ttk.Combobox(panel, state="readonly", values=option if kind == "choice" else ())
            else:
                widget = ttk.Entry(panel)
            widget.grid(row=row + 1, column=0, columnspan=2, sticky="ew")
            self.widgets[label] = widget
            row += 2
        for n, (text, command, style) in enumerate(self.buttons()):
            ttk.Button(panel, text=text, command=command, style=style).grid(
                row=row + 1 + n // 2, column=n % 2, sticky="ew", padx=(0 if n % 2 == 0 else 4, 4 if n % 2 == 0 else 0),
                pady=(16 if n < 2 else 8, 0))

    # Buttons of the record details panel
    def buttons(self):
        return [("Add new", self.add, "TButton"), ("Save changes", self.save, "TButton"),
                ("Delete selected", self.delete, "Danger.TButton"), ("Clear form", self.clear_form, "Secondary.TButton")]

    # Reload the rows and the foreign-key combos, keeping current combo choices
    def refresh(self):
        self.rows = fetch(self.name)
        for label, column, kind, option in TABLES[self.name]["fields"]:
            if kind == "fk":
                combo = self.widgets[label]
                old = self.choice_id(label)
                self.choices[label] = lookup(option)
                combo["values"] = [r[1] for r in self.choices[label]]
                self.set_choice(label, old)
        self.apply_filter()

    # Id behind the current text of a foreign-key combo
    def choice_id(self, label):
        index = self.widgets[label].current()
        rows = self.choices.get(label, [])
        return rows[index][0] if 0 <= index < len(rows) else None

    # Show the combo text that belongs to an id
    def set_choice(self, label, record_id):
        text = next((r[1] for r in self.choices.get(label, []) if r[0] == record_id), "")
        self.widgets[label].set(text)

    # Show only the rows that contain the search text in any column
    def apply_filter(self):
        text = self.search.get().strip().lower()
        self.shown = [r for r in self.rows if not text or any(text in str(v).lower() for v in r)]
        fill_table(self.tree, self.shown)
        self.selected_id = None
        self.app.update_status()

    # Clear the search box and show all rows
    def clear_search(self):
        self.search.delete(0, "end")
        self.apply_filter()

    # Number of rows shown in the table
    def shown_count(self):
        return len(self.shown)

    # Load the selected row into the form
    def on_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        self.selected_id = self.shown[int(selection[0])][0]
        record = get_record(self.name, self.selected_id)
        for label, column, kind, option in TABLES[self.name]["fields"]:
            widget = self.widgets[label]
            if kind == "fk":
                self.set_choice(label, record[column])
            elif kind == "choice":
                widget.set(record[column])
            else:
                widget.delete(0, "end")
                widget.insert(0, record[column])

    # Read the form as raw values keyed by field label
    def form_values(self):
        raw = {}
        for label, column, kind, option in TABLES[self.name]["fields"]:
            if kind == "fk":
                raw[label] = self.choice_id(label) or ""
            else:
                raw[label] = self.widgets[label].get()
        return raw

    # Run a database action, show any rule warning, and refresh everything on success
    def attempt(self, action, *args):
        try:
            action(*args)
        except ValueError as e:
            messagebox.showwarning("Not allowed", str(e))
            return False
        self.app.refresh_all()
        return True

    # Insert the form as a new record
    def add(self):
        if self.attempt(add_record, self.name, self.form_values()):
            self.clear_form()

    # Save the form over the selected record
    def save(self):
        if self.selected_id is None:
            messagebox.showwarning("No selection", "Please select a row to save changes to.")
            return
        if self.attempt(update_record, self.name, self.selected_id, self.form_values()):
            self.clear_form()

    # Delete the selected record after confirmation
    def delete(self):
        if self.selected_id is None:
            messagebox.showwarning("No selection", "Please select a row to delete.")
            return
        if messagebox.askyesno("Confirm delete", "Delete the selected record (ID " + str(self.selected_id) + ")?"):
            if self.attempt(delete_record, self.name, self.selected_id):
                self.clear_form()

    # Empty the form and clear the table selection
    def clear_form(self):
        for widget in self.widgets.values():
            if isinstance(widget, ttk.Combobox):
                widget.set("")
            else:
                widget.delete(0, "end")
        self.tree.selection_remove(self.tree.selection())
        self.selected_id = None

    # The first field of the form
    def first_field(self):
        return next(iter(self.widgets.values()))

    # Save the rows shown in the table to a CSV file
    def export(self):
        os.makedirs("exports", exist_ok=True)
        path = filedialog.asksaveasfilename(title="Export CSV", initialdir=os.path.abspath("exports"),
                                            initialfile=TABLES[self.name]["table"] + ".csv",
                                            defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        try:
            export_csv(path, TABLES[self.name]["columns"], self.shown)
        except OSError as e:
            messagebox.showwarning("Export CSV", "Could not write the file: " + str(e))
            return
        messagebox.showinfo("Export CSV", str(len(self.shown)) + " records exported to\n" + path)

    # Insert the valid rows of a chosen CSV file and report the result
    def import_file(self):
        path = filedialog.askopenfilename(title="Import CSV", initialdir=os.path.abspath("sample_import"),
                                          filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        imported, skipped, reason = import_csv(self.name, path)
        self.app.refresh_all()
        message = str(imported) + " imported, " + str(skipped) + " skipped"
        if reason:
            message += "\n\n" + reason
        messagebox.showinfo("Import CSV", message)


class IssuePage(TablePage):
    hint = "Select a row to mark it returned or delete it, or fill the fields to issue equipment."

    # Build the page and pre-fill today's date
    def __init__(self, parent, app):
        super().__init__(parent, app, "issue", "Issue / Return")
        self.clear_form()

    # Buttons of the issue panel
    def buttons(self):
        return [("Issue", self.add, "TButton"), ("Mark Returned", self.mark_returned, "TButton"),
                ("Delete Record", self.delete, "Danger.TButton"), ("Clear form", self.clear_form, "Secondary.TButton")]

    # Remember the selected issue record without loading it into the form
    def on_select(self, event):
        selection = self.tree.selection()
        self.selected_id = self.shown[int(selection[0])][0] if selection else None

    # Set the return date of the selected record to today
    def mark_returned(self):
        if self.selected_id is None:
            messagebox.showwarning("No selection", "Please select an issue record to mark as returned.")
            return
        self.attempt(mark_returned, self.selected_id)

    # Empty the form and put today's date in Issue Date
    def clear_form(self):
        super().clear_form()
        self.widgets["Issue Date"].insert(0, date.today().isoformat())


class QueriesPage(ttk.Frame):
    title = "Queries"

    # Build the query picker, SQL text box and result table
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.queries = load_sample_queries()
        self.rows = []
        self.ran = False
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        toolbar = ttk.Frame(self)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.picker = ttk.Combobox(toolbar, state="readonly", width=80, values=[t for t, _ in self.queries])
        self.picker.pack(side="left")
        self.picker.bind("<<ComboboxSelected>>", lambda e: self.show_sql())
        ttk.Button(toolbar, text="Run", command=self.run_query).pack(side="left", padx=(8, 0))

        self.sql_text = tk.Text(self, height=9, font=("Consolas", 10), bg=WHITE, fg=TEXT, relief="flat",
                                highlightthickness=1, highlightbackground=BORDER, highlightcolor=GREEN,
                                selectbackground=SELECT, selectforeground=TEXT, padx=12, pady=10, wrap="word")
        self.sql_text.grid(row=1, column=0, sticky="ew")
        ttk.Label(self, text="Result", style="Section.TLabel").grid(row=2, column=0, sticky="w", pady=(16, 8))
        frame, self.tree = make_table(self, ("Result",))
        frame.grid(row=3, column=0, sticky="nsew")
        self.picker.current(0)
        self.show_sql()

    # Show the SQL of the chosen query and clear old results
    def show_sql(self):
        self.sql_text.configure(state="normal")
        self.sql_text.delete("1.0", "end")
        self.sql_text.insert("1.0", self.queries[self.picker.current()][1])
        self.sql_text.configure(state="disabled")
        self.ran = False
        self.rows = []
        set_columns(self.tree, ("Result",))
        fill_table(self.tree, [])
        self.app.update_status()

    # Run the chosen query and show its real results
    def run_query(self):
        try:
            headings, self.rows = run_sample_query(self.queries[self.picker.current()][1])
        except sqlite3.Error as e:
            messagebox.showwarning("Query failed", str(e))
            return
        set_columns(self.tree, headings)
        fill_table(self.tree, self.rows)
        self.ran = True
        self.app.update_status()

    # Re-run the shown query so its results stay live
    def refresh(self):
        if self.ran:
            self.run_query()

    # Number of result rows shown
    def shown_count(self):
        return len(self.rows)


class App:
    # Build the window, sidebar, content area and status bar
    def __init__(self, root):
        self.root = root
        root.title("Sports Equipment Management System")
        try:
            root.state("zoomed")
        except tk.TclError:
            root.geometry("1280x720")
        root.minsize(1000, 600)
        root.configure(bg=BG)
        self.family = setup_theme(root)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        self.sidebar = tk.Frame(root, bg=SIDEBAR, width=210)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)
        self.sidebar.columnconfigure(0, weight=1)
        tk.Label(self.sidebar, text="SPORTSDESK", bg=SIDEBAR, fg=SIDEBAR_TEXT,
                 font=(self.family, 17, "bold")).grid(row=0, column=0, sticky="w", padx=22, pady=(24, 0))
        tk.Label(self.sidebar, text="EQUIPMENT MANAGER", bg=SIDEBAR, fg=SIDEBAR_MUTED,
                 font=(self.family, 8, "bold")).grid(row=1, column=0, sticky="w", padx=22, pady=(0, 22))
        tk.Label(self.sidebar, text="DBMS PROJECT | PYTHON + SQLITE", bg=SIDEBAR, fg=SIDEBAR_MUTED,
                 font=(self.family, 8)).grid(row=99, column=0, sticky="w", padx=14, pady=16)
        self.sidebar.rowconfigure(98, weight=1)

        content = ttk.Frame(root, padding=(24, 16, 24, 12))
        content.grid(row=0, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(1, weight=1)
        self.title = ttk.Label(content, style="Title.TLabel")
        self.title.grid(row=0, column=0, sticky="w", pady=(0, 12))
        ttk.Label(content, text="ABIN SHAJI THOMAS | URK24CS6007", style="Owner.TLabel").grid(row=0, column=1, sticky="e")
        container = ttk.Frame(content)
        container.grid(row=1, column=0, columnspan=2, sticky="nsew")
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

        status = tk.Frame(root, bg=WHITE, highlightthickness=1, highlightbackground=BORDER)
        status.grid(row=1, column=0, columnspan=2, sticky="ew")
        status.columnconfigure(1, weight=1)
        tk.Label(status, text="Last SQL executed:", bg=WHITE, fg=TEXT,
                 font=(self.family, 9, "bold")).grid(row=0, column=0, sticky="nw", padx=(14, 6), pady=7)
        self.sql_label = tk.Label(status, text="(nothing yet)", bg=WHITE, fg=TEXT, font=("Consolas", 9),
                                  anchor="w", justify="left")
        self.sql_label.grid(row=0, column=1, sticky="ew", pady=7)
        self.count_label = tk.Label(status, bg=WHITE, fg=MUTED, font=(self.family, 9))
        self.count_label.grid(row=0, column=2, sticky="ne", padx=14, pady=7)
        status.bind("<Configure>", lambda e: self.sql_label.configure(wraplength=max(300, e.width - 330)))

        self.pages = {}
        self.nav = {}
        self.current = None
        for key, page_class, args in self.page_list():
            page = page_class(container, self, *args)
            page.grid(row=0, column=0, sticky="nsew")
            self.pages[key] = page
            button = ttk.Button(self.sidebar, text=page.title, style="Nav.TButton",
                                command=lambda k=key: self.show(k))
            button.grid(row=len(self.nav) + 2, column=0, sticky="ew")
            self.nav[key] = button
        self.refresh_all()
        self.show("dashboard")

    # The screens in sidebar order
    def page_list(self):
        return [("dashboard", DashboardPage, ()),
                ("categories", TablePage, ("categories", "Categories")),
                ("equipment", TablePage, ("equipment", "Equipment")),
                ("members", TablePage, ("members", "Members")),
                ("issue", IssuePage, ()),
                ("maintenance", TablePage, ("maintenance", "Maintenance")),
                ("fines", TablePage, ("fines", "Fines")),
                ("queries", QueriesPage, ())]

    # Switch to a screen, optionally with an empty form ready for a new record
    def show(self, key, new=False):
        self.current = key
        page = self.pages[key]
        page.tkraise()
        self.title.configure(text=page.title)
        for k, button in self.nav.items():
            button.configure(style="NavActive.TButton" if k == key else "Nav.TButton")
        if new and hasattr(page, "clear_form"):
            page.clear_form()
            page.first_field().focus_set()
        self.update_status()

    # Reload every screen and the status bar after a change
    def refresh_all(self):
        for page in self.pages.values():
            page.refresh()
        self.update_status()

    # Show the last SQL statement and the record count of the current screen
    def update_status(self):
        if last_sql:
            self.sql_label.configure(text=last_sql)
        if self.current:
            self.count_label.configure(text=str(self.pages[self.current].shown_count()) + " records shown")


if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    App(root)
    root.mainloop()
