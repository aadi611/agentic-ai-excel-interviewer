from groq import Groq
from typing import Dict, Any, Optional, List
import json
import logging
import requests
from datetime import datetime

from config import Config
from models import (
    SkillCategory, 
    Difficulty, 
    Question, 
    EvaluationResult, 
    InterviewSession, 
    InterviewReport
)

logger = logging.getLogger(__name__)

class LLMService:
    """Service for using Groq LLM"""
    
    def __init__(self, api_key: str, model: str = None):
        self.api_key = api_key
        # Use the new model directly instead of config
        self.model = model or "meta-llama/llama-4-scout-17b-16e-instruct"
        self.base_url = "https://api.groq.com/openai/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
    def _make_request(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 300) -> Dict[str, Any]:
        """Make a request to Groq API"""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            raise Exception(f"Failed to communicate with Groq API: {e}")
        
    def generate_question(self, 
                         category: SkillCategory, 
                         difficulty: Difficulty,
                         previous_questions: List[str] = None) -> Question:
        """Generate a contextual interview question"""
        
        prompt = f"""Generate an Excel interview question with the following requirements:
        Category: {category.value}
        Difficulty: {difficulty.value}
        
        Previous questions asked: {previous_questions or 'None'}
        
        Return ONLY a JSON object with:
        - question: The interview question (clear and specific)
        - keywords: List of key concepts the answer should include
        - follow_up: A potential follow-up question
        
        Make it practical and scenario-based when possible.
        
        Example format:
        {{"question": "How would you use VLOOKUP to find data?", "keywords": ["VLOOKUP", "exact match", "table array"], "follow_up": "What are the limitations of VLOOKUP?"}}"""
        
        try:
            response_data = self._make_request([
                {"role": "system", "content": "You are an Excel expert interviewer. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ], temperature=0.7, max_tokens=300)
            
            content = response_data["choices"][0]["message"]["content"]
            
            # Try to extract JSON from the response
            result = self._extract_json(content)
            
            return Question(
                id=len(previous_questions) + 1 if previous_questions else 1,
                category=category,
                difficulty=difficulty,
                question=result["question"],
                keywords=result.get("keywords", []),
                follow_up=result.get("follow_up")
            )
            
        except Exception as e:
            logger.error(f"Error generating question: {e}")
            # Fallback to predefined question
            return self._get_fallback_question(category, difficulty)
    
    def evaluate_response(self,
                         question: Question,
                         response: str,
                         context: List[Dict[str, str]] = None) -> EvaluationResult:
        """Evaluate a candidate's response using LLM"""
        
        prompt = f"""Evaluate this Excel interview response:
        
        Question: {question.question}
        Expected Keywords/Concepts: {', '.join(question.keywords)}
        Candidate's Response: {response}
        
        Provide ONLY a JSON evaluation with:
        - score: 0-100 based on accuracy, completeness, and understanding
        - feedback: Brief constructive feedback (2-3 sentences)
        - strengths: List of 1-3 things done well
        - improvements: List of 1-3 areas to improve
        - difficulty_adjustment: "increase", "maintain", or "decrease" based on performance
        
        Be fair but thorough in evaluation.
        
        Example format:
        {{"score": 85, "feedback": "Good understanding shown", "strengths": ["Clear explanation"], "improvements": ["More detail needed"], "difficulty_adjustment": "maintain"}}"""
        
        try:
            messages = [
                {"role": "system", "content": "You are an expert Excel skills evaluator. Always respond with valid JSON only."}
            ]
            
            # Add context if available
            if context:
                messages.extend(context[-4:])  # Last 2 Q&A pairs
                
            messages.append({"role": "user", "content": prompt})
            
            response_data = self._make_request(messages, temperature=0.3, max_tokens=400)
            
            content = response_data["choices"][0]["message"]["content"]
            result = self._extract_json(content)
            
            return EvaluationResult(**result)
            
        except Exception as e:
            logger.error(f"Error evaluating response: {e}")
            # Fallback to simple keyword matching
            return self._simple_evaluation(question, response)
    
    def generate_report(self, session: InterviewSession) -> InterviewReport:
        """Generate final interview report"""
        
        prompt = f"""Generate a comprehensive interview report based on this session:
        
        Total Questions: {len(session.responses)}
        Average Score: {session.total_score / max(len(session.responses), 1):.1f}
        Categories Tested: {', '.join([cat.value for cat in session.tested_categories])}
        
        Responses Summary:
        {json.dumps(session.responses[-5:], indent=2)}  # Last 5 responses
        
        Provide ONLY a JSON report with:
        - skill_level: "Beginner", "Intermediate", "Advanced", or "Expert"
        - strengths: List of 3-5 key strengths observed
        - improvements: List of 3-5 areas for improvement
        - recommendations: List of 3-5 specific learning recommendations
        
        Example format:
        {{"skill_level": "Intermediate", "strengths": ["Good formula knowledge"], "improvements": ["Practice pivot tables"], "recommendations": ["Take advanced Excel course"]}}"""
        
        try:
            response_data = self._make_request([
                {"role": "system", "content": "You are an expert interviewer creating a final assessment report. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ], temperature=0.5, max_tokens=600)
            
            content = response_data["choices"][0]["message"]["content"]
            result = self._extract_json(content)
            
            # Calculate duration
            duration = int((datetime.now() - session.start_time).total_seconds() / 60)
            
            # Calculate category scores
            category_scores = self._calculate_category_scores(session.responses)
            
            return InterviewReport(
                session_id=session.session_id,
                total_score=session.total_score / max(len(session.responses), 1),
                duration_minutes=duration,
                skill_level=result["skill_level"],
                strengths=result["strengths"],
                improvements=result["improvements"],
                recommendations=result["recommendations"],
                category_scores=category_scores
            )
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return self._generate_basic_report(session)
    
    def generate_report_from_data(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate final interview report from response data"""

        if not responses:
            return {
                "overall_score": 0.0,
                "skill_breakdown": {},
                "strengths": ["No responses recorded"],
                "weaknesses": ["Assessment not completed"],
                "recommendations": ["Complete the full assessment"],
                "duration_minutes": 0,
                "technical_proficiency": "Unknown",
                "communication_skills": "Unknown",
                "problem_solving": "Unknown",
                "final_feedback": "Assessment was not completed."
            }

        # Calculate overall statistics
        valid_responses = [r for r in responses if r.get('score') is not None]
        overall_score = sum(r['score'] for r in valid_responses) / len(valid_responses) if valid_responses else 0.0

        # Group by category (if available in response data)
        category_scores = {}
        for response in valid_responses:
            category = response.get('ai_evaluation', {}).get('category', 'General')
            if category not in category_scores:
                category_scores[category] = []
            category_scores[category].append(response['score'])

        skill_breakdown = {cat: sum(scores)/len(scores) for cat, scores in category_scores.items()}

        # Determine proficiency levels
        if overall_score >= 90:
            technical_proficiency = "Expert"
            communication_skills = "Excellent"
            problem_solving = "Advanced"
        elif overall_score >= 75:
            technical_proficiency = "Advanced"
            communication_skills = "Good"
            problem_solving = "Good"
        elif overall_score >= 60:
            technical_proficiency = "Intermediate"
            communication_skills = "Adequate"
            problem_solving = "Developing"
        else:
            technical_proficiency = "Beginner"
            communication_skills = "Needs Improvement"
            problem_solving = "Basic"

        # Generate insights based on responses
        strengths = []
        weaknesses = []
        recommendations = []

        # Analyze response patterns
        high_scores = len([r for r in valid_responses if r['score'] >= 80])
        low_scores = len([r for r in valid_responses if r['score'] < 60])

        if high_scores > len(valid_responses) * 0.7:
            strengths.append("Strong technical knowledge demonstrated")
        if low_scores > len(valid_responses) * 0.3:
            weaknesses.append("Inconsistent performance across questions")

        # Basic recommendations
        if technical_proficiency == "Beginner":
            recommendations.extend([
                "Start with Excel basics and core functions",
                "Practice with sample datasets",
                "Take introductory Excel courses"
            ])
        elif technical_proficiency == "Intermediate":
            recommendations.extend([
                "Focus on advanced functions and data analysis",
                "Learn pivot tables and charts",
                "Practice with real-world scenarios"
            ])
        else:
            recommendations.extend([
                "Explore advanced Excel features like Power Query",
                "Consider Excel certification",
                "Mentor others in Excel skills"
            ])

        return {
            "overall_score": round(overall_score, 2),
            "skill_breakdown": {k: round(v, 2) for k, v in skill_breakdown.items()},
            "strengths": strengths or ["Completed assessment", "Engaged with questions"],
            "weaknesses": weaknesses or ["Could benefit from more practice"],
            "recommendations": recommendations,
            "duration_minutes": 0,  # Would need to calculate from timestamps
            "technical_proficiency": technical_proficiency,
            "communication_skills": communication_skills,
            "problem_solving": problem_solving,
            "final_feedback": f"Overall performance shows {technical_proficiency.lower()} level Excel skills with room for growth in specific areas."
        }
    
    def _get_fallback_question(self, category: SkillCategory, difficulty: Difficulty) -> Question:
        """Fallback questions if LLM fails"""
        fallback_questions = {
            SkillCategory.FORMULAS: {
                Difficulty.EASY: "Explain the difference between SUM and SUMIF functions.",
                Difficulty.MEDIUM: "How would you calculate a weighted average in Excel?",
                Difficulty.HARD: "Describe how to use array formulas for complex calculations."
            },
            SkillCategory.PIVOT_TABLES: {
                Difficulty.EASY: "What is a pivot table and when would you use it?",
                Difficulty.MEDIUM: "How do you create a pivot table with multiple value fields?",
                Difficulty.HARD: "Explain how to use calculated fields in pivot tables."
            }
            # Add more fallback questions as needed
        }
        
        question_text = fallback_questions.get(category, {}).get(
            difficulty, 
            "Describe your experience with Excel."
        )
        
        return Question(
            id=1,
            category=category,
            difficulty=difficulty,
            question=question_text,
            keywords=["excel", "data"],
            max_score=10
        )
    
    def _simple_evaluation(self, question: Question, response: str) -> EvaluationResult:
        """Simple keyword-based evaluation as fallback"""
        response_lower = response.lower()
        matched_keywords = sum(1 for keyword in question.keywords if keyword.lower() in response_lower)
        score = (matched_keywords / max(len(question.keywords), 1)) * 100
        
        return EvaluationResult(
            score=score,
            feedback="Response evaluated based on keyword matching.",
            strengths=["Attempted answer"],
            improvements=["Could provide more detail"],
            difficulty_adjustment="maintain"
        )
    
    def _calculate_category_scores(self, responses: List[Dict]) -> Dict[str, float]:
        """Calculate scores by category"""
        category_scores = {}
        category_counts = {}
        
        for response in responses:
            category = response.get("category", "Unknown")
            score = response.get("score", 0)
            
            if category not in category_scores:
                category_scores[category] = 0
                category_counts[category] = 0
            
            category_scores[category] += score
            category_counts[category] += 1
        
        # Calculate averages
        for category in category_scores:
            if category_counts[category] > 0:
                category_scores[category] /= category_counts[category]
        
        return category_scores
    
    def _extract_json(self, content: str) -> Dict[str, Any]:
        """Extract JSON from LLM response content"""
        try:
            # Try direct JSON parsing first
            return json.loads(content.strip())
        except json.JSONDecodeError:
            # If direct parsing fails, try to find JSON within the text
            import re
            # Look for JSON-like content between braces
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            
            # If no valid JSON found, return a default structure
            logger.warning(f"Could not parse JSON from content: {content}")
            return {
                "question": "What is your experience with Excel?",
                "keywords": ["excel", "experience"],
                "follow_up": "Can you provide more details?",
                "score": 50,
                "feedback": "Response received but could not be properly evaluated.",
                "strengths": ["Participated in assessment"],
                "improvements": ["Provide more detailed responses"],
                "difficulty_adjustment": "maintain",
                "skill_level": "Intermediate",
                "strengths": ["Engaged with the assessment"],
                "improvements": ["Provide more comprehensive answers"],
                "recommendations": ["Continue practicing Excel skills"]
            }
    
    def _generate_basic_report(self, session: InterviewSession) -> InterviewReport:
        """Generate a basic report as fallback"""
        # Calculate duration
        duration = int((datetime.now() - session.start_time).total_seconds() / 60)
        
        # Calculate category scores
        category_scores = self._calculate_category_scores(session.responses)
        
        # Determine skill level based on average score
        avg_score = session.total_score / max(len(session.responses), 1)
        if avg_score >= 90:
            skill_level = "Expert"
        elif avg_score >= 75:
            skill_level = "Advanced"
        elif avg_score >= 60:
            skill_level = "Intermediate"
        else:
            skill_level = "Beginner"
        
        return InterviewReport(
            session_id=session.session_id,
            total_score=avg_score,
            duration_minutes=duration,
            skill_level=skill_level,
            strengths=["Attempted all questions", "Showed engagement"],
            improvements=["Could provide more detailed responses"],
            recommendations=["Continue practicing Excel skills", "Focus on weak areas"],
            category_scores=category_scores
        )
