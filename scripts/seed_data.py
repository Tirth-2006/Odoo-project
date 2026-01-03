import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).parent.parent / "backend"
load_dotenv(ROOT_DIR / '.env')

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def seed_database():
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    print("Clearing existing data...")
    await db.employees.delete_many({})
    await db.attendance.delete_many({})
    await db.leaves.delete_many({})
    
    print("Creating admin user...")
    admin = {
        "employee_id": "EMP001",
        "login_id": "DFJODO20220001",
        "password": pwd_context.hash("admin123"),
        "must_change_password": False,
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@dayflow.com",
        "mobile": "+1234567890",
        "job_position": "HR Manager",
        "department": "Human Resources",
        "manager": None,
        "location": "New York",
        "date_of_birth": "1985-05-15",
        "address": "123 Main St, New York, NY",
        "nationality": "USA",
        "personal_email": "john.doe@gmail.com",
        "gender": "Male",
        "marital_status": "Married",
        "date_of_joining": "2022-01-15",
        "role": "admin",
        "status": "present",
        "profile_image": None,
        "monthly_wage": 80000,
        "yearly_wage": 960000,
        "base_salary": 60000,
        "hra": 10000,
        "standard_allowance": 5000,
        "performance_bonus": 3000,
        "travel_allowance": 2000,
        "pf_employee_percent": 12,
        "pf_employer_percent": 12,
        "tax_deductions": 15000,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.employees.insert_one(admin)
    print(f"Admin created: {admin['login_id']} / password: admin123")
    
    print("Creating sample employees...")
    employees = [
        {
            "employee_id": "EMP002",
            "login_id": "DFANSA20230001",
            "password": pwd_context.hash("Dayflow@123"),
            "must_change_password": True,
            "first_name": "Alice",
            "last_name": "Smith",
            "email": "alice.smith@dayflow.com",
            "mobile": "+1234567891",
            "job_position": "Software Engineer",
            "department": "Engineering",
            "manager": "John Doe",
            "location": "New York",
            "date_of_birth": "1990-08-20",
            "address": "456 Tech Ave, New York, NY",
            "nationality": "USA",
            "personal_email": "alice.smith@gmail.com",
            "gender": "Female",
            "marital_status": "Single",
            "date_of_joining": "2023-03-10",
            "role": "employee",
            "status": "present",
            "profile_image": None,
            "monthly_wage": 65000,
            "yearly_wage": 780000,
            "base_salary": 50000,
            "hra": 8000,
            "standard_allowance": 4000,
            "performance_bonus": 2000,
            "travel_allowance": 1000,
            "pf_employee_percent": 12,
            "pf_employer_percent": 12,
            "tax_deductions": 12000,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "employee_id": "EMP003",
            "login_id": "DFBOJO20230002",
            "password": pwd_context.hash("Dayflow@123"),
            "must_change_password": True,
            "first_name": "Bob",
            "last_name": "Johnson",
            "email": "bob.johnson@dayflow.com",
            "mobile": "+1234567892",
            "job_position": "UI/UX Designer",
            "department": "Design",
            "manager": "John Doe",
            "location": "San Francisco",
            "date_of_birth": "1992-03-12",
            "address": "789 Design Blvd, SF, CA",
            "nationality": "USA",
            "personal_email": "bob.johnson@gmail.com",
            "gender": "Male",
            "marital_status": "Single",
            "date_of_joining": "2023-06-01",
            "role": "employee",
            "status": "leave",
            "profile_image": None,
            "monthly_wage": 55000,
            "yearly_wage": 660000,
            "base_salary": 45000,
            "hra": 5000,
            "standard_allowance": 3000,
            "performance_bonus": 1500,
            "travel_allowance": 500,
            "pf_employee_percent": 12,
            "pf_employer_percent": 12,
            "tax_deductions": 10000,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "employee_id": "EMP004",
            "login_id": "DFCAWI20240001",
            "password": pwd_context.hash("Dayflow@123"),
            "must_change_password": True,
            "first_name": "Carol",
            "last_name": "Williams",
            "email": "carol.williams@dayflow.com",
            "mobile": "+1234567893",
            "job_position": "Product Manager",
            "department": "Product",
            "manager": "John Doe",
            "location": "New York",
            "date_of_birth": "1988-11-25",
            "address": "321 Product Lane, NY, NY",
            "nationality": "USA",
            "personal_email": "carol.williams@gmail.com",
            "gender": "Female",
            "marital_status": "Married",
            "date_of_joining": "2024-01-15",
            "role": "employee",
            "status": "absent",
            "profile_image": None,
            "monthly_wage": 75000,
            "yearly_wage": 900000,
            "base_salary": 60000,
            "hra": 8000,
            "standard_allowance": 4000,
            "performance_bonus": 2500,
            "travel_allowance": 500,
            "pf_employee_percent": 12,
            "pf_employer_percent": 12,
            "tax_deductions": 14000,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    await db.employees.insert_many(employees)
    print(f"Created {len(employees)} sample employees")
    
    print("Creating sample attendance records...")
    attendance_records = [
        {
            "attendance_id": "ATT001",
            "employee_id": "EMP001",
            "employee_name": "John Doe",
            "date": "2025-01-15",
            "check_in": "2025-01-15T09:00:00",
            "check_out": "2025-01-15T18:00:00",
            "work_hours": 9.0,
            "extra_hours": 0.0,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "attendance_id": "ATT002",
            "employee_id": "EMP002",
            "employee_name": "Alice Smith",
            "date": "2025-01-15",
            "check_in": "2025-01-15T09:30:00",
            "check_out": "2025-01-15T19:00:00",
            "work_hours": 9.0,
            "extra_hours": 0.5,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    await db.attendance.insert_many(attendance_records)
    print(f"Created {len(attendance_records)} attendance records")
    
    print("Creating sample leave requests...")
    leave_requests = [
        {
            "leave_id": "LV001",
            "employee_id": "EMP003",
            "employee_name": "Bob Johnson",
            "leave_type": "paid_time_off",
            "start_date": "2025-01-20",
            "end_date": "2025-01-22",
            "allocation": 3,
            "status": "approved",
            "attachment": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "leave_id": "LV002",
            "employee_id": "EMP002",
            "employee_name": "Alice Smith",
            "leave_type": "sick_leave",
            "start_date": "2025-01-10",
            "end_date": "2025-01-11",
            "allocation": 2,
            "status": "pending",
            "attachment": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    await db.leaves.insert_many(leave_requests)
    print(f"Created {len(leave_requests)} leave requests")
    
    print("\n✅ Database seeded successfully!")
    print("\nLogin credentials:")
    print("Admin: DFJODO20220001 / admin123")
    print("Employee: DFANSA20230001 / Dayflow@123")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_database())
