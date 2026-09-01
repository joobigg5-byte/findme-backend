"""
Pydantic schemas — these define exactly what the API accepts and returns.
FastAPI uses these for automatic request validation and for generating the
live OpenAPI docs at /docs.
"""
import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# ---------- Auth ----------

class SignupRequest(BaseModel):
    organization_name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=200)


class MessageResponse(BaseModel):
    message: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    organization_id: int
    organization_name: str


# ---------- Facility ----------

class FacilityCreate(BaseModel):
    slug: str = Field(..., min_length=1, max_length=120, pattern=r"^[a-z0-9-]+$")
    name: str = Field(..., min_length=1, max_length=200)
    subtitle: str = ""
    tagline: str = ""
    receptionist: str = ""
    address: str = ""
    hours: str = ""
    city: str = ""
    country: str = ""
    category: str = ""
    lat: Optional[float] = None
    lng: Optional[float] = None
    template_type: Optional[str] = None


class FacilityUpdate(BaseModel):
    name: Optional[str] = None
    subtitle: Optional[str] = None
    tagline: Optional[str] = None
    receptionist: Optional[str] = None
    address: Optional[str] = None
    hours: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    category: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    template_type: Optional[str] = None


class FacilityOut(BaseModel):
    id: int
    slug: str
    name: str
    subtitle: str
    tagline: str
    receptionist: str
    address: str
    hours: str
    city: str
    country: str
    category: str
    lat: Optional[float]
    lng: Optional[float]
    template_type: Optional[str]

    class Config:
        from_attributes = True


# ---------- Directory items ----------

class DirectoryItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    category: str = Field("places", pattern="^(people|rooms|places)$")
    floor: str = ""
    room: str = ""
    description: str = ""
    status: Optional[str] = None
    icon: str = "door"


class DirectoryItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    floor: Optional[str] = None
    room: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    icon: Optional[str] = None


class DirectoryItemOut(BaseModel):
    id: int
    facility_id: int
    name: str
    category: str
    floor: str
    room: str
    description: str
    status: Optional[str]
    icon: str

    class Config:
        from_attributes = True


# ---------- Staff ----------

class StaffCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    role: str = ""
    department: str = ""
    dest_directory_item_id: Optional[int] = None
    phone: str = ""
    email: str = ""
    hours: str = ""
    handles: List[str] = []
    today_status: str = Field("in", pattern="^(in|remote|out)$")


class StaffUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    dest_directory_item_id: Optional[int] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    hours: Optional[str] = None
    handles: Optional[List[str]] = None
    today_status: Optional[str] = None


class StaffOut(BaseModel):
    id: int
    facility_id: int
    name: str
    role: str
    department: str
    dest_directory_item_id: Optional[int]
    phone: str
    email: str
    hours: str
    handles: List[str]
    today_status: str

    class Config:
        from_attributes = True


# ---------- Cautions ----------

class CautionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    area: str = ""
    description: str = ""


class CautionOut(BaseModel):
    id: int
    facility_id: int
    title: str
    area: str
    description: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True
