import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db
from .facilities import get_owned_facility

router = APIRouter(prefix="/facilities/{facility_id}/staff", tags=["staff"])


def _to_out(s: models.StaffMember) -> schemas.StaffOut:
    return schemas.StaffOut(
        id=s.id, facility_id=s.facility_id, name=s.name, role=s.role, department=s.department,
        dest_directory_item_id=s.dest_directory_item_id, phone=s.phone, email=s.email, hours=s.hours,
        handles=json.loads(s.handles_json or "[]"), today_status=s.today_status,
    )


@router.get("", response_model=List[schemas.StaffOut])
def list_staff(facility_id: int, db: Session = Depends(get_db)):
    """Public — guests browsing Get-Me → People see this."""
    rows = db.query(models.StaffMember).filter(models.StaffMember.facility_id == facility_id).all()
    return [_to_out(s) for s in rows]


@router.post("", response_model=schemas.StaffOut, status_code=status.HTTP_201_CREATED)
def create_staff(
    facility_id: int,
    payload: schemas.StaffCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_facility(facility_id, current_user, db)
    data = payload.model_dump()
    handles = data.pop("handles")
    member = models.StaffMember(facility_id=facility_id, handles_json=json.dumps(handles), **data)
    db.add(member)
    db.commit()
    db.refresh(member)
    return _to_out(member)


@router.put("/{staff_id}", response_model=schemas.StaffOut)
def update_staff(
    facility_id: int,
    staff_id: int,
    payload: schemas.StaffUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_facility(facility_id, current_user, db)
    member = (
        db.query(models.StaffMember)
        .filter(models.StaffMember.id == staff_id, models.StaffMember.facility_id == facility_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="Staff member not found")
    data = payload.model_dump(exclude_unset=True)
    if "handles" in data:
        member.handles_json = json.dumps(data.pop("handles"))
    for field, value in data.items():
        setattr(member, field, value)
    db.commit()
    db.refresh(member)
    return _to_out(member)


@router.delete("/{staff_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_staff(
    facility_id: int,
    staff_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_facility(facility_id, current_user, db)
    member = (
        db.query(models.StaffMember)
        .filter(models.StaffMember.id == staff_id, models.StaffMember.facility_id == facility_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="Staff member not found")
    db.delete(member)
    db.commit()
    return None
