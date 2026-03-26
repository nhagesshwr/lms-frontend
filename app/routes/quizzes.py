from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import Quiz, QuizQuestion, QuizAttempt, Lesson, Employee
from app.schemas import QuizCreate, QuizResponse, QuizSubmitRequest, QuizAttemptResponse
from app.dependencies import require_employee, require_hr_admin

router = APIRouter(prefix="/quizzes", tags=["Quizzes"])


@router.post("/lesson/{lesson_id}", response_model=QuizResponse)
def create_quiz(
    lesson_id: int,
    data: QuizCreate,
    db: Session = Depends(get_db),
    current=Depends(require_hr_admin)
):
    """Create a quiz for a lesson (admin only)."""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    existing = db.query(Quiz).filter(Quiz.lesson_id == lesson_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Quiz already exists for this lesson")

    quiz = Quiz(
        lesson_id=lesson_id,
        title=data.title,
        pass_score=data.pass_score
    )
    db.add(quiz)
    db.flush()

    for i, q in enumerate(data.questions):
        question = QuizQuestion(
            quiz_id=quiz.id,
            text=q.text,
            options=q.options,
            correct_index=q.correct_index,
            order=q.order if q.order is not None else i
        )
        db.add(question)

    db.commit()
    db.refresh(quiz)
    return quiz


@router.get("/lesson/{lesson_id}", response_model=QuizResponse)
def get_quiz_by_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current=Depends(require_employee)
):
    quiz = db.query(Quiz).options(
        joinedload(Quiz.questions)
    ).filter(Quiz.lesson_id == lesson_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="No quiz found for this lesson")
    return quiz


@router.post("/{quiz_id}/submit", response_model=QuizAttemptResponse)
def submit_quiz(
    quiz_id: int,
    data: QuizSubmitRequest,
    db: Session = Depends(get_db),
    current: Employee = Depends(require_employee)
):
    quiz = db.query(Quiz).options(joinedload(Quiz.questions)).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    correct = 0
    total = len(quiz.questions)
    for question in quiz.questions:
        if data.answers.get(question.id) == question.correct_index or data.answers.get(str(question.id)) == question.correct_index:
            correct += 1  # type: ignore

    score = round((correct / total) * 100) if total > 0 else 0  # type: ignore
    passed = score >= quiz.pass_score

    attempt = QuizAttempt(
        quiz_id=quiz_id,
        employee_id=current.id,
        answers={str(k): v for k, v in data.answers.items()},
        score=score,
        passed=passed
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


@router.get("/{quiz_id}/attempts", response_model=list[QuizAttemptResponse])
def get_my_attempts(
    quiz_id: int,
    db: Session = Depends(get_db),
    current: Employee = Depends(require_employee)
):
    return db.query(QuizAttempt).filter(
        QuizAttempt.quiz_id == quiz_id,
        QuizAttempt.employee_id == current.id
    ).order_by(QuizAttempt.attempted_at.desc()).all()


@router.delete("/lesson/{lesson_id}")
def delete_quiz(
    lesson_id: int,
    db: Session = Depends(get_db),
    current=Depends(require_hr_admin)
):
    quiz = db.query(Quiz).filter(Quiz.lesson_id == lesson_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    db.delete(quiz)
    db.commit()
    return {"message": "Quiz deleted"}
