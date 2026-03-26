from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import Enrollment, Course, Employee, Certificate, LessonProgress, Lesson
from app.schemas import (
    EnrollRequest, AssignCourseRequest, EnrollmentResponse, CertificateResponse
)
from app.dependencies import require_employee, require_hr_admin, get_current_employee
from datetime import datetime
import uuid

router = APIRouter(prefix="/enrollments", tags=["Enrollments"])


@router.post("/enroll", response_model=EnrollmentResponse)
def self_enroll(
    data: EnrollRequest,
    db: Session = Depends(get_db),
    current: Employee = Depends(require_employee)
):
    """Employee self-enrolls in a published course."""
    course = db.query(Course).filter(Course.id == data.course_id, Course.is_published == True).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found or not published")

    existing = db.query(Enrollment).filter(
        Enrollment.employee_id == current.id,
        Enrollment.course_id == data.course_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already enrolled in this course")

    enrollment = Enrollment(
        employee_id=current.id,
        course_id=data.course_id,
        enrolled_by=current.id
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


@router.post("/assign", response_model=EnrollmentResponse)
def assign_course(
    data: AssignCourseRequest,
    db: Session = Depends(get_db),
    current: Employee = Depends(require_hr_admin)
):
    """Admin assigns a course to an employee."""
    course = db.query(Course).filter(Course.id == data.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    employee = db.query(Employee).filter(Employee.id == data.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    existing = db.query(Enrollment).filter(
        Enrollment.employee_id == data.employee_id,
        Enrollment.course_id == data.course_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Employee already enrolled in this course")

    enrollment = Enrollment(
        employee_id=data.employee_id,
        course_id=data.course_id,
        enrolled_by=current.id
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


@router.delete("/unenroll/{course_id}")
def unenroll(
    course_id: int,
    db: Session = Depends(get_db),
    current: Employee = Depends(require_employee)
):
    enrollment = db.query(Enrollment).filter(
        Enrollment.employee_id == current.id,
        Enrollment.course_id == course_id
    ).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    db.delete(enrollment)
    db.commit()
    return {"message": "Unenrolled successfully"}


@router.get("/my", response_model=list[EnrollmentResponse])
def get_my_enrollments(
    db: Session = Depends(get_db),
    current: Employee = Depends(require_employee)
):
    enrollments = db.query(Enrollment).options(
        joinedload(Enrollment.course)
    ).filter(Enrollment.employee_id == current.id).all()
    return enrollments


@router.get("/course/{course_id}/employees", response_model=list[dict])
def get_enrolled_employees(
    course_id: int,
    db: Session = Depends(get_db),
    current: Employee = Depends(require_hr_admin)
):
    """Get all employees enrolled in a course (admin only)."""
    enrollments = db.query(Enrollment).options(
        joinedload(Enrollment.employee)
    ).filter(Enrollment.course_id == course_id).all()

    return [
        {
            "enrollment_id": e.id,
            "employee_id": e.employee_id,
            "employee_name": e.employee.name,
            "employee_email": e.employee.email,
            "enrolled_at": e.enrolled_at,
            "progress_pct": e.progress_pct,
            "completed": e.completed
        }
        for e in enrollments
    ]


@router.post("/complete-lesson")
def mark_lesson_complete(
    lesson_id: int,
    course_id: int,
    db: Session = Depends(get_db),
    current: Employee = Depends(require_employee)
):
    """Mark a lesson as completed and update enrollment progress."""
    enrollment = db.query(Enrollment).filter(
        Enrollment.employee_id == current.id,
        Enrollment.course_id == course_id
    ).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Not enrolled in this course")

    # Check if already marked
    existing = db.query(LessonProgress).filter(
        LessonProgress.enrollment_id == enrollment.id,
        LessonProgress.lesson_id == lesson_id
    ).first()

    if existing:
        existing.completed = True
        existing.completed_at = datetime.utcnow()
    else:
        prog = LessonProgress(
            enrollment_id=enrollment.id,
            lesson_id=lesson_id,
            completed=True,
            completed_at=datetime.utcnow()
        )
        db.add(prog)

    # Recalculate progress %
    total_lessons = db.query(Lesson).filter(Lesson.course_id == course_id).count()
    completed_lessons = db.query(LessonProgress).filter(
        LessonProgress.enrollment_id == enrollment.id,
        LessonProgress.completed == True
    ).count()

    if total_lessons > 0:
        enrollment.progress_pct = round((completed_lessons / total_lessons) * 100, 1)

    # If 100% done, mark enrollment as complete and issue certificate
    certificate = None
    if enrollment.progress_pct >= 100 and not enrollment.completed:
        enrollment.completed = True
        enrollment.completed_at = datetime.utcnow()
        # Issue certificate
        existing_cert = db.query(Certificate).filter(
            Certificate.employee_id == current.id,
            Certificate.course_id == course_id
        ).first()
        if not existing_cert:
            cert = Certificate(
                employee_id=current.id,
                course_id=course_id,
                credential_id=f"LMS-{datetime.utcnow().year}-{uuid.uuid4().hex[:8].upper()}"
            )
            db.add(cert)
            certificate = cert

    db.commit()
    return {
        "progress_pct": enrollment.progress_pct,
        "completed": enrollment.completed,
        "certificate_issued": certificate is not None
    }


@router.get("/check/{course_id}")
def check_enrollment(
    course_id: int,
    db: Session = Depends(get_db),
    current: Employee = Depends(require_employee)
):
    """Check if current user is enrolled in a course."""
    enrollment = db.query(Enrollment).filter(
        Enrollment.employee_id == current.id,
        Enrollment.course_id == course_id
    ).first()
    return {
        "enrolled": enrollment is not None,
        "progress_pct": enrollment.progress_pct if enrollment else 0,
        "completed": enrollment.completed if enrollment else False
    }
