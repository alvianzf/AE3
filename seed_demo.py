"""Idempotent LOCAL-ONLY demo seed for the user-manual screenshots.

Creates, through the app's own core_store/vault/auth code (same functions the
signup, approval and admin routes call): one superadmin, one approved Pro
practitioner (library upload enabled) with two clients, one registered client
login, and one pending practitioner for the admin approvals queue.

Credentials are test values for the local dev instance only. Safe to re-run.
Run from the project root:  .venv/bin/python seed_demo.py
"""
from app import auth, core_store, vault

DEMO_PASSWORD = "Demo-Manual-2026"

ADMIN = {"email": "admin@demo.example.test", "name": "Demo Admin"}
PRACTITIONER = {
    "email": "practitioner@demo.example.test",
    "name": "Dr. Maya Demo",
    "bio": "Functional-medicine practitioner focused on metabolic and gut health.",
    "specialties": ["Metabolic health", "Gut health"],
    "languages": ["English", "Bahasa Indonesia"],
    "years_experience": 9,
}
CLIENT = {"email": "client@demo.example.test", "name": "Sam Demo Client"}
EXTRA_CLIENTS = [
    {"email": "client2@demo.example.test", "name": "Alex Sample"},
    {"email": "client3@demo.example.test", "name": "Jordan Example"},
]
PENDING = {"email": "pending@demo.example.test", "name": "Dr. Riley Pending"}


def ensure_admin() -> None:
    if core_store.get_admin_by_email(ADMIN["email"]) is None:
        core_store.create_admin(ADMIN["email"], auth.hash_password(DEMO_PASSWORD),
                                ADMIN["name"], role="superadmin")


def ensure_practitioner() -> str:
    existing = core_store.get_practitioner_by_email(PRACTITIONER["email"])
    if existing is None:
        existing = core_store.create_practitioner_pending(
            PRACTITIONER["email"], auth.hash_password(DEMO_PASSWORD),
            PRACTITIONER["name"], bio=PRACTITIONER["bio"],
            specialties=PRACTITIONER["specialties"],
            languages=PRACTITIONER["languages"],
            years_experience=PRACTITIONER["years_experience"])
    pid = existing["id"]
    core_store.approve_practitioner(pid)
    core_store.set_plan(pid, "pro")
    core_store.set_can_upload_library(pid, True)
    vault.ensure_schema(pid)
    return pid


def ensure_client(pid: str, who: dict) -> None:
    if core_store.get_client_directory_entry(who["email"]) is not None:
        return
    c = vault.create_client(pid, who["name"], who["email"],
                            auth.hash_password(DEMO_PASSWORD))
    core_store.add_client_directory_entry(who["email"], pid, c["id"])


def ensure_pending() -> None:
    if core_store.get_practitioner_by_email(PENDING["email"]) is None:
        core_store.create_practitioner_pending(
            PENDING["email"], auth.hash_password(DEMO_PASSWORD), PENDING["name"],
            bio="Nutritionist awaiting approval.", specialties=["Nutrition"],
            languages=["English"], years_experience=4)


if __name__ == "__main__":
    ensure_admin()
    pid = ensure_practitioner()
    for who in [CLIENT, *EXTRA_CLIENTS]:
        ensure_client(pid, who)
    ensure_pending()
    print("seed_demo: ok (admin, practitioner, 3 clients, 1 pending practitioner)")
