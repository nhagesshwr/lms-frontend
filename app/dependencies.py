from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Employee, RoleEnum
from app.auth import decode_token

security = HTTPBearer()  # ← this shows simple token box in Swagger

def get_current_employee(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Employee:
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    employee = db.query(Employee).filter(
        Employee.email == payload.get("sub")
    ).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee

def require_super_admin(current: Employee = Depends(get_current_employee)):
    if current.role != RoleEnum.super_admin:
        raise HTTPException(status_code=403, detail="Super admin access required")
    return current

def require_hr_admin(current: Employee = Depends(get_current_employee)):
    if current.role not in [RoleEnum.hr_admin, RoleEnum.super_admin]:
        raise HTTPException(status_code=403, detail="HR admin access required")
    return current

def require_manager(current: Employee = Depends(get_current_employee)):
    if current.role not in [RoleEnum.manager, RoleEnum.hr_admin, RoleEnum.super_admin]:
        raise HTTPException(status_code=403, detail="Manager access required")
    return current

def require_employee(current: Employee = Depends(get_current_employee)):
    return current