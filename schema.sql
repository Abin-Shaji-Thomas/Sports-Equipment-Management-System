CREATE TABLE categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    storage_location TEXT NOT NULL
);

CREATE TABLE equipment (
    equipment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    brand TEXT NOT NULL,
    total_quantity INTEGER NOT NULL CHECK (total_quantity >= 0),
    condition TEXT NOT NULL CHECK (condition IN ('Good', 'Fair', 'Poor', 'Under Repair')),
    purchase_date TEXT NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE RESTRICT
);

CREATE TABLE members (
    member_id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    department TEXT NOT NULL,
    year_of_study INTEGER NOT NULL CHECK (year_of_study BETWEEN 1 AND 4),
    phone TEXT NOT NULL,
    email TEXT NOT NULL,
    primary_sport TEXT NOT NULL
);

CREATE TABLE issue_record (
    issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_id INTEGER NOT NULL,
    member_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    issue_date TEXT NOT NULL,
    days_allowed INTEGER NOT NULL CHECK (days_allowed > 0),
    return_date TEXT,
    FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id) ON DELETE CASCADE,
    FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE
);

CREATE TABLE maintenance (
    maintenance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_id INTEGER NOT NULL,
    problem TEXT NOT NULL,
    sent_date TEXT NOT NULL,
    cost REAL NOT NULL CHECK (cost >= 0),
    status TEXT NOT NULL CHECK (status IN ('Pending', 'In Progress', 'Completed')),
    FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id) ON DELETE CASCADE
);

CREATE TABLE fines (
    fine_id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_id INTEGER NOT NULL,
    amount REAL NOT NULL CHECK (amount > 0),
    reason TEXT NOT NULL,
    fine_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('Pending', 'Paid')),
    FOREIGN KEY (issue_id) REFERENCES issue_record(issue_id) ON DELETE CASCADE
);

INSERT INTO categories (name, description, storage_location) VALUES ('Outdoor Games', 'Field games played on the ground', 'Ground Store Room A');
INSERT INTO categories (name, description, storage_location) VALUES ('Indoor Games', 'Board and table games', 'Indoor Stadium Cupboard 1');
INSERT INTO categories (name, description, storage_location) VALUES ('Racket Sports', 'Rackets and bats for court games', 'Indoor Stadium Cupboard 2');
INSERT INTO categories (name, description, storage_location) VALUES ('Athletics', 'Track and field equipment', 'Athletics Shed');
INSERT INTO categories (name, description, storage_location) VALUES ('Fitness', 'Gym and exercise equipment', 'Gym Store');
INSERT INTO categories (name, description, storage_location) VALUES ('Team Sports', 'Balls for team games', 'Ground Store Room B');

