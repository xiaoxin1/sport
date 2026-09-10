import os
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Optional
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, Date, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sfls.db")
JWT_SECRET = os.getenv("JWT_SECRET", "development-only-secret")
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)
security = HTTPBearer()

class Base(DeclarativeBase): pass
class Gender(str, Enum):
    male = "男"; female = "女"; mixed = "混合"
class ProjectType(str, Enum):
    individual = "个人"; team = "团队"
class Admin(Base):
    __tablename__ = "admins"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
class SchoolYear(Base):
    __tablename__ = "school_years"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(20), unique=True)
    sports_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    sports_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
class Event(Base):
    __tablename__ = "events"
    __table_args__ = (UniqueConstraint("school_year_id", "name", "grade_group", "gender", name="uq_event_key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    school_year_id: Mapped[int] = mapped_column(ForeignKey("school_years.id"))
    name: Mapped[str] = mapped_column(String(100))
    grade_group: Mapped[str] = mapped_column(String(50))
    gender: Mapped[Gender] = mapped_column(SAEnum(Gender))
    max_teams: Mapped[int] = mapped_column(Integer, default=0)
    final_teams: Mapped[int] = mapped_column(Integer, default=6)
    project_type: Mapped[ProjectType] = mapped_column(SAEnum(ProjectType), default=ProjectType.individual)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
class Registration(Base):
    __tablename__ = "registrations"
    id: Mapped[int] = mapped_column(primary_key=True)
    school_year_id: Mapped[int] = mapped_column(ForeignKey("school_years.id"))
    grade: Mapped[str] = mapped_column(String(30)); class_name: Mapped[str] = mapped_column(String(30)); leader_name: Mapped[str] = mapped_column(String(50)); student_name: Mapped[str] = mapped_column(String(50))
    gender: Mapped[Gender] = mapped_column(SAEnum(Gender)); event_id: Mapped[Optional[int]] = mapped_column(ForeignKey("events.id"), nullable=True); bib_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    event: Mapped[Optional[Event]] = relationship()
class ScheduleItem(Base):
    __tablename__ = "schedule_items"
    id: Mapped[int] = mapped_column(primary_key=True); school_year_id: Mapped[int] = mapped_column(ForeignKey("school_years.id")); event_id: Mapped[int] = mapped_column(ForeignKey("events.id")); stage: Mapped[str] = mapped_column(String(20)); start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True); venue: Mapped[Optional[str]] = mapped_column(String(100), nullable=True); groups: Mapped[int] = mapped_column(Integer, default=1)

Base.metadata.create_all(bind=engine)
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()
def auth(c: HTTPAuthorizationCredentials = Depends(security)):
    try: return jwt.decode(c.credentials, JWT_SECRET, algorithms=["HS256"])["sub"]
    except JWTError: raise HTTPException(status_code=401, detail="登录已失效")
class LoginIn(BaseModel): username: str; password: str
class YearIn(BaseModel): name: str = Field(min_length=1, max_length=50); sports_start: Optional[date] = None; sports_end: Optional[date] = None; is_current: bool = False
class EventIn(BaseModel): name: str; grade_group: str; gender: Gender; max_teams: int = Field(ge=0); final_teams: int = Field(ge=1); project_type: ProjectType; description: Optional[str] = None
class RegistrationIn(BaseModel): grade: str; class_name: str; leader_name: str; student_name: str; gender: Gender; event_id: Optional[int] = None
class Out(BaseModel): model_config = ConfigDict(from_attributes=True)
class YearOut(Out): id: int; name: str; sports_start: Optional[date]; sports_end: Optional[date]; is_current: bool
class EventOut(Out): id: int; school_year_id: int; name: str; grade_group: str; gender: Gender; max_teams: int; final_teams: int; project_type: ProjectType; description: Optional[str]
class RegistrationOut(Out): id: int; school_year_id: int; grade: str; class_name: str; leader_name: str; student_name: str; gender: Gender; event_id: Optional[int]; bib_number: Optional[int]
app = FastAPI(title="SFLS Sports Meet API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
@app.on_event("startup")
def seed_admin():
    with SessionLocal() as db:
        username = os.getenv("ADMIN_USERNAME", "admin")
        if not db.query(Admin).filter_by(username=username).first(): db.add(Admin(username=username, password_hash=pwd.hash(os.getenv("ADMIN_PASSWORD", "SFLS2026!")))); db.commit()
@app.get("/api/health")
def health(): return {"status":"ok"}
@app.post("/api/auth/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user=db.query(Admin).filter_by(username=data.username).first()
    if not user or not pwd.verify(data.password,user.password_hash): raise HTTPException(401,"账号或密码错误")
    return {"access_token":jwt.encode({"sub":user.username,"exp":datetime.now(timezone.utc)+timedelta(hours=12)},JWT_SECRET,algorithm="HS256")}
@app.get("/api/years",response_model=list[YearOut])
def years(_:str=Depends(auth),db:Session=Depends(get_db)): return db.query(SchoolYear).order_by(SchoolYear.name.desc()).all()
@app.post("/api/years",response_model=YearOut)
def create_year(data:YearIn,_:str=Depends(auth),db:Session=Depends(get_db)):
    if data.is_current: db.query(SchoolYear).update({SchoolYear.is_current:False})
    obj=SchoolYear(**data.model_dump()); db.add(obj)
    try: db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(400,"该学年已存在")
    db.refresh(obj); return obj
@app.patch("/api/years/{year_id}",response_model=YearOut)
def update_year(year_id:int,data:YearIn,_:str=Depends(auth),db:Session=Depends(get_db)):
    obj=db.get(SchoolYear,year_id)
    if not obj: raise HTTPException(404,"学年不存在")
    if data.is_current: db.query(SchoolYear).update({SchoolYear.is_current:False})
    for key,value in data.model_dump().items(): setattr(obj,key,value)
    try: db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(400,"该学年已存在")
    db.refresh(obj); return obj
@app.get("/api/events",response_model=list[EventOut])
def events(year_id:int,_:str=Depends(auth),db:Session=Depends(get_db)): return db.query(Event).filter_by(school_year_id=year_id).order_by(Event.grade_group,Event.name).all()
@app.post("/api/events",response_model=EventOut)
def create_event(year_id:int,data:EventIn,_:str=Depends(auth),db:Session=Depends(get_db)):
    obj=Event(school_year_id=year_id,**data.model_dump()); db.add(obj)
    try: db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(400,"同学年下项目名称、组别和性别不可重复")
    db.refresh(obj); return obj
@app.delete("/api/events/{event_id}")
def delete_event(event_id:int,_:str=Depends(auth),db:Session=Depends(get_db)):
    obj=db.get(Event,event_id)
    if not obj: raise HTTPException(404,"项目不存在")
    db.delete(obj); db.commit(); return {"ok":True}
@app.get("/api/registrations",response_model=list[RegistrationOut])
def registrations(year_id:int,_:str=Depends(auth),db:Session=Depends(get_db)): return db.query(Registration).filter_by(school_year_id=year_id).order_by(Registration.grade,Registration.class_name,Registration.gender).all()
@app.post("/api/registrations",response_model=RegistrationOut)
def create_registration(year_id:int,data:RegistrationIn,_:str=Depends(auth),db:Session=Depends(get_db)):
    count=db.query(Registration).filter_by(school_year_id=year_id,grade=data.grade,class_name=data.class_name,gender=data.gender).count()
    if count>=10: raise HTTPException(400,"同一班级同性别报名人数不能超过10人")
    obj=Registration(school_year_id=year_id,**data.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj
@app.post("/api/registrations/generate-bibs")
def generate_bibs(year_id:int,_:str=Depends(auth),db:Session=Depends(get_db)):
    rows=db.query(Registration).filter_by(school_year_id=year_id).order_by(Registration.grade,Registration.class_name,Registration.gender,Registration.id).all(); classes=sorted({(x.grade,x.class_name) for x in rows}); starts={(g,c):301+i*20 for i,(g,c) in enumerate(classes)}
    for gender in [Gender.male,Gender.female]:
        grouped={}
        for r in rows:
            if r.gender==gender: grouped.setdefault((r.grade,r.class_name),[]).append(r)
        for key,students in grouped.items():
            for i,r in enumerate(students): r.bib_number=starts[key]+(10 if gender==Gender.female else 0)+i
    db.commit(); return {"classes":len(classes),"message":"号码已生成"}
@app.get("/api/dashboard")
def dashboard(year_id:int,_:str=Depends(auth),db:Session=Depends(get_db)): return {"events":db.query(Event).filter_by(school_year_id=year_id).count(),"registrations":db.query(Registration).filter_by(school_year_id=year_id).count(),"schedule_items":db.query(ScheduleItem).filter_by(school_year_id=year_id).count()}
