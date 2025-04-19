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
    
    # user_diseases 테이블이 존재하는지 확인하고 있으면 먼저 수동으로 삭제
    if 'user_diseases' in inspector.get_table_names():
        with engine.begin() as conn:
            conn.execute(sqlalchemy.text("DROP TABLE user_diseases CASCADE;"))
    
    # 다른 테이블들은 정상적으로 생성/재생성
    try:
        # CASCADE 옵션을 사용하거나 존재하지 않으면 넘어가기
        with engine.begin() as conn:
            # 존재하는 경우에만 테이블 드롭
            for table in reversed(SQLModel.metadata.sorted_tables):
                if table.name in inspector.get_table_names():
                    conn.execute(sqlalchemy.text(f"DROP TABLE {table.name} CASCADE;"))
        
        # 테이블 생성
        SQLModel.metadata.create_all(engine)
    except Exception as e:
        print(f"데이터베이스 초기화 중 오류 발생: {e}")
        # 오류가 발생해도 애플리케이션이 시작되도록 함
        # 실제 테이블은 이미 존재할 가능성이 높음


def get_session():
    """데이터베이스 세션을 생성하고 반환합니다."""
    with Session(engine) as session:
        yield session
