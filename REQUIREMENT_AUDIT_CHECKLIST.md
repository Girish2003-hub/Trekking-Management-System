# Trekking Management Requirement Audit Checklist

Date: 2026-07-06

Legend:

- Implemented: Available and working from code + route wiring
- Partial: Exists but with limitation/bug versus requirement
- Missing: Not found in current codebase

## 1) Mandatory Technology and Setup Requirements

| Requirement                              | Status      | Evidence                                                                                                 | Manual Validation                           |
| ---------------------------------------- | ----------- | -------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| Flask backend                            | Implemented | app entry and factory in app.py and app/**init**.py                                                      | Run flask --app app.py routes               |
| Jinja2 + HTML + CSS + Bootstrap frontend | Implemented | Templates in app/templates, Bootstrap CDN in app/templates/base.html, styles in app/static/css/style.css | Open any page and inspect Bootstrap classes |
| SQLite database only                     | Implemented | SQLite URI in config.py                                                                                  | Check created DB file trekking.db           |
| DB created programmatically              | Implemented | init-db CLI command calls db.create_all() in app/**init**.py                                             | Run flask --app app.py init-db              |
| Admin pre-exists in DB                   | Implemented | init-db creates default admin if absent in app/**init**.py                                               | Run init-db and login with default admin    |

## 2) Authentication Requirements

| Requirement                          | Status      | Evidence                                                    | Manual Validation                    |
| ------------------------------------ | ----------- | ----------------------------------------------------------- | ------------------------------------ |
| Login for Admin, Staff, User         | Implemented | auth login route in app/auth/routes.py                      | Login with each role account         |
| Registration for Staff and User only | Implemented | auth register route role check in app/auth/routes.py        | Try registering staff and user       |
| No admin registration                | Implemented | register restricts role to user/staff in app/auth/routes.py | Try sending role=admin (should fail) |

## 3) Admin Functionalities

| Requirement                                          | Status      | Evidence                                                                                            | Manual Validation                          |
| ---------------------------------------------------- | ----------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| Admin dashboard totals: treks, users+staff, bookings | Implemented | admin dashboard logic in app/admin/routes.py and template app/templates/admin/dashboard.html        | Compare dashboard counts with DB records   |
| Add trek                                             | Implemented | create_trek in app/admin/routes.py + form app/templates/admin/trek_form.html                        | Create a new trek                          |
| Edit trek                                            | Implemented | edit_trek in app/admin/routes.py + form app/templates/admin/trek_form.html                          | Edit status/slots/date and save            |
| Remove trek                                          | Implemented | delete_trek in app/admin/routes.py + list app/templates/admin/treks.html                            | Delete a trek                              |
| Approve staff                                        | Implemented | staff_approvals and approve_staff in app/admin/routes.py + app/templates/admin/staff_approvals.html | Register a staff, approve from admin       |
| Assign staff to trek                                 | Implemented | assign_staff in app/admin/routes.py + app/templates/admin/assign_staff.html                         | Assign staff and verify on staff dashboard |
| View users, staff, treks                             | Implemented | admin users + treks pages in app/admin/routes.py and templates                                      | Open Users and Treks pages                 |
| Search treks/staff/users by name or ID               | Implemented | search filters in app/admin/routes.py + app/templates/admin/search.html                             | Search by ID and name/email/location       |
| Blacklist users/staff                                | Implemented | toggle_blacklist in app/admin/routes.py + app/templates/admin/users.html                            | Toggle blacklist and attempt login         |
| Deactivate users/staff                               | Implemented | toggle_deactivate in app/admin/routes.py + app/templates/admin/users.html                           | Deactivate then test access/login          |
| View all bookings (historical data)                  | Implemented | bookings route in app/admin/routes.py + app/templates/admin/bookings.html                           | Verify cancelled/completed appear          |

## 4) Staff Functionalities

| Requirement                                     | Status      | Evidence                                                                                                                                               | Manual Validation                                           |
| ----------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------- |
| Staff self-register and login                   | Implemented | register/login logic in app/auth/routes.py                                                                                                             | Register as staff then login after approval                 |
| Staff needs admin approval for dashboard access | Implemented | staff is_approved checks in app/auth/routes.py and app/staff/routes.py                                                                                 | Attempt login before approval                               |
| View assigned treks                             | Implemented | staff dashboard query in app/staff/routes.py + app/templates/staff/dashboard.html                                                                      | Confirm only assigned treks are shown                       |
| Dashboard shows registered users count per trek | Implemented | counts computed in app/staff/routes.py + app/templates/staff/dashboard.html                                                                            | Verify count against bookings                               |
| Update available slots                          | Implemented | trek_detail POST logic in app/staff/routes.py                                                                                                          | Update slots within allowed range                           |
| Update trek status Open/Closed                  | Implemented | backend and staff UI dropdown both support open/closed in app/staff/routes.py and app/templates/staff/trek_detail.html                                 | Set status to Open and Closed from staff manage page        |
| Mark trek started/completed                     | Implemented | route and staff UI support started/completed, and selected status binding is corrected in app/staff/routes.py and app/templates/staff/trek_detail.html | Reload manage page and verify current status is preselected |
| View participant list for assigned trek         | Implemented | participants query in app/staff/routes.py + app/templates/staff/trek_detail.html                                                                       | Open assigned trek details                                  |
| Manage participant status                       | Implemented | update_participant_status in app/staff/routes.py                                                                                                       | Change booked/cancelled/completed and verify slots updates  |
| Only assigned staff can manage trek             | Implemented | assigned_staff_id check in app/staff/routes.py                                                                                                         | Try opening another staff's trek URL                        |

## 5) User (Trekker) Functionalities

| Requirement                              | Status      | Evidence                                                                              | Manual Validation                           |
| ---------------------------------------- | ----------- | ------------------------------------------------------------------------------------- | ------------------------------------------- |
| User self-register and login             | Implemented | register/login in app/auth/routes.py                                                  | Register and login as user                  |
| View approved/open treks                 | Implemented | dashboard filters in app/user/routes.py + app/templates/user/dashboard.html           | Verify pending/closed treks hidden          |
| Search/filter by difficulty and location | Implemented | query params in app/user/routes.py + filter form in app/templates/user/dashboard.html | Filter by each difficulty and location text |
| Book treks                               | Implemented | book_trek in app/user/routes.py + Book action in app/templates/user/dashboard.html    | Book an open trek                           |
| View booking status/history              | Implemented | history route in app/user/routes.py + app/templates/user/history.html                 | Check booked/cancelled/completed history    |
| Edit profile                             | Implemented | profile route in app/user/routes.py + app/templates/user/profile.html                 | Update name/contact                         |

## 6) Other Core Functionalities

| Requirement                             | Status      | Evidence                                                                                  | Manual Validation                                |
| --------------------------------------- | ----------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------ |
| Prevent overbooking                     | Implemented | slot checks before booking and slot decrement in app/user/routes.py                       | Try booking when slots=0                         |
| Book only when trek is Open             | Implemented | trek.status check in app/user/routes.py                                                   | Try booking approved/closed trek                 |
| Complete booking history per user       | Implemented | booking status transitions without deletion in app/user/routes.py and app/staff/routes.py | Cancel and complete bookings, then check history |
| Admin can view historical trekking data | Implemented | all bookings visible in app/admin/routes.py + app/templates/admin/bookings.html           | Verify old statuses retained                     |

## 7) Recommended/Optional Functionalities

| Requirement                            | Status  | Notes                                       |
| -------------------------------------- | ------- | ------------------------------------------- |
| API resources for treks/users/bookings | Missing | No API blueprints/endpoints found           |
| Charts for trekking statistics         | Missing | No chart views or chart library usage found |

## 8) Runtime Validation Performed in This Audit

- Flask route table command succeeded: flask --app app.py routes
- DB init command succeeded: flask --app app.py init-db (admin already exists)
- Workspace problem scan returned no static errors

## 9) Immediate Fix Candidates Before Final Viva

1. Completed: server-side validation added for trek create/edit date parsing, end-date ordering, required fields, difficulty/status constraints, and positive integer parsing in app/admin/routes.py.
