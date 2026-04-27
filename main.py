from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn
import uuid
from typing import Dict, Any

from src.agents.emailing_agent import run_agent, get_email_draft
from src.tools import get_data, send_final_email

app = FastAPI(
    title="Cold Emailing Agent SaaS",
    description="A premium SaaS for personalized cold emailing",
    version="2.0.0"
)

# Enable CORS for frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Progress tracking (In-memory for simplicity)
job_status: Dict[str, Any] = {}

templates = Jinja2Templates(directory="templates")

@app.get("/")
def read_home(request: Request):
    return templates.TemplateResponse(request=request, name="home.html")

@app.get("/app")
def read_app(request: Request):
    return templates.TemplateResponse(request=request, name="product.html")

class EmailRequest(BaseModel):
    dry_run: bool = False

class DraftRequest(BaseModel):
    hr_name: str
    company_name: str
    email: str
    company_cache: Dict[str, Any] = {}

class SendRequest(BaseModel):
    recipient_email: str
    subject: str
    body: str

@app.get("/contacts")
def get_contacts():
    """Returns the list of contacts from the Excel sheet."""
    try:
        data = get_data()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/draft-email")
def draft_email_endpoint(request: DraftRequest):
    """Generates a draft for a single contact."""
    try:
        draft = get_email_draft(
            hr_name=request.hr_name,
            company_name=request.company_name,
            email=request.email,
            company_cache=request.company_cache
        )
        return draft
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/send-approved-email")
def send_approved_email_endpoint(request: SendRequest):
    """Sends a manually approved email."""
    try:
        result = send_final_email(
            recipient_email=request.recipient_email,
            subject=request.subject,
            body=request.body
        )
        return {"status": "success", "message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "healthy"}

def background_email_task(job_id: str, dry_run: bool):
    """Executes the email agent in the background and updates the job status."""
    try:
        job_status[job_id]["status"] = "processing"
        
        def update_progress(current_results):
            job_status[job_id]["results"] = current_results

        results = run_agent(dry_run=dry_run, progress_callback=update_progress)
        job_status[job_id]["status"] = "completed"
        job_status[job_id]["results"] = results
    except Exception as e:
        job_status[job_id]["status"] = "failed"
        job_status[job_id]["error"] = str(e)

# The old batch endpoints (/send-emails, /status) have been removed
# to favor the new interactive Human-in-the-Loop architecture.

# Mount static files (HTML/CSS/JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
