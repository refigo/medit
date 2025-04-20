#!/usr/bin/env python3
"""
메딧(Medit) 데이터베이스 초기화 및 시연 데이터 세팅 스크립트
- 기존 데이터베이스의 모든 테이블 내용을 지우고
- 질병 정보, 사용자, 가족 구성원, 대화 및 리포트 시연 데이터를 생성합니다.
"""
import sys
from sqlmodel import Session, select, SQLModel
from sqlalchemy import text
from app.database import engine
from app.models import (
    User, FamilyMember, UserContact, 
    Conversation, ConversationMessage, 
    ConversationReport, Disease
)

# seed_diseases.py 및 seed_mock_users.py의 함수 임포트
from seed_diseases import seed_diseases
from seed_mock_users import seed_mock_data

def reset_db():
    """모든 테이블의 데이터를 초기화합니다."""
    with Session(engine) as session:
        # 테이블 간의 외래 키 제약 조건을 일시적으로 비활성화
        session.execute(text("SET CONSTRAINTS ALL DEFERRED"))
        
        # 테이블 비우기 (순서 중요: 외래 키 제약 조건 때문)
        print("테이블 데이터 초기화 중...")
        
        # 1. 대화 리포트 삭제
        session.execute(text("DELETE FROM conversation_reports"))
        print("- conversation_reports 테이블 초기화 완료")
        
        # 2. 대화 메시지 삭제
        session.execute(text("DELETE FROM conversation_messages"))
        print("- conversation_messages 테이블 초기화 완료")
        
        # 3. 대화 삭제
        session.execute(text("DELETE FROM conversations"))
        print("- conversations 테이블 초기화 완료")
        
        # 4. 연락처 삭제
        session.execute(text("DELETE FROM user_contacts"))
        print("- user_contacts 테이블 초기화 완료")
        
        # 5. 가족 구성원 삭제
        session.execute(text("DELETE FROM family_members"))
        print("- family_members 테이블 초기화 완료")
        
        # 6. 사용자 삭제
        session.execute(text("DELETE FROM users"))
        print("- users 테이블 초기화 완료")
        
        # 7. 질병 정보 삭제
        session.execute(text("DELETE FROM diseases"))
        print("- diseases 테이블 초기화 완료")
        
        # 시퀀스 초기화 (ID가 자동 증가하는 경우)
        session.execute(text("ALTER SEQUENCE IF EXISTS diseases_id_seq RESTART WITH 1"))
        
        # 변경사항 커밋
        session.commit()
        print("모든 테이블 초기화 완료!")

def main():
    """DB 초기화 및 시연 데이터 생성"""
    print("==== 메딧(Medit) 데이터베이스 초기화 및 시연 데이터 세팅 ====")
    
    # 확인 메시지
    response = input("⚠️ 주의: 이 작업은 모든 기존 데이터를 삭제합니다. 계속하시겠습니까? (y/n): ")
    if response.lower() != 'y':
        print("작업이 취소되었습니다.")
        sys.exit(0)
    
    # 1. 데이터베이스 초기화
    reset_db()
    
    # 2. 질병 데이터 생성
    print("\n질병 데이터 생성 중...")
    seed_diseases()
    
    # 3. 사용자, 가족, 연락처, 대화, 리포트 데이터 생성
    print("\n사용자 및 관련 데이터 생성 중...")
    seed_mock_data()
    
    print("\n==== 시연 데이터 세팅 완료! ====")
    print("이제 다음 데이터가 준비되었습니다:")
    print("- 20개의 질병 정보")
    print("- 5명의 사용자와 그들의 가족 구성원")
    print("- 사용자 간 연락처 관계")
    print("- 각 사용자별 대화 및 건강 리포트")
    print("\n메딧 앱을 시연할 준비가 되었습니다!")

if __name__ == "__main__":
    main()
