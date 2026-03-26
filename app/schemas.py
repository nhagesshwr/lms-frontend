from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.models import RoleEnum

# ── Employee schemas ──────────────────────────
class EmployeeCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: RoleEnum = RoleEnum.employee
    department_id: Optional[int] = None

class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[RoleEnum] = None
    department_id: Optional[int] = None
    is_active: Optional[bool] = None

class EmployeeResponse(BaseModel):
    id: int
    name: str
    email: str
    role: RoleEnum
    is_active: bool
    department_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

# ── Auth schemas ──────────────────────────────
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    name: str
    id: int

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None

# ── Department schemas ────────────────────────────────────────────────────────
class DepartmentCreate(BaseModel):
    name: str

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None

class DepartmentResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

    class Config:
        from_attributes = True

class DepartmentWithEmployees(BaseModel):
    id: int
    name: str
    created_at: datetime
    employees: List[EmployeeResponse] = []

    class Config:
        from_attributes = True

# ── Lesson schemas ────────────────────────────
class LessonCreate(BaseModel):
    title: str
    description: Optional[str] = None
    video_url: Optional[str] = None
    pdf_url: Optional[str] = None
    order: Optional[int] = 0
    duration_minutes: Optional[int] = None

class LessonUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    video_url: Optional[str] = None
    pdf_url: Optional[str] = None
    order: Optional[int] = None
    duration_minutes: Optional[int] = None

class LessonResponse(BaseModel):
    id: int
    course_id: int
    title: str
    description: Optional[str]
    video_url: Optional[str]
    pdf_url: Optional[str]
    order: int
    duration_minutes: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True

# ── Course schemas ────────────────────────────
class CourseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    category: Optional[str] = None

class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    category: Optional[str] = None

class CourseResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    thumbnail_url: Optional[str]
    category: Optional[str]
    is_published: bool
    created_at: datetime

    class Config:
        from_attributes = True

class CourseWithLessons(BaseModel):
    id: int
    title: str
    description: Optional[str]
    thumbnail_url: Optional[str]
    category: Optional[str]
    is_published: bool
    created_at: datetime
    lessons: List[LessonResponse] = []

    class Config:
        from_attributes = True

# ── Enrollment schemas ────────────────────────────────────────────────────────
class EnrollRequest(BaseModel):
    course_id: int

class AssignCourseRequest(BaseModel):
    employee_id: int
    course_id: int

class EnrollmentResponse(BaseModel):
    id: int
    employee_id: int
    course_id: int
    enrolled_at: datetime
    completed: bool
    completed_at: Optional[datetime]
    progress_pct: float
    course: Optional[CourseResponse] = None

    class Config:
        from_attributes = True

# ── Progress schemas ──────────────────────────────────────────────────────────
class LessonProgressUpdate(BaseModel):
    lesson_id: int
    watched_seconds: Optional[int] = 0
    completed: Optional[bool] = False

class LessonProgressResponse(BaseModel):
    id: int
    enrollment_id: int
    lesson_id: int
    completed: bool
    completed_at: Optional[datetime]
    watched_seconds: int

    class Config:
        from_attributes = True

# ── Quiz schemas ──────────────────────────────────────────────────────────────
class QuizQuestionCreate(BaseModel):
    text: str
    options: List[str]
    correct_index: int
    order: Optional[int] = 0

class QuizCreate(BaseModel):
    title: str
    pass_score: Optional[int] = 70
    questions: List[QuizQuestionCreate]

class QuizQuestionResponse(BaseModel):
    id: int
    quiz_id: int
    text: str
    options: List[str]
    correct_index: int
    order: int

    class Config:
        from_attributes = True

class QuizResponse(BaseModel):
    id: int
    lesson_id: int
    title: str
    pass_score: int
    created_at: datetime
    questions: List[QuizQuestionResponse] = []

    class Config:
        from_attributes = True

class QuizSubmitRequest(BaseModel):
    answers: Dict[int, int]  # {question_id: selected_index}

class QuizAttemptResponse(BaseModel):
    id: int
    quiz_id: int
    employee_id: int
    score: int
    passed: bool
    attempted_at: datetime

    class Config:
        from_attributes = True

# ── Assignment schemas ────────────────────────────────────────────────────────
class AssignmentCreate(BaseModel):
    course_id: int
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    points: Optional[int] = 100
    assignment_type: Optional[str] = "exercise"

class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    points: Optional[int] = None
    assignment_type: Optional[str] = None

class AssignmentResponse(BaseModel):
    id: int
    course_id: int
    title: str
    description: Optional[str]
    due_date: Optional[datetime]
    points: int
    assignment_type: str
    created_at: datetime
    course: Optional[CourseResponse] = None

    class Config:
        from_attributes = True

class SubmissionCreate(BaseModel):
    submission_text: Optional[str] = None

class GradeSubmissionRequest(BaseModel):
    grade: int
    feedback: Optional[str] = None

class SubmissionResponse(BaseModel):
    id: int
    assignment_id: int
    employee_id: int
    submission_text: Optional[str]
    submitted_at: datetime
    grade: Optional[int]
    feedback: Optional[str]
    status: str

    class Config:
        from_attributes = True

# ── Certificate schemas ───────────────────────────────────────────────────────
class CertificateResponse(BaseModel):
    id: int
    employee_id: int
    course_id: int
    credential_id: str
    issued_at: datetime
    pdf_url: Optional[str]
    course: Optional[CourseResponse] = None

    class Config:
        from_attributes = True

# ── Message schemas ───────────────────────────────────────────────────────────
class MessageCreate(BaseModel):
    receiver_id: int
    content: str

class MessageResponse(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    content: str
    is_read: bool
    sent_at: datetime
    sender: Optional[EmployeeResponse] = None
    receiver: Optional[EmployeeResponse] = None

    class Config:
        from_attributes = True

# ── Doubt schemas ─────────────────────────────────────────────────────────────
class DoubtCreate(BaseModel):
    question: str

class DoubtAnswerRequest(BaseModel):
    answer: str

class DoubtResponse(BaseModel):
    id: int
    lesson_id: int
    asked_by: int
    question: str
    answer: Optional[str]
    answered_by: Optional[int]
    answered_at: Optional[datetime]
    created_at: datetime
    asker: Optional[EmployeeResponse] = None
    answerer: Optional[EmployeeResponse] = None

    class Config:
        from_attributes = True