from fastapi import FastAPI, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler

# Import modules
from db.database import Base, engine, SessionLocal, get_db
from routes.auth import router as auth_router
from routes.api import router as api_router
from email_processing import process_new_emails

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
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
