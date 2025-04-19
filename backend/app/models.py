from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
import uuid
from sqlalchemy import Column, String, ARRAY


class UserBase(SQLModel):
    login_id: str = Field(unique=True)
    nickname: str
    age_range: Optional[str] = None
    gender: Optional[str] = None


class User(UserBase, table=True):
    __tablename__ = "users"
    
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
    )
    usual_illness: Optional[List[str]] = Field(sa_column=Column(ARRAY(String)))
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 관계 설정
    family_members: List["FamilyMember"] = Relationship(back_populates="user")
    contacts_as_user: List["UserContact"] = Relationship(
        back_populates="user", 
        sa_relationship_kwargs={"foreign_keys": "[UserContact.user_id]"}
    )
    contacts_as_contact: List["UserContact"] = Relationship(
        back_populates="contact_user",
        sa_relationship_kwargs={"foreign_keys": "[UserContact.contact_user_id]"}
    )


class UserCreate(UserBase):
    password: str
    usual_illness: Optional[List[str]] = None


class UserRead(UserBase):
    id: uuid.UUID
    created_at: datetime
    usual_illness: Optional[List[str]] = None


class FamilyMemberBase(SQLModel):
    nickname: str
    relation: Optional[str] = None
    age: int


class FamilyMember(FamilyMemberBase, table=True):
    __tablename__ = "family_members"
    
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
    )
    user_id: uuid.UUID = Field(foreign_key="users.id")
    usual_illness: Optional[List[str]] = Field(sa_column=Column(ARRAY(String)), default=None)
    
    # 관계 설정
    user: User = Relationship(back_populates="family_members")


class FamilyMemberCreate(FamilyMemberBase):
    usual_illness: Optional[List[str]] = None


class FamilyMemberRead(FamilyMemberBase):
    id: uuid.UUID
    user_id: uuid.UUID
    usual_illness: Optional[List[str]] = None


class UserContactBase(SQLModel):
    alias: Optional[str] = None


class UserContact(UserContactBase, table=True):
    __tablename__ = "user_contacts"
    
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
    )
    user_id: uuid.UUID = Field(foreign_key="users.id")
    contact_user_id: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 관계 설정
    user: User = Relationship(
        back_populates="contacts_as_user",
        sa_relationship_kwargs={"foreign_keys": "[UserContact.user_id]"}
    )
    contact_user: User = Relationship(
        back_populates="contacts_as_contact",
        sa_relationship_kwargs={"foreign_keys": "[UserContact.contact_user_id]"}
    )


class UserContactCreate(UserContactBase):
    contact_login_id: str


class ContactUserInfo(SQLModel):
    id: uuid.UUID
    login_id: str
    nickname: str
    age_range: Optional[str] = None
    gender: Optional[str] = None


class UserContactRead(UserContactBase):
    id: uuid.UUID
    user_id: uuid.UUID
    contact_user_id: uuid.UUID
    created_at: datetime
    contact_user: Optional[ContactUserInfo] = None
