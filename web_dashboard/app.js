/**
 * AI Study Agent — Web Dashboard & Authentication Controller
 * Full-stack integration with Supabase Auth, Google OAuth, Email OTP,
 * Editable Student Profile, Light/Dark Themes & Real Persisted Dashboard.
 */

// --- GLOBAL APPLICATION STATE ---
let supabaseClient = null;
let currentSession = null;
let currentUserId = localStorage.getItem("study_user_id") || "";
let currentProfile = null;
let currentPendingEmail = "";
let otpCooldownTimer = null;
let otpCooldownSeconds = 60;

// Study tools state
let currentQuiz = null;
let currentFlashcards = [];
let currentFlashcardIndex = 0;

// --- INITIALIZATION ---
document.addEventListener("DOMContentLoaded", async () => {
    initTheme();
    setupOtpInputListeners();
    setupDropdownDismissal();
    setupConceptInputListener();
    await initAuth();
});

function setupConceptInputListener() {
    const input = document.getElementById("input-concept");
    if (input) {
        input.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                explainConcept();
            }
        });
    }
}

// --- AUTHENTICATION & SESSION MANAGEMENT ---
async function initAuth() {
    try {
        const res = await fetch("/api/auth/config");
        const config = await res.json();

        if (config.auth_enabled && window.supabase) {
            supabaseClient = window.supabase.createClient(config.supabase_url, config.supabase_anon_key);

            // Listen for auth state changes
            supabaseClient.auth.onAuthStateChange(async (event, session) => {
                if (event === "SIGNED_IN" || event === "TOKEN_REFRESHED" || event === "USER_UPDATED") {
                    if (session && session.user) {
                        currentSession = session;
                        currentUserId = session.user.id;
                        localStorage.setItem("study_user_id", currentUserId);
                        
                        await onUserAuthenticated(session.user);
                    }
                } else if (event === "SIGNED_OUT") {
                    currentSession = null;
                    currentUserId = "";
                    localStorage.removeItem("study_user_id");
                    setView("landing");
                }
            });

            // Check existing session
            const { data } = await supabaseClient.auth.getSession();
            if (data && data.session && data.session.user) {
                currentSession = data.session;
                currentUserId = data.session.user.id;
                localStorage.setItem("study_user_id", currentUserId);
                await onUserAuthenticated(data.session.user);
                return;
            }
        }
    } catch (e) {
        console.warn("Auth initialization notice:", e);
    }

    // Fallback: If user had a local session stored, restore it
    if (currentUserId && currentUserId !== "null" && currentUserId !== "undefined") {
        await onUserAuthenticated({ id: currentUserId, email: `${currentUserId}@studyagent.ai` });
    } else {
        setView("landing");
    }
}

// Handler executed when user is verified and authenticated
async function onUserAuthenticated(user) {
    setView("dashboard");
    
    // Sync / fetch user profile
    await loadProfile(user);

    // Load personalized real study data
    await Promise.all([
        loadDashboardOverview(),
        loadTopics(),
        loadVaultDocuments(),
        loadNewQuiz()
    ]);
    initDropzone();
}

function setView(viewName) {
    const landing = document.getElementById("view-landing");
    const dashboard = document.getElementById("view-dashboard");

    if (viewName === "dashboard") {
        if (landing) landing.classList.remove("active");
        if (dashboard) dashboard.classList.add("active");
    } else {
        if (dashboard) dashboard.classList.remove("active");
        if (landing) landing.classList.add("active");
    }
}

// Google OAuth
async function loginWithGoogle() {
    if (!supabaseClient) {
        showToast("Supabase configuration needed for Google OAuth. Please configure SUPABASE_URL and SUPABASE_ANON_KEY in your environment, or click 'Continue as Guest' below.", "info");
        return;
    }

    try {
        const { error } = await supabaseClient.auth.signInWithOAuth({
            provider: 'google',
            options: {
                redirectTo: window.location.origin
            }
        });
        if (error) {
            showToast(error.message, "error");
        }
    } catch (err) {
        showToast("Google authentication failed. Please try again.", "error");
        console.error("Google Auth error:", err);
    }
}

// Email Passwordless OTP
async function handleSendOtp(event) {
    if (event) event.preventDefault();
    const emailInput = document.getElementById("landing-email-input");
    const email = (emailInput ? emailInput.value : "").trim().toLowerCase();

    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        showToast("Please enter a valid student email address.", "error");
        return;
    }

    currentPendingEmail = email;
    const btnText = document.getElementById("btn-otp-text");
    const spinner = document.getElementById("spinner-send-otp");
    if (btnText) btnText.classList.add("hidden");
    if (spinner) spinner.classList.remove("hidden");

    if (supabaseClient) {
        try {
            const { error } = await supabaseClient.auth.signInWithOtp({
                email: email,
                options: {
                    shouldCreateUser: true,
                    emailRedirectTo: window.location.origin
                }
            });

            if (error) {
                showToast(error.message, "error");
                if (btnText) btnText.classList.remove("hidden");
                if (spinner) spinner.classList.add("hidden");
                return;
            }

            openOtpModal(email);
        } catch (err) {
            showToast("Failed to send verification code. Check connection.", "error");
            console.error("OTP send error:", err);
        }
    } else {
        // Local / Offline demo sandbox fallback
        openOtpModal(email);
        showToast("Demo Mode: Enter code 123456 to verify (Supabase credentials not yet supplied).", "info");
    }

    if (btnText) btnText.classList.remove("hidden");
    if (spinner) spinner.classList.add("hidden");
}

function maskEmail(email) {
    const parts = email.split("@");
    if (parts.length !== 2) return email;
    const name = parts[0];
    const domain = parts[1];
    if (name.length <= 2) return `${name[0]}*@${domain}`;
    return `${name[0]}${"*".repeat(Math.max(1, name.length - 2))}${name.slice(-1)}@${domain}`;
}

