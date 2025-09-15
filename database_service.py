from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import uuid

from config import Config
from models import InterviewSession, InterviewState, SkillCategory, Difficulty

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service for data persistence - currently using in-memory storage"""

    def __init__(self):
        # In-memory storage for development
        self.candidates = {}
        self.interview_sessions = {}
        self.pre_interview_checks = {}
        self.interview_responses = {}
        self.evaluation_reports = {}
        self.support_incidents = {}

    # Candidate Management
    async def create_candidate(self, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new candidate record"""
        candidate_id = str(uuid.uuid4())
        candidate_data['id'] = candidate_id
        candidate_data['created_at'] = datetime.utcnow().isoformat()
        self.candidates[candidate_id] = candidate_data
        return candidate_data

    async def get_candidate(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        """Get candidate by ID"""
        return self.candidates.get(candidate_id)

    async def update_candidate(self, candidate_id: str, updates: Dict[str, Any]) -> bool:
        """Update candidate information"""
        if candidate_id in self.candidates:
            self.candidates[candidate_id].update(updates)
            return True
        return False

    # Interview Session Management
    async def create_interview_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new interview session"""
        session_id = session_data.get('session_id', str(uuid.uuid4()))
        session_data['session_id'] = session_id
        session_data['created_at'] = datetime.utcnow().isoformat()
        self.interview_sessions[session_id] = session_data
        return session_data

    async def get_interview_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get interview session by ID"""
        return self.interview_sessions.get(session_id)

    async def update_interview_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Update interview session"""
        if session_id in self.interview_sessions:
            self.interview_sessions[session_id].update(updates)
            return True
        return False

    async def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get all active interview sessions"""
        active_states = ['init', 'questioning', 'evaluating']
        return [session for session in self.interview_sessions.values()
                if session.get('state') in active_states]

    async def get_latest_session(self) -> Optional[Dict[str, Any]]:
        """Get the most recently created session"""
        if not self.interview_sessions:
            return None
        
        latest_session = max(
            self.interview_sessions.values(),
            key=lambda x: x.get('created_at', '')
        )
        return latest_session

    # Pre-Interview Checks
    async def save_pre_interview_check(self, check_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save pre-interview technical check results"""
        check_id = str(uuid.uuid4())
        check_data['id'] = check_id
        check_data['created_at'] = datetime.utcnow().isoformat()
        session_id = check_data.get('session_id')
        if session_id not in self.pre_interview_checks:
            self.pre_interview_checks[session_id] = []
        self.pre_interview_checks[session_id].append(check_data)
        return check_data

    async def get_pre_interview_checks(self, session_id: str) -> List[Dict[str, Any]]:
        """Get pre-interview checks for a session"""
        return self.pre_interview_checks.get(session_id, [])

    # Interview Responses
    async def save_interview_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save interview response"""
        response_id = str(uuid.uuid4())
        response_data['id'] = response_id
        response_data['created_at'] = datetime.utcnow().isoformat()
        session_id = response_data.get('session_id')
        if session_id not in self.interview_responses:
            self.interview_responses[session_id] = []
        self.interview_responses[session_id].append(response_data)
        return response_data

    async def get_interview_responses(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all responses for an interview session"""
        return sorted(self.interview_responses.get(session_id, []),
                     key=lambda x: x.get('created_at', ''))

    # Evaluation Reports
    async def save_evaluation_report(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save evaluation report"""
        report_id = str(uuid.uuid4())
        report_data['id'] = report_id
        report_data['created_at'] = datetime.utcnow().isoformat()
        session_id = report_data.get('session_id')
        self.evaluation_reports[session_id] = report_data
        return report_data

    async def get_evaluation_report(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get evaluation report for a session"""
        return self.evaluation_reports.get(session_id)

    # Support Incidents
    async def create_support_incident(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a support incident"""
        incident_id = str(uuid.uuid4())
        incident_data['id'] = incident_id
        incident_data['created_at'] = datetime.utcnow().isoformat()
        self.support_incidents[incident_id] = incident_data
        return incident_data

    async def update_support_incident(self, incident_id: str, updates: Dict[str, Any]) -> bool:
        """Update support incident"""
        if incident_id in self.support_incidents:
            self.support_incidents[incident_id].update(updates)
            return True
        return False

    # Cleanup and Maintenance
    async def cleanup_old_sessions(self, hours_old: int = 24) -> int:
        """Clean up old completed sessions"""
        # For in-memory storage, this is a no-op
        # In a real implementation, this would clean up old data
        return 0

    # Real-time subscriptions (for future use)
    def subscribe_to_session_updates(self, session_id: str, callback):
        """Subscribe to real-time updates for a session"""
        # Not implemented for in-memory storage
        pass