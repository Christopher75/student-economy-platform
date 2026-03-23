# Student Economy Platform — Project Plan

## Project Overview

A campus-exclusive Django web application combining a **Campus Marketplace** and a **Campus Skill Exchange** into one unified platform for university students. The platform is built on the entrepreneurship concept of **Synthesis** — merging two complementary ideas into something more powerful than either part alone.

---

## Architecture Overview

### Django Apps

| App | Responsibility |
|-----|---------------|
| `accounts` | Custom user model, registration, login, profiles, student verification |
| `marketplace` | Listings, categories, photos, wishlist, reports |
| `skills` | Skill offerings, categories, bookings, reviews |
| `messaging` | Internal conversation threads, messages, inbox |
| `notifications` | In-platform notification system |
| `core` | Homepage, shared utilities, error pages, admin customisation |

---

## Database Models

### accounts.CustomUser (extends AbstractUser)
- `email` (unique, used for login)
- `full_name`
- `student_id` (unique)
- `university`
- `course`
- `year_of_study` (1–6)
- `phone_number`
- `profile_photo` (ImageField, optional)
- `bio` (TextField, optional)
- `is_verified` (bool, default False)
- `verification_status` (pending / approved / rejected)
- `date_joined` (auto)
- `last_seen` (auto-updated)
- `reputation_score` (computed from reviews)

### accounts.EmailVerificationToken
- `user` (FK)
- `token` (UUID)
- `created_at`
- `is_used`

### marketplace.Category
- `name`, `slug`, `icon`, `description`, `order`

### marketplace.Listing
- `seller` (FK CustomUser)
- `title`, `description`
- `category` (FK Category)
- `condition` (new/like_new/good/fair/poor)
- `price` (DecimalField)
- `negotiable` (bool)
- `university` (str)
- `campus_location` (str)
- `status` (available/sold/reserved)
- `views_count` (int)
- `created_at`, `updated_at`

### marketplace.ListingPhoto
- `listing` (FK)
- `image` (ImageField)
- `is_primary` (bool)
- `order` (int)

### marketplace.SavedListing
- `user` (FK)
- `listing` (FK)
- `saved_at`

### marketplace.ListingReport
- `reporter` (FK)
- `listing` (FK)
- `reason` (inappropriate/spam/fake/other)
- `description`
- `created_at`
- `is_resolved`

### skills.SkillCategory
- `name`, `slug`, `icon`, `description`, `order`

### skills.SkillOffering
- `provider` (FK CustomUser)
- `title`, `description`
- `category` (FK SkillCategory)
- `delivery_method` (in_person/online/both)
- `price_type` (fixed/hourly/negotiable)
- `price_min`, `price_max`
- `estimated_duration`
- `availability` (TextField)
- `university` (str)
- `status` (active/paused/inactive)
- `views_count`
- `created_at`, `updated_at`
- `average_rating` (computed)
- `total_reviews` (computed)

### skills.SkillPortfolioItem
- `skill` (FK SkillOffering)
- `title`
- `image` (ImageField, optional)
- `link` (URL, optional)
- `description`

### skills.SkillBooking
- `skill` (FK SkillOffering)
- `client` (FK CustomUser)
- `provider` (FK CustomUser)
- `status` (pending/confirmed/completed/cancelled)
- `requested_date`
- `notes`
- `created_at`, `updated_at`
- `price_agreed` (DecimalField)

### skills.Review
- `booking` (OneToOne FK SkillBooking)
- `reviewer` (FK CustomUser)
- `reviewee` (FK CustomUser)
- `rating` (1–5)
- `comment`
- `created_at`
- `review_type` (client_to_provider/provider_to_client)

### messaging.Conversation
- `participants` (M2M CustomUser)
- `listing` (FK Listing, nullable)
- `booking` (FK SkillBooking, nullable)
- `created_at`
- `last_message_at`

### messaging.Message
- `conversation` (FK)
- `sender` (FK CustomUser)
- `content` (TextField)
- `created_at`
- `read_at` (nullable — when first read by recipient)

### notifications.Notification
- `user` (FK CustomUser)
- `notification_type` (new_message/booking_request/booking_accepted/booking_declined/item_sold/new_review/listing_reported)
- `title`
- `message`
- `is_read`
- `action_url`
- `created_at`

---

## URL Map

