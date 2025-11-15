from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
import stripe

from api_compass.api.deps import OrgScope, get_db_session, get_org_scope, get_system_session
from api_compass.core.config import settings
from api_compass.schemas import FeatureFlags
from api_compass.services import entitlements as entitlement_service

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/entitlements", response_model=FeatureFlags)
def read_entitlements(
    session: Session = Depends(get_db_session),
    org_scope: OrgScope = Depends(get_org_scope),
) -> FeatureFlags:
    snapshot = entitlement_service.get_entitlements(session, org_scope.org_id)
    payload = entitlement_service.build_feature_flags(snapshot)
    return FeatureFlags(**payload)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    session: Session = Depends(get_system_session),
) -> dict[str, bool]:
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    if signature is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Stripe signature header")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=signature,
            secret=settings.stripe_webhook_secret.get_secret_value(),
        )
    except ValueError as exc:  # pragma: no cover - Stripe validation guard
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload") from exc
    except stripe.error.SignatureVerificationError as exc:  # pragma: no cover - Stripe validation guard
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature") from exc

    handled = entitlement_service.handle_stripe_event(session, event)
    session.commit()
    return {"received": True, "handled": handled}
