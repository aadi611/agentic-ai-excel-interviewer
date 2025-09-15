from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import logging
import io
from datetime import datetime
from typing import Dict, Any

from config import Config
from llm_service import LLMService
from interview_manager import InterviewManager
from database_service import DatabaseService
from models import UserResponse, InterviewState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Excel Skills Assessment API",
    description="AI-powered Excel skills interview system using Groq LLM and Supabase",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory=".", html=True), name="static")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
Config.validate()
llm_service = LLMService(api_key=Config.GROQ_API_KEY)
db_service = DatabaseService()
interview_manager = InterviewManager(llm_service, db_service)

# API Routes
@app.get("/")
async def root():
    """Serve the main UI"""
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content, status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Excel Assessment UI not found</h1>", status_code=404)

@app.get("/api")
async def api_info():
    """API information endpoint"""
    return {
        "message": "Excel Skills Assessment API",
        "version": "1.0.0",
        "endpoints": {
            "POST /api/session/create": "Create new interview session",
            "POST /api/session/{session_id}/start": "Start interview",
            "POST /api/session/{session_id}/respond": "Submit response",
            "GET /api/session/{session_id}/status": "Get session status",
            "GET /api/session/{session_id}/report": "Get final report"
        }
    }

@app.post("/api/session/create")
async def create_session(candidate_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create a new interview session"""
    try:
        session_id = await interview_manager.create_session(candidate_data)
        return {
            "success": True,
            "session_id": session_id,
            "message": "Session created successfully"
        }
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/session/{session_id}/start")
async def start_interview(session_id: str) -> Dict[str, Any]:
    """Start the interview for a session"""
    try:
        result = await interview_manager.start_interview(session_id)
        return {
            "success": True,
            **result
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting interview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/session/{session_id}/respond")
async def submit_response(session_id: str, response: UserResponse) -> Dict[str, Any]:
    """Submit a response to the current question"""
    try:
        result = await interview_manager.process_response(session_id, response.message)
        return {
            "success": True,
            **result
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing response: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/session/{session_id}/status")
async def get_session_status(session_id: str) -> Dict[str, Any]:
    """Get current status of a session"""
    try:
        session_data = await db_service.get_interview_session(session_id)
        if not session_data:
            raise ValueError(f"Session {session_id} not found")

        responses = await db_service.get_interview_responses(session_id)

        return {
            "success": True,
            "session_id": session_id,
            "state": session_data['state'],
            "questions_answered": len([r for r in responses if r['candidate_answer'] is not None]),
            "total_questions": session_data['total_questions'],
            "current_score": session_data['score'] / max(len(responses), 1) if responses else 0,
            "difficulty": session_data['difficulty']
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/session/{session_id}/report")
async def get_report(session_id: str) -> Dict[str, Any]:
    """Get the final interview report"""
    try:
        session_data = await db_service.get_interview_session(session_id)
        if not session_data:
            raise ValueError(f"Session {session_id} not found")

        if session_data['state'] != InterviewState.COMPLETED.value:
            return {
                "success": False,
                "message": "Interview not yet completed"
            }

        report = await db_service.get_evaluation_report(session_id)
        if not report:
            return {
                "success": False,
                "message": "Report not found"
            }

        return {
            "success": True,
            "report": report
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cleanup")
async def cleanup_sessions(background_tasks: BackgroundTasks):
    """Cleanup old sessions"""
    background_tasks.add_task(interview_manager.cleanup_old_sessions)
    return {"message": "Cleanup initiated"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    # Test Groq connectivity by checking API key
    groq_connected = bool(llm_service.api_key and len(llm_service.api_key) > 0)

    # Test database connectivity
    db_connected = False
    try:
        # Try to get active sessions as a connectivity test
        active_sessions = await db_service.get_active_sessions()
        db_connected = True
    except Exception as e:
        logger.error(f"Database connectivity test failed: {e}")
        db_connected = False

    return {
        "status": "healthy" if groq_connected and db_connected else "degraded",
        "groq_connected": groq_connected,
        "database_connected": db_connected
    }

# Run the application
if __name__ == "__main__":
    print(f"""
    ╔══════════════════════════════════════════════╗
    ║   Excel Skills Assessment System - v1.0.0    ║
    ║         Powered by Groq LLM API              ║
    ╚══════════════════════════════════════════════╝
    
    Starting server on http://localhost:{Config.PORT}
    API Docs: http://localhost:{Config.PORT}/docs
    
    Make sure to set GROQ_API_KEY in your .env file!
    """)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=Config.PORT,
        reload=True,
        log_level="info"
    )