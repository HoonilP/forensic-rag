from datetime import datetime
from passlib.context import CryptContext
from sqlalchemy import create_engine, select, ForeignKey, DateTime, Enum
from sqlalchemy.orm import Session, DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import String
from sqlalchemy import Integer, Sequence
from pydantic import BaseModel
from enum import Enum as PyEnum

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Base(DeclarativeBase): 
    pass

class User(Base):
    __tablename__ = 'user'  
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(50), unique=True)
    password: Mapped[str] = mapped_column(String(255))
    organization: Mapped[str] = mapped_column(String(30))
    computers: Mapped[list['Computer']] = relationship("Computer", back_populates="user")

    def __repr__(self) -> str:  
        return (
            f'User(id={self.id!r}, '
            f'email={self.email!r}, '
            f'password={self.password!r}, '
            f'organization={self.organization!r})'
        )
class Computer(Base):
    __tablename__='computer'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))
    user: Mapped[User] = relationship("User", back_populates="computers")
    tasks: Mapped[list['Task']] = relationship("Task", back_populates="computer")

class TaskType(PyEnum):
    Prefetch= "Prefetch"
    Application = "Application"
    Security = "Security"
    Forwarded = "Forwarded"
    Setup = "Setup"
    System = "System"

class Task(Base):
    __tablename__='task'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    computer_id: Mapped[int] = mapped_column(Integer, ForeignKey('computer.id'))
    analysis_result: Mapped[str] = mapped_column(String(255), nullable=True)
    visualization_chart1: Mapped[str] = mapped_column(String(255), nullable=True)
    visualization_chart2: Mapped[str] = mapped_column(String(255), nullable=True)
    visualization_chart3: Mapped[str] = mapped_column(String(255), nullable=True)
    visualization_chart4: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    # Enum 타입 추가
    task_type: Mapped[TaskType] = mapped_column(Enum(TaskType), nullable=False)
    computer: Mapped[Computer] = relationship("Computer", back_populates="tasks")




class Token(BaseModel): 
    access_token: str
    token_type: str
    refresh_token: str

class Database:
    def __init__(self) -> None:
        self.engine = create_engine('postgresql://postgres:postgres@localhost/rag', echo=True, future=True)
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
    
    # 데이터 저장
    def push_data(self, table: classmethod) -> None:
        self.session.add(table)

        try:
            self.session.commit()
        except Exception as err:
            self.session.rollback()
            print(err)

    # ID 중복 검사
    # 이메일 중복 검사
    def check_email_duplication(self, email: str) -> bool:
        try:
            data = self.session.execute(select(User).where(User.email == email)).fetchall()
            return bool(data)  # 중복 여부 반환
        except Exception as err:
            print(err)
            return False


    # 비밀번호 검사
    def authenticate_user(self, email: str, plain_pw: str) -> bool:
        hashed_pw = self.session.execute(select(User.password).where(User.email == email)).fetchone()
        
        if hashed_pw and pwd_context.verify(plain_pw, hashed_pw[0]):
            return True
        else:
            return False
        
class TaskRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_task(self, task: Task) -> Task:
        self.session.add(task)
        self.session.commit()
        return task

    def get_task(self, task_id: int) -> Task:
        task = self.session.execute(select(Task).where(Task.id == task_id)).scalar_one_or_none()
        return task

    def update_task(self, task_id: int, task_update: Task) -> Task:
        task = self.get_task(task_id)
        if task:
            task.analysis_result = task_update.analysis_result
            task.visualization_chart1 = task_update.visualization_chart1
            task.visualization_chart2 = task_update.visualization_chart2
            task.visualization_chart3 = task_update.visualization_chart3
            task.visualization_chart4 = task_update.visualization_chart4
            self.session.commit()
            return task
        return None
 
    def delete_task(self, task_id: int) -> bool:
        task = self.get_task(task_id)
        if task:
            self.session.delete(task)
            self.session.commit()
            return True
        return False
    
class ComputerRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_computer(self, computer: Computer) -> Computer:
        self.session.add(computer)
        self.session.commit()
        return computer

    def get_computer(self, computer_id: int) -> Computer:
        computer = self.session.execute(select(Computer).where(Computer.id == computer_id)).scalar_one_or_none()
        return computer

    def update_computer(self, computer_id: int, computer_update: Computer) -> Computer:
        computer = self.get_computer(computer_id)
        if computer:
            computer.name = computer_update.name
            computer.user_id = computer_update.user_id
            self.session.commit()
            return computer
        return None

    def delete_computer(self, computer_id: int) -> bool:
        computer = self.get_computer(computer_id)
        if computer:
            self.session.delete(computer)
            self.session.commit()
            return True
        return False

    def get_all_computers(self) -> list[Computer]:
        return self.session.execute(select(Computer)).scalars().all()
    
    def get_computer_tasks(self, computer_id: int) -> list[Task]:
        # 특정 컴퓨터에 대한 모든 태스크를 가져옵니다.
        tasks = self.session.execute(select(Task).where(Task.computer_id == computer_id)).scalars().all()
        return tasks
    

class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_user(self, user: User) -> User:
        self.session.add(user)
        self.session.commit()
        return user

    def get_user(self, user_id: int) -> User:
        user =  self.session.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        return user
    
    def get_user_by_email(self, email: str) -> User:
        user =  self.session.execute(select(User).where(User.email == email)).scalar_one_or_none()
        return user

    def update_user(self, user_id: int, user_update: User) -> User:
        user = self.get_user(user_id)
        if user:
            user.email = user_update.email
            user.password = user_update.password
            user.organization = user_update.organization
            self.session.commit()
            return user
        return None

    def delete_user(self, user_id: int) -> bool:
        user =  self.get_user(user_id)
        if user:
            self.session.delete(user)
            self.session.commit()
            return True
        return False

    def get_all_users(self) -> list[User]:
        return self.session.execute(select(User)).scalars().all()

