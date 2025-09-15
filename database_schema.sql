-- Supabase Database Schema for Excel Assessment Interview Platform
-- Run this SQL in your Supabase SQL Editor to create the database tables

-- Enable Row Level Security
ALTER DEFAULT PRIVILEGES REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;

-- Candidates table
CREATE TABLE IF NOT EXISTS candidates (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    resume_url TEXT,
    linkedin_url TEXT,
    github_url TEXT,
    experience_years INTEGER,
    current_position VARCHAR(255),
    skills TEXT[], -- Array of skill names
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Interview sessions table
CREATE TABLE IF NOT EXISTS interview_sessions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    candidate_id UUID REFERENCES candidates(id) ON DELETE CASCADE,
    state VARCHAR(50) NOT NULL DEFAULT 'init', -- init, questioning, evaluating, completed
    skill_category VARCHAR(100) NOT NULL,
    difficulty VARCHAR(50) NOT NULL DEFAULT 'intermediate',
    current_question_index INTEGER DEFAULT 0,
    total_questions INTEGER DEFAULT 10,
    score DECIMAL(5,2) DEFAULT 0.0,
    feedback TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    cleaned_up BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Pre-interview technical checks
CREATE TABLE IF NOT EXISTS pre_interview_checks (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL REFERENCES interview_sessions(session_id) ON DELETE CASCADE,
    check_type VARCHAR(100) NOT NULL, -- camera, microphone, internet, browser
    status VARCHAR(50) NOT NULL, -- passed, failed, warning
    details JSONB, -- Store detailed check results
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Interview responses table
CREATE TABLE IF NOT EXISTS interview_responses (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL REFERENCES interview_sessions(session_id) ON DELETE CASCADE,
    question_index INTEGER NOT NULL,
    question_text TEXT NOT NULL,
    candidate_answer TEXT,
    ai_evaluation JSONB, -- Store AI evaluation results
    score DECIMAL(5,2),
    feedback TEXT,
    response_time_seconds INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Evaluation reports table
CREATE TABLE IF NOT EXISTS evaluation_reports (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id VARCHAR(100) UNIQUE NOT NULL REFERENCES interview_sessions(session_id) ON DELETE CASCADE,
    overall_score DECIMAL(5,2) NOT NULL,
    skill_breakdown JSONB, -- Breakdown by skill categories
    strengths TEXT[],
    weaknesses TEXT[],
    recommendations TEXT[],
    interview_duration_minutes INTEGER,
    technical_proficiency VARCHAR(50),
    communication_skills VARCHAR(50),
    problem_solving VARCHAR(50),
    final_feedback TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Support incidents table
CREATE TABLE IF NOT EXISTS support_incidents (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id VARCHAR(100) REFERENCES interview_sessions(session_id) ON DELETE SET NULL,
    candidate_id UUID REFERENCES candidates(id) ON DELETE SET NULL,
    incident_type VARCHAR(100) NOT NULL, -- technical_issue, question_clarification, system_error
    severity VARCHAR(50) NOT NULL DEFAULT 'medium', -- low, medium, high, critical
    description TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'open', -- open, in_progress, resolved, closed
    assigned_to VARCHAR(255),
    resolution TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- Real-time monitoring data (for analytics)
CREATE TABLE IF NOT EXISTS monitoring_events (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL REFERENCES interview_sessions(session_id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL, -- face_detected, face_lost, tab_switch, etc.
    event_data JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_candidates_email ON candidates(email);
CREATE INDEX IF NOT EXISTS idx_interview_sessions_session_id ON interview_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_interview_sessions_candidate_id ON interview_sessions(candidate_id);
CREATE INDEX IF NOT EXISTS idx_interview_sessions_state ON interview_sessions(state);
CREATE INDEX IF NOT EXISTS idx_interview_responses_session_id ON interview_responses(session_id);
CREATE INDEX IF NOT EXISTS idx_evaluation_reports_session_id ON evaluation_reports(session_id);
CREATE INDEX IF NOT EXISTS idx_support_incidents_session_id ON support_incidents(session_id);
CREATE INDEX IF NOT EXISTS idx_support_incidents_status ON support_incidents(status);
CREATE INDEX IF NOT EXISTS idx_monitoring_events_session_id ON monitoring_events(session_id);
CREATE INDEX IF NOT EXISTS idx_monitoring_events_timestamp ON monitoring_events(timestamp);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add updated_at triggers
CREATE TRIGGER update_candidates_updated_at BEFORE UPDATE ON candidates FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_interview_sessions_updated_at BEFORE UPDATE ON interview_sessions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_support_incidents_updated_at BEFORE UPDATE ON support_incidents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (RLS) on all tables
ALTER TABLE candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE interview_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE pre_interview_checks ENABLE ROW LEVEL SECURITY;
ALTER TABLE interview_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE evaluation_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_incidents ENABLE ROW LEVEL SECURITY;
ALTER TABLE monitoring_events ENABLE ROW LEVEL SECURITY;

-- Create policies for candidates (allow candidates to read/update their own data)
CREATE POLICY "Candidates can view their own data" ON candidates
    FOR SELECT USING (auth.uid()::text = id::text);

CREATE POLICY "Candidates can update their own data" ON candidates
    FOR UPDATE USING (auth.uid()::text = id::text);

-- Create policies for interview sessions
CREATE POLICY "Users can view their own interview sessions" ON interview_sessions
    FOR SELECT USING (auth.uid()::text = candidate_id::text);

CREATE POLICY "Users can create their own interview sessions" ON interview_sessions
    FOR INSERT WITH CHECK (auth.uid()::text = candidate_id::text);

CREATE POLICY "Users can update their own interview sessions" ON interview_sessions
    FOR UPDATE USING (auth.uid()::text = candidate_id::text);

-- Create policies for other tables (similar pattern)
CREATE POLICY "Users can view their own responses" ON interview_responses
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM interview_sessions
            WHERE interview_sessions.session_id = interview_responses.session_id
            AND interview_sessions.candidate_id::text = auth.uid()::text
        )
    );

CREATE POLICY "Users can create their own responses" ON interview_responses
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM interview_sessions
            WHERE interview_sessions.session_id = interview_responses.session_id
            AND interview_sessions.candidate_id::text = auth.uid()::text
        )
    );

-- Similar policies for other tables...
-- (Policies for evaluation_reports, support_incidents, etc. would follow the same pattern)

-- Create a function to get session statistics
CREATE OR REPLACE FUNCTION get_session_statistics(start_date TIMESTAMP WITH TIME ZONE DEFAULT NULL, end_date TIMESTAMP WITH TIME ZONE DEFAULT NULL)
RETURNS TABLE (
    total_sessions BIGINT,
    completed_sessions BIGINT,
    average_score DECIMAL,
    average_duration DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*) as total_sessions,
        COUNT(*) FILTER (WHERE state = 'completed') as completed_sessions,
        ROUND(AVG(score), 2) as average_score,
        ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - started_at))/60), 2) as average_duration
    FROM interview_sessions
    WHERE (start_date IS NULL OR created_at >= start_date)
      AND (end_date IS NULL OR created_at <= end_date);
END;
$$ LANGUAGE plpgsql;