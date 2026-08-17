# 09 · Payments

Stripe, one subscription product: the practitioner **Pro plan**. Nothing
else in this version touches payments — no client-to-practitioner charges,
no per-consultation billing, no marketplace split.

## Flow

1. A Basic practitioner calls `POST /api/me/upgrade`
   ([08](08-api.md#practitioner-basic-or-pro-own-resources-only)) → server
   creates a Stripe Checkout Session for the Pro subscription price, returns
   the redirect URL.
2. Practitioner completes checkout on Stripe's hosted page. Card details
   never touch our servers.
3. Stripe webhook (`checkout.session.completed`) → sets
   `stripe_customer_id`, `stripe_subscription_id`, `stripe_status=active`,
   flips `plan → pro`, and creates the practitioner's vault file
   ([02](02-data-model.md)).
4. Recurring billing is Stripe's — no invoicing logic on our side beyond
   listening for webhook events.

## Webhook events handled

| Event | Effect |
|---|---|
| `checkout.session.completed` | Activate Pro, create vault |
| `customer.subscription.updated` | Sync `stripe_status` |
| `customer.subscription.deleted` | See downgrade, below |
| `invoice.payment_failed` | Flag the practitioner (`stripe_status=past_due`); portal shows a banner, access is not cut immediately |

## Downgrade / cancellation {#downgrade}

When a Pro subscription ends (cancelled or payment ultimately fails past
Stripe's retry schedule): `plan → basic`. The vault file is **not deleted** —
Pro clinical data doesn't disappear because a subscription lapsed. It becomes
inaccessible through the portal (no RAG, no client management routes,
[05](05-practitioner-portal.md)) until the practitioner re-upgrades, at
which point the same vault file is reused rather than recreated.

Actual deletion of a vault (a practitioner leaving the platform entirely) is
an explicit admin action, not a side effect of a lapsed subscription.

## What's not built

Proration edge cases, multiple price tiers, coupons/discounts, and
dunning-email customization are Stripe Billing Portal's job — we link to
Stripe's own customer portal for a practitioner to manage payment method and
cancel, rather than rebuilding that UI.
