-- =========================================================================
-- AI STUDY AGENT — SUPABASE POSTGRESQL SCHEMA WITH ROW LEVEL SECURITY (RLS)
-- =========================================================================

-- 1. PROFILES TABLE (Extends Supabase auth.users)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT,
    avatar_url TEXT,
    email TEXT,
    education_level TEXT,
    field_of_study TEXT,
    learning_goals TEXT,
    preferred_theme TEXT DEFAULT 'dark' CHECK (preferred_theme IN ('dark', 'light')),
    preferred_language TEXT DEFAULT 'en',
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. STUDY SESSIONS TABLE
CREATE TABLE IF NOT EXISTS public.study_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    session_type TEXT NOT NULL, -- 'quiz', 'flashcard', 'summary', 'explain'
    topic TEXT NOT NULL,
    duration_seconds INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. STUDY PROGRESS TABLE
CREATE TABLE IF NOT EXISTS public.study_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    topic TEXT NOT NULL,
    total_quizzes INTEGER DEFAULT 0,
    correct_answers INTEGER DEFAULT 0,
    accuracy_pct NUMERIC(5, 2) DEFAULT 0.0,
    mastery_status TEXT DEFAULT 'Needs Revision' CHECK (mastery_status IN ('Mastered', 'Reviewing', 'Needs Revision')),
    last_studied_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL,
    CONSTRAINT unique_user_topic UNIQUE (user_id, topic)
);

-- 4. QUIZ HISTORY TABLE
CREATE TABLE IF NOT EXISTS public.quiz_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    topic TEXT NOT NULL,
    question TEXT NOT NULL,
    selected_option TEXT NOT NULL,
    correct_option TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL,
    source_doc TEXT,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 5. USER PREFERENCES TABLE
CREATE TABLE IF NOT EXISTS public.user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    notifications_enabled BOOLEAN DEFAULT TRUE,
    daily_goal_minutes INTEGER DEFAULT 30,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- =========================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- =========================================================================

-- Enable RLS on all tables
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.study_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.study_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.quiz_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_preferences ENABLE ROW LEVEL SECURITY;

-- Profiles: Users can view, insert, and update their own record only
CREATE POLICY "Users can view own profile" 
    ON public.profiles FOR SELECT 
    USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile" 
    ON public.profiles FOR INSERT 
    WITH CHECK (auth.uid() = id);

CREATE POLICY "Users can update own profile" 
    ON public.profiles FOR UPDATE 
    USING (auth.uid() = id);

-- Study Sessions: Users can manage their own study sessions only
CREATE POLICY "Users can view own sessions" 
    ON public.study_sessions FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own sessions" 
    ON public.study_sessions FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own sessions" 
    ON public.study_sessions FOR UPDATE 
    USING (auth.uid() = user_id);

-- Study Progress: Users can manage their own progress records only
CREATE POLICY "Users can view own progress" 
    ON public.study_progress FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own progress" 
    ON public.study_progress FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own progress" 
    ON public.study_progress FOR UPDATE 
    USING (auth.uid() = user_id);

-- Quiz History: Users can view and log their own quiz results only
CREATE POLICY "Users can view own quiz history" 
    ON public.quiz_history FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own quiz history" 
    ON public.quiz_history FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

-- User Preferences: Users can manage their own preferences
CREATE POLICY "Users can view own preferences" 
    ON public.user_preferences FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own preferences" 
    ON public.user_preferences FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own preferences" 
    ON public.user_preferences FOR UPDATE 
    USING (auth.uid() = user_id);

-- =========================================================================
-- AUTOMATIC PROFILE INITIALIZATION TRIGGER
-- Automatically creates a public.profiles record when a new user signs up
-- via Google OAuth or Email OTP.
-- =========================================================================

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (
        id, 
        email, 
        full_name, 
        avatar_url, 
        preferred_theme
    )
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(
            NEW.raw_user_meta_data->>'full_name', 
            NEW.raw_user_meta_data->>'name',
            split_part(NEW.email, '@', 1)
        ),
        COALESCE(
            NEW.raw_user_meta_data->>'avatar_url', 
            NEW.raw_user_meta_data->>'picture',
            ''
        ),
        'dark'
    )
    ON CONFLICT (id) DO UPDATE SET
        email = EXCLUDED.email,
        full_name = COALESCE(public.profiles.full_name, EXCLUDED.full_name),
        avatar_url = COALESCE(public.profiles.avatar_url, EXCLUDED.avatar_url),
        updated_at = timezone('utc'::text, now());

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger execution on auth.users insert
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
