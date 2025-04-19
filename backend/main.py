from fastapi import FastAPI, Depends, HTTPException, APIRouter, status, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from sqlalchemy import desc
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio

from app.database import get_session, create_db_and_tables
from app.models import (
    User, UserCreate, UserRead, UserUpdate,
    FamilyMember, FamilyMemberCreate, FamilyMemberRead,
    UserContact, UserContactCreate, UserContactRead, ContactUserInfo,
    Conversation, ConversationCreate, ConversationRead,
    ConversationMessage, ConversationMessageCreate, ConversationMessageRead,
    ConversationReport, ConversationReportCreate, ConversationReportRead,
    Disease, DiseaseCreate, DiseaseRead,
    ConversationWithMessage, MessageWithResponse,
    MeditCalendarResponse, CalendarReportItem
)
from app.config import settings
from app.ai_assistant import (
    generate_ai_response,
    generate_ai_greeting,
    analyze_conversation_for_diseases,
    generate_conversation_report
)
from app.llm.openai_service import OpenAIService

app = FastAPI(title="Medit API")

# 앱 시작 이벤트
@app.on_event("startup")
async def startup():
    # 설정 출력
    print("서버가 시작되었습니다!")
    
    # severity_level 열 추가 시도
    try:
        # 데이터베이스 연결
        db_session = next(get_session())
        
        # 해당 열이 존재하는지 확인
        result = db_session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='conversation_reports' AND column_name='severity_level'")).fetchone()
        
        # 열이 존재하지 않으면 추가
        if not result:
            print("conversation_reports 테이블에 severity_level 열을 추가합니다...")
            db_session.execute(text("ALTER TABLE conversation_reports ADD COLUMN severity_level VARCHAR DEFAULT 'green'"))
            db_session.commit()
            print("severity_level 열이 성공적으로 추가되었습니다.")
        else:
            print("severity_level 열이 이미 존재합니다.")
            
        db_session.close()
    except Exception as e:
        print(f"데이터베이스 열 추가 오류: {str(e)}")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, you should replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 애플리케이션 시작 시 실행할 작업
