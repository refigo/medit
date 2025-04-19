from fastapi import FastAPI, Depends, HTTPException, APIRouter, status, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
import uuid
from typing import Optional, List

from app.database import get_session, create_db_and_tables
from app.models import (
    User, UserCreate, UserRead,
    FamilyMember, FamilyMemberCreate, FamilyMemberRead,
    UserContact, UserContactCreate, UserContactRead,
    ContactUserInfo,
    Conversation, ConversationCreate, ConversationRead,
    ConversationMessage, ConversationMessageCreate, ConversationMessageRead,
    ConversationReport, ConversationReportCreate, ConversationReportRead,
    Disease, DiseaseCreate, DiseaseRead,
    UserDisease, UserDiseaseCreate, UserDiseaseRead
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


# Conversation endpoints
@app.post("/users/{login_id}/conversations/", response_model=ConversationRead, tags=["Conversations"], summary="대화 생성")
def create_conversation(
    login_id: str = Path(..., description="사용자의 로그인 아이디"),
    conversation: ConversationCreate = ...,
    session: Session = Depends(get_session)
):
    """
    새로운 대화를 생성합니다.
    
    - **login_id**: 사용자의 로그인 아이디
    - **title**: 대화 제목 (선택 사항, 없으면 자동 생성될 수 있음)
    """
    # 사용자 존재 여부 확인
    user = session.exec(select(User).where(User.login_id == login_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 대화 생성
    db_conversation = Conversation(
        **conversation.dict(),
        user_id=user.id
    )
    session.add(db_conversation)
    session.commit()
    session.refresh(db_conversation)
    return db_conversation


@app.get("/users/{login_id}/conversations/", response_model=list[ConversationRead], tags=["Conversations"], summary="대화 목록 조회")
def read_conversations(
    login_id: str = Path(..., description="사용자의 로그인 아이디"),
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100
):
    """
    사용자의 대화 목록을 조회합니다.
    
    - **login_id**: 사용자의 로그인 아이디
    - **skip**: 건너뛸 대화 수
    - **limit**: 최대 반환할 대화 수
    """
    # 사용자 존재 여부 확인
    user = session.exec(select(User).where(User.login_id == login_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 대화 목록 조회
    conversations = session.exec(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .offset(skip)
        .limit(limit)
        .order_by(Conversation.started_at.desc())
    ).all()
    return conversations


@app.get("/conversations/{conversation_id}", response_model=ConversationRead, tags=["Conversations"], summary="대화 조회")
def read_conversation(
    conversation_id: uuid.UUID = Path(..., description="조회할 대화의 ID"),
    session: Session = Depends(get_session)
):
    """
    특정 대화를 조회합니다.
    
    - **conversation_id**: 조회할 대화의 ID
    """
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.post("/conversations/{conversation_id}/messages/", response_model=ConversationMessageRead, tags=["Conversation Messages"], summary="대화 메시지 추가")
def create_conversation_message(
    conversation_id: uuid.UUID = Path(..., description="대화의 ID"),
    message: ConversationMessageCreate = ...,
    session: Session = Depends(get_session)
):
    """
    대화에 새 메시지를 추가합니다.
    
    - **conversation_id**: 대화의 ID
    - **sender**: 메시지 발신자 ('user' 또는 'ai assistant')
    - **content**: 메시지 내용
    - **sequence**: 대화 내 메시지 순서
    """
    # 대화 존재 여부 확인
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # 메시지 생성
    db_message = ConversationMessage(
        **message.dict(),
        conversation_id=conversation_id
    )
    session.add(db_message)
    session.commit()
    session.refresh(db_message)
    return db_message


@app.get("/conversations/{conversation_id}/messages/", response_model=list[ConversationMessageRead], tags=["Conversation Messages"], summary="대화 메시지 목록 조회")
def read_conversation_messages(
    conversation_id: uuid.UUID = Path(..., description="대화의 ID"),
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100
):
    """
    대화의 메시지 목록을 조회합니다.
    
    - **conversation_id**: 대화의 ID
    - **skip**: 건너뛸 메시지 수
    - **limit**: 최대 반환할 메시지 수
    """
    # 대화 존재 여부 확인
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # 메시지 목록 조회
    messages = session.exec(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.sequence)
        .offset(skip)
        .limit(limit)
    ).all()
    return messages


@app.post("/conversations/{conversation_id}/reports/", response_model=ConversationReportRead, tags=["Conversation Reports"], summary="대화 보고서 생성")
def create_conversation_report(
    conversation_id: uuid.UUID = Path(..., description="대화의 ID"),
    report: ConversationReportCreate = ...,
    session: Session = Depends(get_session)
):
    """
    대화에 대한 보고서를 생성합니다.
    
    - **conversation_id**: 대화의 ID
    - **summary**: 보고서 요약 (선택 사항)
    - **content**: 보고서 내용
    """
    # 대화 존재 여부 확인
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # 보고서 생성
    db_report = ConversationReport(
        **report.dict(),
        conversation_id=conversation_id
    )
    session.add(db_report)
    session.commit()
    session.refresh(db_report)
    return db_report


@app.get("/conversations/{conversation_id}/reports/", response_model=list[ConversationReportRead], tags=["Conversation Reports"], summary="대화 보고서 목록 조회")
def read_conversation_reports(
    conversation_id: uuid.UUID = Path(..., description="대화의 ID"),
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100
):
    """
    대화의 보고서 목록을 조회합니다.
    
    - **conversation_id**: 대화의 ID
    - **skip**: 건너뛸 보고서 수
    - **limit**: 최대 반환할 보고서 수
    """
    # 대화 존재 여부 확인
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # 보고서 목록 조회
    reports = session.exec(
        select(ConversationReport)
        .where(ConversationReport.conversation_id == conversation_id)
        .order_by(ConversationReport.created_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return reports


# Disease endpoints
@app.post("/diseases/", response_model=DiseaseRead, tags=["Diseases"], summary="질병 등록")
def create_disease(
    disease: DiseaseCreate = ...,
    session: Session = Depends(get_session)
):
    """
    새로운 질병을 등록합니다.
    
    - **name**: 질병 이름
    """
    # 이미 존재하는 질병인지 확인
    existing_disease = session.exec(select(Disease).where(Disease.name == disease.name)).first()
    if existing_disease:
        return existing_disease
    
    # 새 질병 생성
    db_disease = Disease(**disease.dict())
    session.add(db_disease)
    session.commit()
    session.refresh(db_disease)
    return db_disease


@app.get("/diseases/", response_model=list[DiseaseRead], tags=["Diseases"], summary="질병 목록 조회")
def read_diseases(
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100
):
    """
    질병 목록을 조회합니다.
    
    - **skip**: 건너뛸 질병 수
    - **limit**: 최대 반환할 질병 수
    """
    diseases = session.exec(select(Disease).offset(skip).limit(limit)).all()
    return diseases


@app.get("/diseases/{disease_id}", response_model=DiseaseRead, tags=["Diseases"], summary="질병 조회")
def read_disease(
    disease_id: int = Path(..., description="질병 ID"),
    session: Session = Depends(get_session)
):
    """
    특정 질병을 조회합니다.
    
    - **disease_id**: 질병 ID
    """
    disease = session.get(Disease, disease_id)
    if not disease:
        raise HTTPException(status_code=404, detail="Disease not found")
    return disease


# User Disease endpoints
@app.post("/users/{login_id}/diseases/", response_model=UserDiseaseRead, tags=["User Diseases"], summary="사용자 질병 정보 추가")
def create_user_disease(
    login_id: str = Path(..., description="사용자의 로그인 아이디"),
    user_disease: UserDiseaseCreate = ...,
    conversation_id: Optional[uuid.UUID] = Query(None, description="관련 대화 ID (선택 사항)"),
    session: Session = Depends(get_session)
):
    """
    사용자와 관련된 질병 정보를 추가합니다.
    
    - **login_id**: 사용자의 로그인 아이디
    - **disease_id**: 질병 ID
    - **probability**: 질병 가능성 (AI가 추론, 선택 사항)
    - **summary**: AI 요약 (선택 사항)
    - **note**: 추가 정보 (선택 사항)
    - **conversation_id**: 관련 대화 ID (선택 사항)
    """
    # 사용자 존재 여부 확인
    user = session.exec(select(User).where(User.login_id == login_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 질병 존재 여부 확인
    disease = session.get(Disease, user_disease.disease_id)
    if not disease:
        raise HTTPException(status_code=404, detail="Disease not found")
    
    # 대화 존재 여부 확인 (제공된 경우)
    if conversation_id:
        conversation = session.get(Conversation, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    
    # 사용자 질병 정보 생성
    db_user_disease = UserDisease(
        **user_disease.dict(),
        user_id=user.id,
        conversation_id=conversation_id
    )
    session.add(db_user_disease)
    session.commit()
    session.refresh(db_user_disease)
    
    # 결과에 Disease 정보 포함
    result = UserDiseaseRead.from_orm(db_user_disease)
    result.disease = DiseaseRead.from_orm(disease)
    
    return result


@app.get("/users/{login_id}/diseases/", response_model=list[UserDiseaseRead], tags=["User Diseases"], summary="사용자 질병 정보 조회")
def read_user_diseases(
    login_id: str = Path(..., description="사용자의 로그인 아이디"),
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100,
    conversation_id: Optional[uuid.UUID] = Query(None, description="특정 대화의 질병 정보만 조회 (선택 사항)")
):
    """
    사용자와 관련된 질병 정보를 조회합니다.
    
    - **login_id**: 사용자의 로그인 아이디
    - **skip**: 건너뛸 항목 수
    - **limit**: 최대 반환할 항목 수
    - **conversation_id**: 특정 대화의 질병 정보만 조회 (선택 사항)
    """
    # 사용자 존재 여부 확인
    user = session.exec(select(User).where(User.login_id == login_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 기본 쿼리 구성
    query = select(UserDisease).where(UserDisease.user_id == user.id)
    
    # 대화 ID로 필터링 (제공된 경우)
    if conversation_id:
        query = query.where(UserDisease.conversation_id == conversation_id)
    
    # 쿼리 실행
    user_diseases = session.exec(
        query
        .order_by(UserDisease.created_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    
    # 결과에 Disease 정보 포함
    results = []
    for ud in user_diseases:
        disease = session.get(Disease, ud.disease_id)
        result = UserDiseaseRead.from_orm(ud)
        result.disease = DiseaseRead.from_orm(disease)
        results.append(result)
    
    return results


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
