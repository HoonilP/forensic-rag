from passlib.context import CryptContext
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import String

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Base(DeclarativeBase): pass
class Database:
    # def __init__(self, user, password, host, port, db) -> None:
    def __init__(self) -> None:
        # self.user = user
        # self.password = password
        # self.host = host
        # self.port = port
        # self.db = db

        # self.engine = create_engine(f"mysql+mysqlconnector://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}")
        self.engine = create_engine(f"sqlite+pysqlite:///:memory:", echo=True, future=True)
        Base.metadata.create_all(self.engine)
        
        self.session = Session(self.engine)
    
    # 데이터 저장
    def push_data(self, table:classmethod) -> None:
        self.session.add(table)

        try:
           self.session.commit()
        except Exception as err:
            self.session.rollback()
            print(err)

    # ID 중복 검사
    def check_id_duplication(self, user_id: str) -> bool:
        try:
          data = Session(self.engine).execute(select(User).where(User.id == user_id)).fetchall()

          if data:
             return True
          
          else:
             return False
             
        except Exception as err:
          return err

    # 비밀번호 검사
    def authenticate_user(self, user_id: str, plain_pw: str) -> bool:
        hashed_pw = Session(self.engine).execute(select(User.password).where(User.id == user_id)).fetchall()
        
        if pwd_context.verify(plain_pw, hashed_pw):
           return True
        
        else:
           return False

class User(Base):
    __tablename__ = 'user'
    id: Mapped[int] = mapped_column(String(50), primary_key=True)
    email: Mapped[str] = mapped_column(String(50))
    password: Mapped[str] = mapped_column(String(255))
    organization: Mapped[str] = mapped_column(String(30))

    def __repr__(self) -> str:
      return (
        f'User(id={self.id!r}, '
        f'email={self.email!r}, '
        f'password={self.password!r}, '
        f'organization={self.organization!r})'
      )

class Token(Base):
    access_token: str
    token_type: str