@app.on_event("startup")
async def on_startup():
    # 데이터베이스 테이블 생성
    create_db_and_tables()
    
    # OpenAI API 키 테스트
    try:
        print("OpenAI API 키 유효성 테스트 중...")
        openai_service = OpenAIService()
        result = await openai_service.test_api_key()
        
        if result["success"]:
            print(f"OpenAI API 키 유효성 테스트 성공! 모델: {result['model']}, 응답: {result['response']}")
        else:
            print(f"OpenAI API 키 유효성 테스트 실패: {result['error']}")
            print("WARNING: AI 응답이 제대로 작동하지 않을 수 있습니다.")
    except Exception as e:
        print(f"OpenAI API 키 테스트 중 오류 발생: {str(e)}")
        print("WARNING: AI 응답이 제대로 작동하지 않을 수 있습니다.")

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
async def create_conversation(
    login_id: str = Path(..., description="사용자의 로그인 아이디"),
    conversation: ConversationCreate = ...,
    session: Session = Depends(get_session)
):
    """
    새로운 대화를 생성합니다.
    
    - **login_id**: 사용자의 로그인 아이디
    - **title**: 대화 제목 (선택 사항, 없으면 자동 생성될 수 있음)
    - **message_content**: 첫 메시지 내용 (선택 사항, 없으면 AI가 먼저 인사)
    - **request_report**: 리포트 요청 데이터 (선택 사항, 증상 정보 등을 포함)
    
    반환값은 생성된 대화와 시작 메시지(들)를 포함합니다.
    """
    # 사용자 존재 여부 확인
    user = session.exec(select(User).where(User.login_id == login_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 대화 생성 (message_content와 request_report는 Conversation 모델에 없으므로 전달하지 않음)
    conversation_data = conversation.dict(exclude={"message_content", "request_report"})
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
    
    # 리포트 요청이 있는 경우
    if conversation.request_report:
        # 증상 정보를 문자열로 변환
        symptom_text = ""
        if conversation.request_report.get("body_parts"):
            body_parts_str = ", ".join(conversation.request_report.get("body_parts", []))
            symptom_text += f"아픈 부위: {body_parts_str}\n"
        
        if conversation.request_report.get("feeling"):
            symptom_text += f"증상 느낌: {conversation.request_report.get('feeling')}\n"
        
        if conversation.request_report.get("duration"):
            symptom_text += f"지속 기간: {conversation.request_report.get('duration')}\n"
        
        if conversation.request_report.get("pain_intensity"):
            symptom_text += f"통증 강도: {conversation.request_report.get('pain_intensity')}\n"
        
        if conversation.request_report.get("symptom"):
            symptom_text += f"추가 증상: {conversation.request_report.get('symptom')}\n"
        
        # 사용자 메시지 생성
        user_message_content = "다음 증상에 대해 분석해 주세요:\n" + symptom_text
        db_message = ConversationMessage(
            conversation_id=db_conversation.id,
            sender="user",
            content=user_message_content,
            sequence=1  # 첫 번째 메시지는 항상 1
        )
        session.add(db_message)
        session.commit()
        session.refresh(db_message)
        
        # AI 응답 메시지 생성
        try:
            response_text = await generate_ai_response(user_message_content)
        except Exception as e:
            print(f"AI 응답 생성 오류: {str(e)}")
            response_text = "죄송합니다. 현재 AI 서비스에 연결할 수 없습니다. 잠시 후 다시 시도해주세요."
        
        # 응답이 None인 경우 기본 응답으로 대체
        if response_text is None:
            response_text = "현재 AI 서비스에 연결할 수 없습니다. 잠시 후 다시 시도해주세요."
            
        ai_message = ConversationMessage(
            conversation_id=db_conversation.id,
            sender="ai assistant",
            content=response_text or "현재 AI 서비스에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.",
            sequence=2  # 두 번째 메시지 (AI 응답)
        )
        session.add(ai_message)
        session.commit()
        session.refresh(ai_message)
        
        # 분석 데이터 생성 및 리포트 생성
        analysis_data = await analyze_conversation_for_diseases(db_conversation.id, session)
        report_result = await generate_conversation_report(db_conversation.id, analysis_data, session)
        
        # 결과에서 report_content와 severity_level 추출
        report_content = report_result["content"]
        severity_level = report_result["severity_level"]
        
        # 리포트 저장
        db_report = ConversationReport(
            conversation_id=db_conversation.id,
            title=f"{db_conversation.title or '대화'}에 대한 건강 분석 리포트",
            summary="대화 내용을 분석하여 발견된 증상 및 가능성 있는 질환 정보입니다.",
            content=report_content,
            detected_symptoms=analysis_data.get("symptoms", []),
            diseases_with_probabilities=analysis_data.get("diseases_with_probabilities", []),
            health_suggestions=analysis_data.get("suggestions", []),
            severity_level=severity_level
        )
        
        # request_report가 있는 경우 리포트 제목에 반영
        if conversation.request_report and conversation.request_report.get("body_parts"):
            body_parts_str = ", ".join(conversation.request_report.get("body_parts", []))
            feeling = conversation.request_report.get("feeling", "")
            
            if body_parts_str and feeling:
                db_report.title = f"{body_parts_str} {feeling} 분석 리포트"
            elif body_parts_str:
                db_report.title = f"{body_parts_str} 관련 증상 분석 리포트"
        
        session.add(db_report)
        session.commit()
        session.refresh(db_report)
        
        # 대화 제목이 없는 경우, 첫 메시지 기반으로 제목 자동 생성
        if not db_conversation.title:
            body_parts = conversation.request_report.get("body_parts", [])
            body_parts_str = ", ".join(body_parts) if body_parts else "증상"
            feeling = conversation.request_report.get("feeling", "")
            
            if body_parts and feeling:
                title_base = f"{body_parts_str} {feeling} 분석"
            else:
                title_base = f"증상 분석 리포트"
            
            db_conversation.title = title_base
            session.add(db_conversation)
            session.commit()
            session.refresh(db_conversation)
        
        # 결과에 메시지와 리포트 추가
        result.title = db_conversation.title
        result.conversation_message = ConversationMessageRead.from_orm(ai_message)
        result.generated_report = ConversationReportRead.from_orm(db_report)
    
    # 사용자가 메시지를 보낸 경우 (request_report가 없을 때)
    elif conversation.message_content:
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
        try:
            response_text = await generate_ai_response(conversation.message_content)
        except Exception as e:
            print(f"AI 응답 생성 오류: {str(e)}")
            response_text = "죄송합니다. 현재 AI 서비스에 연결할 수 없습니다. 잠시 후 다시 시도해주세요."
        
        # 응답이 None인 경우 기본 응답으로 대체
        if response_text is None:
            response_text = "현재 AI 서비스에 연결할 수 없습니다. 잠시 후 다시 시도해주세요."
            
        ai_message = ConversationMessage(
            conversation_id=db_conversation.id,
            sender="ai assistant",
            content=response_text or "현재 AI 서비스에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.",
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
        try:
            print("AI 인사말 생성 시작...")
            greeting_text = await generate_ai_greeting(user)
            
            # 응답이 None인 경우 기본 인사말로 대체
            if greeting_text is None or greeting_text.strip() == "":
                print("AI 인사말이 비어있어 기본 인사말로 대체합니다.")
                greeting_text = "안녕하세요! 메디트 AI 어시스턴트입니다. 건강에 관한 궁금한 점이 있으신가요?"
        except Exception as e:
            print(f"AI 인사말 생성 중 오류 발생: {str(e)}")
            greeting_text = "안녕하세요! 메디트 AI 어시스턴트입니다. 건강에 관한 궁금한 점이 있으신가요?"
        
        # 최종 안전 검사
        if greeting_text is None or greeting_text.strip() == "":
            greeting_text = "안녕하세요! 메디트 AI 어시스턴트입니다. 건강에 관한 궁금한 점이 있으신가요?"
        
        print(f"최종 AI 인사말: {greeting_text[:50]}..." if len(greeting_text) > 50 else greeting_text)
        
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
async def create_conversation_message(
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
    - **request_report**: 리포트 요청 데이터 (선택 사항, 증상 정보 등을 포함)
    
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
        raise HTTPException(status_code=404, detail="Conversation not found or not owned by this user")
    
    # 메시지 순서 번호 계산
    last_message = session.exec(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(desc(ConversationMessage.sequence))
    ).first()
    
    next_sequence = 1
    if last_message:
        next_sequence = last_message.sequence + 1
    
    # request_report가 있는 경우 content 수정
    if message.request_report:
        # 증상 정보를 문자열로 변환
        symptom_text = ""
        if message.request_report.get("body_parts"):
            body_parts_str = ", ".join(message.request_report.get("body_parts", []))
            symptom_text += f"아픈 부위: {body_parts_str}\n"
        
        if message.request_report.get("feeling"):
            symptom_text += f"증상 느낌: {message.request_report.get('feeling')}\n"
        
        if message.request_report.get("duration"):
            symptom_text += f"지속 기간: {message.request_report.get('duration')}\n"
        
        if message.request_report.get("pain_intensity"):
            symptom_text += f"통증 강도: {message.request_report.get('pain_intensity')}\n"
        
        if message.request_report.get("symptom"):
            symptom_text += f"추가 증상: {message.request_report.get('symptom')}\n"
        
        # 사용자 메시지 내용 업데이트
        message.content = "다음 증상에 대해 분석해 주세요:\n" + symptom_text
    
    # 사용자 메시지 생성
    user_message_data = message.dict(exclude={"request_report"})
    user_message = ConversationMessage(
        **user_message_data,
        conversation_id=conversation_id,
        sequence=next_sequence
    )
    session.add(user_message)
    session.commit()
    session.refresh(user_message)
    
    # AI 응답 생성
    try:
        ai_response_text = await generate_ai_response(message.content)
    except Exception as e:
        print(f"AI 응답 생성 오류: {str(e)}")
        ai_response_text = "현재 AI 서비스에 연결할 수 없습니다. 잠시 후 다시 시도해주세요."
    
    # 응답이 None인 경우 기본 응답으로 대체
    if ai_response_text is None:
        ai_response_text = "현재 AI 서비스에 연결할 수 없습니다. 잠시 후 다시 시도해주세요."
        
    # 대화 분석 및 자동 리포트 생성 조건 확인
    generate_report = message.request_report is not None or (next_sequence + 1 == 7)  # request_report가 있는 경우 항상 리포트 생성
    generated_report = None
    
    # 리포트 생성이 필요한 경우 응답 내용 수정
    if generate_report:
        # 대화에서 증상 분석
        analysis_data = await analyze_conversation_for_diseases(conversation_id, session)
        
        # 리포트 생성
        report_result = await generate_conversation_report(conversation_id, analysis_data, session)
        report_content = report_result["content"]
        severity_level = report_result["severity_level"]
        
        # 리포트 저장 (증상, 질환-확률 통합 정보, 제안 정보 포함)
        title = f"{conversation.title}에 대한 건강 분석 리포트"
        
        # request_report가 있는 경우 리포트 제목에 반영
        if message.request_report and message.request_report.get("body_parts"):
            body_parts_str = ", ".join(message.request_report.get("body_parts", []))
            feeling = message.request_report.get("feeling", "")
            
            if body_parts_str and feeling:
                title = f"{body_parts_str} {feeling} 분석 리포트"
            elif body_parts_str:
                title = f"{body_parts_str} 관련 증상 분석 리포트"
        
        report = ConversationReport(
            conversation_id=conversation_id,
            title=title,
            summary="대화 내용을 분석하여 발견된 증상 및 가능성 있는 질환 정보입니다.",
            content=report_content,
            detected_symptoms=analysis_data.get("symptoms", []),
            diseases_with_probabilities=analysis_data.get("diseases_with_probabilities", []),
            health_suggestions=analysis_data.get("suggestions", []),
            severity_level=severity_level
        )
        
        # request_report가 있는 경우 리포트 제목에 반영
        if message.request_report and message.request_report.get("body_parts"):
            body_parts_str = ", ".join(message.request_report.get("body_parts", []))
            feeling = message.request_report.get("feeling", "")
            
            if body_parts_str and feeling:
                report.title = f"{body_parts_str} {feeling} 분석 리포트"
            elif body_parts_str:
                report.title = f"{body_parts_str} 관련 증상 분석 리포트"
        
        session.add(report)
        session.commit()
        session.refresh(report)
        
        # 생성된 리포트 정보 저장
        generated_report = ConversationReportRead.from_orm(report)
        
        # AI 응답에 리포트 생성 알림 추가
        ai_response_text = f"{ai_response_text}\n\n*분석이 완료되어 건강 리포트가 생성되었습니다.*"
    
    # AI 메시지 생성
    ai_message = ConversationMessage(
        conversation_id=conversation_id,
        sender="ai assistant",
        content=ai_response_text or "현재 AI 서비스에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.",
        sequence=next_sequence + 1
    )
    session.add(ai_message)
    session.commit()
    session.refresh(ai_message)
    
    # 응답 데이터 생성
    return MessageWithResponse(
        user_message=ConversationMessageRead.from_orm(user_message),
        conversation_message=ConversationMessageRead.from_orm(ai_message),
        generated_report=generated_report
    )


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
        .order_by(desc(ConversationReport.created_at))
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


@app.get("/users/{login_id}/calendar/{year}/{month}/reports", response_model=MeditCalendarResponse, tags=["Calendar"], summary="메딧 달력 - 월별 리포트 조회")
async def get_calendar_reports(
    login_id: str = Path(..., description="사용자의 로그인 아이디"),
    year: int = Path(..., description="조회할 연도"),
    month: int = Path(..., ge=1, le=12, description="조회할 월 (1-12)"),
    session: Session = Depends(get_session)
):
    """
    특정 사용자의 특정 월에 생성된 건강 리포트를 조회합니다.
    
    - **login_id**: 사용자의 로그인 아이디
    - **year**: 조회할 연도
    - **month**: 조회할 월 (1-12)
    """
    # 사용자 존재 여부 확인
    user = session.exec(select(User).where(User.login_id == login_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"사용자 ID {login_id}를 찾을 수 없습니다.")
        
    # 월의 시작일과 끝일 계산
    if month == 12:
        next_year = year + 1
        next_month = 1
    else:
        next_year = year
        next_month = month + 1
        
    start_date = datetime(year, month, 1)
    end_date = datetime(next_year, next_month, 1)
    
    # 특정 사용자의 대화 목록 조회
    conversations = session.exec(
        select(Conversation).where(Conversation.user_id == user.id)
    ).all()
    
    conversation_ids = [conv.id for conv in conversations]
    
    if not conversation_ids:
        # 대화가 없는 경우 빈 결과 반환
        return MeditCalendarResponse(
            year=year,
            month=month,
            reports=[]
        )
    
    # 해당 기간의 리포트 조회
    reports = session.exec(
        select(ConversationReport).where(
            ConversationReport.conversation_id.in_(conversation_ids),
            ConversationReport.created_at >= start_date,
            ConversationReport.created_at < end_date
        ).order_by(ConversationReport.created_at)
    ).all()
    
    # 응답 데이터 구성
    calendar_items = []
    for report in reports:
        calendar_items.append(
            CalendarReportItem(
                report_id=report.id,
                conversation_id=report.conversation_id,
                title=report.title,
                summary=report.summary,
                created_at=report.created_at,
                severity_level=report.severity_level or "green",  # 기본값 설정
                day=report.created_at.day  # 일자 추출
            )
        )
    
    return MeditCalendarResponse(
        year=year,
        month=month,
        reports=calendar_items
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
