from typing import List, Dict, Any, Set
from sqlmodel import Session, select
import uuid
import asyncio
from datetime import datetime
import re

from app.models import (
    User, Conversation, ConversationMessage, Disease
)
from app.config import settings
from app.llm.factory import LLMServiceFactory
from app.llm.base import LLMService

# LLM 서비스 초기화 함수
def get_llm_service() -> LLMService:
    """
    설정에 따라 적절한 LLM 서비스 인스턴스를 반환합니다.
    
    Returns:
        LLMService: 구성된 LLM 서비스 인스턴스
    """
    provider = settings.LLM_PROVIDER.lower()
    
    if provider == "openai":
        config = {
            "api_key": settings.OPENAI_API_KEY,
            "model": settings.OPENAI_MODEL
        }
    elif provider == "bedrock":
        config = {
            "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
            "region_name": settings.AWS_REGION,
            "model_id": settings.BEDROCK_MODEL_ID
        }
    else:
        raise ValueError(f"지원되지 않는 LLM 제공자: {provider}")
    
    return LLMServiceFactory.create(provider, config)

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


# AI 응답 생성 함수
async def generate_ai_response(user_message: str) -> str:
    """
    사용자 메시지에 대한 AI 응답을 생성합니다.
    LLM 서비스를 사용하여 자연스러운 응답을 생성합니다.
    
    Args:
        user_message: 사용자가 보낸 메시지 내용
        
    Returns:
        AI 응답 메시지
    """
    try:
        # LLM 서비스 가져오기
        llm_service = get_llm_service()
        
        # 프롬프트 구성
        system_message = """
        당신은 건강 상담을 전문으로 하는 AI 의료 어시스턴트입니다.
        사용자의 건강 관련 질문에 친절하고 도움이 되는 정보를 제공하세요.
        의학적 조언을 제공할 때는 항상 전문의와 상담을 권장하세요.
        실제 진단이나 치료를 제시하지 않도록 주의하세요.
        """
        
        # 채팅 메시지 구성
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        
        # LLM 서비스를 통해 응답 생성
        response = await llm_service.generate_chat(messages)

        print(f"AI 응답: {response}")
        return response
        
    except Exception as e:
        print(f"LLM 서비스 오류: {str(e)}")
        # 오류 발생 시 기본 응답 제공 (기존 규칙 기반 응답 사용)
        return fallback_generate_response(user_message)


# 기존 규칙 기반 응답 생성 함수 (LLM 서비스 실패 시 대비책)
def fallback_generate_response(user_message: str) -> str:
    """
    LLM 서비스 실패 시 사용할 기본 규칙 기반 응답 생성 함수
    """
    user_message_lower = user_message.lower()
    
    # 인사말 감지
    if any(greeting in user_message_lower for greeting in ["안녕", "반가워", "hello", "hi"]):
        return "안녕하세요! 오늘 어떻게 도와드릴까요? 건강에 관한 궁금한 점이 있으신가요?"
    
    # 감사 표현 감지
    if any(thanks in user_message_lower for thanks in ["감사", "고마워", "thanks"]):
        return "천만에요! 도움이 되어 기쁩니다. 다른 도움이 필요하시면 언제든지 말씀해주세요."
    
    # 건강 상태 질문 감지
    if any(health_q in user_message_lower for health_q in ["증상", "아파", "어디가", "통증", "열이", "두통", "어지러"]):
        return "증상에 대해 좀 더 자세히 말씀해 주시겠어요? 언제부터 시작되었나요? 다른 동반 증상은 없으신가요?"
    
    # 약 관련 질문 감지
    if any(med_q in user_message_lower for med_q in ["약", "처방", "복용", "먹어도", "부작용"]):
        return "약물에 관해서는 반드시 전문의와 상담하시는 것이 좋습니다. 의사의 처방과 지시에 따라 약을 복용하시는 것이 안전합니다."
    
    # 식이 관련 질문 감지
    if any(diet_q in user_message_lower for diet_q in ["먹어도", "식단", "음식", "영양", "식이"]):
        return "균형 잡힌 식단은 건강 유지에 매우 중요합니다. 다양한 채소와 과일, 적절한 단백질 섭취를 권장드립니다. 특정 질환이나 상태에 따른 식이요법은 전문가와 상담하시는 것이 좋습니다."
    
    # 운동 관련 질문 감지
    if any(exercise_q in user_message_lower for exercise_q in ["운동", "활동", "체력", "걷기", "헬스"]):
        return "규칙적인 운동은 신체 건강뿐만 아니라 정신 건강에도 매우 좋습니다. 하루 30분 정도의 가벼운 유산소 운동부터 시작해보세요. 본인의 건강 상태에 맞는 운동 강도를 선택하는 것이 중요합니다."
    
    # 기본 응답
    return "말씀해주신 내용에 대해 더 자세히 알려주시면 더 정확한 정보와 도움을 드릴 수 있습니다. 건강 상태나 특정 증상에 대해 구체적으로 말씀해주세요."


