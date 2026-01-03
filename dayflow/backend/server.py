from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
import jwt


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


class CompanySettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    company_name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CompanySettingsCreate(BaseModel):
    company_name: str

class Employee(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    login_id: str
    first_name: str
    last_name: str
    email: EmailStr
    password_hash: str
    year_of_joining: int
    serial_number: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True

class EmployeeSignup(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    year_of_joining: int

class EmployeeLogin(BaseModel):
    login_id: str
    password: str

class LoginIDPreview(BaseModel):
    login_id: str

class EmployeeResponse(BaseModel):
    id: str
    login_id: str
    first_name: str
    last_name: str
    email: str
    year_of_joining: int
    created_at: datetime
    is_active: bool

class AuthResponse(BaseModel):
    token: str
    employee: EmployeeResponse


def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_jwt_token(employee_id: str) -> str:
    expiration = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "employee_id": employee_id,
        "exp": expiration
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_jwt_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

async def get_current_employee(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_jwt_token(token)
    employee_id = payload.get("employee_id")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Employee not found")
    
    return Employee(**employee)

async def generate_login_id(first_name: str, last_name: str, year_of_joining: int) -> tuple[str, int]:
    company = await db.company_settings.find_one({}, {"_id": 0})
    if not company:
        raise HTTPException(status_code=400, detail="Company settings not configured. Please contact admin.")
    
    company_name = company["company_name"]
    cc = company_name[:2].upper()
    fn = first_name[:2].upper()
    ln = last_name[:2].upper()
    yyyy = str(year_of_joining)
    
    counter_doc = await db.login_id_counters.find_one({"year": year_of_joining})
    
    if counter_doc:
        serial_number = counter_doc["current_serial"] + 1
    else:
        serial_number = 1
    
    ssss = str(serial_number).zfill(4)
    login_id = f"{cc}{fn}{ln}{yyyy}{ssss}"
    
    return login_id, serial_number

async def increment_counter(year: int, serial_number: int):
    await db.login_id_counters.update_one(
        {"year": year},
        {"$set": {"current_serial": serial_number}},
        upsert=True
    )


@api_router.post("/company/setup", response_model=CompanySettings)
async def setup_company(input: CompanySettingsCreate):
    existing = await db.company_settings.find_one({})
    if existing:
        raise HTTPException(status_code=400, detail="Company already configured")
    
    company_obj = CompanySettings(**input.model_dump())
    doc = company_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.company_settings.insert_one(doc)
    return company_obj

@api_router.get("/company/settings", response_model=CompanySettings)
async def get_company_settings():
    company = await db.company_settings.find_one({}, {"_id": 0})
    if not company:
        raise HTTPException(status_code=404, detail="Company not configured")
    
    if isinstance(company['created_at'], str):
        company['created_at'] = datetime.fromisoformat(company['created_at'])
    
    return CompanySettings(**company)

@api_router.post("/auth/preview-login-id", response_model=LoginIDPreview)
async def preview_login_id(first_name: str, last_name: str, year_of_joining: int):
    if not first_name or not last_name or not year_of_joining:
        raise HTTPException(status_code=400, detail="All fields required")
    
    login_id, _ = await generate_login_id(first_name, last_name, year_of_joining)
    return LoginIDPreview(login_id=login_id)

@api_router.post("/auth/signup", response_model=AuthResponse)
async def signup_employee(input: EmployeeSignup):
    existing_email = await db.employees.find_one({"email": input.email})
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    login_id, serial_number = await generate_login_id(
        input.first_name,
        input.last_name,
        input.year_of_joining
    )
    
    existing_login_id = await db.employees.find_one({"login_id": login_id})
    if existing_login_id:
        raise HTTPException(status_code=400, detail="Login ID conflict. Please try again.")
    
    password_hash = hash_password(input.password)
    
    employee_data = {
        **input.model_dump(exclude={"password"}),
        "password_hash": password_hash,
        "login_id": login_id,
        "serial_number": serial_number
    }
    
    employee = Employee(**employee_data)
    doc = employee.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.employees.insert_one(doc)
    await increment_counter(input.year_of_joining, serial_number)
    
    token = create_jwt_token(employee.id)
    
    employee_response = EmployeeResponse(
        id=employee.id,
        login_id=employee.login_id,
        first_name=employee.first_name,
        last_name=employee.last_name,
        email=employee.email,
        year_of_joining=employee.year_of_joining,
        created_at=employee.created_at,
        is_active=employee.is_active
    )
    
    return AuthResponse(token=token, employee=employee_response)

@api_router.post("/auth/login", response_model=AuthResponse)
async def login_employee(input: EmployeeLogin):
    employee = await db.employees.find_one({"login_id": input.login_id.upper()}, {"_id": 0})
    
    if not employee:
        raise HTTPException(status_code=401, detail="Invalid login credentials")
    
    if not verify_password(input.password, employee["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid login credentials")
    
    if not employee.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is inactive")
    
    employee_obj = Employee(**employee)
    token = create_jwt_token(employee_obj.id)
    
    employee_response = EmployeeResponse(
        id=employee_obj.id,
        login_id=employee_obj.login_id,
        first_name=employee_obj.first_name,
        last_name=employee_obj.last_name,
        email=employee_obj.email,
        year_of_joining=employee_obj.year_of_joining,
        created_at=employee_obj.created_at,
        is_active=employee_obj.is_active
    )
    
    return AuthResponse(token=token, employee=employee_response)

@api_router.get("/auth/me", response_model=EmployeeResponse)
async def get_current_user(current_employee: Employee = Depends(get_current_employee)):
    return EmployeeResponse(
        id=current_employee.id,
        login_id=current_employee.login_id,
        first_name=current_employee.first_name,
        last_name=current_employee.last_name,
        email=current_employee.email,
        year_of_joining=current_employee.year_of_joining,
        created_at=current_employee.created_at,
        is_active=current_employee.is_active
    )

@api_router.get("/employees", response_model=List[EmployeeResponse])
async def get_all_employees(current_employee: Employee = Depends(get_current_employee)):
    employees = await db.employees.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    
    for emp in employees:
        if isinstance(emp['created_at'], str):
            emp['created_at'] = datetime.fromisoformat(emp['created_at'])
    
    return [EmployeeResponse(**emp) for emp in employees]

@api_router.get("/")
async def root():
    return {"message": "HRMS API is running"}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
