#!/usr/bin/env python3
"""
김건강(kim123) 사용자 중심의 메딧 시연 데이터 스크립트
- 김건강 사용자에 초점을 맞춘 다양한 대화, 리포트, 가족 및 연락처 데이터 생성
- 시연에 적합한 풍부한 데이터셋 구성
"""
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

# 간단한 비밀번호 해싱 함수 (해커톤용)
def hash_password(password):
    return f"mock_hashed_{password}"

# 김건강 사용자 데이터
KIM_USER_DATA = {
    "login_id": "kim123",
    "nickname": "김건강",
    "age_range": "38세",
    "gender": "남성",
    "password": "password123",
    "usual_illness": ["고혈압", "당뇨병", "부정맥"]
}

# 김건강의 가족 구성원 데이터
KIM_FAMILY_DATA = [
    {
        "nickname": "김아버지",
        "relation": "아버지",
        "age": 65,
        "usual_illness": ["고혈압", "관절염", "당뇨병"]
    },
    {
        "nickname": "김어머니",
        "relation": "어머니",
        "age": 62,
        "usual_illness": ["갑상선기능저하증", "골다공증"]
    },
    {
        "nickname": "김아내",
        "relation": "배우자",
        "age": 35,
        "usual_illness": ["편두통", "알레르기성 비염"]
    },
    {
        "nickname": "김딸",
        "relation": "딸",
        "age": 10,
        "usual_illness": ["아토피 피부염"]
    },
    {
        "nickname": "김아들",
        "relation": "아들",
        "age": 7,
        "usual_illness": ["천식", "알레르기"]
    }
]

# 다른 사용자들 데이터 (간소화)
OTHER_USERS_DATA = [
    {
        "login_id": "park456",
        "nickname": "박의사",
        "age_range": "45세",
        "gender": "여성",
        "password": "password456",
        "usual_illness": []
    },
    {
        "login_id": "lee789",
        "nickname": "이헬스",
        "age_range": "40세",
        "gender": "남성",
        "password": "password789",
        "usual_illness": ["고지혈증"]
    },
    {
        "login_id": "choi101",
        "nickname": "최트레이너",
        "age_range": "32세",
        "gender": "여성",
        "password": "password101",
        "usual_illness": []
    }
]

# 김건강의 연락처 데이터
KIM_CONTACTS_DATA = [
    {
        "contact_login_id": "park456",
        "alias_nickname": "박주치의",
        "relation": "담당의사"
    },
    {
        "contact_login_id": "lee789",
        "alias_nickname": "이사촌",
        "relation": "친척"
    },
    {
        "contact_login_id": "choi101",
        "alias_nickname": "최PT",
        "relation": "헬스트레이너"
    }
]

