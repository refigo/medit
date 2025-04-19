from fastapi import FastAPI, Depends, HTTPException, APIRouter, status, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from sqlalchemy import desc
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.database import get_session, create_db_and_tables
from app.models import (
    User, UserCreate, UserRead, UserUpdate,
    FamilyMember, FamilyMemberCreate, FamilyMemberRead,
    UserContact, UserContactCreate, UserContactRead, ContactUserInfo,
    Conversation, ConversationCreate, ConversationRead,
    ConversationMessage, ConversationMessageCreate, ConversationMessageRead,
    ConversationReport, ConversationReportCreate, ConversationReportRead,
    Disease, DiseaseCreate, DiseaseRead,
    ConversationWithMessage, MessageWithResponse
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


@app.patch("/users/{login_id}", response_model=UserRead, tags=["Users"], summary="사용자 정보 업데이트")
def update_user(
    login_id: str = Path(..., description="업데이트할 사용자의 로그인 아이디"),
    user_update: UserUpdate = ...,
    session: Session = Depends(get_session)
):
    """
    사용자 정보를 부분적으로 업데이트합니다.
    
    - **login_id**: 업데이트할 사용자의 로그인 아이디
    - **nickname**: 사용자 별명 (변경하지 않을 경우 제외)
    - **age_range**: 연령대 (변경하지 않을 경우 제외)
    - **gender**: 성별 (변경하지 않을 경우 제외)
    - **usual_illness**: 평소 앓는 질환 목록 (변경하지 않을 경우 제외)
    """
    db_user = session.exec(select(User).where(User.login_id == login_id)).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 변경할 정보가 있는 경우에만 업데이트
    user_data = user_update.dict(exclude_unset=True)
    for key, value in user_data.items():
        setattr(db_user, key, value)
    
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


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
@app.post("/users/{login_id}/conversations/", response_model=ConversationWithMessage, tags=["Conversations"], summary="대화 생성")
def create_conversation(
    login_id: str = Path(..., description="사용자의 로그인 아이디"),
    conversation: ConversationCreate = ...,
    session: Session = Depends(get_session)
):
    """
    새로운 대화를 생성합니다.
    
    - **login_id**: 사용자의 로그인 아이디
    - **title**: 대화 제목 (선택 사항, 없으면 자동 생성될 수 있음)
    - **message_content**: 첫 메시지 내용 (선택 사항, 없으면 AI가 먼저 인사)
    
    반환값은 생성된 대화와 시작 메시지(들)를 포함합니다.
    """
    # 사용자 존재 여부 확인
    user = session.exec(select(User).where(User.login_id == login_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 대화 생성 (message_content는 Conversation 모델에 없으므로 전달하지 않음)
    conversation_data = conversation.dict(exclude={"message_content"})
    db_conversation = Conversation(
        **conversation_data,
        user_id=user.id
    )
    session.add(db_conversation)
    session.commit()
    session.refresh(db_conversation)
    
    # 결과 객체 준비
    result = ConversationWithMessage.from_orm(db_conversation)
    result.conversation_message = None
    
    # 사용자가 메시지를 보낸 경우
    if conversation.message_content:
        # 사용자 메시지 생성 (첫 번째 메시지)
        db_message = ConversationMessage(
            conversation_id=db_conversation.id,
            sender="user",
            content=conversation.message_content,
            sequence=1  # 첫 번째 메시지는 항상 1
        )
        session.add(db_message)
        session.commit()
        session.refresh(db_message)
        
        # AI 응답 메시지 생성
        response_text = generate_ai_response(conversation.message_content)
        ai_message = ConversationMessage(
            conversation_id=db_conversation.id,
            sender="ai assistant",
            content=response_text,
            sequence=2  # 두 번째 메시지 (AI 응답)
        )
        session.add(ai_message)
        session.commit()
        session.refresh(ai_message)
        
        # 대화 제목이 없는 경우, 첫 메시지 기반으로 제목 자동 생성
        if not db_conversation.title:
            # 메시지 길이에 따라 일부만 사용하거나 전체 사용
            title_base = conversation.message_content
            if len(title_base) > 30:
                title_base = title_base[:27] + "..."
            
            db_conversation.title = title_base
            session.add(db_conversation)
            session.commit()
            session.refresh(db_conversation)
        
        # 결과에 메시지 추가
        result.title = db_conversation.title
        result.conversation_message = ConversationMessageRead.from_orm(ai_message)
    
    # 사용자가 메시지를 보내지 않은 경우, AI가 먼저 인사
    else:
        # 사용자 정보를 기반으로 맞춤형 인사말 생성
        greeting_text = generate_ai_greeting(user)
        
        ai_message = ConversationMessage(
            conversation_id=db_conversation.id,
            sender="ai assistant",
            content=greeting_text,
            sequence=1  # 첫 번째 메시지 (AI 인사)
        )
        session.add(ai_message)
        session.commit()
        session.refresh(ai_message)
        
        # 대화 제목이 없는 경우 기본 제목 설정
        if not db_conversation.title:
            db_conversation.title = "메디트 상담"
            session.add(db_conversation)
            session.commit()
            session.refresh(db_conversation)
        
        # 결과에 메시지 추가
        result.title = db_conversation.title
        result.conversation_message = ConversationMessageRead.from_orm(ai_message)
    
    return result


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


@app.post("/users/{login_id}/conversations/{conversation_id}/messages/", response_model=MessageWithResponse, tags=["Conversation Messages"], summary="대화 메시지 추가")
def create_conversation_message(
    login_id: str = Path(..., description="사용자의 로그인 아이디"),
    conversation_id: uuid.UUID = Path(..., description="대화 ID"),
    message: ConversationMessageCreate = ...,
    session: Session = Depends(get_session)
):
    """
    대화에 새 메시지를 추가합니다. 사용자가 메시지를 보내면 자동으로 AI 응답도 생성됩니다.
    
    - **login_id**: 사용자의 로그인 아이디
    - **conversation_id**: 대화의 ID
    - **sender**: 메시지 발신자 ('user' 또는 'ai assistant')
    - **content**: 메시지 내용
    
    반환값은 사용자가 보낸 메시지와 AI의 응답 메시지를 포함한 단일 객체입니다.
    """
    # 사용자 확인
    user = session.exec(select(User).where(User.login_id == login_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 대화 확인
    conversation = session.exec(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id
        )
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # 마지막 메시지 시퀀스 확인
    last_message = session.exec(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(desc(ConversationMessage.sequence))
        .limit(1)
    ).first()
    
    next_sequence = 1
    if last_message:
        next_sequence = last_message.sequence + 1
    
    # 사용자 메시지 저장
    user_message = ConversationMessage(
        conversation_id=conversation_id,
        sender="user",
        content=message.content,
        sequence=next_sequence
    )
    session.add(user_message)
    session.commit()
    session.refresh(user_message)
    
    # AI 응답 생성
    ai_response_text = generate_ai_response(message.content)
    
    # 대화 분석 및 자동 리포트 생성 조건 확인
    generate_report = (next_sequence + 1 == 7)  # 3번 정도의 핑퐁 후 (ai: 1,3,5, user: 2,4,6)
    
    # 리포트 생성이 필요한 경우 응답 내용 수정
    if generate_report:
        # 대화에서 증상 분석
        analysis_data = analyze_conversation_for_diseases(conversation_id, session)
        
        # 리포트 생성
        report_content = generate_conversation_report(conversation_id, analysis_data, session)
        
        # 리포트 저장 (증상, 질환-확률 통합 정보, 제안 정보 포함)
        report = ConversationReport(
            conversation_id=conversation_id,
            title="자동 생성된 건강 분석 리포트",
            summary="AI가 분석한 건강 상태 요약",
            content=report_content,
            detected_symptoms=analysis_data["symptoms"],
            diseases_with_probabilities=analysis_data["diseases_with_probabilities"],
            health_suggestions=analysis_data["suggestions"]
        )
        session.add(report)
        session.commit()
        session.refresh(report)
        
        # AI 응답을 리포트 관련 내용으로 변경
        ai_response_text = f"""대화 내용을 분석한 결과, 다음과 같은 건강 상태가 감지되었습니다:

감지된 증상: {', '.join(analysis_data["symptoms"]) if analysis_data["symptoms"] else "특별한 증상이 감지되지 않음"}

가능성 있는 질환:
{", ".join([f'{disease["name"]} ({disease["probability"]}%)' for disease in analysis_data["diseases_with_probabilities"][:3]])}

자세한 분석 내용을 담은 건강 리포트를 생성했습니다. 리포트에서 더 상세한 정보와 건강 관리 조언을 확인하실 수 있습니다.

이 분석은 대화 내용을 기반으로 한 참고 사항이며, 정확한 진단을 위해서는 의사와 상담하시기 바랍니다."""
    
    # AI 응답 저장
    ai_message = ConversationMessage(
        conversation_id=conversation_id,
        sender="ai assistant",
        content=ai_response_text,
        sequence=next_sequence + 1
    )
    session.add(ai_message)
    session.commit()
    session.refresh(ai_message)
    
    # 응답 구성
    if generate_report:
        # 리포트 정보를 응답에 포함
        result = MessageWithResponse(
            user_message=ConversationMessageRead.from_orm(user_message),
            conversation_message=ConversationMessageRead.from_orm(ai_message),
            generated_report=ConversationReportRead.from_orm(report)
        )
    else:
        # 일반 응답 구성
        result = MessageWithResponse(
            user_message=ConversationMessageRead.from_orm(user_message),
            conversation_message=ConversationMessageRead.from_orm(ai_message)
        )
    
    return result


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
@app.post("/diseases/", response_model=DiseaseRead, tags=["Diseases"], summary="질병 정보 생성")
def create_disease(
    disease: DiseaseCreate = ...,
    session: Session = Depends(get_session)
):
    """
    질병 정보를 생성합니다.
    
    - **name**: 질병 이름
    - **description**: 질병에 대한 설명
    """
    # 이미 존재하는 질병인지 확인
    existing_disease = session.exec(
        select(Disease).where(Disease.name == disease.name)
    ).first()
    
    if existing_disease:
        return existing_disease
    
    # 새 질병 생성
    db_disease = Disease.from_orm(disease)
    session.add(db_disease)
    session.commit()
    session.refresh(db_disease)
    
    return db_disease


@app.get("/diseases/", response_model=list[DiseaseRead], tags=["Diseases"], summary="질병 정보 목록 조회")
def read_diseases(
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100
):
    """
    질병 정보 목록을 조회합니다.
    
    - **skip**: 건너뛸 항목 수
    - **limit**: 최대 반환할 항목 수
    """
    diseases = session.exec(select(Disease).offset(skip).limit(limit)).all()
    return diseases


@app.get("/diseases/{disease_id}", response_model=DiseaseRead, tags=["Diseases"], summary="질병 정보 상세 조회")
def read_disease(
    disease_id: int = Path(..., description="질병 ID"),
    session: Session = Depends(get_session)
):
    """
    특정 질병 정보를 조회합니다.
    
    - **disease_id**: 질병 ID
    """
    disease = session.get(Disease, disease_id)
    if not disease:
        raise HTTPException(status_code=404, detail="Disease not found")
    
    return disease


@app.get("/users/{login_id}/reports/diseases/", response_model=Dict[str, List[Dict[str, Any]]], tags=["Reports"], summary="사용자의 모든 리포트에서 질환 및 확률 정보 조회")
def read_user_disease_probabilities(
    login_id: str = Path(..., description="사용자의 로그인 아이디"),
    session: Session = Depends(get_session),
    report_id: Optional[uuid.UUID] = Query(None, description="특정 리포트 ID (선택 사항)")
):
    """
    사용자의 건강 리포트에서 감지된 질환과 확률 정보를 조회합니다.
    
    - **login_id**: 사용자의 로그인 아이디
    - **report_id**: 특정 리포트 ID (선택적)
    
    각 질환 정보는 다음 형식으로 제공됩니다:
    ```
    {
        "name": "질환명",
        "probability": 85.5
    }
    ```
    
    특정 리포트 ID가 제공되면 해당 리포트의 질환 목록만 반환하고,
    그렇지 않으면 모든 리포트의 질환 정보를 리포트 ID를 키로 하는 사전 형태로 반환합니다.
    """
    # 사용자 확인
    user = session.exec(select(User).where(User.login_id == login_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 사용자의 대화 ID 목록 조회
    conversation_ids = [conv.id for conv in session.exec(
        select(Conversation).where(Conversation.user_id == user.id)
    ).all()]
    
    if not conversation_ids:
        return {}
    
    # 기본 쿼리: 사용자의 모든 대화에 속한 리포트 조회
    query = select(ConversationReport).where(
        ConversationReport.conversation_id.in_(conversation_ids)
    )
    
    # 특정 리포트만 필터링
    if report_id:
        query = query.where(ConversationReport.id == report_id)
    
    reports = session.exec(query).all()
    
    # 결과 구성
    result = {}
    for report in reports:
        if report.diseases_with_probabilities:  # None이 아닐 경우만 추가
            result[str(report.id)] = report.diseases_with_probabilities
    
    # 특정 리포트만 요청한 경우 해당 리포트의 질환 정보만 반환
    if report_id and str(report_id) in result:
        return result[str(report_id)]
    
    return result


@app.get("/users/{login_id}/reports/", response_model=list[ConversationReportRead], tags=["Reports"], summary="사용자 리포트 목록 조회")
def read_user_reports(
    login_id: str = Path(..., description="사용자의 로그인 아이디"),
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100
):
    """
    사용자의 건강 분석 리포트 목록을 조회합니다.
    
    - **login_id**: 사용자의 로그인 아이디
    - **skip**: 건너뛸 항목 수
    - **limit**: 최대 반환할 항목 수
    """
    # 사용자 확인
    user = session.exec(select(User).where(User.login_id == login_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 사용자의 대화 ID 목록 조회
    conversation_ids = [conv.id for conv in session.exec(
        select(Conversation).where(Conversation.user_id == user.id)
    ).all()]
    
    if not conversation_ids:
        return []
    
    # 사용자의 모든 대화에 속한 리포트 조회
    reports = session.exec(
        select(ConversationReport)
        .where(ConversationReport.conversation_id.in_(conversation_ids))
        .order_by(desc(ConversationReport.created_at))
        .offset(skip)
        .limit(limit)
    ).all()
    
    return reports


# AI 응답 생성 함수 (임시)
def generate_ai_response(user_message: str) -> str:
    """
    사용자 메시지에 대한 AI 응답을 생성합니다.
    현재는 간단한 규칙 기반 응답을 생성하지만, 추후 생성형 AI로 대체될 예정입니다.
    
    Args:
        user_message: 사용자가 보낸 메시지 내용
        
    Returns:
        AI 응답 메시지
    """
    # 사용자 메시지에 특정 키워드가 포함되어 있는지 확인하여 간단한 응답 생성
    user_message_lower = user_message.lower()
    
    if "안녕" in user_message_lower or "hello" in user_message_lower:
        return "안녕하세요! 메디트 AI 어시스턴트입니다. 어떻게 도와드릴까요?"
    
    elif "머리" in user_message_lower and ("아프" in user_message_lower or "두통" in user_message_lower):
        return "두통을 경험하고 계시는군요. 두통의 강도와 지속 시간, 다른 증상도 있는지 알려주시면 더 정확한 도움을 드릴 수 있습니다."
    
    elif "배" in user_message_lower and ("아프" in user_message_lower or "통증" in user_message_lower):
        return "복통이 있으신가요? 어느 부위에 통증이 있고, 언제부터 시작되었는지, 식사와 관련이 있는지 알려주시면 도움이 될 것 같습니다."
    
    elif "감기" in user_message_lower or "콧물" in user_message_lower or "기침" in user_message_lower:
        return "감기 증상이 있으신 것 같네요. 체온, 기침, 콧물 등의 구체적인 증상과 지속 기간을 알려주시면 더 자세한 정보를 제공해 드릴 수 있습니다."
    
    elif "처방" in user_message_lower or "약" in user_message_lower:
        return "특정 약물에 대해 문의하시는 것 같습니다. 다만, 온라인에서 처방을 제공할 수 없으니 가까운 의료기관에 방문하시는 것을 권장합니다."
    
    elif "고마워" in user_message_lower or "감사" in user_message_lower:
        return "도움이 되어 기쁩니다. 다른 질문이 있으시면 언제든지 물어보세요!"
    
    elif "질병" in user_message_lower or "병" in user_message_lower:
        return "특정 질병에 대해 궁금하신가요? 어떤 질병에 대해 알고 싶으신지, 더 구체적으로 말씀해 주시면 관련 정보를 제공해 드리겠습니다."
    
    else:
        return "말씀하신 내용에 대해 더 자세히 알려주시겠어요? 건강 상태나 증상에 대해 구체적으로 설명해 주시면 더 정확한 정보를 제공해 드릴 수 있습니다."


# 사용자 정보를 기반으로 인사말 생성
def generate_ai_greeting(user: User) -> str:
    """
    사용자 정보를 기반으로 AI의 첫 인사말을 생성합니다.
    
    Args:
        user: 대화를 시작한 사용자 객체
        
    Returns:
        사용자 맞춤형 인사말
    """
    # 시간대에 따른 인사말
    from datetime import datetime
    current_hour = datetime.utcnow().hour
    
    time_greeting = "안녕하세요"
    if 5 <= current_hour < 12:
        time_greeting = "좋은 아침이에요"
    elif 12 <= current_hour < 18:
        time_greeting = "안녕하세요"
    elif 18 <= current_hour < 22:
        time_greeting = "좋은 저녁이에요"
    else:
        time_greeting = "늦은 시간에도 찾아주셨네요"
    
    # 사용자 이름을 포함한 인사말
    name_greeting = f"{user.nickname}님, {time_greeting}! 메디트 AI 어시스턴트입니다."
    
    # 기본 인사말
    base_greeting = "건강 관련 궁금한 점이 있으신가요? 어떻게 도와드릴까요?"
    
    # 사용자의 평소 질환이 있는 경우, 그에 맞는 인사말 추가
    health_greeting = ""
    if user.usual_illness and len(user.usual_illness) > 0:
        health_greeting = f"\n평소 {', '.join(user.usual_illness)}으로 불편함을 겪고 계시는 것으로 알고 있습니다. 오늘은 어떠신가요?"
    
    # 최종 인사말 조합
    return f"{name_greeting}{health_greeting}\n\n{base_greeting}"


# 질병 및 증상 관련 샘플 데이터
# 실제 프로덕션에서는 외부 의료 API/데이터베이스와 연동이 필요할 수 있습니다
common_symptoms = [
    "두통", "복통", "열", "기침", "어지러움", "피로", "메스꺼움", "설사", 
    "근육통", "발열", "인후통", "콧물", "발진", "관절통"
]

# 증상 키워드와 연관 질환 매핑 (샘플 데이터)
symptom_disease_map = {
    "두통": ["편두통", "긴장성 두통", "군발성 두통"],
    "복통": ["위염", "장염", "과민성 대장 증후군"],
    "열": ["감기", "독감", "코로나19"],
    "기침": ["감기", "기관지염", "코로나19"],
    "어지러움": ["빈혈", "현기증", "저혈압"],
    "피로": ["만성피로증후군", "빈혈", "갑상선 기능 저하증"],
    "메스꺼움": ["위염", "멀미", "편두통"],
    "설사": ["장염", "과민성 대장 증후군", "식중독"],
    "근육통": ["근육염", "독감", "섬유근육통"],
    "발열": ["감기", "독감", "폐렴"],
    "인후통": ["인두염", "편도염", "후두염"],
    "콧물": ["비염", "감기", "알레르기"],
    "발진": ["알레르기", "습진", "수두"],
    "관절통": ["관절염", "류마티스 관절염", "통풍"]
}

# 질환별 증상 매핑 (역방향 매핑 생성)
disease_symptoms = {}
for symptom, diseases in symptom_disease_map.items():
    for disease in diseases:
        if disease not in disease_symptoms:
            disease_symptoms[disease] = []
        disease_symptoms[disease].append(symptom)

# 질환별 건강 제안 (샘플 데이터)
disease_suggestions = {
    "편두통": ["충분한 수면 취하기", "스트레스 관리하기", "정기적인 운동하기"],
    "긴장성 두통": ["목과 어깨 스트레칭", "스트레스 관리", "따뜻한 목욕"],
    "위염": ["자극적인 음식 피하기", "작은 양 자주 먹기", "금주하기"],
    "장염": ["충분한 수분 섭취", "소화가 쉬운 음식 먹기", "휴식 취하기"],
    "감기": ["충분한 휴식", "수분 섭취", "비타민 C 섭취"],
    "독감": ["집에서 휴식", "해열제 복용 고려", "충분한 수분 섭취"],
    "빈혈": ["철분이 풍부한 음식 섭취", "비타민 C와 함께 철분 섭취", "과로 피하기"],
    "저혈압": ["천천히 일어나기", "작은 양 자주 먹기", "충분한 수분 섭취"],
    "알레르기": ["알레르기 유발 물질 피하기", "항히스타민제 고려", "의사와 상담"],
}

# 일반적인 건강 제안 (기본값)
general_suggestions = [
    "충분한 휴식과 수면을 취하세요",
    "물을 충분히 마시세요",
    "균형 잡힌 식단을 유지하세요",
    "규칙적인 운동을 하세요",
    "스트레스를 관리하세요"
]


# 대화 내용을 분석하여 질병 가능성 판단
def analyze_conversation_for_diseases(conversation_id: uuid.UUID, session: Session) -> dict:
    """대화 내용을 분석하여 가능성 있는 질병을 탐지합니다."""
    # 대화 메시지 조회
    messages = session.exec(
        select(ConversationMessage).where(
            ConversationMessage.conversation_id == conversation_id
        ).order_by(ConversationMessage.created_at)
    ).all()
    
    if not messages:
        return {
            "symptoms": [],
            "diseases_with_probabilities": [],
            "suggestions": general_suggestions
        }
    
    # 대화 내용 분석을 위한 텍스트 추출
    conversation_text = ""
    for message in messages:
        if message.sender == "user":
            conversation_text += f"{message.content}\n"
    
    # 증상 감지 (대화에서 언급된 증상 추출)
    detected_symptoms = set()
    for symptom in common_symptoms:
        if symptom.lower() in conversation_text.lower():
            detected_symptoms.add(symptom)
    
    if not detected_symptoms:
        return {
            "symptoms": [],
            "diseases_with_probabilities": [],
            "suggestions": general_suggestions
        }
    
    # 증상 기반 질병 가능성 계산
    possible_diseases = set()
    disease_symptom_counts = {}
    
    for symptom in detected_symptoms:
        for disease in symptom_disease_map.get(symptom, []):
            possible_diseases.add(disease)
            if disease not in disease_symptom_counts:
                disease_symptom_counts[disease] = 0
            disease_symptom_counts[disease] += 1
    
    # 질병 확률 계산 (단순 알고리즘)
    disease_probabilities = {}
    for disease in possible_diseases:
        matched_symptom_count = disease_symptom_counts.get(disease, 0)
        total_symptom_count = len(symptom_disease_map.get(disease, []))
        
        if total_symptom_count > 0:
            # 간단한 확률 계산 (매칭된 증상 수 / 질병 관련 전체 증상 수)
            probability = (matched_symptom_count / total_symptom_count) * 100
            # 최소 확률 50%, 최대 95%로 제한
            probability = min(95, max(50, probability))
            disease_probabilities[disease] = round(probability, 1)
    
    # 확률 기반 질병 정렬
    sorted_diseases = sorted(
        possible_diseases, 
        key=lambda x: disease_probabilities.get(x, 0),
        reverse=True
    )
    
    # 건강 관리 조언 생성
    collected_suggestions = set()
    for disease in sorted_diseases[:3]:  # 상위 3개 질환에 대한 제안만 수집
        if disease in disease_suggestions:
            collected_suggestions.update(disease_suggestions[disease])
    
    # 제안이 부족하면 일반적인 제안 추가
    if len(collected_suggestions) < 5:
        collected_suggestions.update(general_suggestions)
    
    # 질환과 확률 정보를 하나의 리스트로 통합하고 Disease 테이블과 연동
    diseases_with_probabilities = []
    for disease in sorted_diseases:
        probability = disease_probabilities.get(disease, 50.0)
        
        # 데이터베이스에서 질병 검색 또는 생성
        db_disease = session.exec(
            select(Disease).where(Disease.name == disease)
        ).first()
        
        if not db_disease:
            # 새 질병 생성
            db_disease = Disease(
                name=disease,
                description=f"{disease}는 일반적으로 {', '.join(symptom_disease_map.get(disease, [])[:3])} 등의 증상과 연관됩니다."
            )
            session.add(db_disease)
            session.commit()
            session.refresh(db_disease)
        
        # 질병 ID를 포함하여 결과 저장
        diseases_with_probabilities.append({
            "id": db_disease.id,
            "name": disease,
            "probability": probability
        })
    
    return {
        "symptoms": list(detected_symptoms),
        "diseases_with_probabilities": diseases_with_probabilities,
        "suggestions": list(collected_suggestions)[:5]  # 최대 5개의 제안만 반환
    }


# 대화 내용을 분석하여 리포트 내용 생성
def generate_conversation_report(conversation_id: uuid.UUID, analysis_data: dict, session: Session) -> str:
    """대화 내용을 분석하여 건강 분석 리포트를 생성합니다."""
    # 대화에서 사용자 정보 가져오기
    conversation = session.get(Conversation, conversation_id)
    user = session.get(User, conversation.user_id)
    
    # 사용자 기본 정보 수집
    user_info = f"사용자: {user.nickname if user.nickname else '이름 없음'}\n"
    user_info += f"연령대: {user.age_range if user.age_range else '정보 없음'}\n"
    user_info += f"성별: {user.gender if user.gender else '정보 없음'}\n"
    
    # 평소 앓는 질환 정보
    existing_illness = "없음"
    if user.usual_illness and len(user.usual_illness) > 0:
        existing_illness = ", ".join(user.usual_illness)
    
    # 감지된 증상 정리
    symptom_section = "## 감지된 증상\n\n"
    for symptom in analysis_data["symptoms"]:
        symptom_section += f"- {symptom}\n"
    
    # 증상 분석 및 추천 사항
    disease_analysis = "## 분석된 가능성 있는 질환\n\n"
    for disease in analysis_data["diseases_with_probabilities"]:
        probability = disease["probability"]
        disease_analysis += f"- {disease['name']} ({probability}%)\n"
    
    # 건강 관리 조언
    health_advice = "## 건강 관리 조언\n\n"
    for i, suggestion in enumerate(analysis_data["suggestions"], 1):
        health_advice += f"{i}. {suggestion}\n"
    
    # 최종 리포트 작성
    report = f"""# 건강 분석 리포트

## 사용자 정보
{user_info}
평소 앓는 질환: {existing_illness}

## 대화 내용 분석
대화 내용을 바탕으로 분석한 결과입니다.

{symptom_section}

{disease_analysis}

{health_advice}

*참고: 이 리포트는 자동으로 생성된 것으로, 정확한 진단을 위해서는 의사와 상담하시기 바랍니다.*

생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
    
    return report


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
