CREATE TABLE equipment (
    equipment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    total_quantity INTEGER NOT NULL CHECK (total_quantity >= 0),
    condition TEXT NOT NULL CHECK (condition IN ('Good', 'Fair', 'Poor', 'Under Repair'))
);

CREATE TABLE issue_record (
    issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_id INTEGER NOT NULL,
    issued_to TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    issue_date TEXT NOT NULL,
    days_allowed INTEGER NOT NULL CHECK (days_allowed > 0),
    return_date TEXT,
    FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id) ON DELETE CASCADE
);

INSERT INTO equipment (name, category, total_quantity, condition) VALUES ('Football', 'Outdoor', 10, 'Good');
INSERT INTO equipment (name, category, total_quantity, condition) VALUES ('Cricket Bat', 'Outdoor', 6, 'Good');
INSERT INTO equipment (name, category, total_quantity, condition) VALUES ('Badminton Racket', 'Indoor', 8, 'Fair');
INSERT INTO equipment (name, category, total_quantity, condition) VALUES ('Chess Board', 'Indoor', 4, 'Poor');
INSERT INTO equipment (name, category, total_quantity, condition) VALUES ('Basketball', 'Outdoor', 5, 'Under Repair');

INSERT INTO issue_record (equipment_id, issued_to, quantity, issue_date, days_allowed, return_date) VALUES (1, 'Rahul', 2, date('now', '-10 days'), 5, date('now', '-6 days'));
INSERT INTO issue_record (equipment_id, issued_to, quantity, issue_date, days_allowed, return_date) VALUES (2, 'Anjali', 1, date('now', '-2 days'), 7, NULL);
INSERT INTO issue_record (equipment_id, issued_to, quantity, issue_date, days_allowed, return_date) VALUES (3, 'Vishnu', 2, date('now', '-10 days'), 3, NULL);
INSERT INTO issue_record (equipment_id, issued_to, quantity, issue_date, days_allowed, return_date) VALUES (4, 'Meera', 4, date('now', '-1 days'), 7, NULL);