function openOtpModal(email) {
    const display = document.getElementById("otp-destination-display");
    if (display) display.innerText = maskEmail(email);

    clearOtpInputs();
    const errorEl = document.getElementById("otp-error-msg");
    if (errorEl) errorEl.classList.add("hidden");

    openModal("modal-otp-verify");
    startOtpCooldown(60);

    setTimeout(() => {
        const first = document.getElementById("otp-d-1");
        if (first) first.focus();
    }, 200);
}

function setupOtpInputListeners() {
    const inputs = [1, 2, 3, 4, 5, 6].map(i => document.getElementById(`otp-d-${i}`));
    
    inputs.forEach((input, index) => {
        if (!input) return;

        // Auto-advance
        input.addEventListener("input", (e) => {
            const val = e.target.value.replace(/[^0-9]/g, "");
            e.target.value = val ? val[val.length - 1] : "";
            
            if (val && index < inputs.length - 1) {
                inputs[index + 1].focus();
            }
            if (index === inputs.length - 1 && val) {
                submitOtpCode();
            }
        });

        // Backspace handling
        input.addEventListener("keydown", (e) => {
            if (e.key === "Backspace" && !input.value && index > 0) {
                inputs[index - 1].focus();
            }
        });

        // Paste support for full 6 digits
        input.addEventListener("paste", (e) => {
            e.preventDefault();
            const pasteData = (e.clipboardData || window.clipboardData).getData("text").trim();
            const digits = pasteData.replace(/[^0-9]/g, "").slice(0, 6);
            if (digits) {
                digits.split("").forEach((char, i) => {
                    if (inputs[i]) inputs[i].value = char;
                });
                const nextFocus = Math.min(digits.length, 5);
                if (inputs[nextFocus]) inputs[nextFocus].focus();
                if (digits.length === 6) {
                    submitOtpCode();
                }
            }
        });
    });
}

function clearOtpInputs() {
    [1, 2, 3, 4, 5, 6].forEach(i => {
        const inp = document.getElementById(`otp-d-${i}`);
        if (inp) inp.value = "";
    });
}

function getEnteredOtp() {
    let code = "";
    for (let i = 1; i <= 6; i++) {
        const inp = document.getElementById(`otp-d-${i}`);
        if (inp) code += inp.value.trim();
    }
    return code;
}

async function submitOtpCode() {
    const code = getEnteredOtp();
    const errorEl = document.getElementById("otp-error-msg");
    if (errorEl) errorEl.classList.add("hidden");

    if (code.length < 6) {
        if (errorEl) {
            errorEl.innerText = "Please enter the complete 6-digit code.";
            errorEl.classList.remove("hidden");
        }
        return;
    }

    const btnText = document.getElementById("btn-verify-text");
    const spinner = document.getElementById("spinner-verify-otp");
    if (btnText) btnText.classList.add("hidden");
    if (spinner) spinner.classList.remove("hidden");

    if (supabaseClient) {
        try {
            const { data, error } = await supabaseClient.auth.verifyOtp({
                email: currentPendingEmail,
                token: code,
                type: 'email'
            });

            if (error) {
                if (errorEl) {
                    errorEl.innerText = error.message || "Invalid or expired code. Please try again.";
                    errorEl.classList.remove("hidden");
                }
                if (btnText) btnText.classList.remove("hidden");
                if (spinner) spinner.classList.add("hidden");
                return;
            }

            closeModal("modal-otp-verify");
            showToast("Email verified successfully! Welcome to StudyAgent.", "success");
            if (data && data.user) {
                await onUserAuthenticated(data.user);
            }
        } catch (err) {
            if (errorEl) {
                errorEl.innerText = "Verification failed. Check network or resend code.";
                errorEl.classList.remove("hidden");
            }
        }
    } else {
        // Offline / Sandbox Demo verification
        if (code === "123456" || code.length === 6) {
            const demoId = currentPendingEmail.split("@")[0].toLowerCase().replace(/[^a-z0-9]/g, "_");
            currentUserId = demoId || "masai_student";
            localStorage.setItem("study_user_id", currentUserId);

            closeModal("modal-otp-verify");
            showToast("Verified in Demo Mode! Welcome.", "success");
            await onUserAuthenticated({ id: currentUserId, email: currentPendingEmail });
        } else {
            if (errorEl) {
                errorEl.innerText = "Invalid code. In Demo Mode, use code 123456.";
                errorEl.classList.remove("hidden");
            }
        }
    }

    if (btnText) btnText.classList.remove("hidden");
    if (spinner) spinner.classList.add("hidden");
}

function startOtpCooldown(seconds) {
    if (otpCooldownTimer) clearInterval(otpCooldownTimer);
    otpCooldownSeconds = seconds;
    const resendBtn = document.getElementById("btn-resend-otp");
    const cooldownText = document.getElementById("otp-cooldown-text");

    if (resendBtn) resendBtn.disabled = true;
    if (cooldownText) cooldownText.innerText = `(${otpCooldownSeconds}s)`;

    otpCooldownTimer = setInterval(() => {
        otpCooldownSeconds--;
        if (cooldownText) cooldownText.innerText = `(${otpCooldownSeconds}s)`;
        if (otpCooldownSeconds <= 0) {
            clearInterval(otpCooldownTimer);
            if (resendBtn) resendBtn.disabled = false;
            if (cooldownText) cooldownText.innerText = "";
        }
    }, 1000);
}

async function resendOtpCode() {
    if (otpCooldownSeconds > 0) return;
    showToast("Resending verification code...", "info");
    clearOtpInputs();
    await handleSendOtp();
}

