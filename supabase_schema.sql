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

-- Allow service_role to bypass all RLS policies
CREATE POLICY "Service role full access to profiles" ON public.profiles FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access to study_sessions" ON public.study_sessions FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access to study_progress" ON public.study_progress FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access to quiz_history" ON public.quiz_history FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access to user_preferences" ON public.user_preferences FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Allow authenticated and anon clients to insert/read quiz and study progress
CREATE POLICY "Allow anon insert to quiz_history" ON public.quiz_history FOR INSERT TO anon, authenticated WITH CHECK (true);
CREATE POLICY "Allow anon select from quiz_history" ON public.quiz_history FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "Allow anon insert to study_sessions" ON public.study_sessions FOR INSERT TO anon, authenticated WITH CHECK (true);
CREATE POLICY "Allow anon select from study_sessions" ON public.study_sessions FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "Allow anon insert to study_progress" ON public.study_progress FOR INSERT TO anon, authenticated WITH CHECK (true);
CREATE POLICY "Allow anon select from study_progress" ON public.study_progress FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "Allow anon update to study_progress" ON public.study_progress FOR UPDATE TO anon, authenticated USING (true);
CREATE POLICY "Allow anon insert to profiles" ON public.profiles FOR INSERT TO anon, authenticated WITH CHECK (true);
CREATE POLICY "Allow anon select from profiles" ON public.profiles FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "Allow anon update to profiles" ON public.profiles FOR UPDATE TO anon, authenticated USING (true);

-- Optional migration commands to allow guest/demo user persistence without foreign key errors:
-- ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS profiles_id_fkey;
-- ALTER TABLE public.study_sessions DROP CONSTRAINT IF EXISTS study_sessions_user_id_fkey;
-- ALTER TABLE public.study_progress DROP CONSTRAINT IF EXISTS study_progress_user_id_fkey;
-- ALTER TABLE public.quiz_history DROP CONSTRAINT IF EXISTS quiz_history_user_id_fkey;
-- ALTER TABLE public.user_preferences DROP CONSTRAINT IF EXISTS user_preferences_user_id_fkey;

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
