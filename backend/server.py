from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
import shutil
from fastapi.staticfiles import StaticFiles

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

UPLOADS_DIR = ROOT_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dayflow-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return {"user_id": user_id, "role": role, "must_change_password": payload.get("must_change_password", False)}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

async def get_admin_user(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "hr"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

class LoginRequest(BaseModel):
    login_id: str
    password: str

class LoginResponse(BaseModel):
    token: str
    role: str
    employee_id: str
    must_change_password: bool
    name: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class EmployeeCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    mobile: Optional[str] = None
    job_position: Optional[str] = None
    department: Optional[str] = None
    manager: Optional[str] = None
    location: Optional[str] = None
    date_of_birth: Optional[str] = None
    address: Optional[str] = None
    nationality: Optional[str] = None
    personal_email: Optional[str] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    date_of_joining: str
    monthly_wage: Optional[float] = 0
    base_salary: Optional[float] = 0
    hra: Optional[float] = 0
    standard_allowance: Optional[float] = 0
    performance_bonus: Optional[float] = 0
    travel_allowance: Optional[float] = 0
    pf_employee_percent: Optional[float] = 0
    pf_employer_percent: Optional[float] = 0
    tax_deductions: Optional[float] = 0
    role: str = "employee"

class EmployeeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    employee_id: str
    login_id: str
    first_name: str
    last_name: str
    email: str
    mobile: Optional[str] = None
    job_position: Optional[str] = None
    department: Optional[str] = None
    manager: Optional[str] = None
    location: Optional[str] = None
    date_of_birth: Optional[str] = None
    address: Optional[str] = None
    nationality: Optional[str] = None
    personal_email: Optional[str] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    date_of_joining: str
    role: str
    profile_image: Optional[str] = None
    status: str = "absent"
    monthly_wage: Optional[float] = None
    yearly_wage: Optional[float] = None
    base_salary: Optional[float] = None
    hra: Optional[float] = None
    standard_allowance: Optional[float] = None
    performance_bonus: Optional[float] = None
    travel_allowance: Optional[float] = None
    pf_employee_percent: Optional[float] = None
    pf_employer_percent: Optional[float] = None
    tax_deductions: Optional[float] = None

class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    mobile: Optional[str] = None
    address: Optional[str] = None
    date_of_birth: Optional[str] = None
    nationality: Optional[str] = None
    personal_email: Optional[str] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    job_position: Optional[str] = None
    department: Optional[str] = None
    manager: Optional[str] = None
    location: Optional[str] = None
    monthly_wage: Optional[float] = None
    base_salary: Optional[float] = None
    hra: Optional[float] = None
    standard_allowance: Optional[float] = None
    performance_bonus: Optional[float] = None
    travel_allowance: Optional[float] = None
    pf_employee_percent: Optional[float] = None
    pf_employer_percent: Optional[float] = None
    tax_deductions: Optional[float] = None

class AttendanceCreate(BaseModel):
    employee_id: str
    date: str
    check_in: Optional[str] = None
    check_out: Optional[str] = None

class AttendanceResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    attendance_id: str
    employee_id: str
    employee_name: str
    date: str
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    work_hours: Optional[float] = 0
    extra_hours: Optional[float] = 0

class LeaveCreate(BaseModel):
    employee_id: str
    leave_type: str
    start_date: str
    end_date: str
    allocation: int
    attachment: Optional[str] = None

class LeaveResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    leave_id: str
    employee_id: str
    employee_name: str
    leave_type: str
    start_date: str
    end_date: str
    allocation: int
    status: str
    attachment: Optional[str] = None
    created_at: str

class LeaveBalanceResponse(BaseModel):
    paid_time_off: int
    sick_leave: int
    unpaid_leave: int

async def generate_login_id(first_name: str, last_name: str, year: str) -> str:
    company_code = "DF"
    first_two = first_name[:2].upper()
    last_two = last_name[:2].upper()
    
    count = await db.employees.count_documents({"date_of_joining": {"$regex": f"^{year}"}})
    serial = str(count + 1).zfill(4)
    
    return f"{company_code}{first_two}{last_two}{year}{serial}"

@api_router.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    employee = await db.employees.find_one({"login_id": request.login_id}, {"_id": 0})
    
    if not employee or not verify_password(request.password, employee["password"]):
        raise HTTPException(status_code=401, detail="Invalid login credentials")
    
    access_token = create_access_token({
        "sub": employee["employee_id"],
        "role": employee["role"],
        "must_change_password": employee.get("must_change_password", False)
    })
    
    return LoginResponse(
        token=access_token,
        role=employee["role"],
        employee_id=employee["employee_id"],
        must_change_password=employee.get("must_change_password", False),
        name=f"{employee['first_name']} {employee['last_name']}"
    )

@api_router.post("/auth/change-password")
async def change_password(request: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    employee = await db.employees.find_one({"employee_id": current_user["user_id"]}, {"_id": 0})
    
    if not employee or not verify_password(request.old_password, employee["password"]):
        raise HTTPException(status_code=401, detail="Invalid old password")
    
    await db.employees.update_one(
        {"employee_id": current_user["user_id"]},
        {"$set": {"password": hash_password(request.new_password), "must_change_password": False}}
    )
    
    return {"message": "Password changed successfully"}

@api_router.post("/employees", response_model=EmployeeResponse)
async def create_employee(employee: EmployeeCreate, current_user: dict = Depends(get_admin_user)):
    year = employee.date_of_joining.split("-")[0]
    login_id = await generate_login_id(employee.first_name, employee.last_name, year)
    
    default_password = "Dayflow@123"
    employee_id = f"EMP{datetime.now(timezone.utc).timestamp()}".replace(".", "")
    
    yearly_wage = employee.monthly_wage * 12 if employee.monthly_wage else 0
    
    employee_doc = {
        "employee_id": employee_id,
        "login_id": login_id,
        "password": hash_password(default_password),
        "must_change_password": True,
        "first_name": employee.first_name,
        "last_name": employee.last_name,
        "email": employee.email,
        "mobile": employee.mobile,
        "job_position": employee.job_position,
        "department": employee.department,
        "manager": employee.manager,
        "location": employee.location,
        "date_of_birth": employee.date_of_birth,
        "address": employee.address,
        "nationality": employee.nationality,
        "personal_email": employee.personal_email,
        "gender": employee.gender,
        "marital_status": employee.marital_status,
        "date_of_joining": employee.date_of_joining,
        "role": employee.role,
        "status": "absent",
        "profile_image": None,
        "monthly_wage": employee.monthly_wage,
        "yearly_wage": yearly_wage,
        "base_salary": employee.base_salary,
        "hra": employee.hra,
        "standard_allowance": employee.standard_allowance,
        "performance_bonus": employee.performance_bonus,
        "travel_allowance": employee.travel_allowance,
        "pf_employee_percent": employee.pf_employee_percent,
        "pf_employer_percent": employee.pf_employer_percent,
        "tax_deductions": employee.tax_deductions,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.employees.insert_one(employee_doc)
    return EmployeeResponse(**employee_doc)

@api_router.get("/employees", response_model=List[EmployeeResponse])
async def get_employees(current_user: dict = Depends(get_current_user)):
    projection = {"_id": 0, "password": 0}
    
    if current_user["role"] not in ["admin", "hr"]:
        projection.update({
            "monthly_wage": 0,
            "yearly_wage": 0,
            "base_salary": 0,
            "hra": 0,
            "standard_allowance": 0,
            "performance_bonus": 0,
            "travel_allowance": 0,
            "pf_employee_percent": 0,
            "pf_employer_percent": 0,
            "tax_deductions": 0
        })
    
    employees = await db.employees.find({}, projection).to_list(1000)
    return [EmployeeResponse(**emp) for emp in employees]

@api_router.get("/employees/{employee_id}", response_model=EmployeeResponse)
async def get_employee(employee_id: str, current_user: dict = Depends(get_current_user)):
    projection = {"_id": 0, "password": 0}
    
    if current_user["role"] not in ["admin", "hr"] and current_user["user_id"] != employee_id:
        projection.update({
            "monthly_wage": 0,
            "yearly_wage": 0,
            "base_salary": 0,
            "hra": 0,
            "standard_allowance": 0,
            "performance_bonus": 0,
            "travel_allowance": 0,
            "pf_employee_percent": 0,
            "pf_employer_percent": 0,
            "tax_deductions": 0
        })
    
    employee = await db.employees.find_one({"employee_id": employee_id}, projection)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    return EmployeeResponse(**employee)

@api_router.put("/employees/{employee_id}", response_model=EmployeeResponse)
async def update_employee(employee_id: str, update: EmployeeUpdate, current_user: dict = Depends(get_current_user)):
    is_admin = current_user["role"] in ["admin", "hr"]
    
    if not is_admin and current_user["user_id"] != employee_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this profile")
    
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    
    if not is_admin:
        allowed_fields = ["mobile", "address", "date_of_birth", "nationality", "personal_email", "gender", "marital_status"]
        update_data = {k: v for k, v in update_data.items() if k in allowed_fields}
    else:
        if "monthly_wage" in update_data:
            update_data["yearly_wage"] = update_data["monthly_wage"] * 12
    
    if update_data:
        await db.employees.update_one({"employee_id": employee_id}, {"$set": update_data})
    
    return await get_employee(employee_id, current_user)

@api_router.post("/employees/{employee_id}/upload-image")
async def upload_profile_image(employee_id: str, file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "hr"] and current_user["user_id"] != employee_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    file_extension = file.filename.split(".")[-1]
    file_name = f"{employee_id}_profile.{file_extension}"
    file_path = UPLOADS_DIR / file_name
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    file_url = f"/uploads/{file_name}"
    await db.employees.update_one({"employee_id": employee_id}, {"$set": {"profile_image": file_url}})
    
    return {"url": file_url}

@api_router.post("/attendance", response_model=AttendanceResponse)
async def create_attendance(attendance: AttendanceCreate, current_user: dict = Depends(get_admin_user)):
    employee = await db.employees.find_one({"employee_id": attendance.employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    work_hours = 0
    extra_hours = 0
    
    if attendance.check_in and attendance.check_out:
        check_in_time = datetime.fromisoformat(attendance.check_in)
        check_out_time = datetime.fromisoformat(attendance.check_out)
        hours = (check_out_time - check_in_time).total_seconds() / 3600
        work_hours = min(hours, 9)
        extra_hours = max(0, hours - 9)
    
    attendance_id = f"ATT{datetime.now(timezone.utc).timestamp()}".replace(".", "")
    
    attendance_doc = {
        "attendance_id": attendance_id,
        "employee_id": attendance.employee_id,
        "employee_name": f"{employee['first_name']} {employee['last_name']}",
        "date": attendance.date,
        "check_in": attendance.check_in,
        "check_out": attendance.check_out,
        "work_hours": round(work_hours, 2),
        "extra_hours": round(extra_hours, 2),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.attendance.insert_one(attendance_doc)
    
    await db.employees.update_one({"employee_id": attendance.employee_id}, {"$set": {"status": "present"}})
    
    return AttendanceResponse(**attendance_doc)

@api_router.get("/attendance", response_model=List[AttendanceResponse])
async def get_attendance(employee_id: Optional[str] = None, month: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    query = {}
    
    if current_user["role"] not in ["admin", "hr"]:
        query["employee_id"] = current_user["user_id"]
    elif employee_id:
        query["employee_id"] = employee_id
    
    if month:
        query["date"] = {"$regex": f"^{month}"}
    
    attendance_records = await db.attendance.find(query, {"_id": 0}).sort("date", -1).to_list(1000)
    return [AttendanceResponse(**record) for record in attendance_records]

@api_router.post("/leaves", response_model=LeaveResponse)
async def create_leave(leave: LeaveCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "hr"] and current_user["user_id"] != leave.employee_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    employee = await db.employees.find_one({"employee_id": leave.employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    leave_id = f"LV{datetime.now(timezone.utc).timestamp()}".replace(".", "")
    
    leave_doc = {
        "leave_id": leave_id,
        "employee_id": leave.employee_id,
        "employee_name": f"{employee['first_name']} {employee['last_name']}",
        "leave_type": leave.leave_type,
        "start_date": leave.start_date,
        "end_date": leave.end_date,
        "allocation": leave.allocation,
        "status": "pending",
        "attachment": leave.attachment,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.leaves.insert_one(leave_doc)
    return LeaveResponse(**leave_doc)

@api_router.get("/leaves", response_model=List[LeaveResponse])
async def get_leaves(employee_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    query = {}
    
    if current_user["role"] not in ["admin", "hr"]:
        query["employee_id"] = current_user["user_id"]
    elif employee_id:
        query["employee_id"] = employee_id
    
    leaves = await db.leaves.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return [LeaveResponse(**leave) for leave in leaves]

@api_router.put("/leaves/{leave_id}/status")
async def update_leave_status(leave_id: str, status: str, current_user: dict = Depends(get_admin_user)):
    result = await db.leaves.update_one({"leave_id": leave_id}, {"$set": {"status": status}})
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    leave = await db.leaves.find_one({"leave_id": leave_id}, {"_id": 0})
    
    if status == "approved":
        await db.employees.update_one({"employee_id": leave["employee_id"]}, {"$set": {"status": "leave"}})
    
    return {"message": f"Leave request {status}"}

@api_router.get("/leaves/balance/{employee_id}", response_model=LeaveBalanceResponse)
async def get_leave_balance(employee_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "hr"] and current_user["user_id"] != employee_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    approved_leaves = await db.leaves.find(
        {"employee_id": employee_id, "status": "approved"},
        {"_id": 0}
    ).to_list(1000)
    
    paid_used = sum(l["allocation"] for l in approved_leaves if l["leave_type"] == "paid_time_off")
    sick_used = sum(l["allocation"] for l in approved_leaves if l["leave_type"] == "sick_leave")
    unpaid_used = sum(l["allocation"] for l in approved_leaves if l["leave_type"] == "unpaid_leave")
    
    return LeaveBalanceResponse(
        paid_time_off=24 - paid_used,
        sick_leave=7 - sick_used,
        unpaid_leave=0
    )

@api_router.post("/leaves/upload-attachment")
async def upload_leave_attachment(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    file_extension = file.filename.split(".")[-1]
    file_name = f"leave_{datetime.now(timezone.utc).timestamp()}.{file_extension}".replace(".", "_", 1)
    file_path = UPLOADS_DIR / file_name
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {"url": f"/uploads/{file_name}"}

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