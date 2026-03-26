from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Employee, RoleEnum
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
@router.get("/", response_model=list[EmployeeResponse])
def get_all_employees(
    db: Session = Depends(get_db),
    current=Depends(require_manager)
):
    return db.query(Employee).all()

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

# Super admin can deactivate employee
@router.delete("/{employee_id}")
def deactivate_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current=Depends(require_super_admin)
):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    emp.is_active = False
    db.commit()
    return {"message": f"Employee '{emp.name}' deactivated"}