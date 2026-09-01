from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/facilities", tags=["facilities"])


def get_owned_facility(facility_id: int, current_user: models.User, db: Session) -> models.Facility:
    """
    THE multi-tenant enforcement point. Fetches a facility only if it
    belongs to the current user's organization. Returns 404 — not 403 —
    for a facility that exists but belongs to someone else, so we never
    even confirm that ID exists in another tenant's data.
    """
    facility = (
        db.query(models.Facility)
        .filter(models.Facility.id == facility_id, models.Facility.organization_id == current_user.organization_id)
        .first()
    )
    if not facility:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found")
    return facility


@router.post("", response_model=schemas.FacilityOut, status_code=status.HTTP_201_CREATED)
def create_facility(
    payload: schemas.FacilityCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.query(models.Facility).filter(models.Facility.slug == payload.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="That slug is already taken — try another")
    facility = models.Facility(organization_id=current_user.organization_id, **payload.model_dump())
    db.add(facility)
    db.commit()
    db.refresh(facility)
    return facility


@router.get("", response_model=List[schemas.FacilityOut])
def list_my_facilities(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Every facility belonging to the caller's organization — never anyone else's."""
    return db.query(models.Facility).filter(models.Facility.organization_id == current_user.organization_id).all()


@router.get("/{facility_id}", response_model=schemas.FacilityOut)
def get_facility_public(facility_id: int, db: Session = Depends(get_db)):
    """
    Public, unauthenticated — this is what the GUEST-facing find-me app
    calls after a QR scan. No login required to look up a building.
    """
    facility = db.query(models.Facility).filter(models.Facility.id == facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    return facility


@router.get("/by-slug/{slug}", response_model=schemas.FacilityOut)
def get_facility_by_slug(slug: str, db: Session = Depends(get_db)):
    """Same as above but by slug — what a QR code's URL actually encodes."""
    facility = db.query(models.Facility).filter(models.Facility.slug == slug).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    return facility


@router.put("/{facility_id}", response_model=schemas.FacilityOut)
def update_facility(
    facility_id: int,
    payload: schemas.FacilityUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    facility = get_owned_facility(facility_id, current_user, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(facility, field, value)
    db.commit()
    db.refresh(facility)
    return facility


@router.delete("/{facility_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_facility(
    facility_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    facility = get_owned_facility(facility_id, current_user, db)
    db.delete(facility)
    db.commit()
    return None
