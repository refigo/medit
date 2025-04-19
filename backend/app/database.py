from sqlmodel import SQLModel, Session, create_engine
from app.config import settings
import sqlalchemy

# Create engine
engine = create_engine(settings.DATABASE_URL, echo=True)


def create_db_and_tables():
    """데이터베이스 테이블을 모델 정의에 따라 자동 생성합니다."""
    # 개발 환경에서는 직접 테이블 생성
    # 주의: 프로덕션 환경에서는 Alembic 등을 사용한 마이그레이션 권장
    
    # 테이블 존재 확인을 위한 인스펙션
    inspector = sqlalchemy.inspect(engine)
    existing_tables = inspector.get_table_names()
    
    try:
        # 테이블이 존재하지 않는 경우에만 생성
        # 기존 테이블은 유지하여 데이터 보존
        if not existing_tables:
            # 데이터베이스가 완전히 비어있을 때만 모든 테이블 생성
            print("데이터베이스가 비어있습니다. 모든 테이블을 생성합니다.")
            SQLModel.metadata.create_all(engine)
        else:
            # 누락된 테이블만 생성
            for table in SQLModel.metadata.sorted_tables:
                if table.name not in existing_tables:
                    print(f"테이블 생성: {table.name}")
                    table.create(engine)
            print("기존 테이블 유지, 누락된 테이블만 생성합니다.")
    except Exception as e:
        print(f"데이터베이스 초기화 중 오류 발생: {e}")
        # 오류가 발생해도 애플리케이션이 시작되도록 함
    
    print(f"데이터베이스 초기화 완료. 현재 테이블: {', '.join(inspector.get_table_names())}")


def get_session():
    """데이터베이스 세션을 생성하고 반환합니다."""
    with Session(engine) as session:
        yield session
