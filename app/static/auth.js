// Login / register page logic for GraminSahay.
// On success, stores the JWT in localStorage and redirects to the main app.

const TOKEN_KEY = "graminsahay_token";
const USER_KEY = "graminsahay_user";

// If already logged in, skip straight to the app.
if (localStorage.getItem(TOKEN_KEY)) {
    window.location.href = "/app.html";
}

let mode = "login"; // or "register"

const form = document.getElementById("auth-form");
const title = document.getElementById("auth-title");
const submit = document.getElementById("auth-submit");
const errorEl = document.getElementById("auth-error");
const tabLogin = document.getElementById("tab-login");
const tabRegister = document.getElementById("tab-register");
const switchText = document.getElementById("switch-text");
const switchLink = document.getElementById("switch-link");
const passwordInput = document.getElementById("password");

function setMode(newMode) {
    mode = newMode;
    const isLogin = mode === "login";
    title.textContent = isLogin ? "Welcome back" : "Create your account";
    submit.textContent = isLogin ? "Sign in" : "Create account";
    tabLogin.classList.toggle("active", isLogin);
    tabRegister.classList.toggle("active", !isLogin);
    switchText.textContent = isLogin ? "New here?" : "Already have an account?";
    switchLink.textContent = isLogin ? "Create an account" : "Sign in instead";
    passwordInput.autocomplete = isLogin ? "current-password" : "new-password";
    hideError();
}

tabLogin.addEventListener("click", () => setMode("login"));
tabRegister.addEventListener("click", () => setMode("register"));
switchLink.addEventListener("click", (e) => {
    e.preventDefault();
    setMode(mode === "login" ? "register" : "login");
});

form.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideError();

    const username = document.getElementById("username").value.trim();
    const password = passwordInput.value;

    // Validate here so WE control the message (no cryptic browser-native validation popups).
    if (username.length < 3) {
        showError("Username must be at least 3 characters.");
        return;
    }
    if (password.length < 6) {
        showError("Password must be at least 6 characters.");
        return;
    }

    const endpoint = mode === "login" ? "/api/auth/login" : "/api/auth/register";

    submit.disabled = true;
    submit.textContent = mode === "login" ? "Signing in…" : "Creating…";

    try {
        const response = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password }),
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(extractError(data));
        }
        localStorage.setItem(TOKEN_KEY, data.token);
        localStorage.setItem(USER_KEY, data.username);
        window.location.href = "/app.html";
    } catch (err) {
        showError(err.message);
        submit.disabled = false;
        submit.textContent = mode === "login" ? "Sign in" : "Create account";
    }
});

// Turn any server error shape into a readable sentence.
// FastAPI/Pydantic 422 errors come back as { detail: [ { msg, loc, ... } ] }; our own
// AuthErrors come back as { detail: "a plain message" }.
function extractError(data) {
    const detail = data && data.detail;
    if (!detail) return "Something went wrong. Please try again.";
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
        const first = detail[0];
        if (first && first.msg) {
            // Make it friendly: which field + what's wrong.
            const field = Array.isArray(first.loc) ? first.loc[first.loc.length - 1] : "input";
            return `${field}: ${first.msg}`;
        }
    }
    return "Please check your details and try again.";
}

function showError(msg) {
    errorEl.textContent = msg;
    errorEl.hidden = false;
}
function hideError() {
    errorEl.hidden = true;
}
