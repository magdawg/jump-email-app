# /*
#  * -----------------------------------------------------------------------------
#  *  Copyright (c) 2025 Magda Kowalska. All rights reserved.
#  *
#  *  This software and its source code are the intellectual property of
#  *  Magda Kowalska. Unauthorized copying, reproduction, or use of this
#  *  software, in whole or in part, is strictly prohibited without express
#  *  written permission.
#  *
#  *  This software is protected under the Berne Convention for the Protection
#  *  of Literary and Artistic Works, EU copyright law, and international
#  *  copyright treaties.
#  *
#  *  Author: Magda Kowalska
#  *  Created: 2025-11-02
#  *  Last Modified: 2025-11-02
#  * -----------------------------------------------------------------------------
#  */

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import BackgroundTasks, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.db.database import Base, SessionLocal, engine, get_db
from backend.email_processing import process_new_emails
from backend.routes.api import router as api_router
from backend.routes.auth import router as auth_router

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(api_router)


@app.get("/")
def read_root():
    return {"message": "Email Sorter API"}


@app.post("/api/process-emails")
def process_emails_endpoint(
    background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    background_tasks.add_task(process_new_emails, db)
    return {"message": "Processing started"}


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
