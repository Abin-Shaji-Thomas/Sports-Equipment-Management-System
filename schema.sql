CREATE TABLE equipment (
    equipment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    condition TEXT NOT NULL
);

CREATE TABLE issue_record (
    issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_id INTEGER NOT NULL,
    issued_to TEXT NOT NULL,
    issue_date TEXT NOT NULL,
    return_date TEXT,
    FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id) ON DELETE CASCADE
);

INSERT INTO equipment (name, category, quantity, condition) VALUES ('Football', 'Outdoor', 10, 'Good');
INSERT INTO equipment (name, category, quantity, condition) VALUES ('Cricket Bat', 'Outdoor', 6, 'Good');
INSERT INTO equipment (name, category, quantity, condition) VALUES ('Shuttle Racket', 'Indoor', 8, 'Fair');
INSERT INTO equipment (name, category, quantity, condition) VALUES ('Chess Board', 'Indoor', 4, 'Good');

INSERT INTO issue_record (equipment_id, issued_to, issue_date, return_date) VALUES (1, 'Rahul', '2026-11-01', '2026-11-02');
INSERT INTO issue_record (equipment_id, issued_to, issue_date, return_date) VALUES (2, 'Anjali', '2026-11-02', NULL);
INSERT INTO issue_record (equipment_id, issued_to, issue_date, return_date) VALUES (4, 'Vishnu', '2026-11-03', NULL);
