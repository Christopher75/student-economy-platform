# Design Decisions

This file documents key design decisions made during development where the original specification left room for interpretation.

---

## Frontend: Bootstrap 5 over Tailwind CSS

**Decision**: Used Bootstrap 5 (CDN) instead of Tailwind CSS.

**Reason**: Bootstrap 5 provides a mature component ecosystem (cards, badges, modals, pagination, tabs, offcanvas) that maps directly to the UI requirements of this platform. For a Django-template-based project at this complexity level, Bootstrap produces cleaner template code. Tailwind's utility-first approach becomes verbose in large templates without a build step. crispy-forms integrates seamlessly with Bootstrap 5 via `crispy-bootstrap5`.

---

## Authentication: Email as USERNAME_FIELD

**Decision**: Used `email` as the `USERNAME_FIELD` rather than `username`. Both fields still exist — `username` is stored for profile URLs and display.

**Reason**: Students more reliably remember their email than a chosen username. Email-based login is the modern standard for student platforms.

---

## Messaging: No WebSockets

**Decision**: Messaging is page-refresh based, not real-time. No WebSockets or polling.

**Reason**: This is an academic MVP. Real-time messaging (Django Channels + Redis) adds significant infrastructure complexity inappropriate for a first version. The architecture is clean and upgrading to Channels later is straightforward.

---

## Photo Storage: Local Media Files

**Decision**: All photos are stored in `MEDIA_ROOT` on the local filesystem.

**Reason**: This is a development/demonstration platform. In production, this would be swapped for AWS S3 or similar cloud storage with minimal settings changes (the storage backend is abstracted via Django's file storage API).

---

## Skill Booking: Simple Date Request Model

**Decision**: Booking requests include a `requested_date` (date only, no time-slot picker).

**Reason**: A full calendar/availability scheduling system is complex and out of scope for version 1. The `availability` text field on skill offerings is used for free-form availability description. Upgrading to a calendar picker is a planned future improvement.

---

## Reviews: Booking-Gated Only

**Decision**: Reviews can only be left after a booking reaches `completed` status.

**Reason**: This prevents fake/spam reviews and ensures all reviews are backed by an actual completed transaction, which is critical for platform trust.

---

## Notifications: Database-Only (No Email)

**Decision**: Notifications are stored in the database and displayed in-app only. No email notifications sent for platform events.

**Reason**: Avoids email deliverability complexity for the demo. The notification system is fully built — adding email sending to notification creation is a one-line addition per notification type.

---

## Seed Data: Ugandan Universities Represented

**Decision**: Seed data includes students from Cavendish University Uganda, Makerere University, Mbarara University of Science and Technology (MUST), International University of East Africa (IUEA), Kampala Capital City Authority University, and Nkumba University.

**Reason**: Creates a realistic multi-campus experience. The platform is designed to serve any Ugandan university student, not just one institution.

---

## Trust Score: Computed (Not Stored)

**Decision**: `get_trust_score()` is computed on demand rather than stored in the database.

**Reason**: Trust score is a composite of several quickly-changing fields. Caching it in the DB risks staleness. For a platform at this scale, the computation is fast enough to run per-request. Caching (Redis) can be added later if performance requires it.

---

## Admin: Django's Built-In Admin (Customised)

**Decision**: Used Django's built-in admin panel rather than building a custom admin dashboard.

**Reason**: Django admin is production-grade, well-tested, and extremely powerful for this use case. The time saved allows more polish on the student-facing interface.
