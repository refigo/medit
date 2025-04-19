from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
import uuid
from sqlalchemy import Column, String, ARRAY, Integer, Text, JSON
from pydantic import BaseModel


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
    conversations: List["Conversation"] = Relationship(back_populates="user")


class UserCreate(UserBase):
    password: str
    usual_illness: Optional[List[str]] = None


class UserRead(UserBase):
    id: uuid.UUID
    created_at: datetime
    usual_illness: Optional[List[str]] = None


class UserUpdate(SQLModel):
    nickname: Optional[str] = None
    age_range: Optional[str] = None
    gender: Optional[str] = None
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
    alias_nickname: Optional[str] = None
    relation: Optional[str] = None


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
    alias_nickname: Optional[str] = None
    relation: Optional[str] = None


# Q&A Conversation Models
class ConversationBase(SQLModel):
    title: Optional[str] = None


class Conversation(ConversationBase, table=True):
    __tablename__ = "conversations"
    
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
    )
    user_id: uuid.UUID = Field(foreign_key="users.id")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 관계 설정
    user: User = Relationship(back_populates="conversations")
    messages: List["ConversationMessage"] = Relationship(back_populates="conversation")
    reports: List["ConversationReport"] = Relationship(back_populates="conversation")


class ConversationCreate(ConversationBase):
    message_content: Optional[str] = None
    request_report: Optional[Dict[str, Any]] = None


class ConversationRead(ConversationBase):
    id: uuid.UUID
    user_id: uuid.UUID
    started_at: datetime


class ConversationMessageBase(SQLModel):
    sender: str  # 'user' | 'ai assistant'
    content: Optional[str] = Field(default=None, sa_column=Column(Text))


class ConversationMessage(ConversationMessageBase, table=True):
    __tablename__ = "conversation_messages"
    
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
    )
    conversation_id: uuid.UUID = Field(foreign_key="conversations.id")
    sequence: int  # 대화 내 메시지 순서
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 관계 설정
    conversation: Conversation = Relationship(back_populates="messages")


class ConversationMessageCreate(ConversationMessageBase):
    request_report: Optional[Dict[str, Any]] = None


class ConversationMessageRead(ConversationMessageBase):
    id: uuid.UUID
    conversation_id: uuid.UUID
    created_at: datetime
    sequence: int


class ConversationReportBase(SQLModel):
    title: str = Field(max_length=200)
    summary: Optional[str] = Field(default=None, max_length=500)
    content: str = Field(sa_column=Column(Text))
    detected_symptoms: Optional[List[str]] = Field(default=None, sa_column=Column(ARRAY(String)))
    diseases_with_probabilities: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))
    health_suggestions: Optional[List[str]] = Field(default=None, sa_column=Column(ARRAY(String)))
    severity_level: Optional[str] = Field(default="green", description="응급도 수준: red(심한 통증/위급), orange(중간 통증/불편), green(통증 없음/양호)")


class ConversationReport(ConversationReportBase, table=True):
    __tablename__ = "conversation_reports"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    conversation_id: uuid.UUID = Field(foreign_key="conversations.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 관계 설정
    conversation: "Conversation" = Relationship(back_populates="reports")


class ConversationReportCreate(ConversationReportBase):
    pass


class ConversationReportRead(ConversationReportBase):
    id: uuid.UUID
    conversation_id: uuid.UUID
    created_at: datetime


class DiseaseBase(SQLModel):
    name: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))


class Disease(DiseaseBase, table=True):
    __tablename__ = "diseases"
    
    id: int = Field(default=None, primary_key=True, index=True)


class DiseaseCreate(DiseaseBase):
    pass


class DiseaseRead(DiseaseBase):
    id: int


# 대화 응답 통합 모델
class ConversationWithMessage(ConversationRead):
    conversation_message: Optional[ConversationMessageRead] = None
    generated_report: Optional[ConversationReportRead] = None


# 메시지 응답 통합 모델
class MessageWithResponse(BaseModel):
    user_message: ConversationMessageRead
    conversation_message: ConversationMessageRead
    generated_report: Optional[ConversationReportRead] = None
