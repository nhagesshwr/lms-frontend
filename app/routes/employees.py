from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app.models import (
    Employee, RoleEnum, Message, Enrollment, Certificate,
    LessonProgress, PasswordResetToken, LiveClassEnrollment, LiveClassAudience
)
from app.schemas import EmployeeCreate, EmployeeUpdate, EmployeeResponse
from app.auth import hash_password
from app.dependencies import require_super_admin, require_hr_admin, require_manager, get_current_employee

router = APIRouter(prefix="/employees", tags=["Employees"])

# Only super admin can add employee
@router.post("/", response_model=EmployeeResponse)
def create_employee(
    employee: EmployeeCreate,
    db: Session = Depends(get_db),
    current=Depends(require_super_admin)
):
    existing = db.query(Employee).filter(Employee.email == employee.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")
    new_emp = Employee(
        name=employee.name,
        email=employee.email,
        hashed_password=hash_password(employee.password),
        role=employee.role,
        department_id=employee.department_id
    )
    db.add(new_emp)
    db.commit()
    db.refresh(new_emp)
    return new_emp

# Manager and above can view all employees
@router.get("/admins", response_model=list[EmployeeResponse])
def get_admin_users(
    db: Session = Depends(get_db),
    current=Depends(get_current_employee)
):
    """Return all super_admin and hr_admin users. Accessible by any logged-in user."""
    return db.query(Employee).filter(
        Employee.role.in_([RoleEnum.super_admin, RoleEnum.hr_admin])
    ).all()

# Manager and above can view all employees (active only)
@router.get("/", response_model=list[EmployeeResponse])
def get_all_employees(
    db: Session = Depends(get_db),
    current=Depends(require_manager)
):
    return db.query(Employee).filter(Employee.is_active == True).all()


# Get employees by department
@router.get("/department/{dept_id}", response_model=list[EmployeeResponse])
def get_employees_by_department(
    dept_id: int,
    db: Session = Depends(get_db),
    current=Depends(require_manager)
):
    employees = db.query(Employee).filter(
        Employee.department_id == dept_id
    ).all()
    if not employees:
        raise HTTPException(status_code=404, detail="No employees found in this department")
    return employees

# Get single employee
@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current=Depends(require_manager)
):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp

# Super admin can update employee role or department
@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: int,
    emp_update: EmployeeUpdate,
    db: Session = Depends(get_db),
    current=Depends(require_super_admin)
):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    if emp_update.name:
        emp.name = emp_update.name
    if emp_update.role:
        emp.role = emp_update.role
    if emp_update.department_id is not None:
        emp.department_id = emp_update.department_id
    if emp_update.is_active is not None:
        emp.is_active = emp_update.is_active
    db.commit()
    db.refresh(emp)
    return emp

# Super admin or HR admin can permanently delete an employee
@router.delete("/{employee_id}")
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current=Depends(require_hr_admin)
):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Prevent deleting yourself
    if emp.id == current.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")

    # Cascade-delete related data manually to avoid FK constraint errors
    # 1. Messages (sent and received)
    db.query(Message).filter(
        or_(Message.sender_id == employee_id, Message.receiver_id == employee_id)
    ).delete(synchronize_session=False)

    # 2. Lesson progress (via enrollments)
    enroll_ids = [e.id for e in db.query(Enrollment).filter(Enrollment.employee_id == employee_id).all()]
    if enroll_ids:
        db.query(LessonProgress).filter(
            LessonProgress.enrollment_id.in_(enroll_ids)
        ).delete(synchronize_session=False)

    # 3. Enrollments
    db.query(Enrollment).filter(Enrollment.employee_id == employee_id).delete(synchronize_session=False)

    # 4. Certificates
    db.query(Certificate).filter(Certificate.employee_id == employee_id).delete(synchronize_session=False)

    # 5. Password reset tokens
    db.query(PasswordResetToken).filter(PasswordResetToken.employee_id == employee_id).delete(synchronize_session=False)

    # 6. Live class enrollments
    db.query(LiveClassEnrollment).filter(LiveClassEnrollment.employee_id == employee_id).delete(synchronize_session=False)

    # 7. Live class audience entries
    db.query(LiveClassAudience).filter(LiveClassAudience.employee_id == employee_id).delete(synchronize_session=False)

    name = emp.name
    db.delete(emp)
    db.commit()
    return {"message": f"Employee '{name}' permanently deleted"}