# 동기 버전의 응답 생성 함수 (기존 코드와의 호환성 유지)
def generate_ai_response_sync(user_message: str) -> str:
    """
    generate_ai_response의 동기 버전 (기존 코드와의 호환성 유지)
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(generate_ai_response(user_message))
    finally:
        loop.close()


# 사용자 정보를 기반으로 인사말 생성
async def generate_ai_greeting(user: User) -> str:
    """
    사용자 정보를 기반으로 AI의 첫 인사말을 생성합니다.
    
    Args:
        user: 대화를 시작한 사용자 객체
        
    Returns:
        사용자 맞춤형 인사말
    """
    print(f"인사말 생성 시작 - 사용자: {user.login_id}, 닉네임: {user.nickname}")
    
    try:
        # LLM 서비스 가져오기
        llm_service = get_llm_service()
        
        
        system_message = """
        당신은 건강 상담을 전문으로 하는 친절한 AI 의료 어시스턴트입니다.
        지금 첫인사를 건네며, 사용자의 프로필 정보를 참고해 개인화된 인사말을 제공하세요.
        항상 공감과 존중의 태도로 대화를 시작하며, 의학적 정보가 필요하면 질문해도 좋다고 알려주세요.
        """
        
        # 사용자 정보를 기반으로 한 인사말 프롬프트 구성
        user_info = f"사용자 정보: 닉네임={user.nickname}, 성별={user.gender}, 연령대={user.age_range}"
        
        if user.usual_illness and len(user.usual_illness) > 0:
            user_info += f", 평소 건강 이슈: {', '.join(user.usual_illness)}"
        
        prompt = f"""
        {user_info}
        
        위 정보를 바탕으로 친절하고 개인화된 첫 인사말을 작성해주세요.
        사용자의 건강 상태에 공감하고, 어떻게 도울 수 있는지 알려주세요.
        """
        
        print(f"OpenAI에 인사말 생성 요청 - 프롬프트 길이: {len(prompt)}")
        
        # 채팅 메시지 구성
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
        
        # LLM 서비스를 통해 인사말 생성
        greeting = await llm_service.generate_chat(messages)
        
        print(f"OpenAI 인사말 응답 결과: {greeting[:50]}..." if greeting and len(greeting) > 50 else f"응답: {greeting}")
        
        return greeting
        
    except Exception as e:
        print(f"인사말 생성 오류: {str(e)}")
        # 오류 발생 시 기본 인사말 제공
        return fallback_generate_greeting(user)


# 기존 규칙 기반 인사말 생성 함수 (LLM 서비스 실패 시 대비책)
def fallback_generate_greeting(user: User) -> str:
    """
    LLM 서비스 실패 시 사용할 기본 인사말 생성 함수
    """
    # 기본 인사말
    base_greeting = "저는 건강 상담 AI 비서입니다. 건강에 관한 질문이나 상담이 필요하시면 언제든지 말씀해주세요."
    
    # 사용자 이름에 따른 맞춤형 인사
    name_greeting = "안녕하세요!"
    if user.nickname:
        name_greeting = f"안녕하세요, {user.nickname}님!"
    
    # 사용자의 평소 질환이 있는 경우, 그에 맞는 인사말 추가
    health_greeting = ""
    if user.usual_illness and len(user.usual_illness) > 0:
        health_greeting = f"\n평소 {', '.join(user.usual_illness)}으로 불편함을 겪고 계시는 것으로 알고 있습니다. 오늘은 어떠신가요?"
    
    # 최종 인사말 조합
    return f"{name_greeting}{health_greeting}\n\n{base_greeting}"


# 동기 버전의 인사말 생성 함수 (기존 코드와의 호환성 유지)
def generate_ai_greeting_sync(user: User) -> str:
    """
    generate_ai_greeting의 동기 버전 (기존 코드와의 호환성 유지)
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(generate_ai_greeting(user))
    finally:
        loop.close()