INSERT INTO equipment (category_id, name, brand, total_quantity, condition, purchase_date) VALUES (6, 'Football', 'Nivia', 12, 'Good', '2024-06-10');
INSERT INTO equipment (category_id, name, brand, total_quantity, condition, purchase_date) VALUES (1, 'Cricket Bat', 'SG', 8, 'Good', '2023-07-15');
INSERT INTO equipment (category_id, name, brand, total_quantity, condition, purchase_date) VALUES (6, 'Volleyball', 'Mikasa', 6, 'Fair', '2024-01-20');
INSERT INTO equipment (category_id, name, brand, total_quantity, condition, purchase_date) VALUES (6, 'Basketball', 'Spalding', 5, 'Under Repair', '2022-08-05');
INSERT INTO equipment (category_id, name, brand, total_quantity, condition, purchase_date) VALUES (3, 'Badminton Racket', 'Yonex', 10, 'Good', '2024-03-12');
INSERT INTO equipment (category_id, name, brand, total_quantity, condition, purchase_date) VALUES (3, 'Table Tennis Bat', 'Stag', 8, 'Good', '2023-11-02');
INSERT INTO equipment (category_id, name, brand, total_quantity, condition, purchase_date) VALUES (3, 'Tennis Racket', 'Wilson', 4, 'Fair', '2022-12-18');
INSERT INTO equipment (category_id, name, brand, total_quantity, condition, purchase_date) VALUES (2, 'Chess Board', 'Classic', 6, 'Good', '2023-05-25');
INSERT INTO equipment (category_id, name, brand, total_quantity, condition, purchase_date) VALUES (2, 'Carrom Board', 'Precise', 3, 'Poor', '2021-09-14');
INSERT INTO equipment (category_id, name, brand, total_quantity, condition, purchase_date) VALUES (1, 'Hockey Stick', 'Vixen', 10, 'Good', '2024-02-08');
INSERT INTO equipment (category_id, name, brand, total_quantity, condition, purchase_date) VALUES (4, 'Javelin', 'Nelco', 4, 'Good', '2023-08-30');
INSERT INTO equipment (category_id, name, brand, total_quantity, condition, purchase_date) VALUES (4, 'Shot Put', 'Nelco', 5, 'Under Repair', '2021-10-11');
INSERT INTO equipment (category_id, name, brand, total_quantity, condition, purchase_date) VALUES (5, 'Dumbbell Set', 'Kore', 6, 'Good', '2024-04-22');
INSERT INTO equipment (category_id, name, brand, total_quantity, condition, purchase_date) VALUES (5, 'Yoga Mat', 'Strauss', 15, 'Good', '2024-07-01');
INSERT INTO equipment (category_id, name, brand, total_quantity, condition, purchase_date) VALUES (5, 'Skipping Rope', 'Cosco', 12, 'Fair', '2023-09-09');

INSERT INTO members (full_name, department, year_of_study, phone, email, primary_sport) VALUES ('Arjun Nair', 'CSE', 2, '9100000001', 'demo.arjun@example.com', 'Football');
INSERT INTO members (full_name, department, year_of_study, phone, email, primary_sport) VALUES ('Priya Menon', 'ECE', 3, '9100000002', 'demo.priya@example.com', 'Badminton');
INSERT INTO members (full_name, department, year_of_study, phone, email, primary_sport) VALUES ('Rahul Krishnan', 'MECH', 1, '9100000003', 'demo.rahul@example.com', 'Cricket');
INSERT INTO members (full_name, department, year_of_study, phone, email, primary_sport) VALUES ('Anjali Thomas', 'CSE', 4, '9100000004', 'demo.anjali@example.com', 'Volleyball');
INSERT INTO members (full_name, department, year_of_study, phone, email, primary_sport) VALUES ('Vishnu Prasad', 'EEE', 2, '9100000005', 'demo.vishnu@example.com', 'Hockey');
INSERT INTO members (full_name, department, year_of_study, phone, email, primary_sport) VALUES ('Meera Joseph', 'IT', 3, '9100000006', 'demo.meera@example.com', 'Chess');
INSERT INTO members (full_name, department, year_of_study, phone, email, primary_sport) VALUES ('Karthik Raja', 'CIVIL', 1, '9100000007', 'demo.karthik@example.com', 'Athletics');
INSERT INTO members (full_name, department, year_of_study, phone, email, primary_sport) VALUES ('Divya Pillai', 'CSE', 2, '9100000008', 'demo.divya@example.com', 'Table Tennis');
INSERT INTO members (full_name, department, year_of_study, phone, email, primary_sport) VALUES ('Sanjay Kumar', 'ECE', 4, '9100000009', 'demo.sanjay@example.com', 'Basketball');
INSERT INTO members (full_name, department, year_of_study, phone, email, primary_sport) VALUES ('Lakshmi Iyer', 'IT', 1, '9100000010', 'demo.lakshmi@example.com', 'Yoga');
INSERT INTO members (full_name, department, year_of_study, phone, email, primary_sport) VALUES ('Aditya Varma', 'MECH', 3, '9100000011', 'demo.aditya@example.com', 'Tennis');
INSERT INTO members (full_name, department, year_of_study, phone, email, primary_sport) VALUES ('Neha Sharma', 'BIOTECH', 2, '9100000012', 'demo.neha@example.com', 'Carrom');
INSERT INTO members (full_name, department, year_of_study, phone, email, primary_sport) VALUES ('Rohan Das', 'AERO', 4, '9100000013', 'demo.rohan@example.com', 'Cricket');
INSERT INTO members (full_name, department, year_of_study, phone, email, primary_sport) VALUES ('Sneha George', 'CSE', 3, '9100000014', 'demo.sneha@example.com', 'Fitness');
INSERT INTO members (full_name, department, year_of_study, phone, email, primary_sport) VALUES ('Faisal Rahman', 'EEE', 1, '9100000015', 'demo.faisal@example.com', 'Javelin');

