from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from app.database import get_session, create_db_and_tables
from app.models import User, UserCreate, UserRead
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


@app.get("/")
def read_root():
    return {"message": "Welcome to Medit API"}


# User endpoints
@app.post("/users/", response_model=UserRead)
def create_user(user: UserCreate, session: Session = Depends(get_session)):
    # 간단한 사용자 생성 로직
    db_user = User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        hashed_password=user.password  # 일단 평문 그대로 저장 (보안상 좋지 않음)
    )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


@app.get("/users/", response_model=list[UserRead])
def read_users(
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100
):
    users = session.exec(select(User).offset(skip).limit(limit)).all()
    return users


@app.get("/users/{user_id}", response_model=UserRead)
def read_user(user_id: int, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