# 대화 내용을 분석하여 질병 가능성 판단
async def analyze_conversation_for_diseases(conversation_id: uuid.UUID, session: Session) -> dict:
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
    
    try:
        # LLM 서비스를 사용하여 의학적 분석 수행
        llm_service = get_llm_service()
        analysis_result = await llm_service.analyze_text(
            conversation_text, 
            task="medical_analysis"
        )
        
        # LLM 응답 처리
        detected_symptoms = analysis_result.get("symptoms", [])
        
        # 질병 확률 정보 처리
        diseases_with_probabilities = []
        possible_diseases = analysis_result.get("possible_diseases", [])
        
        for disease_info in possible_diseases:
            disease_name = disease_info.get("name", "")
            probability = disease_info.get("probability", 50.0)
            
            # 데이터베이스에서 질병 검색 또는 생성
            db_disease = session.exec(
                select(Disease).where(Disease.name == disease_name)
            ).first()
            
            # 질병이 없으면 새로 생성
            if not db_disease and disease_name:
                # 질병에 대한 설명 생성 (관련 증상으로부터)
                related_symptoms = []
                for symptom, diseases in symptom_disease_map.items():
                    if disease_name in diseases:
                        related_symptoms.append(symptom)
                
                description = f"{disease_name}는 일반적으로 {', '.join(related_symptoms[:3] if related_symptoms else ['다양한 증상'])} 등의 증상과 연관됩니다."
                
                db_disease = Disease(
                    name=disease_name,
                    description=description
                )
                session.add(db_disease)
                session.commit()
                session.refresh(db_disease)
            
            # 질병 ID를 포함하여 결과 저장 (질병이 DB에 있는 경우만)
            if db_disease:
                diseases_with_probabilities.append({
                    "id": db_disease.id,
                    "name": disease_name,
                    "probability": probability
                })
        
        # 건강 관리 조언
        health_suggestions = analysis_result.get("health_suggestions", [])
        
        # 제안이 부족하면 일반적인 제안 추가
        if len(health_suggestions) < 3:
            health_suggestions.extend(general_suggestions)
            health_suggestions = list(set(health_suggestions))[:5]  # 중복 제거 및 최대 5개로 제한
        
        return {
            "symptoms": detected_symptoms,
            "diseases_with_probabilities": diseases_with_probabilities,
            "suggestions": health_suggestions[:5]  # 최대 5개의 제안만 반환
        }
        
    except Exception as e:
        print(f"LLM 의학 분석 오류: {str(e)}")
        # 오류 발생 시 기존 규칙 기반 분석으로 대체
        return fallback_analyze_conversation(conversation_text, session)


