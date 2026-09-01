from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db
from .facilities import get_owned_facility

router = APIRouter(prefix="/facilities/{facility_id}/cautions", tags=["cautions"])


@router.get("", response_model=List[schemas.CautionOut])
def list_cautions(facility_id: int, db: Session = Depends(get_db)):
    """Public — the live notice list every guest sees."""
    return (
        db.query(models.Caution)
        .filter(models.Caution.facility_id == facility_id)
        .order_by(models.Caution.created_at.desc())
        .all()
    )


@router.post("", response_model=schemas.CautionOut, status_code=status.HTTP_201_CREATED)
def post_caution(
    facility_id: int,
    payload: schemas.CautionCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Staff or admin posts a notice. The moment this commits, it's live for
    every guest calling GET on this same endpoint — no separate publish step.
    """
    get_owned_facility(facility_id, current_user, db)
    caution = models.Caution(facility_id=facility_id, **payload.model_dump())
    db.add(caution)
    db.commit()
    db.refresh(caution)
    return caution


@router.delete("/{caution_id}", status_code=status.HTTP_204_NO_CONTENT)
def resolve_caution(
    facility_id: int,
    caution_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_facility(facility_id, current_user, db)
    caution = (
        db.query(models.Caution)
        .filter(models.Caution.id == caution_id, models.Caution.facility_id == facility_id)
        .first()
    )
    if not caution:
        raise HTTPException(status_code=404, detail="Notice not found")
    db.delete(caution)
    db.commit()
    return None
