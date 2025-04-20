#!/usr/bin/env python3
import random
import uuid
from datetime import datetime, timedelta
from sqlmodel import Session, select
from app.database import engine
from app.models import (
    User, FamilyMember, UserContact, 
    Conversation, ConversationMessage, 
    ConversationReport, Disease
)

# 간단한 비밀번호 해싱 함수 (해커톤용 - 실제 보안에 적합하지 않음)
def hash_password(password):
    return f"mock_hashed_{password}"  # 실제로는 해싱 안함, 해커톤 목적으로만 사용

# 목업 사용자 데이터
mock_users = [
    {
        "login_id": "kim123",
        "nickname": "김건강",
        "age_range": "30대",
        "gender": "남성",
        "password": "password123",
        "usual_illness": ["고혈압", "당뇨병"]
    },
    {
        "login_id": "park456",
        "nickname": "박소연",
        "age_range": "20대",
        "gender": "여성",
        "password": "password456",
        "usual_illness": ["편두통", "천식"]
    },
    {
        "login_id": "lee789",
        "nickname": "이진호",
        "age_range": "40대",
        "gender": "남성",
        "password": "password789",
        "usual_illness": ["위궤양", "관절염"]
    },
    {
        "login_id": "choi101",
        "nickname": "최미라",
        "age_range": "50대",
        "gender": "여성",
        "password": "password101",
        "usual_illness": ["골다공증", "불안장애"]
    },
    {
        "login_id": "jung202",
        "nickname": "정현우",
        "age_range": "30대",
        "gender": "남성",
        "password": "password202",
        "usual_illness": ["역류성 식도염"]
    }
]

# 목업 가족 구성원 데이터 (각 사용자마다 1-2명의 가족 구성원)
mock_family_members = [
    # 김건강의 가족
    {
        "user_login_id": "kim123",
        "nickname": "김아버지",
        "relation": "아버지",
        "age": 65,
        "usual_illness": ["고혈압", "당뇨병"]
    },
    {
        "user_login_id": "kim123",
        "nickname": "김어머니",
        "relation": "어머니",
        "age": 62,
        "usual_illness": ["관절염"]
    },
    # 박소연의 가족
    {
        "user_login_id": "park456",
        "nickname": "박동생",
        "relation": "동생",
        "age": 17,
        "usual_illness": ["천식"]
    },
    # 이진호의 가족
    {
        "user_login_id": "lee789",
        "nickname": "이아들",
        "relation": "아들",
        "age": 10,
        "usual_illness": []
    },
    # 최미라의 가족
    {
        "user_login_id": "choi101",
        "nickname": "최할머니",
        "relation": "어머니",
        "age": 78,
        "usual_illness": ["고혈압", "관절염", "당뇨병"]
    },
    # 정현우의 가족
    {
        "user_login_id": "jung202",
        "nickname": "정아내",
        "relation": "배우자",
        "age": 32,
        "usual_illness": ["불안장애"]
    }
]

# 목업 연락처 데이터 (사용자 간의 관계)
mock_contacts = [
    # 김건강의 연락처
    {
        "user_login_id": "kim123",
        "contact_login_id": "park456",
        "alias_nickname": "박의사선생님",
        "relation": "주치의"
    },
    {
        "user_login_id": "kim123",
        "contact_login_id": "lee789",
        "alias_nickname": "이형",
        "relation": "친구"
    },
    # 박소연의 연락처
    {
        "user_login_id": "park456",
        "contact_login_id": "choi101",
        "alias_nickname": "최선생님",
        "relation": "스승님"
    },
    # 이진호의 연락처
    {
        "user_login_id": "lee789",
        "contact_login_id": "jung202",
        "alias_nickname": "정사장",
        "relation": "직장동료"
    },
    # 최미라의 연락처
    {
        "user_login_id": "choi101",
        "contact_login_id": "kim123",
        "alias_nickname": "김팀장",
        "relation": "직장동료"
    }
]