# 김건강의 대화 데이터 (다양한 증상, 응급도 포함)
KIM_CONVERSATIONS_DATA = [
    # 1. 고혈압 관련 대화 (3일 전) - GREEN
    {
        "title": "혈압 관리 상담",
        "days_ago": 3,
        "messages": [
            {"sender": "user", "content": "요즘 혈압 조절이 잘 되는 것 같아요. 생활습관 개선이 효과가 있나봐요."},
            {"sender": "assistant", "content": "혈압은 어느 정도 측정되고 있나요?"},
            {"sender": "user", "content": "아침에 측정했을 때 130/85 정도로 안정적이에요."},
            {"sender": "assistant", "content": "생활습관 개선의 효과가 나타나고 있네요. 꾸준한 운동과 저염식이 유지하시는 것이 중요합니다."}
        ],
        "report": {
            "title": "혈압 안정화 확인",
            "summary": "생활습관 개선으로 혈압이 안정적으로 유지되는 상태",
            "content": "생활습관 개선을 통해 혈압이 130/85 수준으로 안정화됨. 지속적인 관리가 필요하며 현재 상태는 양호함.",
            "detected_symptoms": ["혈압 안정"],
            "diseases_with_probabilities": [
                {"name": "고혈압", "probability": 0.7}
            ],
            "health_suggestions": [
                "규칙적인 혈압 측정 유지",
                "저염식 식단 유지",
                "꾸준한 유산소 운동",
                "스트레스 관리"
            ],
            "severity_level": "green"
        }
    },
    
    # 2. 가슴 통증 (10일 전) - RED
    {
        "title": "급성 가슴 통증",
        "days_ago": 10,
        "messages": [
            {"sender": "user", "content": "갑자기 가슴이 너무 아프고 숨쉬기 힘들어요. 식은땀도 나고 왼쪽 팔도 저려요."},
            {"sender": "assistant", "content": "언제부터 증상이 시작되었나요? 통증의 강도는 어느 정도인가요?"},
            {"sender": "user", "content": "30분 전부터 시작됐고, 통증이 10점 만점에 8점 정도로 심해요."},
            {"sender": "assistant", "content": "심각한 증상으로 보입니다. 즉시 응급실에 방문하시기 바랍니다. 심장 관련 응급 상황일 수 있습니다."}
        ],
        "report": {
            "title": "급성 흉통 - 응급 상황",
            "summary": "급성 흉통, 호흡 곤란, 방사통 - 심장 관련 응급 의심",
            "content": "갑작스러운 심한 흉통(8/10), 호흡 곤란, 식은땀, 왼쪽 팔 저림 등의 증상. 심근경색 등 심장 관련 응급 상황 의심. 즉각적인 응급 처치 필요.",
            "detected_symptoms": ["심한 흉통", "호흡 곤란", "왼팔 방사통", "식은땀"],
            "diseases_with_probabilities": [
                {"name": "급성 심근경색", "probability": 0.8},
                {"name": "불안정 협심증", "probability": 0.75},
                {"name": "대동맥 박리", "probability": 0.4}
            ],
            "health_suggestions": [
                "즉시 응급실 방문",
                "구급차 호출 고려",
                "아스피린 복용 고려(의사 지시에 따라)",
                "안정 취하기"
            ],
            "severity_level": "red"
        }
    },
    
    # 3. 두통 (20일 전) - ORANGE
    {
        "title": "지속되는 두통",
        "days_ago": 20,
        "messages": [
            {"sender": "user", "content": "3일째 두통이 계속되고 있어요. 진통제를 먹어도 효과가 별로 없네요."},
            {"sender": "assistant", "content": "두통은 어느 부위에 있고, 어떤 성격의 통증인가요?"},
            {"sender": "user", "content": "머리 전체가 지끈지끈 아프고, 가끔은 욱신거리기도 해요. 통증은 6점 정도로 일상생활에 지장이 있어요."},
            {"sender": "assistant", "content": "지속되는 두통으로 보입니다. 휴식과 함께 병원 방문을 추천드립니다. 혈압과 관련이 있을 수 있습니다."}
        ],
        "report": {
            "title": "지속성 두통 분석",
            "summary": "3일 이상 지속된 중등도 두통, 일상생활 영향",
            "content": "3일 이상 지속된 두통으로 통증 강도 6/10, 진통제에 반응이 적음. 전두부 전체의 지속적인 압박성/박동성 통증. 고혈압과 연관 가능성 있음.",
            "detected_symptoms": ["지속성 두통", "진통제 저항성", "통증 강도 6/10"],
            "diseases_with_probabilities": [
                {"name": "긴장성 두통", "probability": 0.65},
                {"name": "고혈압성 두통", "probability": 0.55},
                {"name": "편두통", "probability": 0.4}
            ],
            "health_suggestions": [
                "신경과 전문의 상담",
                "혈압 측정",
                "충분한 휴식",
                "수분 섭취 늘리기",
                "스트레스 관리"
            ],
            "severity_level": "orange"
        }
    },
    
    # 4. 소화불량 (45일 전) - GREEN
    {
        "title": "식후 소화불량",
        "days_ago": 45,
        "messages": [
            {"sender": "user", "content": "요즘 식사 후에 속이 더부룩하고 소화가 잘 안돼요."},
            {"sender": "assistant", "content": "어떤 음식을 드신 후에 특히 증상이 심한가요?"},
            {"sender": "user", "content": "기름진 음식이나 과식했을 때 특히 심한 것 같아요."},
            {"sender": "assistant", "content": "소화불량 증상으로 보입니다. 식사량 조절과 천천히 먹는 습관이 도움이 될 수 있습니다."}
        ],
        "report": {
            "title": "소화불량 증상 분석",
            "summary": "식후 포만감, 더부룩함 등의 소화불량 증상",
            "content": "식후 더부룩함, 포만감 등의 소화불량 증상. 기름진 음식과 과식 후 증상 악화됨. 기능성 소화불량 의심.",
            "detected_symptoms": ["식후 더부룩함", "소화불량", "과식 후 증상 악화"],
            "diseases_with_probabilities": [
                {"name": "기능성 소화불량", "probability": 0.7},
                {"name": "위식도역류질환", "probability": 0.4}
            ],
            "health_suggestions": [
                "소량씩 자주 먹기",
                "천천히 식사하기",
                "기름진 음식 제한",
                "식후 바로 눕지 않기",
                "카페인 제한"
            ],
            "severity_level": "green"
        }
    },
    
    # 5. 관절통 (60일 전) - ORANGE
    {
        "title": "무릎 관절통",
        "days_ago": 60,
        "messages": [
            {"sender": "user", "content": "계단을 오르내릴 때 무릎이 많이 아파요. 특히 아침에 일어날 때 뻣뻣하고 통증이 있어요."},
            {"sender": "assistant", "content": "통증은 어느 정도이며, 붓거나 열이 나는 증상도 있나요?"},
            {"sender": "user", "content": "통증은 5~6점 정도이고, 약간 부어있는 것 같아요. 열은 없습니다."},
            {"sender": "assistant", "content": "관절염 초기 증상으로 보입니다. 적절한 휴식과 함께 정형외과 진료를 받아보시는 것이 좋겠습니다."}
        ],
        "report": {
            "title": "무릎 관절염 의심",
            "summary": "계단 오르내릴 때 악화되는 무릎 통증, 조조강직",
            "content": "계단 사용시 악화되는 무릎 통증(5-6/10), 아침 뻣뻣함(조조강직), 경미한 부종. 퇴행성 관절염 초기 증상 의심.",
            "detected_symptoms": ["무릎 통증", "조조강직", "활동시 통증 악화", "경미한 부종"],
            "diseases_with_probabilities": [
                {"name": "퇴행성 관절염", "probability": 0.75},
                {"name": "활액막염", "probability": 0.45}
            ],
            "health_suggestions": [
                "정형외과 진료",
                "체중 관리",
                "저충격 운동(수영, 자전거)",
                "무릎 보호대 사용 고려",
                "온찜질"
            ],
            "severity_level": "orange"
        }
    }
]

