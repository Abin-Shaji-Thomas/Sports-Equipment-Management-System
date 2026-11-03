import os
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import font as tkfont
from datetime import date, datetime

DB = "sports.db"
CONDITIONS = ("Good", "Fair", "Poor", "Under Repair")
last_sql = ""

BG = "#F7F5F0"
WHITE = "#FFFFFF"
TEXT = "#2B2B2B"
GREEN = "#2E7D5B"
GREEN_DARK = "#24644A"
SELECT = "#DCEFE4"
BORDER = "#D9D5CC"
TAB = "#ECE9E2"
STATUS_COLOURS = {
    "Available": "#E8F5EC",
    "Returned": "#E8F5EC",
    "Issued": "#FFF3D6",
    "Overdue": "#F8DADA",
    "All Issued": "#F8DADA",
    "Under Repair": "#E6E6E6",
}

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


class App:
    # Build the main window
    def __init__(self, root):
        self.root = root
        self.selected_equipment = None
        self.selected_issue = None
        self.issue_choices = []
        root.title("Sports Equipment Management System")
        root.geometry("1100x650")
        root.minsize(900, 550)
        root.configure(bg=BG)
        self.setup_theme()

        header = ttk.Frame(root, padding=(16, 12, 16, 6))
        header.pack(fill="x")
        ttk.Label(header, text="Sports Equipment Management System", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="ABIN SHAJI THOMAS | URK24CS6007", style="Sub.TLabel").pack(anchor="w")
        self.summary = ttk.Label(header, style="Summary.TLabel")
        self.summary.pack(anchor="w", pady=(6, 0))

        bottom = ttk.Frame(root, style="Card.TFrame", padding=(16, 8))
        bottom.pack(side="bottom", fill="x")
        ttk.Label(bottom, text="Last SQL executed:", style="CardBold.TLabel").pack(side="left")
        self.sql_label = ttk.Label(bottom, text="(none yet)", style="Sql.TLabel", wraplength=900)
        self.sql_label.pack(side="left", padx=(8, 0))

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, padx=16, pady=(6, 10))
        self.build_equipment_tab(notebook)
        self.build_issue_tab(notebook)
        self.refresh()

    # Apply the clam theme with custom colours and fonts
    def setup_theme(self):
        family = "Segoe UI" if "Segoe UI" in tkfont.families() else "Arial"
        for name in ("TkDefaultFont", "TkTextFont", "TkHeadingFont"):
            tkfont.nametofont(name).configure(family=family, size=10)
        self.root.option_add("*TCombobox*Listbox.background", WHITE)
        self.root.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", SELECT)
        self.root.option_add("*TCombobox*Listbox.selectForeground", TEXT)

        s = ttk.Style()
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=TEXT, font=(family, 10))
        s.configure("TFrame", background=BG)
        s.configure("Card.TFrame", background=WHITE)
        s.configure("TLabel", background=BG, foreground=TEXT)
        s.configure("Card.TLabel", background=WHITE)
        s.configure("CardBold.TLabel", background=WHITE, font=(family, 10, "bold"))
        s.configure("Title.TLabel", foreground=GREEN, font=(family, 18, "bold"))
        s.configure("Sub.TLabel", font=(family, 10))
        s.configure("Summary.TLabel", font=(family, 10, "bold"))
        s.configure("Sql.TLabel", background=WHITE, font=("Consolas", 10))

        s.configure("TButton", background=GREEN, foreground=WHITE, borderwidth=0, relief="flat",
                    padding=(14, 6), bordercolor=GREEN, lightcolor=GREEN, darkcolor=GREEN, focuscolor=GREEN)
        s.map("TButton", background=[("active", GREEN_DARK), ("pressed", GREEN_DARK)],
              lightcolor=[("active", GREEN_DARK)], darkcolor=[("active", GREEN_DARK)])

        for widget in ("TEntry", "TCombobox"):
            s.configure(widget, fieldbackground=WHITE, foreground=TEXT, bordercolor=BORDER, lightcolor=WHITE,
                        darkcolor=WHITE, selectbackground=SELECT, selectforeground=TEXT, padding=4)
            s.map(widget, bordercolor=[("focus", GREEN)], lightcolor=[("focus", GREEN)])
        s.configure("TCombobox", background=WHITE, arrowcolor=TEXT)
        s.map("TCombobox", fieldbackground=[("readonly", WHITE)], selectbackground=[("readonly", WHITE)],
              selectforeground=[("readonly", TEXT)], background=[("active", SELECT)])

        s.configure("TNotebook", background=BG, borderwidth=0)
        s.configure("TNotebook.Tab", background=TAB, foreground=TEXT, padding=(16, 6), borderwidth=0,
                    lightcolor=TAB, bordercolor=BORDER)
        s.map("TNotebook.Tab", background=[("selected", GREEN)], foreground=[("selected", WHITE)],
              lightcolor=[("selected", GREEN)])

        s.configure("Treeview", background=WHITE, fieldbackground=WHITE, foreground=TEXT, rowheight=28,
                    bordercolor=BORDER, lightcolor=WHITE, darkcolor=WHITE)
        s.map("Treeview", background=[("selected", SELECT)], foreground=[("selected", TEXT)])
        s.configure("Treeview.Heading", background=TAB, foreground=TEXT, font=(family, 10, "bold"),
                    relief="flat", bordercolor=BORDER, lightcolor=TAB, darkcolor=TAB)
        s.map("Treeview.Heading", background=[("active", BORDER)])

    # Create a labelled entry or combobox in a form row
    def field(self, parent, col, label, widget):
        ttk.Label(parent, text=label, style="Card.TLabel").grid(row=0, column=col, sticky="w", padx=6)
        widget.grid(row=1, column=col, sticky="we", padx=6, pady=(2, 0))
        return widget

    # Create a table with a scrollbar and status colour tags
    def table(self, parent, columns, widths):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True, pady=(10, 0))
        tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
        for col, width in zip(columns, widths):
            tree.heading(col, text=col)
            tree.column(col, width=width, anchor="w")
        bar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=bar.set)
        tree.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        for tag, colour in STATUS_COLOURS.items():
            tree.tag_configure(tag, background=colour)
        return tree

    # Build the Equipment tab
    def build_equipment_tab(self, notebook):
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="Equipment")
        form = ttk.Frame(tab, style="Card.TFrame", padding=10)
        form.pack(fill="x")
        self.eq_name = self.field(form, 0, "Name", ttk.Entry(form, width=26))
        self.eq_category = self.field(form, 1, "Category", ttk.Entry(form, width=20))
        self.eq_total = self.field(form, 2, "Total Quantity", ttk.Entry(form, width=14))
        self.eq_condition = self.field(form, 3, "Condition", ttk.Combobox(form, values=CONDITIONS, state="readonly", width=16))

        buttons = ttk.Frame(tab)
        buttons.pack(fill="x", pady=(10, 0))
        for text, command in (("Add", self.on_add_equipment), ("Update", self.on_update_equipment),
                              ("Delete", self.on_delete_equipment), ("Clear", self.clear_equipment)):
            ttk.Button(buttons, text=text, command=command).pack(side="left", padx=(0, 8))

        self.eq_tree = self.table(tab, ("ID", "Name", "Category", "Total", "Issued", "Available", "Condition", "Status"),
                                  (50, 200, 140, 70, 70, 80, 120, 120))
        self.eq_tree.bind("<<TreeviewSelect>>", self.on_select_equipment)

    # Build the Issue / Return tab
    def build_issue_tab(self, notebook):
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="Issue / Return")
        form = ttk.Frame(tab, style="Card.TFrame", padding=10)
        form.pack(fill="x")
        self.is_equipment = self.field(form, 0, "Equipment", ttk.Combobox(form, state="readonly", width=30))
        self.is_to = self.field(form, 1, "Issued To", ttk.Entry(form, width=22))
        self.is_qty = self.field(form, 2, "Quantity", ttk.Entry(form, width=10))
        self.is_days = self.field(form, 3, "Days Allowed", ttk.Entry(form, width=12))
        self.is_date = self.field(form, 4, "Issue Date", ttk.Entry(form, width=14))
        self.is_date.insert(0, date.today().isoformat())

        buttons = ttk.Frame(tab)
        buttons.pack(fill="x", pady=(10, 0))
        for text, command in (("Issue", self.on_issue), ("Mark Returned", self.on_return),
                              ("Delete Record", self.on_delete_issue), ("Clear", self.clear_issue)):
            ttk.Button(buttons, text=text, command=command).pack(side="left", padx=(0, 8))

        self.is_tree = self.table(tab, ("ID", "Equipment", "Issued To", "Qty", "Issue Date", "Days", "Due Date",
                                        "Return Date", "Status"), (50, 180, 160, 50, 100, 60, 100, 100, 100))
        self.is_tree.bind("<<TreeviewSelect>>", self.on_select_issue)

    # Reload both tables, the equipment dropdown, the summary and the last SQL
    def refresh(self):
        self.eq_tree.delete(*self.eq_tree.get_children())
        self.issue_choices = []
        for e in fetch_equipment():
            self.eq_tree.insert("", "end", iid=e["equipment_id"], tags=(e["status"],),
                                values=(e["equipment_id"], e["name"], e["category"], e["total_quantity"],
                                        e["issued_now"], e["available"], e["condition"], e["status"]))
            self.issue_choices.append((e["equipment_id"], e["name"] + " (" + str(e["available"]) + " available)"))
        self.is_equipment["values"] = [text for _, text in self.issue_choices]
        self.is_equipment.set("")

        self.is_tree.delete(*self.is_tree.get_children())
        for i in fetch_issues():
            self.is_tree.insert("", "end", iid=i["issue_id"], tags=(i["status"],),
                                values=(i["issue_id"], i["name"], i["issued_to"], i["quantity"], i["issue_date"],
                                        i["days_allowed"], i["due_date"], i["return_date"] or "", i["status"]))

        total, issued, overdue = fetch_summary()
        self.summary.configure(text="Total items: %d | Currently issued: %d | Overdue: %d" % (total, issued, overdue))
        if last_sql:
            self.sql_label.configure(text=last_sql)

    # Run a database action, show any rule warning, and refresh on success
    def attempt(self, action, *args):
        try:
            action(*args)
        except ValueError as e:
            messagebox.showwarning("Not allowed", str(e))
            return False
        self.refresh()
        return True

    # Load the selected equipment row into the form
    def on_select_equipment(self, event):
        selection = self.eq_tree.selection()
        if not selection:
            return
        values = self.eq_tree.item(selection[0], "values")
        self.selected_equipment = int(values[0])
        for entry, value in ((self.eq_name, values[1]), (self.eq_category, values[2]), (self.eq_total, values[3])):
            entry.delete(0, "end")
            entry.insert(0, value)
        self.eq_condition.set(values[6])

    # Remember the selected issue record
    def on_select_issue(self, event):
        selection = self.is_tree.selection()
        self.selected_issue = int(selection[0]) if selection else None

    # Add equipment from the form
    def on_add_equipment(self):
        if self.attempt(add_equipment, self.eq_name.get(), self.eq_category.get(), self.eq_total.get(),
                        self.eq_condition.get()):
            self.clear_equipment()

    # Update the selected equipment from the form
    def on_update_equipment(self):
        if self.selected_equipment is None:
            messagebox.showwarning("No selection", "Please select an equipment row to update.")
            return
        if self.attempt(update_equipment, self.selected_equipment, self.eq_name.get(), self.eq_category.get(),
                        self.eq_total.get(), self.eq_condition.get()):
            self.clear_equipment()

    # Delete the selected equipment after confirmation
    def on_delete_equipment(self):
        if self.selected_equipment is None:
            messagebox.showwarning("No selection", "Please select an equipment row to delete.")
            return
        if messagebox.askyesno("Confirm delete", "Delete this equipment? Its issue records will also be deleted."):
            if self.attempt(delete_equipment, self.selected_equipment):
                self.clear_equipment()

    # Clear the equipment form and selection
    def clear_equipment(self):
        for entry in (self.eq_name, self.eq_category, self.eq_total):
            entry.delete(0, "end")
        self.eq_condition.set("")
        self.eq_tree.selection_remove(self.eq_tree.selection())
        self.selected_equipment = None

    # Issue equipment from the form
    def on_issue(self):
        index = self.is_equipment.current()
        equipment_id = self.issue_choices[index][0] if index >= 0 else None
        if self.attempt(issue_equipment, equipment_id, self.is_to.get(), self.is_qty.get(), self.is_date.get(),
                        self.is_days.get()):
            self.clear_issue()

    # Mark the selected issue record as returned today
    def on_return(self):
        if self.selected_issue is None:
            messagebox.showwarning("No selection", "Please select an issue record to mark as returned.")
            return
        self.attempt(mark_returned, self.selected_issue)
        self.selected_issue = None

    # Delete the selected issue record after confirmation
    def on_delete_issue(self):
        if self.selected_issue is None:
            messagebox.showwarning("No selection", "Please select an issue record to delete.")
            return
        if messagebox.askyesno("Confirm delete", "Delete this issue record?"):
            self.attempt(delete_issue, self.selected_issue)
            self.selected_issue = None

    # Clear the issue form and selection
    def clear_issue(self):
        for entry in (self.is_to, self.is_qty, self.is_days, self.is_date):
            entry.delete(0, "end")
        self.is_date.insert(0, date.today().isoformat())
        self.is_equipment.set("")
        self.is_tree.selection_remove(self.is_tree.selection())
        self.selected_issue = None


if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    App(root)
    root.mainloop()
