# Sports Equipment Management System

A small Python desktop inventory application built with Tkinter and SQLite. It initializes a local database from `schema.sql`, provides an equipment interface, and includes sample CSV import data.

## Requirements

- Python 3
- Tkinter and SQLite support in the Python installation

## Run

From the repository root:

```sh
python app.py
```

The application creates `sports.db` from `schema.sql` on first run. `queries.sql` contains sample SQL, and `sample_import/equipment.csv` can be used with the equipment import feature.

## Repository layout

- `app.py` — desktop application
- `schema.sql` — initial database schema
- `queries.sql` — example queries
- `sample_import/` — sample import data
- `.gitignore` — excludes local/generated files

## Data notes

The SQLite database is local application data. Back it up before testing destructive operations, and do not commit real inventory or personal data.
