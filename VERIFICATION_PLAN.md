# Verification System Implementation Plan
# Student Economy Platform — Cavendish University Uganda

## Overview
Five-layer verification system: domain gate → uniqueness → email OTP → document selfie → trust score.
SMS OTP is deferred to a future phase. No third-party services required for this phase.

---

## Existing State

- `CustomUser` has `is_email_verified` (BooleanField) and `is_verified` (BooleanField)
- `verification_status` exists with choices: pending / approved / rejected
- `EmailVerificationToken` model uses UUID click-through links (being replaced by OTP)
- In DEBUG mode, registration auto-verifies users; production sends a token link
- Email settings are already configured in settings.py via env vars
- Middleware only has `UpdateLastSeenMiddleware`
- `phone_number` is currently required

---

## Layer 1 — Registration Gate

### Form changes (`accounts/forms.py`)
- `clean_email()`: reject any email whose domain is not `students.cavendish.ac.ug`
  - Error: "Only Cavendish University Uganda student emails are accepted. Please use your @students.cavendish.ac.ug address."
- `clean_student_id()`: validate alphanumeric only (regex `^[a-zA-Z0-9]+$`)
  - Error: format example "cd121356"
- `phone_number`: change to `required=False`; add help_text note about SMS coming soon
- Update error messages for duplicate email/student_id to match spec

### Template changes (`templates/accounts/register.html`)
- Add `id="id_email"` blur JS to check domain instantly on the client
- Show red inline `<div id="emailDomainError">` beneath email field
- Disable submit if domain error is shown
- Update phone_number field to show optional label + help text

---

## Layer 2 — Uniqueness Enforcement

### Model changes (`accounts/models.py` — `CustomUser`)
- `student_id`: add `db_index=True`
- `phone_number`: change to `blank=True` (optional)
- Add `registration_ip = models.GenericIPAddressField(null=True, blank=True)`

### View changes (`accounts/views.py`)
- `RegisterView.post()`: capture IP from `HTTP_X_FORWARDED_FOR` or `REMOTE_ADDR`, strip to first IP, assign to `user.registration_ip`

---

## Layer 3 — Email OTP Verification

### New model: `EmailOTPVerification` (`accounts/models.py`)
```
user           OneToOneField(User, CASCADE, related_name='email_otp')
otp_hash       CharField(64)  — SHA-256 hex digest, never store plain OTP
otp_created_at DateTimeField
otp_expires_at DateTimeField  — otp_created_at + 15 minutes
attempts       IntegerField, default=0
is_verified    BooleanField, default=False
verified_at    DateTimeField, null=True
resend_count   IntegerField, default=0
last_resent_at DateTimeField, null=True
locked_until   DateTimeField, null=True  — set when attempts >= 5
```

### OTP helpers (top-level functions in models.py)
- `_generate_otp()` → 6-char string of digits
- `_hash_otp(otp)` → `hashlib.sha256(otp.encode()).hexdigest()`

### Registration flow changes (`RegisterView.post()`)
- Remove DEBUG auto-verify shortcut (users must complete OTP now in all environments)
- After saving user: create `EmailOTPVerification`, generate OTP, store hash, set expiry
- Send email (console backend in dev, SMTP in prod)
- Redirect to `/accounts/verify-email/` (no token in URL — session-based)
- Store `pending_verify_user_id` in session to identify who is verifying

### New views
- `verify_email_otp(request)` — GET shows form, POST checks OTP
  - Reads `pending_verify_user_id` from session
  - Shows masked email (first 2 chars + *** + @students.cavendish.ac.ug)
  - 6-digit input
  - On correct: set `is_email_verified=True`, `EmailOTPVerification.is_verified=True`, clear session var, login user, redirect to `verify_identity` page
  - On incorrect: increment attempts, show remaining count
  - On attempts >= 5: lock for 30 minutes via `locked_until`
  - On expired: show resend prompt
