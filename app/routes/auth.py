from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Employee, PasswordResetToken
from app.schemas import (
    EmployeeCreate, LoginRequest, TokenResponse, EmployeeResponse,
    ChangePasswordRequest, ForgotPasswordRequest, ResetPasswordRequest,
    UpdateProfileRequest
)
from app.auth import hash_password, verify_password, create_access_token
from app.dependencies import get_current_employee
from datetime import datetime, timedelta
import secrets
import os

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", response_model=EmployeeResponse)
def register(employee: EmployeeCreate, db: Session = Depends(get_db)):
    existing = db.query(Employee).filter(Employee.email == employee.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_employee = Employee(
        name=employee.name,
        email=employee.email,
        hashed_password=hash_password(employee.password),
        role=employee.role,
        department_id=employee.department_id
    )
    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)
    return new_employee

@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    employee = db.query(Employee).filter(Employee.email == request.email).first()
    if not employee or not verify_password(request.password, employee.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not employee.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated. Contact your administrator.")
    token = create_access_token({"sub": employee.email, "role": employee.role, "id": employee.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": employee.role,
        "name": employee.name,
        "id": employee.id
    }

@router.get("/me", response_model=EmployeeResponse)
def get_me(current: Employee = Depends(get_current_employee)):
    return current

@router.put("/me", response_model=EmployeeResponse)
def update_profile(
    data: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current: Employee = Depends(get_current_employee)
):
    if data.name:
        current.name = data.name
    db.commit()
    db.refresh(current)
    return current

@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current: Employee = Depends(get_current_employee)
):
    if not verify_password(data.current_password, current.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current.hashed_password = hash_password(data.new_password)
    db.commit()
    return {"message": "Password changed successfully"}

@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    employee = db.query(Employee).filter(Employee.email == data.email).first()
    if not employee:
        # Return success even if email not found (security best practice)
        return {"message": "If this email is registered, a reset link has been sent."}

    # Invalidate any existing tokens
    db.query(PasswordResetToken).filter(
        PasswordResetToken.employee_id == employee.id,
        PasswordResetToken.used == False
    ).update({"used": True})

    token = secrets.token_urlsafe(32)
    reset_token = PasswordResetToken(
        employee_id=employee.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    db.add(reset_token)
    db.commit()

    # In production, send email here. For now, return token in response for testing.
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    reset_link = f"{frontend_url}/reset-password?token={token}"

    # Try to send email if SMTP is configured
    try:
        _send_reset_email(employee.email, employee.name, reset_link)
    except Exception:
        pass  # Email sending failed silently

    return {
        "message": "If this email is registered, a reset link has been sent.",
        "reset_link": reset_link,  # Remove in production
        "token": token  # Remove in production
    }

@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    token_record = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == data.token,
        PasswordResetToken.used == False
    ).first()

    if not token_record:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    if token_record.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Reset token has expired")

    employee = db.query(Employee).filter(Employee.id == token_record.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    employee.hashed_password = hash_password(data.new_password)
    token_record.used = True
    db.commit()

    return {"message": "Password reset successfully. You can now log in."}


def _send_reset_email(to_email: str, name: str, reset_link: str):
    """Send password reset email. Configure SMTP env vars to enable."""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    from_email = os.getenv("FROM_EMAIL", smtp_user)

    if not all([smtp_host, smtp_user, smtp_pass]):
        raise Exception("SMTP not configured")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset Your LMS Password"
    msg["From"] = f"Bryte LMS <{from_email}>"
    msg["To"] = to_email

    html = f"""
    <html>
      <body style="font-family: 'Segoe UI', sans-serif; background: #f8fafc; padding: 40px; color: #0f172a;">
        <div style="max-width: 480px; margin: 0 auto; background: #fff; border-radius: 16px; padding: 40px; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
          <h2 style="color: #6366f1; margin-bottom: 8px;">Password Reset</h2>
          <p style="color: #64748b;">Hi {name},</p>
          <p style="color: #64748b;">We received a request to reset your password. Click the button below to set a new password.</p>
          <a href="{reset_link}" style="display: inline-block; margin: 24px 0; padding: 14px 28px; background: #6366f1; color: #fff; border-radius: 10px; text-decoration: none; font-weight: 600;">Reset Password</a>
          <p style="color: #94a3b8; font-size: 13px;">This link expires in 1 hour. If you didn't request this, you can safely ignore it.</p>
        </div>
      </body>
    </html>
    """

    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(str(smtp_host), smtp_port) as server:
        server.starttls()
        server.login(str(smtp_user), str(smtp_pass))
        server.sendmail(str(from_email), to_email, msg.as_string())