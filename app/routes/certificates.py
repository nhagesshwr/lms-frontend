from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import Certificate, Employee, Course
from app.schemas import CertificateResponse
from app.dependencies import require_employee, require_hr_admin
import uuid
from datetime import datetime

router = APIRouter(prefix="/certificates", tags=["Certificates"])


@router.get("/my", response_model=list[CertificateResponse])
def get_my_certificates(
    db: Session = Depends(get_db),
    current: Employee = Depends(require_employee)
):
    certs = db.query(Certificate).options(
        joinedload(Certificate.course)
    ).filter(Certificate.employee_id == current.id).all()
    return certs


@router.get("/all", response_model=list[dict])
def get_all_certificates(
    db: Session = Depends(get_db),
    current=Depends(require_hr_admin)
):
    """Admin: view all issued certificates."""
    certs = db.query(Certificate).options(
        joinedload(Certificate.course),
        joinedload(Certificate.employee)
    ).all()
    return [
        {
            "id": c.id,
            "employee_name": c.employee.name,
            "employee_email": c.employee.email,
            "course_title": c.course.title if c.course else "",
            "credential_id": c.credential_id,
            "issued_at": c.issued_at
        }
        for c in certs
    ]


@router.post("/issue/{employee_id}/{course_id}", response_model=CertificateResponse)
def issue_certificate(
    employee_id: int,
    course_id: int,
    db: Session = Depends(get_db),
    current=Depends(require_hr_admin)
):
    """Admin manually issues a certificate."""
    existing = db.query(Certificate).filter(
        Certificate.employee_id == employee_id,
        Certificate.course_id == course_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Certificate already issued for this course")

    cert = Certificate(
        employee_id=employee_id,
        course_id=course_id,
        credential_id=f"LMS-{datetime.utcnow().year}-{uuid.uuid4().hex[:8].upper()}"
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)
    return cert


@router.get("/{cert_id}", response_model=CertificateResponse)
def get_certificate(
    cert_id: int,
    db: Session = Depends(get_db),
    current: Employee = Depends(require_employee)
):
    cert = db.query(Certificate).options(
        joinedload(Certificate.course)
    ).filter(Certificate.id == cert_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    # Only allow owner or admin
    if cert.employee_id != current.id and current.role not in ["hr_admin", "super_admin", "manager"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return cert


@router.delete("/{cert_id}")
def revoke_certificate(
    cert_id: int,
    db: Session = Depends(get_db),
    current=Depends(require_hr_admin)
):
    cert = db.query(Certificate).filter(Certificate.id == cert_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    db.delete(cert)
    db.commit()
    return {"message": "Certificate revoked"}
