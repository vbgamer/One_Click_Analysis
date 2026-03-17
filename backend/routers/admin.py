"""
Admin Router - Handles admin-only endpoints:
  - View all users + credit balances
  - View & approve/reject credit requests
  - Manually adjust any user's credits
"""
import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import models, schemas, database, auth

router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Helper ──────────────────────────────────────────────────────────────────

def get_db():
    return next(database.get_db())


# ── Users ────────────────────────────────────────────────────────────────────

@router.get("/users", response_model=list[schemas.User])
def list_users(
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(auth.get_current_admin_user),
):
    """Return every registered user with their role and credits."""
    return db.query(models.User).all()


@router.patch("/users/{user_id}/credits")
def set_user_credits(
    user_id: int,
    payload: schemas.AdminCreditUpdate,
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(auth.get_current_admin_user),
):
    """Directly set a user's credit balance (overwrite)."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.credits = payload.credits
    db.commit()
    db.refresh(user)
    return {"message": f"Credits updated to {user.credits} for {user.email}"}


# ── Credit Requests ───────────────────────────────────────────────────────────

@router.get("/requests", response_model=list[schemas.CreditRequestOut])
def list_credit_requests(
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(auth.get_current_admin_user),
):
    """Return all credit requests (all statuses)."""
    return (
        db.query(models.CreditRequest)
        .order_by(models.CreditRequest.created_at.desc())
        .all()
    )


@router.post("/requests/{req_id}/approve")
def approve_credit_request(
    req_id: int,
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(auth.get_current_admin_user),
):
    """Approve a pending credit request — credits are deposited to the user."""
    req = db.query(models.CreditRequest).filter(models.CreditRequest.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {req.status}")

    # Deposit credits
    user = db.query(models.User).filter(models.User.id == req.user_id).first()
    user.credits += req.amount_requested
    req.status = "approved"
    req.resolved_at = datetime.datetime.utcnow()
    db.commit()
    return {
        "message": f"Approved. {req.amount_requested} credits added to {user.email}. New balance: {user.credits}"
    }


@router.post("/requests/{req_id}/reject")
def reject_credit_request(
    req_id: int,
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(auth.get_current_admin_user),
):
    """Reject a pending credit request."""
    req = db.query(models.CreditRequest).filter(models.CreditRequest.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {req.status}")

    req.status = "rejected"
    req.resolved_at = datetime.datetime.utcnow()
    db.commit()
    return {"message": "Request rejected."}