# 기존 규칙 기반 대화 분석 함수 (LLM 서비스 실패 시 대비책)
def fallback_analyze_conversation(conversation_text: str, session: Session) -> dict:
    """
    LLM 서비스 실패 시 사용할 기본 대화 분석 함수
    """
    conversation_text_lower = conversation_text.lower()
    
    # 증상 감지 (대화에서 언급된 증상 추출)
    detected_symptoms = set()
    for symptom in common_symptoms:
        if symptom.lower() in conversation_text_lower:
            detected_symptoms.add(symptom)
    
    # 직접 언급된 질병 감지
    directly_mentioned_diseases = set()
    # 모든 질병 이름 목록 생성 (중복 제거)
    all_diseases = set()
    for symptoms_list in symptom_disease_map.values():
        all_diseases.update(symptoms_list)
    
    for disease in all_diseases:
        if disease.lower() in conversation_text_lower:
            directly_mentioned_diseases.add(disease)
            # 해당 질병과 관련된 대표 증상도 추가 (분석의 정확도를 위해)
            for symptom, diseases in symptom_disease_map.items():
                if disease in diseases:
                    detected_symptoms.add(symptom)
    
    # 어떤 증상도 발견되지 않았고, 직접 언급된 질병도 없는 경우
    if not detected_symptoms and not directly_mentioned_diseases:
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
    
    # 직접 언급된 질병 추가
    possible_diseases.update(directly_mentioned_diseases)
    for disease in directly_mentioned_diseases:
        # 직접 언급된 질병은 높은 점수 부여
        disease_symptom_counts[disease] = disease_symptom_counts.get(disease, 0) + 3
    
    # 질병 확률 계산 (단순 알고리즘)
    disease_probabilities = {}
    for disease in possible_diseases:
        if disease in directly_mentioned_diseases:
            # 직접 언급된 질병은 높은 확률 부여 (80~95%)
            probability = 80 + (disease_symptom_counts.get(disease, 3) - 3) * 5
            probability = min(95, probability)
        else:
            matched_symptom_count = disease_symptom_counts.get(disease, 0)
            total_symptom_count = len(disease_symptoms.get(disease, []))
            
            if total_symptom_count > 0:
                # 간단한 확률 계산 (매칭된 증상 수 / 질병 관련 전체 증상 수)
                probability = (matched_symptom_count / total_symptom_count) * 100
                # 최소 확률 50%, 최대 95%로 제한
                probability = min(95, max(50, probability))
            else:
                probability = 50.0
        
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
                description=f"{disease}는 일반적으로 {', '.join(disease_symptoms.get(disease, [])[:3])} 등의 증상과 연관됩니다."
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


