from sqlmodel import SQLModel, Session, create_engine
from app.config import settings

# Create engine
engine = create_engine(settings.DATABASE_URL, echo=True)


def create_db_and_tables():
    """데이터베이스 테이블을 모델 정의에 따라 자동 생성합니다."""
    # 기존 테이블 삭제 후 재생성 (개발 환경에서만 사용)
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


def get_session():
    """데이터베이스 세션을 생성하고 반환합니다."""
    with Session(engine) as session:
        yield session
