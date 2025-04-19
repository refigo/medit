from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
import uuid

from app.database import get_session, create_db_and_tables
from app.models import (
    User, UserCreate, UserRead,
    FamilyMember, FamilyMemberCreate, FamilyMemberRead,
    UserContact, UserContactCreate, UserContactRead,
    ContactUserInfo
)
from app.config import settings

app = FastAPI(title="Medit API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, you should replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    # 애플리케이션 시작 시 데이터베이스 테이블 자동 생성
    create_db_and_tables()
    print("Database tables created successfully")


@app.get("/")
def read_root():
    return {"message": "Welcome to Medit API"}


# User endpoints
@app.post("/users/", response_model=UserRead)
def create_user(user: UserCreate, session: Session = Depends(get_session)):
    db_user = User(
        login_id=user.login_id,
        nickname=user.nickname,
        age_range=user.age_range,
        gender=user.gender,
        usual_illness=user.usual_illness,
        hashed_password=user.password  # 일단 평문 그대로 저장 (보안상 좋지 않음)
    )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


@app.get("/users/", response_model=list[UserRead])
def read_users(
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100
):
    users = session.exec(select(User).offset(skip).limit(limit)).all()
    return users


@app.get("/users/{login_id}", response_model=UserRead)
def read_user(login_id: str, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.login_id == login_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/users/uuid/{user_id}", response_model=UserRead)
def read_user_by_uuid(user_id: uuid.UUID, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# Family Member endpoints
@app.post("/users/{login_id}/family-members/", response_model=FamilyMemberRead)
def create_family_member(
    login_id: str,
    family_member: FamilyMemberCreate,
    session: Session = Depends(get_session)
):
    # 사용자 존재 여부 확인
    user = session.exec(select(User).where(User.login_id == login_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 가족 구성원 생성
    db_family_member = FamilyMember(
        **family_member.dict(),
        user_id=user.id  # user_id는 내부 UUID 식별자를 사용
    )
    session.add(db_family_member)
    session.commit()
    session.refresh(db_family_member)
    return db_family_member


@app.get("/users/{login_id}/family-members/", response_model=list[FamilyMemberRead])
def read_family_members(
    login_id: str,
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100
):
    # 사용자 존재 여부 확인
    user = session.exec(select(User).where(User.login_id == login_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 가족 구성원 조회
    family_members = session.exec(
        select(FamilyMember)
        .where(FamilyMember.user_id == user.id)  # user_id는 내부 UUID 식별자를 사용
        .offset(skip)
        .limit(limit)
    ).all()
    return family_members


@app.get("/family-members/{family_member_id}", response_model=FamilyMemberRead)
def read_family_member(
    family_member_id: uuid.UUID,
    session: Session = Depends(get_session)
):
    family_member = session.get(FamilyMember, family_member_id)
    if not family_member:
        raise HTTPException(status_code=404, detail="Family member not found")
    return family_member


# User Contact endpoints
@app.post("/users/{login_id}/contacts/", response_model=UserContactRead)
def create_user_contact(
    login_id: str,
    contact: UserContactCreate,
    session: Session = Depends(get_session)
):
    print(f"user_id: {login_id}")
    # 사용자 존재 여부 확인
    user = session.exec(select(User).where(User.login_id == login_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 연락처 사용자 존재 여부 확인 - login_id로 조회
    contact_user = session.exec(select(User).where(User.login_id == contact.contact_login_id)).first()
    if not contact_user:
        raise HTTPException(status_code=404, detail="Contact user not found")
    
    # 연락처 생성
    db_contact = UserContact(
        alias=contact.alias,
        user_id=user.id,
        contact_user_id=contact_user.id  # 조회한 사용자의 UUID를 사용
    )
    session.add(db_contact)
    session.commit()
    session.refresh(db_contact)
    return db_contact


@app.get("/users/{login_id}/contacts/", response_model=list[UserContactRead])
def read_user_contacts(
    login_id: str,
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100
):
    # 사용자 존재 여부 확인
    user = session.exec(select(User).where(User.login_id == login_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 연락처 조회
    contacts = session.exec(
        select(UserContact)
        .where(UserContact.user_id == user.id)  # user_id는 내부 UUID 식별자를 사용
        .offset(skip)
        .limit(limit)
    ).all()
    
    # 연락처 사용자 정보 추가
    result = []
    for contact in contacts:
        # 연락처 사용자 정보 조회
        contact_user = session.get(User, contact.contact_user_id)
        
        # UserContactRead 모델에 맞게 데이터 구성
        contact_data = UserContactRead(
            id=contact.id,
            user_id=contact.user_id,
            contact_user_id=contact.contact_user_id,
            alias=contact.alias,
            created_at=contact.created_at,
            contact_user=ContactUserInfo(
                id=contact_user.id,
                login_id=contact_user.login_id,
                nickname=contact_user.nickname,
                age_range=contact_user.age_range,
                gender=contact_user.gender
            ) if contact_user else None
        )
        result.append(contact_data)
    
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