function editOtpEmail() {
    closeModal("modal-otp-verify");
    scrollToAuth("signup");
    const emailInput = document.getElementById("landing-email-input");
    if (emailInput) {
        emailInput.focus();
        emailInput.select();
    }
}

// Quick sandbox demo login
async function loginAsDemoUser() {
    currentUserId = "alex_scholar";
    localStorage.setItem("study_user_id", currentUserId);
    showToast("Logged in as Demo Student. Your study vault is active!", "success");
    await onUserAuthenticated({ id: currentUserId, email: "alex@studyagent.ai" });
}

// Logout
async function handleLogout() {
    if (supabaseClient) {
        try {
            await supabaseClient.auth.signOut();
        } catch (e) {
            console.warn("Sign out notice:", e);
        }
    }
    currentSession = null;
    currentUserId = "";
    localStorage.removeItem("study_user_id");
    showToast("You have been signed out safely.", "info");
    setView("landing");
}

function scrollToAuth(mode) {
    const authCard = document.getElementById("auth-card");
    if (authCard) {
        authCard.scrollIntoView({ behavior: 'smooth' });
    }
    const emailInput = document.getElementById("landing-email-input");
    if (emailInput) emailInput.focus();
}

// --- USER PROFILE & SETTINGS ---
async function loadProfile(user) {
    try {
        const uid = (user && user.id) ? user.id : currentUserId;
        const res = await fetch(`/api/profile?user_id=${encodeURIComponent(uid)}`);
        const profile = await res.json();
        currentProfile = profile;

        // Extract first name for greeting
        const fullName = profile.full_name || (user && user.user_metadata && user.user_metadata.full_name) || "Student";
        const firstName = fullName.split(" ")[0] || "Student";
        
        // Update header & greeting displays
        const greetEl = document.getElementById("header-greeting-name");
        if (greetEl) greetEl.innerText = firstName;
        const welcomeFirstName = document.getElementById("welcome-first-name");
        if (welcomeFirstName) welcomeFirstName.innerText = firstName;

        const dropdownName = document.getElementById("dropdown-full-name");
        if (dropdownName) dropdownName.innerText = fullName;
        const dropdownEmail = document.getElementById("dropdown-email");
        if (dropdownEmail) dropdownEmail.innerText = profile.email || (user ? user.email : "");

        // Update Avatar
        const avatarImg = document.getElementById("header-avatar-img");
        const avatarInitials = document.getElementById("header-avatar-initials");
        const effectiveAvatar = profile.avatar_url || (user && user.user_metadata && user.user_metadata.avatar_url);

        if (effectiveAvatar && avatarImg) {
            avatarImg.src = effectiveAvatar;
            avatarImg.classList.remove("hidden");
            if (avatarInitials) avatarInitials.classList.add("hidden");
        } else if (avatarInitials) {
            avatarInitials.innerText = firstName[0].toUpperCase();
            avatarInitials.classList.remove("hidden");
            if (avatarImg) avatarImg.classList.add("hidden");
        }

        // Apply saved theme preference
        if (profile.preferred_theme) {
            applyTheme(profile.preferred_theme, false);
        }

        // Vault badge
        const privacyBadge = document.getElementById("vault-privacy-badge");
        if (privacyBadge) privacyBadge.innerText = `🔒 Private Vault: ${firstName}`;

        // Populate form if modal opens
        populateProfileForm(profile, user);
    } catch (e) {
        console.error("Error loading user profile:", e);
    }
}

function populateProfileForm(profile, user) {
    if (!profile) return;
    const nameInp = document.getElementById("profile-input-fullname");
    if (nameInp) nameInp.value = profile.full_name || "";
    const emailInp = document.getElementById("profile-input-email");
    if (emailInp) emailInp.value = profile.email || (user ? user.email : "");
    const avatarInp = document.getElementById("profile-input-avatar");
    if (avatarInp) avatarInp.value = profile.avatar_url || "";
    const eduInp = document.getElementById("profile-input-education");
    if (eduInp) eduInp.value = profile.education_level || "Undergraduate";
    const fieldInp = document.getElementById("profile-input-field");
    if (fieldInp) fieldInp.value = profile.field_of_study || "";
    const langInp = document.getElementById("profile-input-language");
    if (langInp) langInp.value = profile.preferred_language || "en";
    const goalsInp = document.getElementById("profile-input-goals");
    if (goalsInp) goalsInp.value = profile.learning_goals || "";
    const themeInp = document.getElementById("profile-input-theme");
    if (themeInp) themeInp.value = profile.preferred_theme || "dark";
    const createdEl = document.getElementById("profile-display-created");
    if (createdEl && profile.created_at) {
        const d = new Date(profile.created_at);
        createdEl.innerText = isNaN(d.getTime()) ? profile.created_at : d.toLocaleDateString("en-US", { month: "long", year: "numeric" });
    }
}

function openProfileModal() {
    closeProfileDropdown();
    if (currentProfile) {
        populateProfileForm(currentProfile, currentSession ? currentSession.user : null);
    }
    openModal("modal-profile");
}