INSERT INTO issue_record (equipment_id, member_id, quantity, issue_date, days_allowed, return_date) VALUES (1, 1, 2, date('now', 'localtime', '-30 days'), 7, date('now', 'localtime', '-25 days'));
INSERT INTO issue_record (equipment_id, member_id, quantity, issue_date, days_allowed, return_date) VALUES (2, 3, 1, date('now', 'localtime', '-28 days'), 5, date('now', 'localtime', '-20 days'));
INSERT INTO issue_record (equipment_id, member_id, quantity, issue_date, days_allowed, return_date) VALUES (5, 2, 2, date('now', 'localtime', '-25 days'), 7, date('now', 'localtime', '-19 days'));
INSERT INTO issue_record (equipment_id, member_id, quantity, issue_date, days_allowed, return_date) VALUES (4, 9, 1, date('now', 'localtime', '-40 days'), 7, date('now', 'localtime', '-30 days'));
INSERT INTO issue_record (equipment_id, member_id, quantity, issue_date, days_allowed, return_date) VALUES (8, 6, 1, date('now', 'localtime', '-20 days'), 3, date('now', 'localtime', '-15 days'));
INSERT INTO issue_record (equipment_id, member_id, quantity, issue_date, days_allowed, return_date) VALUES (13, 14, 1, date('now', 'localtime', '-18 days'), 10, date('now', 'localtime', '-10 days'));
INSERT INTO issue_record (equipment_id, member_id, quantity, issue_date, days_allowed, return_date) VALUES (12, 15, 1, date('now', 'localtime', '-35 days'), 5, date('now', 'localtime', '-26 days'));
INSERT INTO issue_record (equipment_id, member_id, quantity, issue_date, days_allowed, return_date) VALUES (2, 13, 2, date('now', 'localtime', '-3 days'), 7, NULL);
INSERT INTO issue_record (equipment_id, member_id, quantity, issue_date, days_allowed, return_date) VALUES (3, 4, 2, date('now', 'localtime', '-2 days'), 5, NULL);
INSERT INTO issue_record (equipment_id, member_id, quantity, issue_date, days_allowed, return_date) VALUES (6, 8, 2, date('now', 'localtime', '-1 days'), 7, NULL);
INSERT INTO issue_record (equipment_id, member_id, quantity, issue_date, days_allowed, return_date) VALUES (14, 10, 3, date('now', 'localtime', '-4 days'), 10, NULL);
INSERT INTO issue_record (equipment_id, member_id, quantity, issue_date, days_allowed, return_date) VALUES (10, 5, 4, date('now', 'localtime', '-5 days'), 14, NULL);
INSERT INTO issue_record (equipment_id, member_id, quantity, issue_date, days_allowed, return_date) VALUES (1, 1, 1, date('now', 'localtime', '-15 days'), 7, NULL);
INSERT INTO issue_record (equipment_id, member_id, quantity, issue_date, days_allowed, return_date) VALUES (7, 11, 1, date('now', 'localtime', '-12 days'), 5, NULL);
INSERT INTO issue_record (equipment_id, member_id, quantity, issue_date, days_allowed, return_date) VALUES (9, 12, 1, date('now', 'localtime', '-10 days'), 3, NULL);

