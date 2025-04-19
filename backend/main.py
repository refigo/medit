from fastapi import FastAPI, Depends, HTTPException, APIRouter, status, Query, Path
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


@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to Medit API"}


# User endpoints
@app.post("/users/", response_model=UserRead, tags=["Users"], summary="사용자 생성")
def create_user(user: UserCreate, session: Session = Depends(get_session)):
    """
    새로운 사용자를 생성합니다.
    
    - **login_id**: 로그인에 사용할 고유 아이디
    - **nickname**: 사용자 별명
    - **password**: 비밀번호 (현재는 평문 저장)
    - **age_range**: 연령대 (예: "20-29")
    - **gender**: 성별
    - **usual_illness**: 평소 앓는 질환 목록
    """
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


@app.get("/users/", response_model=list[UserRead], tags=["Users"], summary="모든 사용자 조회")
def read_users(
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100
):
    """
    모든 사용자 목록을 조회합니다.
    
    - **skip**: 건너뛸 사용자 수
    - **limit**: 최대 반환할 사용자 수
    """
    users = session.exec(select(User).offset(skip).limit(limit)).all()
    return users


@app.get("/users/{login_id}", response_model=UserRead, tags=["Users"], summary="로그인 아이디로 사용자 조회")
def read_user_by_login_id(
    login_id: str = Path(..., description="조회할 사용자의 로그인 아이디"),
    session: Session = Depends(get_session)
):
    """
    로그인 아이디로 특정 사용자를 조회합니다.
    
    - **login_id**: 조회할 사용자의 로그인 아이디
    """
    user = session.exec(select(User).where(User.login_id == login_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/users/uuid/{user_id}", response_model=UserRead, tags=["Users"], summary="UUID로 사용자 조회")
def read_user_by_uuid(
    user_id: uuid.UUID = Path(..., description="조회할 사용자의 UUID"),
    session: Session = Depends(get_session)
):
    """
    UUID로 특정 사용자를 조회합니다.
    
    - **user_id**: 조회할 사용자의 UUID
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# Family Member endpoints
@app.post("/users/{login_id}/family-members/", response_model=FamilyMemberRead, tags=["Family Members"], summary="가족 구성원 추가")
def create_family_member(
    login_id: str = Path(..., description="사용자의 로그인 아이디"),
    family_member: FamilyMemberCreate = ...,
    session: Session = Depends(get_session)
):
    """
    사용자의 가족 구성원을 추가합니다.
    
    - **login_id**: 사용자의 로그인 아이디
    - **nickname**: 가족 구성원 별명
    - **relation**: 가족 관계 (예: "부모", "형제", "자녀")
    - **age**: 가족 구성원의 나이
    - **usual_illness**: 평소 앓는 질환 목록
    """
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


@app.get("/users/{login_id}/family-members/", response_model=list[FamilyMemberRead], tags=["Family Members"], summary="가족 구성원 목록 조회")
def read_family_members(
    login_id: str = Path(..., description="사용자의 로그인 아이디"),
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100
):
    """
    사용자의 가족 구성원 목록을 조회합니다.
    
    - **login_id**: 사용자의 로그인 아이디
    - **skip**: 건너뛸 가족 구성원 수
    - **limit**: 최대 반환할 가족 구성원 수
    """
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


# User Contact endpoints
@app.post("/users/{login_id}/contacts/", response_model=UserContactRead, tags=["User Contacts"], summary="사용자 연락처 추가")
def create_user_contact(
    login_id: str = Path(..., description="사용자의 로그인 아이디"),
    contact: UserContactCreate = ...,
    session: Session = Depends(get_session)
):
    """
    사용자의 연락처를 추가합니다.
    
    - **login_id**: 사용자의 로그인 아이디
    - **contact_login_id**: 추가할 연락처 사용자의 로그인 아이디
    - **alias_nickname**: 연락처의 별명 (선택 사항)
    - **relation**: 관계 (예: "친구", "동료", "지인" 등) (선택 사항)
    """
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
        alias_nickname=contact.alias_nickname,
        relation=contact.relation,
        user_id=user.id,
        contact_user_id=contact_user.id  # 조회한 사용자의 UUID를 사용
    )
    session.add(db_contact)
    session.commit()
    session.refresh(db_contact)
    return db_contact


@app.get("/users/{login_id}/contacts/", response_model=list[UserContactRead], tags=["User Contacts"], summary="사용자 연락처 목록 조회")
def read_user_contacts(
    login_id: str = Path(..., description="사용자의 로그인 아이디"),
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100
):
    """
    사용자의 연락처 목록을 조회합니다.
    
    - **login_id**: 사용자의 로그인 아이디
    - **skip**: 건너뛸 연락처 수
    - **limit**: 최대 반환할 연락처 수
    
    반환되는 데이터에는 연락처 사용자의 기본 정보(id, login_id, nickname, age_range, gender)도 포함됩니다.
    """
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
            alias_nickname=contact.alias_nickname,
            relation=contact.relation,
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