# 동기 버전의 대화 분석 함수 (기존 코드와의 호환성 유지)
def analyze_conversation_for_diseases_sync(conversation_id: uuid.UUID, session: Session) -> dict:
    """
    analyze_conversation_for_diseases의 동기 버전 (기존 코드와의 호환성 유지)
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(analyze_conversation_for_diseases(conversation_id, session))
    finally:
        loop.close()


# 대화 내용을 분석하여 리포트 내용 생성
async def generate_conversation_report(conversation_id: uuid.UUID, analysis_data: dict, session: Session) -> dict:
    """대화 내용을 분석하여 건강 분석 리포트를 생성합니다."""
    # 대화에서 사용자 정보 가져오기
    conversation = session.get(Conversation, conversation_id)
    user = session.get(User, conversation.user_id)
    
    try:
        # LLM 서비스 가져오기
        llm_service = get_llm_service()
        
        # 대화 내용 수집
        messages = session.exec(
            select(ConversationMessage).where(
                ConversationMessage.conversation_id == conversation_id
            ).order_by(ConversationMessage.created_at)
        ).all()
        
        conversation_text = ""
        for message in messages:
            sender = "사용자" if message.sender == "user" else "AI 어시스턴트"
            conversation_text += f"{sender}: {message.content}\n\n"
        
        # 사용자 정보 구성
        user_info = f"""
        사용자 정보:
        - 이름: {user.nickname if user.nickname else '이름 없음'}
        - 연령대: {user.age_range if user.age_range else '정보 없음'}
        - 성별: {user.gender if user.gender else '정보 없음'}
        - 평소 앓는 질환: {', '.join(user.usual_illness) if user.usual_illness and len(user.usual_illness) > 0 else '없음'}
        """
        
        # 분석 결과 처리
        symptoms_text = "감지된 증상이 없습니다."
        if analysis_data["symptoms"]:
            symptoms_text = ", ".join(analysis_data["symptoms"])
        
        diseases_text = "가능성 있는 질환이 감지되지 않았습니다."
        if analysis_data["diseases_with_probabilities"]:
            diseases_text = "\n".join([
                f"- {d['name']} ({d['probability']}%)" 
                for d in analysis_data["diseases_with_probabilities"]
            ])
        
        suggestions_text = "\n".join([f"- {s}" for s in analysis_data["suggestions"]])
        
        # 프롬프트 구성
        system_message = """
        당신은 의료 보고서 작성 전문가입니다. 대화 분석 결과를 바탕으로 환자를 위한 
        건강 분석 리포트를 작성해주세요. 리포트는 전문적이면서도 이해하기 쉬운 말로 
        작성되어야 하며, 다음 섹션을 포함해야 합니다:

        1. 사용자 정보
        2. 대화 내용 분석 소개
        3. 감지된 증상 요약
        4. 가능성 있는 질환 및 확률 분석
        5. 건강 관리 조언
        6. 면책 조항

        추가적으로, 다음 3가지 중 하나로 응급도 수준을 판단해주세요:
        - red: 심한 통증이나 위급한 상황으로 즉각적인 의료 조치가 필요한 경우
        - orange: 중간 정도 통증이나 불편함으로 가까운 시일 내 의료 조치가 필요한 경우
        - green: 통증이 없거나 양호한 상태로 정기적인 관리만 필요한 경우

        리포트 마지막에 다음 형식으로 응급도를 표시해주세요:
        "SEVERITY_LEVEL: [red/orange/green]"

        주의: 최종 진단은 내리지 말고, 항상 전문의와 상담을 권장하세요.
        리포트는 마크다운 형식으로 작성해주세요.
        """
        
        prompt = f"""
        다음 정보를 바탕으로 건강 분석 리포트를 작성해주세요:
        
        {user_info}
        
        ### 대화 내용 요약:
        {conversation_text[:1000]}... (대화 내용 일부)
        
        ### 분석 결과:
        
        감지된 증상:
        {symptoms_text}
        
        가능성 있는 질환:
        {diseases_text}
        
        건강 관리 조언:
        {suggestions_text}
        
        현재 시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        """
        
        # 채팅 메시지 구성
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
        
        # LLM 서비스를 통해 리포트 생성
        report = await llm_service.generate_chat(messages)
        
        # 응급도 수준 추출
        severity_level = "green"  # 기본값
        severity_pattern = r"SEVERITY_LEVEL:\s*(red|orange|green)"
        match = re.search(severity_pattern, report, re.IGNORECASE)
        if match:
            severity_level = match.group(1).lower()
            # 리포트에서 SEVERITY_LEVEL 표시 제거 (UI에서 별도로 표시할 예정)
            report = re.sub(r"\nSEVERITY_LEVEL:\s*(red|orange|green)\s*", "", report)
        
        # 만약 pain_intensity가 있으면 이를 기반으로 severity_level 추가 판단
        # analysis_data에 pain_intensity 정보가 있는 경우
        try:
            if "pain_intensity" in analysis_data:
                pain_level = float(analysis_data["pain_intensity"])
                if pain_level >= 7:
                    severity_level = "red"
                elif pain_level >= 4:
                    severity_level = "orange"
                else:
                    severity_level = "green"
        except (ValueError, TypeError):
            pass  # pain_intensity가 올바른 형식이 아닌 경우 무시
            
        # severity_level과 report를 딕셔너리로 반환
        return {
            "content": report,
            "severity_level": severity_level
        }
        
    except Exception as e:
        print(f"LLM 리포트 생성 오류: {str(e)}")
        # 오류 발생 시 기본 리포트 제공 (기존 규칙 기반 리포트 사용)
        fallback_report = fallback_generate_report(conversation_id, analysis_data, session)
        return {
            "content": fallback_report,
            "severity_level": "green"  # 오류 시 안전하게 기본값으로 설정
        }


# 기존 규칙 기반 리포트 생성 함수 (LLM 서비스 실패 시 대비책)
def fallback_generate_report(conversation_id: uuid.UUID, analysis_data: dict, session: Session) -> str:
    """
    LLM 서비스 실패 시 사용할 기본 리포트 생성 함수
    """
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


# 동기 버전의 리포트 생성 함수 (기존 코드와의 호환성 유지)
def generate_conversation_report_sync(conversation_id: uuid.UUID, analysis_data: dict, session: Session) -> dict:
    """
    generate_conversation_report의 동기 버전 (기존 코드와의 호환성 유지)
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(generate_conversation_report(conversation_id, analysis_data, session))
    finally:
        loop.close()