# 목업 대화 및 건강 리포트 내용
mock_conversations = [
    # 김건강의 대화
    {
        "user_login_id": "kim123",
        "title": "고혈압 관련 상담",
        "messages": [
            {"sender": "user", "content": "요즘 두통이 심하고 가끔 현기증이 나요. 혈압도 좀 높은 것 같아요."},
            {"sender": "assistant", "content": "언제부터 증상이 있었나요? 혈압은 얼마나 높게 측정되었나요?"},
            {"sender": "user", "content": "일주일 전부터 두통이 있었고, 혈압은 150/95 정도로 측정됐어요."},
            {"sender": "assistant", "content": "고혈압으로 인한 증상으로 보입니다. 생활습관 개선과 함께 정기적인 혈압 체크가 필요합니다. 소금 섭취를 줄이고 규칙적인 운동을 권장합니다."}
        ],
        "report": {
            "title": "고혈압 의심 증상 분석",
            "summary": "두통, 현기증 및 혈압 상승 증상에 대한 상담",
            "content": "일주일 전부터 두통과 현기증이 있으며 혈압이 150/95로 측정됨. 고혈압 의심 증상으로 판단되며 생활습관 개선 권장.",
            "detected_symptoms": ["두통", "현기증", "고혈압"],
            "diseases_with_probabilities": [
                {"name": "고혈압", "probability": 0.85},
                {"name": "스트레스", "probability": 0.45}
            ],
            "health_suggestions": [
                "소금 섭취 줄이기",
                "규칙적인 운동하기",
                "정기적인 혈압 체크",
                "스트레스 관리"
            ],
            "severity_level": "orange"
        }
    },
    # 박소연의 대화
    {
        "user_login_id": "park456",
        "title": "편두통 상담",
        "messages": [
            {"sender": "user", "content": "3일 전부터 머리 한쪽이 계속 아프고, 메스꺼움도 있어요. 불빛을 보면 더 심해져요."},
            {"sender": "assistant", "content": "편두통 증상으로 보입니다. 통증이 얼마나 심한가요? 일상생활에 지장이 있나요?"},
            {"sender": "user", "content": "통증이 7점 정도로 심해요. 일을 제대로 못하고 있습니다."},
            {"sender": "assistant", "content": "심한 편두통으로 판단됩니다. 조용하고 어두운 곳에서 휴식을 취하고, 진통제 복용을 고려해보세요. 지속될 경우 병원 방문이 필요합니다."}
        ],
        "report": {
            "title": "편두통 증상 분석",
            "summary": "머리 한쪽의 심한 통증과 메스꺼움, 빛에 대한 과민 반응",
            "content": "3일 전부터 머리 한쪽의 통증, 메스꺼움, 빛에 대한 과민 반응 등 전형적인 편두통 증상을 보임. 통증 강도 7/10으로 일상생활에 지장을 줌.",
            "detected_symptoms": ["편측성 두통", "메스꺼움", "빛 과민성"],
            "diseases_with_probabilities": [
                {"name": "편두통", "probability": 0.9},
                {"name": "긴장성 두통", "probability": 0.3}
            ],
            "health_suggestions": [
                "어둡고 조용한 환경에서 휴식",
                "충분한 수분 섭취",
                "적절한 진통제 복용",
                "규칙적인 수면 습관 유지"
            ],
            "severity_level": "orange"
        }
    },
    # 이진호의 대화
    {
        "user_login_id": "lee789",
        "title": "위장 불편 상담",
        "messages": [
            {"sender": "user", "content": "식사 후에 배가 아프고 속이 쓰려요. 특히 공복에 통증이 심해요."},
            {"sender": "assistant", "content": "언제부터 증상이 있었나요? 기타 증상도 있으신가요?"},
            {"sender": "user", "content": "한 달 정도 됐고, 가끔 소화가 안 되고 더부룩해요."},
            {"sender": "assistant", "content": "위궤양 증상으로 보입니다. 식이 조절과 함께 스트레스 관리가 필요하며, 지속될 경우 위내시경 검사를 권장합니다."}
        ],
        "report": {
            "title": "위장 질환 의심 증상",
            "summary": "식후 복통 및 공복 시 통증, 속쓰림 증상",
            "content": "한 달간 지속된 식사 후 복통, 공복 시 더 심한 통증, 속쓰림 및 소화불량 증상. 위궤양 의심 소견으로 생활습관 개선 필요.",
            "detected_symptoms": ["복통", "속쓰림", "소화불량"],
            "diseases_with_probabilities": [
                {"name": "위궤양", "probability": 0.75},
                {"name": "역류성 식도염", "probability": 0.5},
                {"name": "위염", "probability": 0.6}
            ],
            "health_suggestions": [
                "자극적인 음식 피하기",
                "규칙적인 식사",
                "스트레스 관리",
                "위장 약물 복용 고려"
            ],
            "severity_level": "green"
        }
    },
    # 최미라의 대화
    {
        "user_login_id": "choi101",
        "title": "불안 증상 상담",
        "messages": [
            {"sender": "user", "content": "요즘 불안감이 심하고 가슴이 두근거리며 잠을 잘 못자요."},
            {"sender": "assistant", "content": "스트레스를 받는 상황이 있으신가요? 불안감을 더 악화시키는 요인이 있나요?"},
            {"sender": "user", "content": "직장에서 스트레스를 많이 받고, 사람들 많은 곳에 가면 더 심해져요."},
            {"sender": "assistant", "content": "불안장애 증상으로 보입니다. 호흡 및 명상 연습이 도움될 수 있으며, 심리 상담을 고려해보세요."}
        ],
        "report": {
            "title": "불안장애 의심 증상",
            "summary": "지속적인 불안감, 심계항진, 불면증",
            "content": "지속적인 불안감, 심장 두근거림, 불면증을 호소. 직장 스트레스, 사회적 상황에서 증상 악화. 불안장애 의심 소견으로 심리적 접근이 필요함.",
            "detected_symptoms": ["불안감", "심계항진", "불면증", "사회적 상황 회피"],
            "diseases_with_probabilities": [
                {"name": "불안장애", "probability": 0.8},
                {"name": "사회불안장애", "probability": 0.6},
                {"name": "공황장애", "probability": 0.4}
            ],
            "health_suggestions": [
                "심호흡 및 명상 연습",
                "규칙적인 운동",
                "심리 상담 받기",
                "카페인 섭취 줄이기"
            ],
            "severity_level": "green"
        }
    },
    # 정현우의 대화
    {
        "user_login_id": "jung202",
        "title": "역류성 식도염 상담",
        "messages": [
            {"sender": "user", "content": "늘 식사 후에 가슴이 쓰리고 신물이 올라와요. 기침도 자주하게 됩니다."},
            {"sender": "assistant", "content": "어떤 음식을 먹을 때 증상이 더 심해지나요?"},
            {"sender": "user", "content": "매운 음식이나 커피를 마시면 더 심해져요. 특히 저녁에 증상이 심합니다."},
            {"sender": "assistant", "content": "역류성 식도염으로 보입니다. 식이 조절이 중요하며, 취침 전 3시간은 음식 섭취를 피하는 것이 좋습니다."}
        ],
        "report": {
            "title": "역류성 식도염 증상 분석",
            "summary": "식후 가슴쓰림, 산 역류, 만성 기침",
            "content": "식사 후 가슴쓰림, 신물 역류, 만성 기침 증상. 매운 음식, 커피, 취침 전 식사에 의해 악화됨. 역류성 식도염 의심 소견으로 생활습관 개선 필요.",
            "detected_symptoms": ["가슴쓰림", "산 역류", "만성 기침"],
            "diseases_with_probabilities": [
                {"name": "역류성 식도염", "probability": 0.9},
                {"name": "위염", "probability": 0.4}
            ],
            "health_suggestions": [
                "매운 음식, 커피, 알코올 제한",
                "취침 전 3시간 내 음식 섭취 피하기",
                "상체를 높이고 수면",
                "금연, 체중 감량"
            ],
            "severity_level": "green"
        }
    }
]

