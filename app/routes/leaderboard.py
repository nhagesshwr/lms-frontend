from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Enrollment, Employee, Department
from app.dependencies import require_employee

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])

@router.get("/")
def get_leaderboard(db: Session = Depends(get_db)):
    # Calculate leaderboard based on progress_pct
    # Sum of progress divided by enrolled courses (or just sum for XP)
    results = db.query(
        Employee.id,
        Employee.name,
        Department.name.label("department"),
        func.sum(Enrollment.progress_pct).label("total_progress"),
        func.count(Enrollment.id).label("courses")
    ).join(Enrollment, Employee.id == Enrollment.employee_id)\
     .outerjoin(Department, Employee.department_id == Department.id)\
     .group_by(Employee.id, Department.name)\
     .order_by(func.sum(Enrollment.progress_pct).desc())\
     .limit(50).all()

    return [
        {
            "rank": i + 1,
            "id": r.id,
            "name": r.name,
            "department": r.department or "General",
            "xp": int(r.total_progress * 10), # Simple XP calculation
            "streak": 5, # Mock streak for now
            "courses": r.courses,
            "avatar": r.name[:2].upper(),
            "change": 0
        } for i, r in enumerate(results)
    ]

@router.get("/me")
def get_my_rank(db: Session = Depends(get_db), current: Employee = Depends(require_employee)):
    # Very inefficient but works for small scale
    all_leaders = get_leaderboard(db)
    for leader in all_leaders:
        if leader["id"] == current.id:
            return leader
    
    # Not found in leaderboard (perhaps no progress yet)
    return {
        "rank": len(all_leaders) + 1,
        "name": current.name,
        "department": current.department.name if current.department else "General",
        "xp": 0,
        "streak": 0,
        "courses": 0,
        "avatar": current.name[:2].upper(),
        "change": 0
    }