- `resend_otp(request)` — POST only
  - Checks `resend_count < 5` and `last_resent_at` cooldown (60 seconds)
  - Generates new OTP, resets expiry and attempts, increments resend_count
  - Returns JSON `{ok: true, resend_count: N}` for use by JS countdown

### Email templates (new files)
- `templates/accounts/emails/otp_email.txt`
- `templates/accounts/emails/otp_email.html`  — large OTP in styled box

### New template
- `templates/accounts/verify_email_otp.html`
  - Masked email display
  - 6 separate digit inputs (for UX) that join into one hidden field on submit
  - 60-second resend countdown (JS)
  - "Resend code" link that calls `/accounts/resend-otp/` via fetch, resets countdown

### Middleware (`accounts/middleware.py`)
Add `EmailVerificationMiddleware`:
- Runs after `AuthenticationMiddleware`
- If `user.is_authenticated` and `not user.is_email_verified`
- Exempt URLs: `/accounts/verify-email/`, `/accounts/resend-otp/`, `/accounts/logout/`, `/static/`, `/media/`, `/` (homepage)
- Redirect to `/accounts/verify-email/`

### Settings
```python
# Dev
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# Prod
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'cd121012@students.cavendish.ac.ug'
EMAIL_HOST_PASSWORD = '<app password>'
DEFAULT_FROM_EMAIL = 'Student Economy Platform <noreply@studenteconomy.com>'
```

---

## Layer 4 — Document Verification

### Model changes to `CustomUser`
- Change `verification_status` choices to: `unverified / pending / verified / rejected`
- Change default to `'unverified'`
- Add `id_card_photo = ImageField(upload_to='verification/id_cards/', null=True, blank=True)`
- Add `selfie_photo = ImageField(upload_to='verification/selfies/', null=True, blank=True)`
- Add `verification_submitted_at = DateTimeField(null=True, blank=True)`
- Add `verification_reviewed_at = DateTimeField(null=True, blank=True)`
- Add `verification_reviewed_by = ForeignKey(User, null=True, related_name='reviewed_verifications')`
- Add `verification_rejection_reason = TextField(blank=True)`

### New form: `IdentityVerificationForm`
- `id_card_photo`: ImageField, required, accept jpg/png, max 5MB
- `selfie_photo`: ImageField, required, accept jpg/png, max 5MB
- `consent`: BooleanField, required
- Validation: check mimetype/extension, check file size

### New views
- `verify_identity(request)`:
  - GET: show only if `is_email_verified=True` and `verification_status in ('unverified', 'rejected')`
  - POST: save both photos, set `verification_status='pending'`, `verification_submitted_at=now()`
  - Redirect to confirmation page (inline in same view)
- `serve_verification_photo(request, photo_type, pk)`:
  - Staff-only view that streams the file from storage
  - Returns `FileResponse` or redirects to signed Cloudinary URL
- `admin_verification_list(request)`:
  - Lists all pending submissions with both photos + user details
- `admin_verification_approve(request, pk)`:
  - POST only — sets `verification_status='verified'`, `is_verified=True`, `verification_reviewed_at`, `reviewed_by`
  - Sends notification + email
- `admin_verification_reject(request, pk)`:
  - POST with `reason` and `notes` — sets `verification_status='rejected'`
  - Stores rejection reason, sends notification + email
  - Resets to allow resubmission

### File security
If Cloudinary is configured: upload with `type='private'`, serve via signed URL (valid 300 seconds).
If local storage: serve through `serve_verification_photo` view after staff check.

### New templates
- `templates/accounts/verify_identity.html` — two upload fields, consent checkbox, privacy notice
- `templates/accounts/verify_identity_submitted.html` — confirmation page
- `templates/admin_panel/verification.html` — side-by-side photo review interface
- `templates/accounts/emails/identity_verified.txt/.html`
- `templates/accounts/emails/identity_rejected.txt/.html`