def seed_mock_data():
    with Session(engine) as session:
        # 1. 사용자 데이터 추가
        user_id_map = {}  # login_id -> user_id 매핑을 위한 딕셔너리
        
        for user_data in mock_users:
            login_id = user_data["login_id"]
            
            # 이미 존재하는 사용자인지 확인
            existing_user = session.exec(select(User).where(User.login_id == login_id)).first()
            
            if existing_user:
                print(f"사용자 업데이트: {login_id}")
                existing_user.nickname = user_data["nickname"]
                existing_user.age_range = user_data["age_range"]
                existing_user.gender = user_data["gender"]
                existing_user.usual_illness = user_data["usual_illness"]
                user = existing_user
            else:
                print(f"사용자 추가: {login_id}")
                user = User(
                    login_id=login_id,
                    nickname=user_data["nickname"],
                    age_range=user_data["age_range"],
                    gender=user_data["gender"],
                    usual_illness=user_data["usual_illness"],
                    hashed_password=hash_password(user_data["password"])
                )
                session.add(user)
            
            session.commit()
            session.refresh(user)
            user_id_map[login_id] = user.id
        
        # 2. 가족 구성원 데이터 추가
        for family_data in mock_family_members:
            user_login_id = family_data["user_login_id"]
            user_id = user_id_map.get(user_login_id)
            
            if not user_id:
                print(f"사용자를 찾을 수 없음: {user_login_id}, 가족 구성원 추가 건너뜀")
                continue
                
            # 닉네임으로 기존 가족 구성원 확인
            existing_family = session.exec(
                select(FamilyMember).where(
                    FamilyMember.user_id == user_id,
                    FamilyMember.nickname == family_data["nickname"]
                )
            ).first()
            
            if existing_family:
                print(f"가족 구성원 업데이트: {family_data['nickname']} ({user_login_id}의 {family_data['relation']})")
                existing_family.relation = family_data["relation"]
                existing_family.age = family_data["age"]
                existing_family.usual_illness = family_data.get("usual_illness", [])
            else:
                print(f"가족 구성원 추가: {family_data['nickname']} ({user_login_id}의 {family_data['relation']})")
                family = FamilyMember(
                    user_id=user_id,
                    nickname=family_data["nickname"],
                    relation=family_data["relation"],
                    age=family_data["age"],
                    usual_illness=family_data.get("usual_illness", [])
                )
                session.add(family)
                
        session.commit()
        
        # 3. 연락처 데이터 추가
        for contact_data in mock_contacts:
            user_login_id = contact_data["user_login_id"]
            contact_login_id = contact_data["contact_login_id"]
            
            user_id = user_id_map.get(user_login_id)
            contact_user_id = user_id_map.get(contact_login_id)
            
            if not user_id or not contact_user_id:
                print(f"사용자 또는 연락처를 찾을 수 없음: {user_login_id} -> {contact_login_id}, 연락처 추가 건너뜀")
                continue
                
            # 기존 연락처 확인
            existing_contact = session.exec(
                select(UserContact).where(
                    UserContact.user_id == user_id,
                    UserContact.contact_user_id == contact_user_id
                )
            ).first()
            
            if existing_contact:
                print(f"연락처 업데이트: {user_login_id} -> {contact_login_id}")
                existing_contact.alias_nickname = contact_data["alias_nickname"]
                existing_contact.relation = contact_data["relation"]
            else:
                print(f"연락처 추가: {user_login_id} -> {contact_login_id}")
                contact = UserContact(
                    user_id=user_id,
                    contact_user_id=contact_user_id,
                    alias_nickname=contact_data["alias_nickname"],
                    relation=contact_data["relation"]
                )
                session.add(contact)
                
        session.commit()
        
        # 4. 대화 및 리포트 데이터 추가
        for conv_data in mock_conversations:
            user_login_id = conv_data["user_login_id"]
            user_id = user_id_map.get(user_login_id)
            
            if not user_id:
                print(f"사용자를 찾을 수 없음: {user_login_id}, 대화 추가 건너뜀")
                continue
            
            # 이미 존재하는 대화인지 확인 (제목으로)
            existing_convs = session.exec(
                select(Conversation).where(
                    Conversation.user_id == user_id,
                    Conversation.title == conv_data["title"]
                )
            ).all()
            
            if existing_convs:
                # 기존 대화가 있으면 삭제하고 새로 생성 (더미 데이터이므로 단순화)
                for conv in existing_convs:
                    # 연결된 메시지와 리포트 삭제
                    session.exec(select(ConversationMessage).where(
                        ConversationMessage.conversation_id == conv.id
                    )).delete()
                    session.exec(select(ConversationReport).where(
                        ConversationReport.conversation_id == conv.id
                    )).delete()
                    session.delete(conv)
                session.commit()
                print(f"기존 대화 삭제: {conv_data['title']} ({user_login_id})")
            
            # 새 대화 생성
            conversation = Conversation(
                user_id=user_id,
                title=conv_data["title"],
                started_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
            )
            session.add(conversation)
            session.commit()
            session.refresh(conversation)
            
            print(f"대화 추가: {conv_data['title']} ({user_login_id})")
            
            # 메시지 추가
            for i, msg_data in enumerate(conv_data["messages"]):
                message = ConversationMessage(
                    conversation_id=conversation.id,
                    sender=msg_data["sender"],
                    content=msg_data["content"],
                    sequence=i+1,
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30), minutes=random.randint(1, 60))
                )
                session.add(message)
            
            session.commit()
            
            # 리포트 추가
            report_data = conv_data["report"]
            report = ConversationReport(
                conversation_id=conversation.id,
                title=report_data["title"],
                summary=report_data["summary"],
                content=report_data["content"],
                detected_symptoms=report_data["detected_symptoms"],
                diseases_with_probabilities=report_data["diseases_with_probabilities"],
                health_suggestions=report_data["health_suggestions"],
                severity_level=report_data["severity_level"],
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
            )
            session.add(report)
            
            session.commit()
            print(f"리포트 추가: {report_data['title']} ({user_login_id})")
            
        print("목업 데이터 생성 완료!")

if __name__ == "__main__":
    print("목업 데이터 추가를 시작합니다...")
    seed_mock_data()
    print("목업 데이터 추가가 완료되었습니다!")
