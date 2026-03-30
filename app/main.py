from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.database import Base, engine
from app.routes import (
    auth as auth_router, courses, departments, employees, uploads,
    enrollments, quizzes, assignments, certificates, messages, doubts,
    live_classes, activity, notifications, leaderboard
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Company LMS API",
    version="1.0.0",
    swagger_ui_parameters={"persistAuthorization": True}
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(auth_router.router)
app.include_router(employees.router)
app.include_router(departments.router)
app.include_router(courses.router)
app.include_router(uploads.router)
app.include_router(uploads.course_thumb_router)
app.include_router(enrollments.router)
app.include_router(quizzes.router)
app.include_router(assignments.router)
app.include_router(certificates.router)
app.include_router(messages.router)
app.include_router(doubts.router)
app.include_router(live_classes.router)
app.include_router(activity.router)
app.include_router(notifications.router)
app.include_router(leaderboard.router)

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("app/static/favicon.ico")

@app.get("/")
def root():
    return {"message": "Company LMS API is running 🚀"}