"""Stripe billing for the practitioner Pro plan — the only subscription
product in this version (see specs/v2/09-payments.md). No client-to-
practitioner charges, no per-consultation billing.

Card details never touch our servers: checkout happens on Stripe's hosted
page, and everything here just reacts to Stripe's webhook events.
"""
from __future__ import annotations

import stripe
from fastapi import Depends, FastAPI, HTTPException, Request

from . import auth, core_store
from .config import get_config

cfg = get_config()
stripe.api_key = cfg.stripe_secret_key


def create_checkout_session(practitioner_id: str, email: str) -> str:
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": cfg.stripe_price_id_pro, "quantity": 1}],
        customer_email=email,
        client_reference_id=practitioner_id,
        metadata={"practitioner_id": practitioner_id},
        subscription_data={"metadata": {"practitioner_id": practitioner_id}},
        success_url=f"{cfg.public_base_url}/static/practitioner/profile.html?upgraded=1",
        cancel_url=f"{cfg.public_base_url}/static/practitioner/profile.html",
    )
    return session.url


def handle_webhook(payload: bytes, sig_header: str) -> dict:
    event = stripe.Webhook.construct_event(payload, sig_header, cfg.stripe_webhook_secret)
    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        practitioner_id = data.get("client_reference_id") or data.get("metadata", {}).get("practitioner_id")
        core_store.activate_pro(practitioner_id)
        core_store.set_stripe_fields(
            practitioner_id,
            customer_id=data.get("customer"),
            subscription_id=data.get("subscription"),
            status="active",
        )

    elif event_type == "customer.subscription.updated":
        practitioner_id = data.get("metadata", {}).get("practitioner_id")
        core_store.set_stripe_fields(practitioner_id, status=data.get("status"))

    elif event_type == "customer.subscription.deleted":
        practitioner_id = data.get("metadata", {}).get("practitioner_id")
        core_store.set_plan(practitioner_id, "basic")

    elif event_type == "invoice.payment_failed":
        # Invoice objects carry the subscription's metadata snapshot at
        # parent.subscription_details.metadata (stripe-python 15.x / current
        # API version) rather than a top-level field.
        parent = data.get("parent") or {}
        subscription_details = parent.get("subscription_details") or {}
        practitioner_id = (subscription_details.get("metadata") or {}).get("practitioner_id")
        core_store.set_stripe_fields(practitioner_id, status="past_due")

    return {"handled": event_type}


def billing_portal_url(customer_id: str) -> str:
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{cfg.public_base_url}/static/practitioner/profile.html",
    )
    return session.url


def register(app: FastAPI) -> None:
    @app.post("/api/me/upgrade")
    async def upgrade(session: dict = Depends(auth.require_practitioner)):
        practitioner = core_store.get_practitioner(session["id"])
        if practitioner is None:
            raise HTTPException(status_code=404, detail="Practitioner not found.")
        url = create_checkout_session(practitioner["id"], practitioner["email"])
        return {"url": url}

    @app.post("/api/stripe/webhook")
    async def webhook(request: Request):
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature", "")
        try:
            result = handle_webhook(payload, sig_header)
        except (stripe.error.SignatureVerificationError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid webhook signature.")
        return result

    @app.get("/api/me/billing-portal")
    async def billing_portal(session: dict = Depends(auth.require_pro_practitioner)):
        practitioner = core_store.get_practitioner(session["id"])
        if practitioner is None or not practitioner.get("stripe_customer_id"):
            raise HTTPException(status_code=404, detail="No Stripe customer on file.")
        url = billing_portal_url(practitioner["stripe_customer_id"])
        return {"url": url}