async function handleSaveProfile(event) {
    if (event) event.preventDefault();

    const fullName = document.getElementById("profile-input-fullname").value.trim();
    const avatarUrl = document.getElementById("profile-input-avatar").value.trim();
    const educationLevel = document.getElementById("profile-input-education").value;
    const fieldOfStudy = document.getElementById("profile-input-field").value.trim();
    const preferredLanguage = document.getElementById("profile-input-language").value;
    const learningGoals = document.getElementById("profile-input-goals").value.trim();
    const preferredTheme = document.getElementById("profile-input-theme").value;

    if (!fullName) {
        showToast("Full name is required.", "error");
        return;
    }

    const btnText = document.getElementById("btn-save-profile-text");
    const spinner = document.getElementById("spinner-save-profile");
    if (btnText) btnText.classList.add("hidden");
    if (spinner) spinner.classList.remove("hidden");

    const payload = {
        user_id: currentUserId,
        full_name: fullName,
        avatar_url: avatarUrl,
        education_level: educationLevel,
        field_of_study: fieldOfStudy,
        preferred_language: preferredLanguage,
        learning_goals: learningGoals,
        preferred_theme: preferredTheme
    };

    try {
        const res = await fetch("/api/profile", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const updated = await res.json();
        currentProfile = updated;

        // Apply theme if changed
        applyTheme(preferredTheme, true);

        // Update greeting & header
        const firstName = fullName.split(" ")[0] || "Student";
        const greetEl = document.getElementById("header-greeting-name");
        if (greetEl) greetEl.innerText = firstName;
        const welcomeFirstName = document.getElementById("welcome-first-name");
        if (welcomeFirstName) welcomeFirstName.innerText = firstName;

        closeModal("modal-profile");
        showToast("Profile saved to database successfully!", "success");
    } catch (e) {
        showToast("Error updating profile. Please try again.", "error");
    } finally {
        if (btnText) btnText.classList.remove("hidden");
        if (spinner) spinner.classList.add("hidden");
    }
}

function toggleProfileDropdown() {
    const menu = document.getElementById("profile-dropdown-menu");
    if (menu) menu.classList.toggle("hidden");
}

function closeProfileDropdown() {
    const menu = document.getElementById("profile-dropdown-menu");
    if (menu) menu.classList.add("hidden");
}

function setupDropdownDismissal() {
    document.addEventListener("click", (e) => {
        const container = document.querySelector(".profile-dropdown-container");
        if (container && !container.contains(e.target)) {
            closeProfileDropdown();
        }
    });
}

// --- LIGHT / DARK THEME SYSTEM ---
function initTheme() {
    const saved = localStorage.getItem("study_theme") || 
                  (window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
    applyTheme(saved, false);
}

function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme") || "dark";
    const next = current === "dark" ? "light" : "dark";
    applyTheme(next, true);
}

function applyTheme(theme, persist) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("study_theme", theme);

    // Update toggle icons
    const icon1 = document.getElementById("theme-icon-indicator");
    const icon2 = document.querySelector("#landing-theme-toggle .theme-icon");
    const iconChar = theme === "light" ? "☀️" : "🌙";
    if (icon1) icon1.innerText = iconChar;
    if (icon2) icon2.innerText = iconChar;

    if (persist && currentUserId) {
        fetch("/api/profile", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: currentUserId, preferred_theme: theme })
        }).catch(() => {});
    }
}

// --- PERSONALIZED DASHBOARD OVERVIEW ---
async function loadDashboardOverview() {
    if (!currentUserId) return;
    try {
        const res = await fetch(`/api/dashboard/overview?user_id=${encodeURIComponent(currentUserId)}`);
        const data = await res.json();

        // Update stats ribbon
        const sessionsEl = document.getElementById("stat-total-sessions");
        if (sessionsEl) sessionsEl.innerText = data.total_sessions || 0;

        const timeEl = document.getElementById("stat-study-time");
        if (timeEl) timeEl.innerText = `${data.study_time_minutes || 0} min`;

        const accEl = document.getElementById("stat-accuracy");
        if (accEl) accEl.innerText = `${data.accuracy_pct || 0}%`;

        const masteredEl = document.getElementById("stat-mastered-count");
        if (masteredEl) masteredEl.innerText = data.mastered_topics_count || 0;

        // Render recent activity timeline
        renderActivityTimeline(data.recent_activity || []);

        // Today's date banner
        const dateEl = document.getElementById("welcome-date-string");
        if (dateEl) {
            const today = new Date();
            dateEl.innerText = today.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" });
        }
    } catch (e) {
        console.error("Dashboard overview error:", e);
    }
}

function renderActivityTimeline(activities) {
    const container = document.getElementById("activity-timeline");
    if (!container) return;

    if (!activities || activities.length === 0) {
        container.innerHTML = `
            <div class="empty-state-container">
                <div class="empty-icon">🌱</div>
                <h4>No study activity recorded yet</h4>
                <p>Complete a quiz challenge, review flashcards, or upload lecture notes to start building your streak!</p>
            </div>
        `;
        return;
    }

    container.innerHTML = activities.map(act => {
        let icon = "⚡";
        if (act.type === "flashcards") icon = "📇";
        else if (act.type === "summary") icon = "📖";
        else if (act.type === "eli5") icon = "💡";
        else if (act.type === "quiz") icon = act.is_correct ? "🎯" : "⚠️";

        let timeStr = act.created_at ? formatTimeAgo(act.created_at) : "Just now";

        return `
            <div class="activity-item">
                <div class="activity-main">
                    <div class="activity-icon-badge">${icon}</div>
                    <div>
                        <div class="activity-desc">${escapeHtml(act.description)}</div>
                        <div class="activity-meta">📌 Topic: <strong>${escapeHtml(act.topic || "General")}</strong></div>
                    </div>
                </div>
                <div class="activity-time">${timeStr}</div>
            </div>
        `;
    }).join("");
}

function formatTimeAgo(dateString) {
    try {
        const d = new Date(dateString);
        const diffSeconds = Math.floor((new Date() - d) / 1000);
        if (diffSeconds < 60) return "Just now";
        if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)}m ago`;
        if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)}h ago`;
        return `${Math.floor(diffSeconds / 86400)}d ago`;
    } catch {
        return "Recently";
    }
}

function refreshDashboardOverview() {
    loadDashboardOverview();
    showToast("Dashboard stats updated!", "info");
}

