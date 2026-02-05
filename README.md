# prj-grp4-Marks

## Description

This is a full-stack web application designed for a **Salon Appointment & Feedback Management System**. It supports three user roles — **clients**, **professionals**, and **administrators** — and allows for managing appointments, submitting and responding to feedback reports, and performing administrative operations with fine-grained access control.

The platform also features a **public API documentation interface** with live request support.

---

## Key Features

### ✅ User & Role Management
- Multi-level roles: `client`, `professional`, `admin_user`, `admin_appoint`, `admin_super`.
- Admins can add, edit, deactivate, and issue warnings to users.
- Superadmins have exclusive access to logs and full privileges.

### ✅ Appointment System
- Clients can schedule appointments with professionals using an intuitive UI.
- Admins can view, filter, edit, and delete appointments.
- Appointment cost is calculated dynamically based on duration and provider’s pay rate.

### ✅ Report Feedback Workflow
- Clients can submit feedback on completed appointments.
- Professionals respond afterward. Each party sees only their respective input interface.
- Notification system alerts users when new feedback or responses are available.

### ✅ Admin Control Center
- Separate admin dashboards for managing users, appointments, and reports.
- Admin Logs panel with badge-tagged activity summaries and emoji feedback.

### ✅ Caching and Performance
- Flask-Caching is used to cache heavy views (appointments, reports, user lists).
- Automatic cache invalidation on update operations.

### ✅ Responsive and Animated UI
- Uses CSS animations and floating label forms for modern look-and-feel.
- Includes modals for confirmation dialogs and interactive UI filters.

### ✅ Public API Explorer
- Interactive `/api/docs` page with working **Try It** buttons for:
  - Users
  - Appointments
  - Reports

---

## Setup & Run Instructions
This project uses Flask, PostgreSQL, and HTML templates.

Make sure to pip install the requirements.txt
pip install -r requirements.txt


The Docker container is:
  - salon_web
  - my_postgres

The Docker Image is:
  - salon_project

---

## Authors
This project was completed by Group 4 for the Web Applications III course.
  - Andrew Marks (Team Leader)
  - Alexander Roxas
  - Van Rix Ryan Njoumene Meli
---

