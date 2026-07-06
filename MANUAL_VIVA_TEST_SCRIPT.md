# Manual Viva Test Script (Trekking Management)

Date: 2026-07-06

## Pre-setup

1. Install dependencies:
   pip install -r requirements.txt
2. Initialize DB:
   flask --app app.py init-db
3. Run app:
   flask --app app.py run
4. Admin login:
   Email: admin@trek.local
   Password: admin123

## Test Run (Suggested 12-Step Flow)

1. Register one staff account and one user account from /auth/register.
2. Try staff login immediately: expect pending approval warning and blocked dashboard access.
3. Login as admin and open Staff Approvals page.
4. Approve the new staff account.
5. Go to Manage Treks and create one trek (Easy/Moderate/Hard as needed).
6. Edit trek status to Open if not already open.
7. Assign approved staff to the created trek from Assign Staff page.
8. Login as staff and verify assigned trek appears with booked-user count.
9. On staff trek detail page:
   - verify status dropdown now shows Open, Closed, Started, Completed
   - update status to Closed and then Open
   - verify current status is preselected when page reloads
10. Login as user and open dashboard:

- filter by difficulty and location
- book the Open trek

11. Verify overbooking prevention:

- reduce available slots to 0 (staff/admin), then try another booking as user
- expect booking rejection

12. Verify history and lifecycle:

- cancel one booking from user history
- mark a booking completed from staff participant list
- login admin and verify all statuses appear in All Bookings

## Requirement-oriented Spot Checks

1. Only Open trek can be booked.
2. Staff cannot manage unassigned treks (direct URL attempt should fail).
3. Blacklisted user/staff cannot continue normal access.
4. Deactivated user/staff cannot access expected role flows.
5. Search page finds records by ID and by text fields.

## Viva-ready Demo Order (5-7 min)

1. 30 sec: Problem statement and role model.
2. 90 sec: Admin flow (approve staff, create trek, assign staff, search, bookings).
3. 90 sec: Staff flow (assigned trek, update slots/status, manage participants).
4. 90 sec: User flow (filter/search, booking, cancellation, history, profile).
5. 30 sec: Core constraints (overbooking prevention and role-based restrictions).

## Backup Data Plan

If data gets inconsistent during demo, run:
flask --app app.py init-db
Then re-create one staff, one user, one trek for a clean flow.