// --- STUDY TABS ROUTER ---
function switchTab(tabId) {
    document.querySelectorAll(".tab-content").forEach(el => el.classList.remove("active"));
    document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active"));

    const targetTab = document.getElementById(`tab-${tabId}`);
    const targetBtn = document.getElementById(`tab-btn-${tabId}`);
    if (targetTab) targetTab.classList.add("active");
    if (targetBtn) targetBtn.classList.add("active");

    if (tabId === "vault") loadVaultDocuments();
    if (tabId === "flashcards") loadFlashcards();
    if (tabId === "revise") loadRevisionData();
}

// --- INTERACTIVE QUIZ ENGINE ---
async function loadNewQuiz() {
    const topicSelect = document.getElementById("select-quiz-topic");
    const chosenTopic = topicSelect ? topicSelect.value : "";
    const questionStem = document.getElementById("question-stem");
    const optionsGrid = document.getElementById("options-grid");
    const feedbackBox = document.getElementById("feedback-box");
    const uid = currentUserId && currentUserId.trim() ? currentUserId : (localStorage.getItem("study_user_id") || "default_student");

    if (questionStem) questionStem.innerHTML = '<span class="loading-pulse">Generating fresh grounded question...</span>';
    if (optionsGrid) optionsGrid.innerHTML = '';
    if (feedbackBox) feedbackBox.classList.add("hidden");

    try {
        const res = await fetch("/api/quiz", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: uid, topic: chosenTopic || null })
        });
        const quiz = await res.json();
        if (!quiz || !quiz.question) {
            throw new Error("Invalid quiz data received");
        }
        currentQuiz = quiz;
        renderQuiz(quiz);
    } catch (e) {
        console.error("Quiz load error:", e);
        if (questionStem) questionStem.innerText = "Error loading question. Please check backend connection.";
    }
}

function renderQuiz(quiz) {
    const topicBadge = document.getElementById("quiz-topic-badge");
    const questionStem = document.getElementById("question-stem");
    const optionsGrid = document.getElementById("options-grid");

    if (topicBadge) topicBadge.innerText = `Topic: ${quiz.topic || "Core Concept"}`;
    if (questionStem) questionStem.innerText = quiz.question;
    if (!optionsGrid) return;

    optionsGrid.innerHTML = '';

    // Robustly handle options as Object { A: "...", B: "..." } or Array ["...", "..."]
    let entries = [];
    if (Array.isArray(quiz.options)) {
        const letters = ["A", "B", "C", "D"];
        entries = quiz.options.map((opt, idx) => [letters[idx] || `${idx + 1}`, opt]);
    } else if (quiz.options && typeof quiz.options === 'object') {
        entries = Object.entries(quiz.options);
    }

    if (entries.length === 0) {
        optionsGrid.innerHTML = '<div style="color: var(--text-muted); padding: 1rem;">No options found for this question. Click New Question to generate another.</div>';
        return;
    }

    entries.forEach(([letter, optText]) => {
        const btn = document.createElement("button");
        btn.className = "option-btn";
        btn.setAttribute("data-letter", letter);
        btn.setAttribute("data-text", optText);
        btn.innerHTML = `<span class="option-letter">${letter}</span> <span class="option-text">${escapeHtml(optText)}</span>`;
        btn.onclick = () => submitAnswer(quiz.quiz_id, letter, optText, btn);
        optionsGrid.appendChild(btn);
    });
}

async function submitAnswer(quizId, selectedLetter, selectedText, selectedBtn) {
    document.querySelectorAll(".option-btn").forEach(btn => btn.disabled = true);
    const uid = currentUserId && currentUserId.trim() ? currentUserId : (localStorage.getItem("study_user_id") || "default_student");

    try {
        const res = await fetch("/api/answer", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                quiz_id: quizId,
                user_id: uid,
                selected_option: selectedLetter
            })
        });
        const result = await res.json();

        // Highlight options by letter or text
        document.querySelectorAll(".option-btn").forEach(btn => {
            const letter = btn.getAttribute("data-letter");
            const text = btn.getAttribute("data-text");
            const isCorrectOption = (letter === result.correct_option || text === result.correct_option);
            if (isCorrectOption) {
                btn.classList.add("correct");
            } else if ((letter === selectedLetter || text === selectedText) && !result.is_correct) {
                btn.classList.add("incorrect");
            }
        });

        // Show feedback box
        const feedbackBox = document.getElementById("feedback-box");
        const badge = document.getElementById("feedback-badge");
        const citation = document.getElementById("citation-badge");
        const explanation = document.getElementById("feedback-explanation");

        if (badge) {
            badge.innerText = result.is_correct ? "✅ Correct Answer!" : "❌ Incorrect";
            badge.className = `feedback-badge ${result.is_correct ? "correct" : "incorrect"}`;
        }
        if (citation) citation.innerText = `📖 Source: ${result.source_citation || "Vault Notes"}`;
        if (explanation) explanation.innerText = result.explanation || "";
        if (feedbackBox) feedbackBox.classList.remove("hidden");

        // Refresh stats automatically
        loadDashboardOverview();
    } catch (e) {
        showToast("Error evaluating answer.", "error");
    }
}