def seed_kim_data():
    """김건강 사용자 중심의 시연 데이터 생성"""
    with Session(engine) as session:
        # 1. 사용자 데이터 생성
        user_id_map = {}  # login_id -> user_id 매핑
        
        # 김건강 사용자 생성
        kim_data = KIM_USER_DATA
        existing_kim = session.exec(select(User).where(User.login_id == kim_data["login_id"])).first()
        
        if existing_kim:
            print(f"기존 김건강 사용자 업데이트")
            for key, value in kim_data.items():
                if key != "password" and hasattr(existing_kim, key):
                    setattr(existing_kim, key, value)
            kim_user = existing_kim
        else:
            print(f"김건강 사용자 생성")
            kim_user = User(
                login_id=kim_data["login_id"],
                nickname=kim_data["nickname"],
                age_range=kim_data["age_range"],
                gender=kim_data["gender"],
                usual_illness=kim_data["usual_illness"],
                hashed_password=hash_password(kim_data["password"])
            )
            session.add(kim_user)
        
        session.commit()
        session.refresh(kim_user)
        user_id_map[kim_data["login_id"]] = kim_user.id
        
        # 김건강 주변 사용자들 생성
        for user_data in OTHER_USERS_DATA:
            login_id = user_data["login_id"]
            existing_user = session.exec(select(User).where(User.login_id == login_id)).first()
            
            if existing_user:
                print(f"기존 사용자 업데이트: {login_id}")
                for key, value in user_data.items():
                    if key != "password" and hasattr(existing_user, key):
                        setattr(existing_user, key, value)
                user = existing_user
            else:
                print(f"사용자 생성: {login_id}")
                user = User(
                    login_id=login_id,
                    nickname=user_data["nickname"],
                    age_range=user_data["age_range"],
                    gender=user_data["gender"],
                    usual_illness=user_data.get("usual_illness", []),
                    hashed_password=hash_password(user_data["password"])
                )
                session.add(user)
            
            session.commit()
            session.refresh(user)
            user_id_map[login_id] = user.id
        
        # 2. 김건강의 가족 구성원 생성
        # 기존 가족 구성원 삭제
        existing_family = session.exec(
            select(FamilyMember).where(FamilyMember.user_id == kim_user.id)
        ).all()
        
        for family in existing_family:
            session.delete(family)
        session.commit()
        
        # 새 가족 구성원 추가
        for family_data in KIM_FAMILY_DATA:
            print(f"가족 구성원 추가: {family_data['nickname']} ({family_data['relation']})")
            family = FamilyMember(
                user_id=kim_user.id,
                nickname=family_data["nickname"],
                relation=family_data["relation"],
                age=family_data["age"],
                usual_illness=family_data.get("usual_illness", [])
            )
            session.add(family)
        
        session.commit()
        
        # 3. 김건강의 연락처 생성
        # 기존 연락처 삭제
        existing_contacts = session.exec(
            select(UserContact).where(UserContact.user_id == kim_user.id)
        ).all()
        
        for contact in existing_contacts:
            session.delete(contact)
        session.commit()
        
        # 새 연락처 추가
        for contact_data in KIM_CONTACTS_DATA:
            contact_user_id = user_id_map.get(contact_data["contact_login_id"])
            if not contact_user_id:
                continue
                
            print(f"연락처 추가: {contact_data['alias_nickname']} ({contact_data['relation']})")
            contact = UserContact(
                user_id=kim_user.id,
                contact_user_id=contact_user_id,
                alias_nickname=contact_data["alias_nickname"],
                relation=contact_data["relation"]
            )
            session.add(contact)
        
        session.commit()
        
        # 4. 김건강의 대화 및 리포트 생성
        # 기존 대화 및 리포트 삭제
        kim_conversations = session.exec(
            select(Conversation).where(Conversation.user_id == kim_user.id)
        ).all()
        
        for conv in kim_conversations:
            # 연결된 메시지 삭제
            messages = session.exec(
                select(ConversationMessage).where(ConversationMessage.conversation_id == conv.id)
            ).all()
            for msg in messages:
                session.delete(msg)
                
            # 연결된 리포트 삭제
            reports = session.exec(
                select(ConversationReport).where(ConversationReport.conversation_id == conv.id)
            ).all()
            for report in reports:
                session.delete(report)
                
            # 대화 자체 삭제
            session.delete(conv)
            
        session.commit()
        
        # 새 대화 및 리포트 추가
        for conv_data in KIM_CONVERSATIONS_DATA:
            now = datetime.utcnow()
            conversation_date = now - timedelta(days=conv_data["days_ago"])
            
            # 대화 생성
            conversation = Conversation(
                user_id=kim_user.id,
                title=conv_data["title"],
                started_at=conversation_date
            )
            session.add(conversation)
            session.commit()
            session.refresh(conversation)
            
            print(f"대화 추가: {conv_data['title']} (날짜: {conversation_date.strftime('%Y-%m-%d')})")
            
            # 메시지 추가
            for i, msg_data in enumerate(conv_data["messages"]):
                message_date = conversation_date + timedelta(minutes=i*5)  # 5분 간격으로 메시지
                message = ConversationMessage(
                    conversation_id=conversation.id,
                    sender=msg_data["sender"],
                    content=msg_data["content"],
                    sequence=i+1,
                    created_at=message_date
                )
                session.add(message)
            
            session.commit()
            
            # 리포트 추가
            report_data = conv_data["report"]
            report_date = conversation_date + timedelta(minutes=len(conv_data["messages"])*5 + 10)
            report = ConversationReport(
                conversation_id=conversation.id,
                title=report_data["title"],
                summary=report_data["summary"],
                content=report_data["content"],
                detected_symptoms=report_data["detected_symptoms"],
                diseases_with_probabilities=report_data["diseases_with_probabilities"],
                health_suggestions=report_data["health_suggestions"],
                severity_level=report_data["severity_level"],
                created_at=report_date
            )
            session.add(report)
            
            session.commit()
            print(f"리포트 추가: {report_data['title']} (응급도: {report_data['severity_level']})")
        
        print("\n김건강 사용자 중심 시연 데이터 생성 완료!")
        print(f"- 사용자: 김건강 (login_id: {KIM_USER_DATA['login_id']})")
        print(f"- 가족 구성원: {len(KIM_FAMILY_DATA)}명")
        print(f"- 연락처: {len(KIM_CONTACTS_DATA)}명")
        print(f"- 대화 및 리포트: {len(KIM_CONVERSATIONS_DATA)}개")
        print("\n각 리포트는 다양한 날짜(3일 전, 10일 전, 20일 전, 45일 전, 60일 전)와")
        print("다양한 응급도 수준(red, orange, green)을 포함하고 있습니다.")
        print("이제 김건강 사용자 중심으로 모든 기능을 시연할 준비가 되었습니다!")

if __name__ == "__main__":
    print("==== 김건강 사용자 중심 메딧 시연 데이터 세팅 ====")
    print("김건강과 관련된 기존 데이터를 재설정하고 시연용 데이터를 생성합니다...")
    seed_kim_data()
