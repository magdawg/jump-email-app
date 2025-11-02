from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import BackgroundTasks, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Import modules
from backend.db.database import Base, SessionLocal, engine, get_db
from backend.email_processing import process_new_emails
from backend.routes.api import router as api_router
from backend.routes.auth import router as auth_router

# Create database tables
Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(api_router)


# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Email Sorter API"}


# Manual email processing
@app.post("/api/process-emails")
def process_emails_endpoint(
    background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    background_tasks.add_task(process_new_emails, db)
    return {"message": "Processing started"}


# Background scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(
    func=lambda: process_new_emails(SessionLocal()), trigger="interval", minutes=5
)
scheduler.start()

if __name__ == "__main__":
    import os

    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