// --- TOPICS & VAULT DOCUMENTS ---
async function loadTopics() {
    try {
        const res = await fetch(`/api/topics?user_id=${encodeURIComponent(currentUserId)}`);
        const topics = await res.json();

        const selectQuiz = document.getElementById("select-quiz-topic");
        const selectFlashcard = document.getElementById("select-flashcard-topic");
        const topicList = document.getElementById("topic-list");

        if (selectQuiz) selectQuiz.innerHTML = '<option value="">🎯 Auto-Pick Topic</option>';
        if (selectFlashcard) selectFlashcard.innerHTML = '<option value="Agile Methodology">Agile Methodology</option>';
        if (topicList) topicList.innerHTML = '';

        if (!topics || topics.length === 0) {
            if (topicList) topicList.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem; padding: 0.5rem 0;">No topics indexed yet. Upload notes to begin!</div>';
            return;
        }

        topics.forEach(t => {
            const shortTitle = t.topic.length > 25 ? t.topic.slice(0, 23) + '...' : t.topic;
            
            if (selectQuiz) {
                const opt1 = document.createElement("option");
                opt1.value = t.topic;
                opt1.innerText = shortTitle;
                selectQuiz.appendChild(opt1);
            }

            if (selectFlashcard && t.topic.toLowerCase() !== "agile methodology") {
                const opt2 = document.createElement("option");
                opt2.value = t.topic;
                opt2.innerText = shortTitle;
                selectFlashcard.appendChild(opt2);
            }

            if (topicList) {
                const item = document.createElement("div");
                item.className = "topic-item";
                const countVal = t.chunk_count != null ? t.chunk_count : (t.count != null ? t.count : 0);
                item.innerHTML = `<span>📌 ${escapeHtml(t.topic)}</span> <span class="chunk-badge">${countVal} chunks</span>`;
                topicList.appendChild(item);
            }
        });
    } catch (e) {
        console.error("Topics load error:", e);
    }
}

async function loadVaultDocuments() {
    try {
        const res = await fetch(`/api/vault/documents?user_id=${encodeURIComponent(currentUserId)}`);
        const docs = await res.json();
        const docList = document.getElementById("doc-list");
        if (!docList) return;

        if (!docs || docs.length === 0) {
            docList.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem; padding: 0.5rem 0;">No private files uploaded yet. Drag & drop files above!</div>';
            return;
        }

        docList.innerHTML = docs.map(d => {
            const privacyIcon = d.is_private ? "🔒" : "🌐";
            const privacyLabel = d.is_private ? `Private to ${currentUserId}` : "Shared Library";
            const chunkVal = d.chunk_count != null ? d.chunk_count : (d.chunks != null ? d.chunks : 0);
            return `
                <div class="doc-item">
                    <div class="doc-icon">${getFileIcon(d.filename)}</div>
                    <div class="doc-meta">
                        <div class="doc-title">${escapeHtml(d.filename)}</div>
                        <div class="doc-sub">${privacyIcon} ${privacyLabel} • ${chunkVal} chunks</div>
                    </div>
                </div>
            `;
        }).join("");
    } catch (e) {
        console.error("Vault docs error:", e);
    }
}

function getFileIcon(filename) {
    if (filename.endsWith(".pdf")) return "📕";
    if (filename.endsWith(".docx")) return "📘";
    if (filename.endsWith(".pptx")) return "📙";
    if (filename.endsWith(".xlsx")) return "📊";
    if (filename.endsWith(".mp3") || filename.endsWith(".wav")) return "🎙️";
    return "📄";
}

// File Upload
function initDropzone() {
    const dropzone = document.getElementById("dropzone");
    if (!dropzone) return;

    ["dragenter", "dragover"].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add("dragover");
        }, false);
    });

    ["dragleave", "drop"].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove("dragover");
        }, false);
    });

    dropzone.addEventListener("drop", (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length) handleFileUpload({ target: { files: files } });
    });
}

async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const progressContainer = document.getElementById("upload-progress-container");
    const progressBar = document.getElementById("upload-progress-fill");
    const statusText = document.getElementById("upload-status-text");

    if (progressContainer) progressContainer.classList.remove("hidden");
    if (progressBar) progressBar.style.width = "35%";
    if (statusText) statusText.innerText = `Uploading and parsing ${file.name}...`;

    const formData = new FormData();
    formData.append("file", file);
    formData.append("user_id", currentUserId);

    try {
        if (progressBar) progressBar.style.width = "75%";
        const res = await fetch("/api/ingest", {
            method: "POST",
            body: formData
        });
        const result = await res.json();

        const indexedCount = result.chunks_indexed != null ? result.chunks_indexed : (result.indexed_count != null ? result.indexed_count : 0);
        if (progressBar) progressBar.style.width = "100%";
        if (statusText) statusText.innerText = `Success! Indexed ${indexedCount} chunks.`;

        showToast(`Indexed ${file.name} successfully into your private vault!`, "success");

        await Promise.all([
            loadTopics(),
            loadVaultDocuments(),
            loadDashboardOverview()
        ]);

        setTimeout(() => {
            if (progressContainer) progressContainer.classList.add("hidden");
            if (progressBar) progressBar.style.width = "0%";
        }, 3000);
    } catch (e) {
        if (statusText) statusText.innerText = "Upload failed. Please check file format.";
        showToast("File upload error.", "error");
    }
}

async function handleTextIngest() {
    const titleInput = document.getElementById("paste-title");
    const contentInput = document.getElementById("paste-content");
    const title = titleInput ? titleInput.value.trim() : "";
    const text = contentInput ? contentInput.value.trim() : "";

    if (!title || !text) {
        showToast("Please provide both a Title and Note Content.", "error");
        return;
    }

    try {
        const res = await fetch("/api/ingest/text", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title, text, user_id: currentUserId })
        });
        const result = await res.json();
        const indexedCount = result.chunks_indexed != null ? result.chunks_indexed : (result.indexed_count != null ? result.indexed_count : 0);
        showToast(`Notes stored in private vault! Indexed ${indexedCount} chunks.`, "success");

        if (titleInput) titleInput.value = "";
        if (contentInput) contentInput.value = "";

        await Promise.all([
            loadTopics(),
            loadVaultDocuments(),
            loadDashboardOverview()
        ]);
    } catch (e) {
        showToast("Failed to ingest notes.", "error");
    }
}

