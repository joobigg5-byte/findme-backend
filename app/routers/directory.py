from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db
from .facilities import get_owned_facility

router = APIRouter(prefix="/facilities/{facility_id}/directory", tags=["directory"])


@router.get("", response_model=List[schemas.DirectoryItemOut])
def list_directory_items(facility_id: int, db: Session = Depends(get_db)):
    """Public — this is the guest-facing wayfinding directory."""
    return db.query(models.DirectoryItem).filter(models.DirectoryItem.facility_id == facility_id).all()


@router.post("", response_model=schemas.DirectoryItemOut, status_code=status.HTTP_201_CREATED)
def create_directory_item(
    facility_id: int,
    payload: schemas.DirectoryItemCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_facility(facility_id, current_user, db)  # raises 404 if not owned
    item = models.DirectoryItem(facility_id=facility_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{item_id}", response_model=schemas.DirectoryItemOut)
def update_directory_item(
    facility_id: int,
    item_id: int,
    payload: schemas.DirectoryItemUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_facility(facility_id, current_user, db)
    item = (
        db.query(models.DirectoryItem)
        .filter(models.DirectoryItem.id == item_id, models.DirectoryItem.facility_id == facility_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Directory item not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_directory_item(
    facility_id: int,
    item_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_facility(facility_id, current_user, db)
    item = (
        db.query(models.DirectoryItem)
        .filter(models.DirectoryItem.id == item_id, models.DirectoryItem.facility_id == facility_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Directory item not found")
    db.delete(item)
    db.commit()
    return None
