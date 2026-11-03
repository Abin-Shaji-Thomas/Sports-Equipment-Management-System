-- Sample queries for the Sports Equipment Management System.
-- The same queries can be run from the Queries screen of the app.

-- 1. All equipment with category (JOIN)
SELECT e.equipment_id, e.name, e.brand, c.name AS category, e.total_quantity, e.condition
FROM equipment e
JOIN categories c ON e.category_id = c.category_id
ORDER BY e.equipment_id;

-- 2. Issue details with equipment and member names (JOIN of 3 tables)
SELECT i.issue_id, e.name AS equipment, m.full_name AS member, i.quantity, i.issue_date, i.return_date
FROM issue_record i
JOIN equipment e ON i.equipment_id = e.equipment_id
JOIN members m ON i.member_id = m.member_id
ORDER BY i.issue_id;

-- 3. Number of issues per equipment (LEFT JOIN + COUNT + GROUP BY)
SELECT e.name AS equipment, COUNT(i.issue_id) AS times_issued
FROM equipment e
LEFT JOIN issue_record i ON e.equipment_id = i.equipment_id
GROUP BY e.equipment_id, e.name
ORDER BY times_issued DESC, e.name;

-- 4. Currently overdue issues (calculated due date, WHERE)
SELECT i.issue_id, e.name AS equipment, m.full_name AS member,
       date(i.issue_date, '+' || i.days_allowed || ' days') AS due_date
FROM issue_record i
JOIN equipment e ON i.equipment_id = e.equipment_id
JOIN members m ON i.member_id = m.member_id
WHERE i.return_date IS NULL
  AND date(i.issue_date, '+' || i.days_allowed || ' days') < date('now', 'localtime')
ORDER BY due_date;

-- 5. Pending fines (WHERE status = 'Pending')
SELECT fine_id, issue_id, amount, reason, fine_date
FROM fines
WHERE status = 'Pending'
ORDER BY fine_date;

-- 6. Issue records ordered by issue date (ORDER BY)
SELECT i.issue_id, e.name AS equipment, m.full_name AS member, i.issue_date, i.return_date
FROM issue_record i
JOIN equipment e ON i.equipment_id = e.equipment_id
JOIN members m ON i.member_id = m.member_id
ORDER BY i.issue_date DESC;

-- 7. Total fine amount per member (JOIN + SUM + GROUP BY)
SELECT m.full_name AS member, SUM(f.amount) AS total_fine
FROM members m
JOIN issue_record i ON m.member_id = i.member_id
JOIN fines f ON i.issue_id = f.issue_id
GROUP BY m.member_id, m.full_name
ORDER BY total_fine DESC;

-- 8. Nested query: names of members who have borrowed 'Cricket Bat' (IN with a subquery)
SELECT full_name
FROM members
WHERE member_id IN (SELECT member_id FROM issue_record
                    WHERE equipment_id IN (SELECT equipment_id FROM equipment WHERE name = 'Cricket Bat'))
ORDER BY full_name;
