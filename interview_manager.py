from typing import Dict, Optional, List, Any
import uuid
from datetime import datetime, timedelta
import logging
import asyncio
import json

from config import Config
from models import InterviewSession, InterviewState, SkillCategory, Difficulty, Question
from llm_service import LLMService
from database_service import DatabaseService

logger = logging.getLogger(__name__)

class InterviewManager:
    """Enhanced Agentic Interview Manager with conversational intelligence"""

    def __init__(self, llm_service: LLMService, db_service: DatabaseService):
        self.llm_service = llm_service
        self.db_service = db_service
        self.question_pool = self._initialize_question_pool()

    async def create_session(self, candidate_data: Optional[Dict[str, Any]] = None) -> str:
        """Create a new interview session with enhanced tracking"""
        session_id = str(uuid.uuid4())

        # Create candidate record if data provided
        candidate_id = None
        if candidate_data:
            candidate = await self.db_service.create_candidate(candidate_data)
            candidate_id = candidate['id']

        # Enhanced session data with conversation tracking
        session_data = {
            'session_id': session_id,
            'candidate_id': candidate_id,
            'state': InterviewState.INIT.value,
            'skill_category': SkillCategory.FORMULAS.value,
            'difficulty': Difficulty.MEDIUM.value,
            'current_question_index': 0,
            'total_questions': Config.MAX_QUESTIONS,
            'score': 0.0,
            'started_at': datetime.utcnow().isoformat(),
            'conversation_context': [],
            'candidate_profile': {
                'experience_level': 'unknown',
                'strengths': [],
                'weaknesses': [],
                'response_patterns': [],
                'engagement_level': 'neutral'
            },
            'interview_flow': {
                'introduction_complete': False,
                'technical_assessment_started': False,
                'depth_questions_asked': 0,
                'follow_up_questions': 0
            }
        }

        await self.db_service.create_interview_session(session_data)
        logger.info(f"Created enhanced session: {session_id}")
        return session_id

    async def start_interview(self, session_id: str) -> Dict[str, Any]:
        """Start interview with intelligent introduction"""
        session_data = await self.db_service.get_interview_session(session_id)
        if not session_data:
            raise ValueError(f"Session {session_id} not found")

        # Update session state with conversation context
        conversation_context = [{
            "role": "system",
            "content": """You are an expert Excel interviewer conducting a professional assessment. 
            You should be conversational, encouraging, and adaptive. Your goal is to:
            1. Build rapport and put the candidate at ease
            2. Assess their Excel skills through thoughtful questions
            3. Adapt your approach based on their responses
            4. Provide constructive feedback throughout
            5. Maintain a professional yet friendly tone"""
        }]

        await self.db_service.update_interview_session(session_id, {
            'state': InterviewState.INTRO.value,
            'conversation_context': conversation_context
        })

        intro_message = """Hello! I'm your AI interviewer conducting your Excel skills assessment today.

Format: 10 questions over 25 minutes covering technical concepts, problem-solving, creativity, and domain expertise.

How it works: I'll adapt questions based on your responses and evaluate your technical knowledge, thought process, and practical application skills in real-time.

Tips for success:
• Be specific with examples
• Explain your reasoning  
• Share alternative approaches when possible

Let's begin: What's your background with Excel, what do you primarily use it for, and how would you describe your current skill level?""" 
        
        return {
            "session_id": session_id,
            "message": intro_message,
            "state": InterviewState.INTRO.value,
            "interview_stage": "introduction",
            "guidance": "Take your time to share your Excel experience. I'm here to learn about YOU!"
        }

    async def process_response(self, session_id: str, user_response: str) -> Dict[str, Any]:
        """Process user response with intelligent conversation management"""
        session_data = await self.db_service.get_interview_session(session_id)
        if not session_data:
            raise ValueError(f"Session {session_id} not found")

        current_state = InterviewState(session_data['state'])
        conversation_context = session_data.get('conversation_context', [])
        candidate_profile = session_data.get('candidate_profile', {})
        interview_flow = session_data.get('interview_flow', {})

        # Add user response to conversation context
        conversation_context.append({
            "role": "user", 
            "content": user_response,
            "timestamp": datetime.utcnow().isoformat()
        })

        if current_state == InterviewState.INTRO:
            return await self._handle_intelligent_introduction(
                session_id, session_data, user_response, conversation_context, candidate_profile, interview_flow
            )

        elif current_state == InterviewState.QUESTIONING:
            return await self._handle_adaptive_questioning(
                session_id, session_data, user_response, conversation_context, candidate_profile, interview_flow
            )

        elif current_state == InterviewState.COMPLETED:
            return {
                "session_id": session_id,
                "message": "Thank you for completing the assessment! Your comprehensive report has been generated.",
                "state": current_state.value,
                "interview_stage": "completed"
            }

        return {
            "session_id": session_id,
            "message": "I'm processing your response. Please give me a moment...",
            "state": current_state.value,
            "interview_stage": "processing"
        }

    async def _handle_intelligent_introduction(self, session_id: str, session_data: Dict[str, Any], 
                                             intro: str, conversation_context: List[Dict], 
                                             candidate_profile: Dict, interview_flow: Dict) -> Dict[str, Any]:
        """Handle introduction with intelligent profiling and adaptive response"""
        
        # Analyze the introduction using LLM
        analysis_prompt = f"""Analyze this candidate's Excel introduction and extract key insights:
        
        Introduction: "{intro}"
        
        Please provide a JSON response with:
        {{
            "experience_level": "beginner|intermediate|advanced|expert",
            "primary_use_cases": ["list", "of", "use", "cases"],
            "mentioned_skills": ["list", "of", "skills"],
            "confidence_indicators": ["indicators", "of", "confidence"],
            "areas_to_explore": ["areas", "to", "dive", "deeper"],
            "suggested_starting_difficulty": "easy|medium|hard",
            "personality_traits": ["traits", "observed"],
            "next_question_focus": "what area to focus on first"
        }}"""

        try:
            # Clean conversation context for API call (remove timestamps and extra fields)
            clean_context = [
                {"role": msg["role"], "content": msg["content"]} 
                for msg in conversation_context 
                if "role" in msg and "content" in msg
            ]
            
            analysis_response = await asyncio.get_event_loop().run_in_executor(
                None, self.llm_service._make_request, 
                [{"role": "system", "content": "You are an expert interviewer analyzer. Respond only with valid JSON."},
                 {"role": "user", "content": analysis_prompt}],
                0.3, 400
            )
            
            analysis = self.llm_service._extract_json(analysis_response["choices"][0]["message"]["content"])
            
            # Update candidate profile with analysis
            candidate_profile.update({
                'experience_level': analysis.get('experience_level', 'intermediate'),
                'mentioned_skills': analysis.get('mentioned_skills', []),
                'confidence_indicators': analysis.get('confidence_indicators', []),
                'areas_to_explore': analysis.get('areas_to_explore', []),
                'personality_traits': analysis.get('personality_traits', []),
                'primary_use_cases': analysis.get('primary_use_cases', [])
            })
            
            # Generate personalized transition message
            transition_prompt = f"""Based on this analysis, create a brief, encouraging response:
            
            Analysis: {json.dumps(analysis, indent=2)}
            Candidate Introduction: "{intro}"
            
            Create a SHORT response (2-3 sentences max) that:
            1. Warmly acknowledges their experience (use encouraging phrases like: "That sounds fantastic", "Great background", "I love that you", "Wonderful experience", "That's really valuable", etc.)
            2. Asks one focused technical question based on their level with enthusiasm
            
            AVOID repetitive phrases like "I appreciate" or "Thank you for". Use natural, encouraging, and supportive language."""

            # Clean conversation context for API call
            clean_context = [
                {"role": msg["role"], "content": msg["content"]} 
                for msg in conversation_context 
                if "role" in msg and "content" in msg
            ]

            response_data = await asyncio.get_event_loop().run_in_executor(
                None, self.llm_service._make_request,
                [{"role": "system", "content": "You are an enthusiastic Excel interviewer. Keep responses to 2-3 sentences maximum. Use warm, encouraging, and supportive language. NEVER start with 'I appreciate' or 'Thank you for'. Be genuinely excited about their knowledge and progress."},
                 {"role": "user", "content": transition_prompt}],
                0.7, 200
            )
            
            ai_response = response_data["choices"][0]["message"]["content"]
            
            # Update conversation context
            conversation_context.append({
                "role": "assistant",
                "content": ai_response,
                "timestamp": datetime.utcnow().isoformat(),
                "analysis": analysis
            })
            
            # Update interview flow
            interview_flow.update({
                'introduction_complete': True,
                'technical_assessment_started': True,
                'analysis_insights': analysis
            })
            
            # Update session with enhanced data
            await self.db_service.update_interview_session(session_id, {
                'state': InterviewState.QUESTIONING.value,
                'difficulty': analysis.get('suggested_starting_difficulty', 'medium'),
                'conversation_context': conversation_context,
                'candidate_profile': candidate_profile,
                'interview_flow': interview_flow
            })

            return {
                "session_id": session_id,
                "message": ai_response,
                "state": InterviewState.QUESTIONING.value,
                "question_number": 1,
                "total_questions": Config.MAX_QUESTIONS,
                "interview_stage": "technical_assessment",
                "candidate_insights": {
                    "experience_level": analysis.get('experience_level'),
                    "focus_areas": analysis.get('areas_to_explore', [])[:3],
                    "confidence_level": "high" if len(analysis.get('confidence_indicators', [])) > 2 else "moderate"
                },
                "guidance": "I'm now asking questions tailored to your experience level. Feel free to elaborate!"
            }
            
        except Exception as e:
            logger.error(f"Error in intelligent introduction analysis: {e}")
            # Fallback to simpler handling
            return await self._fallback_introduction_handling(session_id, session_data, intro)

    async def _handle_adaptive_questioning(self, session_id: str, session_data: Dict[str, Any], 
                                           response: str, conversation_context: List[Dict], 
                                           candidate_profile: Dict, interview_flow: Dict) -> Dict[str, Any]:
        """Handle questioning with adaptive intelligence and conversation awareness"""
        
        current_index = session_data['current_question_index']
        
        # Get the current question context
        responses = await self.db_service.get_interview_responses(session_id)
        
        # Comprehensive evaluation using conversation context
        evaluation_prompt = f"""You are an expert Excel interviewer. Evaluate this response comprehensively:
        
        CONVERSATION HISTORY:
        {json.dumps(conversation_context[-4:], indent=2)}
        
        CANDIDATE PROFILE:
        {json.dumps(candidate_profile, indent=2)}
        
        CURRENT RESPONSE: "{response}"
        
        Provide detailed evaluation in JSON format:
        {{
            "technical_accuracy": {{"score": 0-100, "reasoning": "explanation"}},
            "depth_of_knowledge": {{"score": 0-100, "indicators": ["what shows depth"]}},
            "communication_clarity": {{"score": 0-100, "strengths": ["clear aspects"]}},
            "practical_understanding": {{"score": 0-100, "examples": ["practical elements"]}},
            "overall_score": 0-100,
            "key_strengths": ["strength1", "strength2"],
            "areas_for_improvement": ["area1", "area2"],
            "follow_up_suggestions": ["follow-up question topics"],
            "difficulty_adjustment": "increase|maintain|decrease",
            "engagement_level": "high|medium|low",
            "confidence_indicators": ["what shows confidence"],
            "knowledge_gaps": ["identified gaps"],
            "next_focus_area": "what to explore next",
            "personalized_feedback": "encouraging, specific feedback"
        }}"""

        try:
            # Clean conversation context for API call
            clean_context = [
                {"role": msg["role"], "content": msg["content"]} 
                for msg in conversation_context[-4:] 
                if "role" in msg and "content" in msg
            ]
            
            evaluation_response = await asyncio.get_event_loop().run_in_executor(
                None, self.llm_service._make_request,
                [{"role": "system", "content": "You are an expert Excel skills evaluator. Respond only with valid JSON."},
                 {"role": "user", "content": evaluation_prompt}],
                0.3, 600
            )
            
            evaluation = self.llm_service._extract_json(evaluation_response["choices"][0]["message"]["content"])
            
            # Save detailed response evaluation
            await self.db_service.save_interview_response({
                'session_id': session_id,
                'question_index': current_index,
                'question_text': conversation_context[-2]['content'] if len(conversation_context) > 1 else "Previous question",
                'candidate_answer': response,
                'ai_evaluation': evaluation,
                'score': evaluation.get('overall_score', 0),
                'feedback': evaluation.get('personalized_feedback', 'Good response'),
                'response_time_seconds': 0,
                'conversation_context': conversation_context[-2:]
            })

            # Update candidate profile with new insights
            candidate_profile['strengths'].extend(evaluation.get('key_strengths', []))
            candidate_profile['weaknesses'].extend(evaluation.get('areas_for_improvement', []))
            candidate_profile['engagement_level'] = evaluation.get('engagement_level', 'medium')
            candidate_profile['response_patterns'].append({
                'question_index': current_index,
                'accuracy': evaluation.get('technical_accuracy', {}).get('score', 0),
                'depth': evaluation.get('depth_of_knowledge', {}).get('score', 0),
                'clarity': evaluation.get('communication_clarity', {}).get('score', 0)
            })

            # Update session tracking
            new_index = current_index + 1
            new_score = session_data['score'] + evaluation.get('overall_score', 0)

            # Determine if we need follow-up questions
            should_ask_followup = (
                evaluation.get('depth_of_knowledge', {}).get('score', 0) > 80 and
                interview_flow.get('follow_up_questions', 0) < 2 and
                len(evaluation.get('follow_up_suggestions', [])) > 0
            )

            if should_ask_followup:
                # Generate intelligent follow-up question
                followup_result = await self._generate_intelligent_followup(
                    session_id, conversation_context, evaluation, candidate_profile
                )
                interview_flow['follow_up_questions'] = interview_flow.get('follow_up_questions', 0) + 1
                
                # Update conversation context
                conversation_context.append({
                    "role": "assistant",
                    "content": followup_result['message'],
                    "timestamp": datetime.utcnow().isoformat(),
                    "question_type": "follow_up",
                    "evaluation": evaluation
                })

                await self.db_service.update_interview_session(session_id, {
                    'conversation_context': conversation_context,
                    'candidate_profile': candidate_profile,
                    'interview_flow': interview_flow,
                    'score': new_score
                })

                return followup_result

            # Check if interview should be completed
            if new_index >= Config.MAX_QUESTIONS:
                return await self._complete_intelligent_interview(session_id, session_data, conversation_context, candidate_profile)

            # Generate next adaptive question
            next_question_result = await self._generate_adaptive_next_question(
                session_id, conversation_context, evaluation, candidate_profile, new_index
            )

            # Update session state
            await self.db_service.update_interview_session(session_id, {
                'current_question_index': new_index,
                'score': new_score,
                'difficulty': evaluation.get('difficulty_adjustment', session_data['difficulty']),
                'conversation_context': conversation_context + [{"role": "assistant", "content": next_question_result['message']}],
                'candidate_profile': candidate_profile,
                'interview_flow': interview_flow
            })

            return next_question_result

        except Exception as e:
            logger.error(f"Error in adaptive questioning: {e}")
            return await self._fallback_question_handling(session_id, session_data, response)

    async def _generate_intelligent_followup(self, session_id: str, conversation_context: List[Dict], 
                                            evaluation: Dict, candidate_profile: Dict) -> Dict[str, Any]:
        """Generate intelligent follow-up questions based on strong responses"""
        
        followup_prompt = f"""Based on this response, create a brief follow-up:
        
        CONVERSATION CONTEXT:
        {json.dumps(conversation_context[-3:], indent=2)}
        
        EVALUATION INSIGHTS:
        {json.dumps(evaluation, indent=2)}
        
        Create a SHORT follow-up (1-2 sentences max):
        1. Enthusiastic positive comment (use encouraging phrases like: "Excellent!", "That's brilliant", "Love that approach", "You're on the right track", "Fantastic thinking", "That's really smart", etc.)
        2. One focused follow-up question with genuine interest
        
        AVOID repetitive starts like "I appreciate" or "Thank you for". Be encouraging, enthusiastic, and supportive."""

        try:
            # Clean conversation context for API call
            clean_context = [
                {"role": msg["role"], "content": msg["content"]} 
                for msg in conversation_context[-3:] 
                if "role" in msg and "content" in msg
            ]
            
            response_data = await asyncio.get_event_loop().run_in_executor(
                None, self.llm_service._make_request,
                [{"role": "system", "content": "You are an Excel interviewer. Keep responses to 1-2 sentences maximum. Use varied, natural language. AVOID 'I appreciate' or 'Thank you for'. Be brief and focused."},
                 {"role": "user", "content": followup_prompt}],
                0.7, 150
            )
            
            followup_message = response_data["choices"][0]["message"]["content"]
            
            return {
                "session_id": session_id,
                "message": followup_message,
                "state": InterviewState.QUESTIONING.value,
                "interview_stage": "follow_up_exploration",
                "question_type": "follow_up",
                "guidance": "Great response! I'd love to explore this further with you."
            }
            
        except Exception as e:
            logger.error(f"Error generating follow-up: {e}")
            return {
                "session_id": session_id,
                "message": "That's a great response! Could you tell me about a specific situation where you've applied this knowledge?",
                "state": InterviewState.QUESTIONING.value,
                "interview_stage": "follow_up_exploration",
                "question_type": "follow_up"
            }

    async def _generate_adaptive_next_question(self, session_id: str, conversation_context: List[Dict], 
                                             evaluation: Dict, candidate_profile: Dict, question_index: int) -> Dict[str, Any]:
        """Generate the next question adaptively based on conversation flow"""
        
        adaptive_prompt = f"""Generate a brief next interview question:
        
        CONVERSATION HISTORY:
        {json.dumps(conversation_context[-4:], indent=2)}
        
        LATEST EVALUATION:
        {json.dumps(evaluation, indent=2)}
        
        QUESTION #{question_index + 1} of {Config.MAX_QUESTIONS}
        
        Create a SHORT response (2-3 sentences max):
        1. Encouraging positive comment (use supportive phrases like: "Outstanding!", "You really know your stuff", "That's impressive", "Well done", "Perfect explanation", "You're doing great", "Awesome insight", etc.)
        2. One focused Excel question with genuine enthusiasm
        
        AVOID starting with "I appreciate" or "Thank you for". Use encouraging, supportive, and enthusiastic language."""

        try:
            # Clean conversation context for API call
            clean_context = [
                {"role": msg["role"], "content": msg["content"]} 
                for msg in conversation_context[-4:] 
                if "role" in msg and "content" in msg
            ]
            
            response_data = await asyncio.get_event_loop().run_in_executor(
                None, self.llm_service._make_request,
                [{"role": "system", "content": "You are an Excel interviewer. Keep responses to 2-3 sentences maximum. Use varied, natural language. AVOID repetitive phrases like 'I appreciate' or 'Thank you for'. Be brief, encouraging, and focused."},
                 {"role": "user", "content": adaptive_prompt}],
                0.7, 200
            )
            
            next_question = response_data["choices"][0]["message"]["content"]
            
            return {
                "session_id": session_id,
                "message": next_question,
                "state": InterviewState.QUESTIONING.value,
                "question_number": question_index + 1,
                "total_questions": Config.MAX_QUESTIONS,
                "interview_stage": "adaptive_questioning",
                "evaluation_summary": {
                    "last_score": evaluation.get('overall_score', 0),
                    "key_strengths": evaluation.get('key_strengths', [])[:2],
                    "focus_area": evaluation.get('next_focus_area', 'general')
                },
                "guidance": "Building on your previous response..."
            }
            
        except Exception as e:
            logger.error(f"Error generating adaptive question: {e}")
            return await self._fallback_next_question(session_id, question_index)

    async def _complete_intelligent_interview(self, session_id: str, session_data: Dict[str, Any], 
                                            conversation_context: List[Dict], candidate_profile: Dict) -> Dict[str, Any]:
        """Complete interview with intelligent summary and comprehensive report"""
        
        # Update session state
        await self.db_service.update_interview_session(session_id, {
            'state': InterviewState.COMPLETED.value,
            'completed_at': datetime.utcnow().isoformat(),
            'conversation_context': conversation_context,
            'candidate_profile': candidate_profile
        })

        # Get all responses for comprehensive analysis
        responses = await self.db_service.get_interview_responses(session_id)

        # Generate intelligent completion message
        completion_prompt = f"""Create a warm, personalized completion message based on this interview:
        
        CANDIDATE PROFILE:
        {json.dumps(candidate_profile, indent=2)}
        
        CONVERSATION SUMMARY:
        - Total responses: {len(responses)}
        - Average engagement: {candidate_profile.get('engagement_level', 'good')}
        - Key strengths: {candidate_profile.get('strengths', [])}
        
        Create a message that:
        1. Thanks them personally and warmly
        2. Acknowledges specific strengths you observed
        3. Builds excitement for the detailed report
        4. Feels like a natural conclusion to your conversation
        5. Maintains the encouraging, professional tone"""

        try:
            # Clean conversation context for API call
            clean_context = [
                {"role": msg["role"], "content": msg["content"]} 
                for msg in conversation_context 
                if "role" in msg and "content" in msg
            ]
            
            completion_response = await asyncio.get_event_loop().run_in_executor(
                None, self.llm_service._make_request,
                [{"role": "system", "content": "You are concluding a successful interview warmly and professionally."},
                 {"role": "user", "content": completion_prompt}],
                0.7, 300
            )
            
            completion_message = completion_response["choices"][0]["message"]["content"]
            
            # Generate comprehensive report using enhanced data
            report = await self._generate_comprehensive_report(session_id, responses, conversation_context, candidate_profile)

            # Save the enhanced report
            await self.db_service.save_evaluation_report({
                'session_id': session_id,
                'overall_score': report.get('overall_score', 0.0),
                'skill_breakdown': report.get('skill_breakdown', {}),
                'strengths': report.get('strengths', []),
                'weaknesses': report.get('weaknesses', []),
                'recommendations': report.get('recommendations', []),
                'interview_duration_minutes': report.get('duration_minutes', 0),
                'technical_proficiency': report.get('technical_proficiency', 'Intermediate'),
                'communication_skills': report.get('communication_skills', 'Good'),
                'problem_solving': report.get('problem_solving', 'Developing'),
                'final_feedback': completion_message,
                'conversation_insights': candidate_profile,
                'engagement_analysis': report.get('engagement_analysis', {}),
                'learning_recommendations': report.get('learning_recommendations', [])
            })

            return {
                "session_id": session_id,
                "message": completion_message,
                "state": InterviewState.COMPLETED.value,
                "interview_stage": "completed",
                "report": report,
                "interview_summary": {
                    "total_questions": len(responses),
                    "engagement_level": candidate_profile.get('engagement_level', 'good'),
                    "key_insights": candidate_profile.get('strengths', [])[:3]
                }
            }
            
        except Exception as e:
            logger.error(f"Error in intelligent completion: {e}")
            return await self._fallback_completion(session_id, session_data)

    async def _generate_comprehensive_report(self, session_id: str, responses: List[Dict], 
                                           conversation_context: List[Dict], candidate_profile: Dict) -> Dict[str, Any]:
        """Generate comprehensive report using all conversation data"""
        
        report_prompt = f"""Generate a comprehensive Excel skills assessment report:
        
        CANDIDATE PROFILE:
        {json.dumps(candidate_profile, indent=2)}
        
        RESPONSE ANALYSIS:
        - Total responses: {len(responses)}
        - Response patterns: {candidate_profile.get('response_patterns', [])}
        
        CONVERSATION INSIGHTS:
        - Engagement level: {candidate_profile.get('engagement_level', 'medium')}
        - Communication style: Professional and clear
        - Areas explored: {candidate_profile.get('areas_to_explore', [])}
        
        Create a detailed JSON report with:
        {{
            "overall_score": 0-100,
            "technical_proficiency": "Beginner|Intermediate|Advanced|Expert",
            "communication_skills": "Excellent|Good|Fair|Needs Improvement",
            "problem_solving": "Advanced|Good|Developing|Basic",
            "engagement_analysis": {{
                "participation_level": "high|medium|low",
                "detail_in_responses": "comprehensive|adequate|basic",
                "enthusiasm_indicators": ["observed indicators"]
            }},
            "skill_breakdown": {{
                "formulas": 0-100,
                "data_analysis": 0-100,
                "pivot_tables": 0-100,
                "charting": 0-100,
                "general_excel": 0-100
            }},
            "strengths": ["specific strengths observed"],
            "weaknesses": ["areas needing development"],
            "recommendations": ["specific actionable recommendations"],
            "learning_recommendations": ["tailored learning paths"],
            "final_feedback": "personalized summary of their performance"
        }}"""

        try:
            # Clean conversation context for API call
            clean_context = [
                {"role": msg["role"], "content": msg["content"]} 
                for msg in conversation_context 
                if "role" in msg and "content" in msg
            ]
            
            report_response = await asyncio.get_event_loop().run_in_executor(
                None, self.llm_service._make_request,
                [{"role": "system", "content": "You are generating a comprehensive skills assessment report. Respond only with valid JSON."},
                 {"role": "user", "content": report_prompt}],
                0.3, 800
            )
            
            return self.llm_service._extract_json(report_response["choices"][0]["message"]["content"])
            
        except Exception as e:
            logger.error(f"Error generating comprehensive report: {e}")
            return await self.llm_service.generate_report_from_data(responses)

    # Fallback methods for error handling
    async def _fallback_introduction_handling(self, session_id: str, session_data: Dict[str, Any], intro: str) -> Dict[str, Any]:
        """Fallback method for introduction handling"""
        await self.db_service.update_interview_session(session_id, {
            'state': InterviewState.QUESTIONING.value,
            'candidate_profile': {'experience_level': 'intermediate', 'engagement_level': 'medium'}
        })
        
        return {
            "session_id": session_id,
            "message": "Thank you for sharing your background! I can see you have valuable Excel experience. Let's dive into some questions to explore your skills further.\n\nLet's start with this: How would you approach analyzing a large dataset in Excel to identify trends and outliers?",
            "state": InterviewState.QUESTIONING.value,
            "question_number": 1,
            "total_questions": Config.MAX_QUESTIONS,
            "interview_stage": "technical_assessment"
        }

    async def _fallback_question_handling(self, session_id: str, session_data: Dict[str, Any], response: str) -> Dict[str, Any]:
        """Fallback method for question response handling"""
        current_index = session_data['current_question_index']
        new_index = current_index + 1
        
        if new_index >= Config.MAX_QUESTIONS:
            return await self._fallback_completion(session_id, session_data)
        
        return {
            "session_id": session_id,
            "message": "Thank you for that response. Let me ask you about another Excel topic: What's your experience with Excel's lookup functions like VLOOKUP or XLOOKUP?",
            "state": InterviewState.QUESTIONING.value,
            "question_number": new_index + 1,
            "total_questions": Config.MAX_QUESTIONS,
            "interview_stage": "technical_assessment"
        }

    async def _fallback_next_question(self, session_id: str, question_index: int) -> Dict[str, Any]:
        """Fallback method for generating next question"""
        questions = [
            "How do you handle data validation in Excel?",
            "What's your approach to creating dynamic charts?",
            "Tell me about your experience with Excel macros or VBA.",
            "How would you troubleshoot a formula that's not working as expected?",
            "What Excel features do you find most useful for data analysis?"
        ]
        
        question = questions[min(question_index % len(questions), len(questions) - 1)]
        
        return {
            "session_id": session_id,
            "message": f"Great! Let's explore another area. {question}",
            "state": InterviewState.QUESTIONING.value,
            "question_number": question_index + 1,
            "total_questions": Config.MAX_QUESTIONS,
            "interview_stage": "technical_assessment"
        }

    async def _fallback_completion(self, session_id: str, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback method for interview completion"""
        await self.db_service.update_interview_session(session_id, {
            'state': InterviewState.COMPLETED.value,
            'completed_at': datetime.utcnow().isoformat()
        })

        responses = await self.db_service.get_interview_responses(session_id)
        report = await self.llm_service.generate_report_from_data(responses)

        await self.db_service.save_evaluation_report({
            'session_id': session_id,
            'overall_score': report.get('overall_score', 0.0),
            'skill_breakdown': report.get('skill_breakdown', {}),
            'strengths': report.get('strengths', []),
            'weaknesses': report.get('weaknesses', []),
            'recommendations': report.get('recommendations', []),
            'final_feedback': "Thank you for completing the Excel assessment!"
        })

        return {
            "session_id": session_id,
            "message": "Thank you for completing the Excel skills assessment! It's been a pleasure learning about your experience and skills. Your detailed report is now ready.",
            "state": InterviewState.COMPLETED.value,
            "interview_stage": "completed",
            "report": report
        }

    def _select_next_category(self, session_data: Dict[str, Any]) -> SkillCategory:
        """Select next category to test"""
        all_categories = list(SkillCategory)
        current_index = session_data.get('current_question_index', 0)

        # Simple rotation through categories
        return all_categories[current_index % len(all_categories)]

    def _increase_difficulty(self, current: Difficulty) -> Difficulty:
        """Increase difficulty level"""
        difficulty_order = [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD, Difficulty.EXPERT]
        current_index = difficulty_order.index(current)
        return difficulty_order[min(current_index + 1, len(difficulty_order) - 1)]

    def _decrease_difficulty(self, current: Difficulty) -> Difficulty:
        """Decrease difficulty level"""
        difficulty_order = [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD, Difficulty.EXPERT]
        current_index = difficulty_order.index(current)
        return difficulty_order[max(current_index - 1, 0)]

    def _initialize_question_pool(self) -> List[Question]:
        """Initialize backup question pool"""
        return [
            Question(
                id=1,
                category=SkillCategory.FORMULAS,
                difficulty=Difficulty.EASY,
                question="What is the difference between relative and absolute cell references?",
                keywords=["relative", "absolute", "$", "dollar", "reference"],
                max_score=10
            ),
            # Add more backup questions here
        ]

    async def cleanup_old_sessions(self):
        """Clean up old completed sessions"""
        cleaned_count = await self.db_service.cleanup_old_sessions(24)  # 24 hours
        logger.info(f"Cleaned up {cleaned_count} old sessions")

