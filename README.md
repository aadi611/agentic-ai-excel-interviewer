Excel Skills Assessment Platform

An AI-powered interview system that evaluates Microsoft Excel skills through conversational questioning.
What This Does

AI Interviewer: Conducts natural conversations to assess Excel knowledge
Adaptive Questions: Adjusts difficulty based on your answers
Real-time Scoring: Provides immediate feedback and evaluation
Comprehensive Reports: Generates detailed skill assessments

Quick Setup
1. Get the Code
bashgit clone <your-repo-url>
cd excel-assessment-platform
2. Install Python Dependencies
bashpip install -r requirements.txt
3. Get a Groq API Key

Go to https://groq.com
Sign up for a free account
Get your API key from the dashboard

4. Configure Environment
Create a .env file in the project folder:
GROQ_API_KEY=your_groq_api_key_here
PORT=8000
5. Run the Application
bashpython main.py
6. Use the Platform
Open your browser and go to: http://localhost:8000
How It Works

Start Assessment: Click "Begin Assessment"
Answer Questions: The AI asks Excel-related questions
Get Evaluated: Each answer is scored in real-time
View Report: Get a detailed skills report at the end

Files Overview

main.py - Main application server
interview_manager.py - Handles the interview logic
llm_service.py - Connects to Groq AI
index.html - Web interface
requirements.txt - Python packages needed

API Endpoints

POST /api/session/create - Start new interview
POST /api/session/{id}/start - Begin questions
POST /api/session/{id}/respond - Submit answers
GET /api/session/{id}/report - Get final report

Requirements

Python 3.8+
Groq API key (free)
Web browser

That's it! The system uses in-memory storage for development, so no database setup is needed.