### New URL patterns
```
/accounts/verify-email/                  → verify_email_otp
/accounts/resend-otp/                    → resend_otp
/accounts/verify-identity/               → verify_identity
/accounts/verification-photo/<type>/<pk>/ → serve_verification_photo
/admin-panel/verification/               → admin_verification_list
/admin-panel/verification/<pk>/approve/  → admin_verification_approve
/admin-panel/verification/<pk>/reject/   → admin_verification_reject
```

Note: existing `/accounts/verify-email/<uuid:token>/` path is kept for backward compatibility.

---

## Layer 5 — Trust Score

### Updated `get_trust_score()` on `CustomUser`
```
+15  email OTP verified (is_email_verified=True)
+20  identity documents verified (is_verified=True)
+5   per completed marketplace transaction (up to 3 → max +15)
+5   per completed skill booking (up to 3 → max +15)
+3   per 5-star review received
+2   per 4-star review received
+1   per 3-star review received
-10  per confirmed report against this user
-5   per listing or skill removed by admin
cap: 0 to 100
```

---

## Verification Journey Widget (Dashboard)

Add a 4-step progress indicator to `templates/accounts/dashboard.html`:

```
Step 1 — Create account     (always complete once logged in)   ✅ green
Step 2 — Verify email        (check is_email_verified)          ✅/🔵/⬜
Step 3 — Submit documents    (check verification_status)        ✅/🔵/⬜
Step 4 — Admin approval      (check verification_status=verified) ✅/🔵/⬜
```

Hide the widget entirely once all four steps are complete and the Verified badge is shown.

---

## Migration Plan

```
python manage.py makemigrations accounts
python manage.py migrate
```

One migration covers:
- Add `registration_ip` to `CustomUser`
- Add `id_card_photo`, `selfie_photo` and related verification fields
- Change `verification_status` choices + default
- Add `db_index` to `student_id`
- Make `phone_number` blank=True
- Create `EmailOTPVerification` model

---

## Environment Variables (`.env.example` additions)

```
# Email (production SMTP)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=cd121012@students.cavendish.ac.ug
EMAIL_HOST_PASSWORD=aiub pbym eyaj odjx
DEFAULT_FROM_EMAIL=Student Economy Platform <noreply@studenteconomy.com>

# Email (development — prints OTP to terminal, no mail sent)
# EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

---

## Future Phase Note

SMS OTP via MTN/Airtel is deferred. The phone number is collected at registration (optional) and stored for admin reference. When SMS is added, a `PhoneOTPVerification` model will be introduced alongside `EmailOTPVerification` and a new verification step will be inserted between steps 2 and 3 in the journey.

---

## Files Changed

| File | Change |
|---|---|
| `accounts/models.py` | Add fields + EmailOTPVerification model, update trust score |
| `accounts/forms.py` | Email domain gate, phone optional, student_id validation, doc upload form |
| `accounts/views.py` | OTP views, identity upload, admin verification, secure photo serving |
| `accounts/middleware.py` | Add EmailVerificationMiddleware |
| `accounts/urls.py` | New URL patterns |
| `accounts/admin.py` | Register EmailOTPVerification |
| `student_economy/settings.py` | Add middleware, email env docs |
| `templates/accounts/register.html` | Client-side domain check JS, phone optional |
| `templates/accounts/verify_email_otp.html` | New — OTP entry page |
| `templates/accounts/verify_identity.html` | New — document upload page |
| `templates/accounts/verify_identity_submitted.html` | New — confirmation |
| `templates/accounts/emails/otp_email.txt` | New |
| `templates/accounts/emails/otp_email.html` | New |
| `templates/accounts/emails/identity_verified.txt` | New |
| `templates/accounts/emails/identity_verified.html` | New |
| `templates/accounts/emails/identity_rejected.txt` | New |
| `templates/accounts/emails/identity_rejected.html` | New |
| `templates/accounts/dashboard.html` | Add 4-step progress widget |
| `templates/admin_panel/verification.html` | New — side-by-side review |
| `.env.example` | Document new email variables |
