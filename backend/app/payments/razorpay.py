"""Razorpay payment-link client: live Razorpay API when real keys are configured, sandbox otherwise."""

import logging
import uuid
from typing import Any

try:
    import razorpay
except ImportError:  # optional in sandbox-only setups
    razorpay = None

from app.core.config import settings

logger = logging.getLogger(__name__)


def is_sandbox_key(key_id: str) -> bool:
    return not key_id or key_id.startswith("rzp_test_mock")


def _real_contact(email: str | None, phone: str | None) -> dict[str, str]:
    """Only pass contact details Razorpay should actually notify (never demo placeholders)."""
    contact = {}
    if email and not email.endswith("@example.com"):
        contact["email"] = email
    if phone:
        contact["contact"] = phone
    return contact


class RazorpayClient:
    def __init__(
        self, key_id: str = settings.RAZORPAY_KEY_ID, key_secret: str = settings.RAZORPAY_KEY_SECRET
    ):
        self.client: Any = None
        if razorpay and not is_sandbox_key(key_id):
            try:
                self.client = razorpay.Client(auth=(key_id, key_secret))
            except Exception as e:
                logger.warning("Failed to initialise the Razorpay client: %s", e)

    @property
    def mode(self) -> str:
        return "live" if self.client else "sandbox"

    def create_payment_link(
        self,
        amount_in_inr: float,
        description: str,
        reference_id: str,
        customer_name: str | None = None,
        customer_email: str | None = None,
        customer_phone: str | None = None,
    ) -> dict[str, Any]:
        amount_in_paise = round(amount_in_inr * 100)
        base = {"amount_in_inr": round(amount_in_inr, 2), "tool": "create_payment_link", "mode": self.mode}

        if not self.client:
            link_id = f"plink_sbx_{uuid.uuid4().hex}"
            return {
                **base,
                "success": True,
                "sandbox": True,
                "payment_link_id": link_id,
                "short_url": f"{settings.PUBLIC_APP_URL.rstrip('/')}/pay/{link_id}",
                "status": "created",
                "description": description,
            }

        contact = _real_contact(customer_email, customer_phone)
        try:
            response = self.client.payment_link.create(
                {
                    "amount": amount_in_paise,
                    "currency": "INR",
                    "accept_partial": False,
                    "description": description,
                    "reference_id": reference_id[:40],
                    "customer": {"name": customer_name or "Customer", **contact},
                    "notify": {"sms": "contact" in contact, "email": "email" in contact},
                    "reminder_enable": bool(contact),
                }
            )
        except Exception as e:
            # Never hand the customer a link that doesn't exist.
            logger.warning("Razorpay payment link creation failed: %s", e)
            return {**base, "success": False, "sandbox": False, "error": "Payment link could not be created."}
        return {
            **base,
            "success": True,
            "sandbox": False,
            "payment_link_id": response.get("id"),
            "short_url": response.get("short_url"),
            "status": response.get("status", "created"),
            "description": description,
        }

    def fetch_payment_link(self, link_id: str) -> dict[str, Any]:
        if not self.client:
            return {"success": False, "error": "Sandbox links are tracked locally."}
        try:
            link = self.client.payment_link.fetch(link_id)
        except Exception as e:
            logger.warning("Razorpay payment link fetch failed: %s", e)
            return {"success": False, "error": "Payment link status unavailable."}
        return {
            "success": True,
            "payment_link_id": link_id,
            "status": link.get("status"),
            "amount_paid_inr": (link.get("amount_paid") or 0) / 100,
        }


razorpay_client = RazorpayClient()