// --- CONCEPT EXPLAINER (ELI5) ---
async function explainConcept() {
    const input = document.getElementById("input-concept");
    const concept = input ? input.value.trim() : "";
    if (!concept) {
        showToast("Please enter a concept to explain.", "error");
        return;
    }

    const resultBox = document.getElementById("explain-result");
    const badge = document.getElementById("explain-badge");
    const sourcesEl = document.getElementById("explain-sources");
    const output = document.getElementById("explain-output");

    if (resultBox) resultBox.classList.remove("hidden");
    if (badge) badge.innerText = `Concept: ${concept}`;
    if (sourcesEl) sourcesEl.innerText = "Analyzing study notes...";
    if (output) output.innerHTML = '<span class="loading-pulse">Synthesizing ELI5 explanation and real-world analogy...</span>';

    try {
        const uid = currentUserId && currentUserId.trim() ? currentUserId : (localStorage.getItem("study_user_id") || "default_student");
        const res = await fetch("/api/explain", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ concept: concept, user_id: uid })
        });
        if (!res.ok) throw new Error(`HTTP error ${res.status}`);
        const data = await res.json();
        if (output) output.innerHTML = formatMarkdown(data.explanation || "");
        if (sourcesEl) {
            const srcList = data.sources && data.sources.length ? data.sources.join(", ") : "Agile_Product_Management.md";
            sourcesEl.innerText = `Sources: ${srcList}`;
        }
        loadDashboardOverview();
    } catch (e) {
        console.error("Explain concept error:", e);
        if (output) output.innerText = "Error generating explanation. Please check your backend connection.";
        if (sourcesEl) sourcesEl.innerText = "";
    }
}

async function summarizeChapter() {
    const input = document.getElementById("input-concept");
    const topic = input ? input.value.trim() : "";
    if (!topic) {
        showToast("Please enter a topic or chapter to summarize.", "error");
        return;
    }

    const resultBox = document.getElementById("explain-result");
    const badge = document.getElementById("explain-badge");
    const sourcesEl = document.getElementById("explain-sources");
    const output = document.getElementById("explain-output");

    if (resultBox) resultBox.classList.remove("hidden");
    if (badge) badge.innerText = `Summary: ${topic}`;
    if (sourcesEl) sourcesEl.innerText = "Distilling key frameworks...";
    if (output) output.innerHTML = '<span class="loading-pulse">Distilling chapter notes into key takeaways...</span>';

    try {
        const uid = currentUserId && currentUserId.trim() ? currentUserId : (localStorage.getItem("study_user_id") || "default_student");
        const res = await fetch("/api/summary", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ topic_or_chapter: topic, user_id: uid })
        });
        if (!res.ok) throw new Error(`HTTP error ${res.status}`);
        const data = await res.json();
        if (output) output.innerHTML = formatMarkdown(data.summary || "");
        if (sourcesEl) {
            const srcList = data.sources && data.sources.length ? data.sources.join(", ") : "Agile_Product_Management.md";
            sourcesEl.innerText = `Sources: ${srcList}`;
        }
        loadDashboardOverview();
    } catch (e) {
        console.error("Summarize error:", e);
        if (output) output.innerText = "Error generating chapter summary. Please check your backend connection.";
        if (sourcesEl) sourcesEl.innerText = "";
    }
}

function quickExplain(concept) {
    const input = document.getElementById("input-concept");
    if (input) {
        input.value = concept;
        input.focus();
    }
    explainConcept();
}

// --- 3D FLASHCARDS ---
async function loadFlashcards() {
    const topicSelect = document.getElementById("select-flashcard-topic");
    let topic = (topicSelect && topicSelect.value && topicSelect.value.trim()) ? topicSelect.value.trim() : "Agile Methodology";

    const frontText = document.getElementById("card-front-text");
    const backText = document.getElementById("card-back-text");
    const takeawayText = document.getElementById("card-takeaway-text");
    const indexLabel = document.getElementById("flashcard-index");
    const flashcardEl = document.getElementById("flashcard-card");
    const uid = currentUserId && currentUserId.trim() ? currentUserId : (localStorage.getItem("study_user_id") || "default_student");

    if (flashcardEl) {
        flashcardEl.classList.remove("is-flipped");
        flashcardEl.classList.remove("flipped");
    }

    if (frontText) frontText.innerHTML = '<span class="loading-pulse">Generating 3D recall cards...</span>';
    if (backText) backText.innerText = "Retrieving key concepts and high-yield definitions...";
    if (takeawayText) takeawayText.innerText = "Memory Hook: Preparing active recall prompts...";
    if (indexLabel) indexLabel.innerText = "Loading...";

    try {
        const res = await fetch("/api/flashcards", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ topic: topic, count: 5, user_id: uid })
        });
        if (!res.ok) {
            throw new Error(`HTTP error ${res.status}`);
        }
        const data = await res.json();
        currentFlashcards = (data && data.flashcards && data.flashcards.length) ? data.flashcards : [];
        currentFlashcardIndex = 0;
        renderFlashcard();
        loadDashboardOverview();
    } catch (e) {
        console.error("Flashcards error:", e);
        if (frontText) frontText.innerText = "Error loading flashcard deck. Click 'Generate Decks' to retry.";
        if (backText) backText.innerText = "Please check your network or backend connection.";
        if (takeawayText) takeawayText.innerText = "Memory Hook: Active recall works best with consistent review.";
        if (indexLabel) indexLabel.innerText = "Error";
    }
}

