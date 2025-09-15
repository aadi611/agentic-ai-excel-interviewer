from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class InterviewState(str, Enum):
    """Interview state enumeration"""
    INIT = "init"
    INTRO = "intro"
    QUESTIONING = "questioning"
    EVALUATING = "evaluating"
    COMPLETED = "completed"

class Difficulty(str, Enum):
    """Question difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"

class SkillCategory(str, Enum):
    """Excel skill categories"""
    FORMULAS = "Formulas & Functions"
    PIVOT_TABLES = "Pivot Tables"
    DATA_ANALYSIS = "Data Analysis"
    VLOOKUP = "VLOOKUP & Lookups"
    MACROS = "Macros & VBA"
    CHARTS = "Charts & Visualization"
    POWER_QUERY = "Power Query & Power Pivot"
    CONDITIONAL = "Conditional Formatting"

class Question(BaseModel):
    """Question model"""
    id: int
    category: SkillCategory
    difficulty: Difficulty
    question: str
    keywords: List[str]
    max_score: int = 10
    follow_up: Optional[str] = None

class UserResponse(BaseModel):
    """User response model"""
    session_id: str
    message: str
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)

class EvaluationResult(BaseModel):
    """LLM evaluation result"""
    score: float = Field(ge=0, le=100)
    feedback: str
    strengths: List[str] = []
    improvements: List[str] = []
    follow_up_question: Optional[str] = None
    difficulty_adjustment: Optional[str] = None

class InterviewSession(BaseModel):
    """Interview session model"""
    session_id: str
    state: InterviewState = InterviewState.INIT
    current_question_index: int = 0
    responses: List[Dict[str, Any]] = []
    total_score: float = 0
    start_time: datetime = Field(default_factory=datetime.now)
    context: List[Dict[str, str]] = []
    difficulty: Difficulty = Difficulty.MEDIUM
    tested_categories: List[SkillCategory] = []

class InterviewReport(BaseModel):
    """Final interview report"""
    session_id: str
    total_score: float
    duration_minutes: int
    skill_level: str
    strengths: List[str]
    improvements: List[str]
    recommendations: List[str]
    category_scores: Dict[str, float]