INSERT INTO maintenance (equipment_id, problem, sent_date, cost, status) VALUES (4, 'Valve leaking, balls not holding air', date('now', 'localtime', '-6 days'), 350, 'In Progress');
INSERT INTO maintenance (equipment_id, problem, sent_date, cost, status) VALUES (12, 'Surface rust and chipped coating', date('now', 'localtime', '-4 days'), 500, 'In Progress');
INSERT INTO maintenance (equipment_id, problem, sent_date, cost, status) VALUES (1, 'Stitching torn on two balls', date('now', 'localtime', '-60 days'), 400, 'Completed');
INSERT INTO maintenance (equipment_id, problem, sent_date, cost, status) VALUES (2, 'Handle grip replacement', date('now', 'localtime', '-50 days'), 250, 'Completed');
INSERT INTO maintenance (equipment_id, problem, sent_date, cost, status) VALUES (5, 'Restringing of four rackets', date('now', 'localtime', '-45 days'), 800, 'Completed');
INSERT INTO maintenance (equipment_id, problem, sent_date, cost, status) VALUES (15, 'Handles cracked on three ropes', date('now', 'localtime', '-3 days'), 150, 'Pending');
INSERT INTO maintenance (equipment_id, problem, sent_date, cost, status) VALUES (3, 'Patching and re-inflation', date('now', 'localtime', '-90 days'), 200, 'Completed');
INSERT INTO maintenance (equipment_id, problem, sent_date, cost, status) VALUES (11, 'Tip sharpening', date('now', 'localtime', '-75 days'), 300, 'Completed');
INSERT INTO maintenance (equipment_id, problem, sent_date, cost, status) VALUES (13, 'Loose plates tightened', date('now', 'localtime', '-30 days'), 180, 'Completed');
INSERT INTO maintenance (equipment_id, problem, sent_date, cost, status) VALUES (9, 'Board surface uneven', date('now', 'localtime', '-120 days'), 650, 'Completed');

INSERT INTO fines (issue_id, amount, reason, fine_date, status) VALUES (2, 30, 'Returned 3 days late', date('now', 'localtime', '-20 days'), 'Paid');
INSERT INTO fines (issue_id, amount, reason, fine_date, status) VALUES (2, 100, 'Bat handle grip damaged', date('now', 'localtime', '-20 days'), 'Paid');
INSERT INTO fines (issue_id, amount, reason, fine_date, status) VALUES (4, 30, 'Returned 3 days late', date('now', 'localtime', '-30 days'), 'Paid');
INSERT INTO fines (issue_id, amount, reason, fine_date, status) VALUES (4, 150, 'Ball valve damaged during use', date('now', 'localtime', '-30 days'), 'Pending');
INSERT INTO fines (issue_id, amount, reason, fine_date, status) VALUES (5, 20, 'Returned 2 days late', date('now', 'localtime', '-15 days'), 'Paid');
INSERT INTO fines (issue_id, amount, reason, fine_date, status) VALUES (7, 40, 'Returned 4 days late', date('now', 'localtime', '-26 days'), 'Paid');
INSERT INTO fines (issue_id, amount, reason, fine_date, status) VALUES (7, 200, 'Coating chipped during use', date('now', 'localtime', '-26 days'), 'Pending');
INSERT INTO fines (issue_id, amount, reason, fine_date, status) VALUES (13, 50, 'Overdue return', date('now', 'localtime', '-3 days'), 'Pending');
INSERT INTO fines (issue_id, amount, reason, fine_date, status) VALUES (14, 50, 'Overdue return', date('now', 'localtime', '-2 days'), 'Pending');
INSERT INTO fines (issue_id, amount, reason, fine_date, status) VALUES (15, 50, 'Overdue return', date('now', 'localtime', '-1 days'), 'Pending');