function renderFlashcard() {
    const frontText = document.getElementById("card-front-text");
    const backText = document.getElementById("card-back-text");
    const takeawayText = document.getElementById("card-takeaway-text");
    const indexLabel = document.getElementById("flashcard-index");
    const flashcardEl = document.getElementById("flashcard-card");

    if (flashcardEl) {
        flashcardEl.classList.remove("is-flipped");
        flashcardEl.classList.remove("flipped");
    }

    if (!currentFlashcards || !currentFlashcards.length) {
        if (frontText) frontText.innerText = "No flashcards generated for this topic yet. Click 'Generate Decks' to create cards!";
        if (backText) backText.innerText = "Upload lecture notes to create more custom flashcards.";
        if (takeawayText) takeawayText.innerText = "Memory Hook: Active recall improves long-term retention.";
        if (indexLabel) indexLabel.innerText = "Card 0 of 0";
        return;
    }

    const card = currentFlashcards[currentFlashcardIndex];
    const prompt = card.front || card.question || card.prompt || "Question prompt";
    const answer = card.back || card.answer || card.definition || "Answer details";
    const hook = card.key_takeaway || card.takeaway || "Review regularly";

    if (frontText) frontText.innerText = prompt;
    if (backText) backText.innerText = answer;
    if (takeawayText) takeawayText.innerText = `Memory Hook: ${hook}`;
    if (indexLabel) indexLabel.innerText = `Card ${currentFlashcardIndex + 1} of ${currentFlashcards.length}`;
}

function flipCard() {
    const card = document.getElementById("flashcard-card");
    if (card) {
        card.classList.toggle("is-flipped");
        card.classList.toggle("flipped");
    }
}

function nextFlashcard() {
    if (!currentFlashcards.length) return;
    currentFlashcardIndex = (currentFlashcardIndex + 1) % currentFlashcards.length;
    renderFlashcard();
}

function prevFlashcard() {
    if (!currentFlashcards.length) return;
    currentFlashcardIndex = (currentFlashcardIndex - 1 + currentFlashcards.length) % currentFlashcards.length;
    renderFlashcard();
}

// Global keyboard navigation for 3D Flashcards (Space/Enter to flip, Left/Right arrow keys to navigate)
document.addEventListener("keydown", (e) => {
    const flashcardTab = document.getElementById("tab-flashcards");
    if (!flashcardTab || !flashcardTab.classList.contains("active")) return;
    if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) return;

    if (e.code === "Space" || e.code === "Enter") {
        e.preventDefault();
        flipCard();
    } else if (e.code === "ArrowRight") {
        e.preventDefault();
        nextFlashcard();
    } else if (e.code === "ArrowLeft") {
        e.preventDefault();
        prevFlashcard();
    }
});

// --- REVISION ROADMAP ---
async function loadRevisionData() {
    try {
        const res = await fetch(`/api/progress?user_id=${encodeURIComponent(currentUserId)}`);
        const stats = await res.json();
        const container = document.getElementById("mastery-bars-list");
        if (!container) return;

        if (!stats.topic_breakdown || stats.topic_breakdown.length === 0) {
            container.innerHTML = '<p class="placeholder-text">Take quiz questions to see your topic mastery diagnostics!</p>';
            return;
        }

        container.innerHTML = stats.topic_breakdown.map(t => {
            const acc = t.accuracy || 0;
            let barColor = "var(--accent-emerald)";
            let statusBadge = "badge-mastered";
            if (acc < 60) {
                barColor = "var(--accent-crimson)";
                statusBadge = "badge-needs-revision";
            } else if (acc < 80) {
                barColor = "var(--accent-amber)";
                statusBadge = "badge-reviewing";
            }

            return `
                <div class="mastery-item" style="margin-bottom: 1.1rem;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.35rem; font-size: 0.9rem;">
                        <strong>${escapeHtml(t.topic)}</strong>
                        <span>${acc}% (${t.correct}/${t.attempts})</span>
                    </div>
                    <div class="progress-bar-bg" style="height: 10px; background: rgba(255,255,255,0.06); border-radius: 999px; overflow: hidden;">
                        <div style="width: ${acc}%; height: 100%; background: ${barColor}; transition: width 0.5s ease;"></div>
                    </div>
                </div>
            `;
        }).join("");
    } catch (e) {
        console.error("Revision data load error:", e);
    }
}

async function generateRevisionRoadmap() {
    const output = document.getElementById("revision-plan-output");
    if (output) output.innerHTML = '<span class="loading-pulse">Analyzing weak spots and drafting 15-minute targeted sprint...</span>';

    try {
        const res = await fetch(`/api/revise?user_id=${encodeURIComponent(currentUserId)}`);
        const data = await res.json();
        if (output) output.innerHTML = formatMarkdown(data.revision_plan || "No weak areas detected! You're performing exceptionally well across all topics.");
        loadDashboardOverview();
    } catch (e) {
        if (output) output.innerText = "Error generating revision roadmap.";
    }
}

// --- UTILITIES: TOASTS & MODALS ---
function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast-message toast-${type}`;
    let icon = "ℹ️";
    if (type === "success") icon = "✅";
    if (type === "error") icon = "⚠️";

    toast.innerHTML = `<span>${icon}</span> <span>${escapeHtml(message)}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(50px)";
        toast.style.transition = "all 0.3s ease";
        setTimeout(() => toast.remove(), 300);
    }, 4500);
}

function openModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.classList.remove("hidden");
}

function closeModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.classList.add("hidden");
}

function formatMarkdown(text) {
    if (!text) return "";
    return text
        .replace(/### (.*?)\n/g, '<h4 style="margin: 0.9rem 0 0.4rem; color: var(--text-primary);">$1</h4>')
        .replace(/## (.*?)\n/g, '<h3 style="margin: 1.1rem 0 0.5rem; color: var(--text-primary);">$1</h3>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n\n/g, '<p style="margin-bottom: 0.75rem;"></p>')
        .replace(/\n/g, '<br>');
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
