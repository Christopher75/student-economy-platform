# Subscription Tier Plan — Student Economy Platform

## Overview

A freemium system. Every user starts on the Free tier at registration.
Pro Seller is UGX 5,000/month. Payment is manual Mobile Money with
admin confirmation — no payment gateway required.

---

## Tier Comparison

| Feature                        | Free         | Pro Seller        |
|-------------------------------|--------------|-------------------|
| Active marketplace listings    | 3            | Unlimited         |
| Active skill offerings         | 2            | Unlimited         |
| Photos per listing             | 2            | 5                 |
| Messages per day               | 15           | Unlimited         |
| Search placement               | Chronological | Priority (first)  |
| Analytics dashboard            | Locked        | Full access       |
| Pro badge                      | No            | Yes               |
| Price                          | Free          | UGX 5,000/month   |

---

## Payment Flow

1. User visits `/accounts/upgrade/` — sees Free vs Pro comparison
2. Clicks "Upgrade to Pro" — a `SubscriptionPayment` record is created
   with status=`pending` and a unique reference code (SEP-PRO-XXXX)
3. User sees payment instructions page at `/accounts/payment/<ref_code>/`
   — told to send UGX 5,000 to the platform MTN or Airtel number with
   their reference code in the payment note
4. User fills in their MoMo transaction ID and phone number and submits
5. Admin reviews at `/admin-panel/payments/` and clicks Confirm or Reject
6. On Confirm: user's subscription_tier set to 'pro', subscription_end
   set to today+30 days, notification sent
7. On Reject: payment marked rejected, user notified with reason

---

## Free Tier Limit UX

Limits are only surfaced at the moment of breach — never at registration.

- **Listing limit (3)**: User fills the full create form. On submit the
  view intercepts, re-renders the form with `show_upgrade_modal=True`,
  and a Bootstrap modal explains the limit and offers to upgrade.
  Form data is preserved so they lose nothing.

- **Skill limit (2)**: Same modal pattern.

- **Photo limit (2)**: The photo upload input is capped via JavaScript
  at the user's `max_photos` limit (2 free / 5 pro). A tooltip quietly
  informs: "Pro users can upload up to 5 photos."

- **Message limit (15/day)**: Tracked on `CustomUser.daily_messages_sent`
  + `daily_messages_reset_date`. On message 16, the send is blocked and
  a banner is shown. Resets automatically next day on next message attempt.

---

## Pro Badge

Amber/gold `⭐ Pro` badge. Appears:
- Navbar — next to username (logged-in Pro users)
- Profile page — next to name
- Listing cards — corner overlay
- Skill cards — next to provider name
- Listing detail — seller info section
- Skill detail — provider info section

---

## Analytics (Pro Only)

Four cards on `/accounts/analytics/`:
1. Listing Performance — total views, top listing by views
2. Skill Performance — total booking requests, top skill by bookings
3. Profile Engagement — profile views, contact clicks
4. Account Status — plan, expiry date, renew button

Free users see a blurred/locked preview with an Upgrade CTA.

---

## Subscription Expiry

Management command `python manage.py check_subscriptions`:
- Finds all pro users with `subscription_end < today`
- Downgrades them to free
- Notifies them to renew
- Safe to run multiple times (idempotent)

In production this would run nightly via cron or Celery beat.

---

## Settings to Configure

In `.env`:
```
PLATFORM_MTN_NUMBER=077XXXXXXX
PLATFORM_AIRTEL_NUMBER=075XXXXXXX
```

In `settings.py`, these are exposed as:
```python
PLATFORM_MTN_NUMBER = config('PLATFORM_MTN_NUMBER', default='077X XXX XXX')
PLATFORM_AIRTEL_NUMBER = config('PLATFORM_AIRTEL_NUMBER', default='075X XXX XXX')
```

---

## Migration Notes

Single migration adds:
- `CustomUser`: subscription_tier, subscription_start, subscription_end,
  pro_activated_by, profile_view_count, daily_messages_sent,
  daily_messages_reset_date
- `Listing`: contact_click_count
- New model: `SubscriptionPayment`