```
/                                    → Homepage
/accounts/register/                  → Register
/accounts/login/                     → Login
/accounts/logout/                    → Logout
/accounts/verify-email/<token>/      → Email verification
/accounts/profile/<username>/        → View profile
/accounts/profile/edit/              → Edit own profile
/accounts/password-reset/            → Password reset request
/accounts/password-reset/done/       → Password reset sent
/accounts/password-reset/<uidb64>/<token>/ → Password reset confirm
/accounts/password-reset/complete/   → Password reset complete
/accounts/dashboard/                 → User dashboard (my activity)

/marketplace/                        → Browse listings
/marketplace/create/                 → Create listing
/marketplace/<pk>/                   → Listing detail
/marketplace/<pk>/edit/              → Edit listing
/marketplace/<pk>/delete/            → Delete listing
/marketplace/<pk>/mark-sold/         → Mark as sold
/marketplace/<pk>/save/              → Toggle save/unsave
/marketplace/<pk>/report/            → Report listing
/marketplace/wishlist/               → Saved listings

/skills/                             → Browse skills
/skills/create/                      → Create skill offering
/skills/<pk>/                        → Skill detail
/skills/<pk>/edit/                   → Edit skill
/skills/<pk>/delete/                 → Delete skill
/skills/<pk>/book/                   → Book skill session

/bookings/                           → My bookings
/bookings/<pk>/                      → Booking detail
/bookings/<pk>/accept/               → Accept booking
/bookings/<pk>/decline/              → Decline booking
/bookings/<pk>/complete/             → Mark complete
/bookings/<pk>/review/               → Leave review

/messages/                           → Inbox
/messages/<pk>/                      → Conversation thread
/messages/start/<username>/          → Start new conversation

/notifications/                      → All notifications
/notifications/mark-read/<pk>/       → Mark one as read
/notifications/mark-all-read/        → Mark all as read

/admin/                              → Django admin (customised)
```

---

## Template Structure

```
templates/
  base.html                  ← Master layout with navbar, footer, alerts
  home.html                  ← Dynamic homepage
  accounts/
    login.html
    register.html
    verify_email.html
    profile.html
    edit_profile.html
    dashboard.html
    password_reset_form.html
    password_reset_done.html
    password_reset_confirm.html
    password_reset_complete.html
  marketplace/
    list.html                ← Browse with filters/search
    detail.html              ← Listing detail with contact
    create.html
    edit.html
    wishlist.html
  skills/
    list.html
    detail.html
    create.html
    edit.html
  bookings/
    list.html
    detail.html
    review_form.html
  messaging/
    inbox.html
    conversation.html
  notifications/
    list.html
  errors/
    404.html
    500.html
  partials/
    navbar.html
    footer.html
    listing_card.html
    skill_card.html
    star_rating.html
    pagination.html
    empty_state.html
```

---

## Third-Party Packages

| Package | Reason |
|---------|--------|
| `django` | Core framework |
| `pillow` | Image upload processing |
| `django-crispy-forms` | Styled form rendering |
| `crispy-bootstrap5` | Bootstrap 5 integration for crispy forms |
| `django-widget-tweaks` | Granular form field control in templates |
| `python-decouple` | Environment variable management |
| `django-cleanup` | Auto-delete orphaned media files |

---

## Smart / Creative Features Planned

1. **Trust Score** — Users earn a trust badge after email verification + completing 3+ transactions
2. **"Hot Right Now"** section on homepage — most-viewed listings this week
3. **Similar Listings** — Based on same category and university
4. **Seller Response Rate** — Shown on profiles (ratio of messages replied to)
5. **Online Status** — "Active today", "Active this week", "Inactive"
6. **Listing View Counter** — Tracks how many times each listing was viewed
7. **Price Drop Alert** (simple) — If a saved item's price drops, notify the saver
8. **Featured Listings** — Admin can mark listings as featured for homepage display
9. **Dashboard Analytics** — Sellers/providers see views, saves, booking counts
10. **Verification Badge** — Verified students get a badge next to their name

---

## Frontend Choice

**Bootstrap 5** via CDN — chosen for:
- Mature component library (cards, modals, badges, forms, pagination)
- Mobile-first responsive grid
- No build step needed (CDN)
- Cleaner template code than Tailwind utility-heavy approach for a project this size
- crispy-forms integration works perfectly with Bootstrap 5

---

## Development Phases

1. **Phase 1** — Project setup, custom user model, authentication
2. **Phase 2** — Marketplace app (listings, photos, search, filter)
3. **Phase 3** — Skills app (offerings, bookings, reviews)
4. **Phase 4** — Messaging system
5. **Phase 5** — Notifications system
6. **Phase 6** — Admin customisation
7. **Phase 7** — Smart features, homepage, polish
8. **Phase 8** — Seed data management command
9. **Phase 9** — Documentation (Report.docx)
