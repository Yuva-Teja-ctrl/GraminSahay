// GraminSahay frontend — calls the Spring Boot /api/navigate endpoint and renders results.
// ---- Optional auth: the navigator works with OR without an account ----
// Login is a convenience (to save your profile), never required to get welfare info.
const TOKEN_KEY = "graminsahay_token";
const USER_KEY = "graminsahay_user";

function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

// Attach the Bearer token ONLY if the user is signed in; otherwise call anonymously.
function authHeaders(extra = {}) {
    const token = getToken();
    return token ? { ...extra, Authorization: `Bearer ${token}` } : { ...extra };
}

function logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    window.location.reload(); // back to anonymous mode, still usable
}

const LANG_KEY = "graminsahay_lang";

// Header reflects sign-in state: a "Sign in" link when anonymous, name + "Log out" when signed in.
document.addEventListener("DOMContentLoaded", () => {
    // Restore the saved language, translate the whole UI, and wire the language switcher so
    // changing it re-translates the entire interface immediately.
    const langSelect = document.getElementById("language");
    const savedLang = localStorage.getItem(LANG_KEY) || "en";
    if (langSelect) {
        langSelect.value = savedLang;
        langSelect.addEventListener("change", () => {
            localStorage.setItem(LANG_KEY, langSelect.value);
            applyTranslations();
        });
    }
    applyTranslations();

    const nameEl = document.getElementById("user-name");
    const logoutBtn = document.getElementById("logout-btn");
    const signInLink = document.getElementById("signin-link");
    const user = localStorage.getItem(USER_KEY);

    if (user && getToken()) {
        if (nameEl) nameEl.textContent = `Hi, ${user}`;
        if (logoutBtn) {
            logoutBtn.hidden = false;
            logoutBtn.addEventListener("click", logout);
        }
        if (signInLink) signInLink.hidden = true;
    } else {
        if (signInLink) signInLink.hidden = false;
        if (logoutBtn) logoutBtn.hidden = true;
    }
});

const form = document.getElementById("navigate-form");
const submitBtn = document.getElementById("submit-btn");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");
const conflictsEl = document.getElementById("conflicts");
const conflictsList = document.getElementById("conflicts-list");

// Human-friendly labels for the four eligibility statuses.
const STATUS_LABEL = {
    ELIGIBLE: "Eligible",
    POSSIBLY_ELIGIBLE: "Possibly eligible",
    MISSING_INFORMATION: "More info needed",
    NOT_ELIGIBLE: "Not eligible",
};

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await navigate();
});

async function navigate() {
    const body = collectRequest();
    if (!body.situation) {
        showStatus("error", "Please describe your situation first.");
        return;
    }

    setLoading(true);
    clearResults();
    showStatus("loading", "Finding schemes for you…");

    try {
        const response = await fetch("/api/navigate", {
            method: "POST",
            headers: authHeaders({ "Content-Type": "application/json" }),
            body: JSON.stringify(body),
        });

        if (response.status === 401) {
            // An expired/invalid token — drop it and continue anonymously.
            logout();
            return;
        }
        if (!response.ok) {
            const text = await response.text();
            throw new Error(`Server returned ${response.status}. ${text}`);
        }

        const data = await response.json();
        render(data);
    } catch (err) {
        showStatus("error", `Something went wrong: ${err.message}`);
    } finally {
        setLoading(false);
    }
}

// Build the request body, omitting blank fields so the backend treats them as "unknown".
function collectRequest() {
    const value = (id) => {
        const el = document.getElementById(id);
        return el && el.value !== "" ? el.value : null;
    };
    const num = (id) => (value(id) === null ? null : Number(value(id)));
    const bool = (id) => (value(id) === null ? null : value(id) === "true");

    return {
        situation: value("situation"),
        occupation: value("occupation"),
        age: num("age"),
        gender: value("gender"),
        landHoldingAcres: num("landHoldingAcres"),
        annualIncome: num("annualIncome"),
        district: value("district"),
        category: value("category"),
        isBpl: bool("isBpl"),
        withExplanations: document.getElementById("withExplanations").checked,
        language: document.getElementById("language").value,
    };
}

// The most recent results, kept so the user can download/print them.
let lastResults = null;

function render(data) {
    const schemes = data.schemes || [];
    const conflicts = data.conflicts || [];

    renderUnderstood(data.understoodProfile);
    renderConflicts(conflicts);

    const actions = document.getElementById("results-actions");

    if (schemes.length === 0) {
        lastResults = null;
        if (actions) actions.hidden = true;
        showStatus("empty", "No matching schemes found. Try describing your situation differently or adding more details.");
        return;
    }

    hideStatus();
    const eligibleCount = schemes.filter((s) => s.status === "ELIGIBLE").length;
    showStatus("loading",
        `Found ${schemes.length} relevant scheme(s)${eligibleCount ? ` — you appear eligible for ${eligibleCount}.` : "."}`);

    schemes.forEach((scheme) => resultsEl.appendChild(buildCard(scheme)));

    // Keep the data and reveal the download button.
    lastResults = { schemes, profile: data.understoodProfile || null };
    if (actions) actions.hidden = false;
}

function renderConflicts(conflicts) {
    conflictsList.innerHTML = "";
    if (conflicts.length === 0) {
        conflictsEl.hidden = true;
        return;
    }
    conflicts.forEach((c) => {
        const li = document.createElement("li");
        li.textContent = c.message;
        conflictsList.appendChild(li);
    });
    conflictsEl.hidden = false;
}

// Show the profile the system understood from the free-text situation.
const UNDERSTOOD_LABELS = {
    occupation: "Occupation",
    annual_income: "Annual income (₹)",
    land_holding_acres: "Land owned (acres)",
    age: "Age",
    gender: "Gender",
    district: "District",
    is_bpl: "Below Poverty Line",
    category: "Social category",
};

function renderUnderstood(profile) {
    const panel = document.getElementById("understood");
    const list = document.getElementById("understood-list");
    list.innerHTML = "";
    if (!profile) {
        panel.hidden = true;
        return;
    }
    const entries = Object.entries(UNDERSTOOD_LABELS)
        .filter(([key]) => profile[key] !== null && profile[key] !== undefined)
        .map(([key, label]) => {
            let value = profile[key];
            if (key === "is_bpl") value = value ? "Yes" : "No";
            return `<li><strong>${label}:</strong> ${value}</li>`;
        });
    if (entries.length === 0) {
        panel.hidden = true;
        return;
    }
    list.innerHTML = entries.join("");
    panel.hidden = false;
}

function buildCard(scheme) {
    const tpl = document.getElementById("scheme-template");
    const node = tpl.content.cloneNode(true);

    node.querySelector(".scheme-name").textContent = scheme.schemeName;
    node.querySelector(".scheme-category").textContent = scheme.category;

    // Tint the card's left border by status (CSS: .scheme-card.s-ELIGIBLE etc.)
    node.querySelector(".scheme-card").classList.add(`s-${scheme.status}`);

    const badge = node.querySelector(".badge");
    badge.textContent = t(`status_label_${scheme.status}`);
    badge.classList.add(scheme.status);

    const explanation = node.querySelector(".scheme-explanation");
    const speakBtn = node.querySelector(".speak-btn");
    if (scheme.explanation) {
        explanation.textContent = scheme.explanation;
        // Wire the "read aloud" button (browser text-to-speech, free, offline).
        if ("speechSynthesis" in window) {
            speakBtn.hidden = false;
            speakBtn.addEventListener("click", () => speak(scheme.explanation, currentLanguage()));
        }
    } else {
        explanation.remove();
        speakBtn.remove();
    }

    fillList(node.querySelector(".satisfied ul"), scheme.satisfiedConditions, node.querySelector(".satisfied"));
    fillList(node.querySelector(".unmet ul"), scheme.unmetConditions, node.querySelector(".unmet"));
    fillList(node.querySelector(".missing ul"), scheme.informationNeeded, node.querySelector(".missing"));

    // "How to apply" opens the guided application modal (PPT step 6). Hide it for schemes the
    // citizen is not eligible for — there is nothing to apply to yet.
    const applyBtn = node.querySelector(".apply-btn");
    if (scheme.status === "NOT_ELIGIBLE") {
        applyBtn.remove();
    } else {
        applyBtn.addEventListener("click", () => openApplyModal(scheme));
    }

    return node;
}

// Fill a <ul>/<ol>; hide the whole block if there are no items.
function fillList(listEl, items, block) {
    if (!items || items.length === 0) {
        block.classList.add("hidden");
        return;
    }
    items.forEach((item) => {
        const li = document.createElement("li");
        li.textContent = item;
        listEl.appendChild(li);
    });
}

/* =========================================================================
   Application guidance modal (PPT step 6): documents checklist, steps,
   and a prominent link to the official portal.
   ========================================================================= */
const applyModal = document.getElementById("apply-modal");
const applyClose = document.getElementById("apply-close");

function openApplyModal(scheme) {
    document.getElementById("apply-title").textContent = scheme.schemeName;

    // Documents as a tickable checklist, with live progress ("2 of 4 gathered").
    const docsEl = document.getElementById("apply-docs");
    const progressEl = document.getElementById("apply-docs-progress");
    docsEl.innerHTML = "";
    const docs = scheme.requiredDocuments || [];
    const updateProgress = () => {
        const total = docs.length;
        const done = docsEl.querySelectorAll("input:checked").length;
        progressEl.textContent = total ? `${done} of ${total} documents gathered` : "";
    };
    docs.forEach((doc, i) => {
        const li = document.createElement("li");
        const id = `doc-${i}`;
        li.innerHTML = `<label><input type="checkbox" id="${id}"/> <span></span></label>`;
        li.querySelector("span").textContent = doc;
        li.querySelector("input").addEventListener("change", updateProgress);
        docsEl.appendChild(li);
    });
    updateProgress();

    // Numbered steps — a complete journey: universal "general" steps (open the site, keep
    // documents ready, register/login, find the scheme) followed by the scheme-specific steps.
    const stepsEl = document.getElementById("apply-steps");
    stepsEl.innerHTML = "";

    const addHeading = (key) => {
        const li = document.createElement("li");
        li.className = "step-heading";
        li.textContent = t(key);
        stepsEl.appendChild(li);
    };
    const addStep = (text) => {
        const li = document.createElement("li");
        li.textContent = text;
        stepsEl.appendChild(li);
    };

    addHeading("apply_general_heading");
    ["gstep_1", "gstep_2", "gstep_3", "gstep_4"].forEach((k) => addStep(t(k)));

    const schemeSteps = scheme.applicationSteps || [];
    if (schemeSteps.length) {
        addHeading("apply_scheme_heading");
        schemeSteps.forEach(addStep);
    }

    // Official portal link.
    const portal = document.getElementById("apply-portal");
    if (scheme.officialUrl) {
        portal.href = scheme.officialUrl;
        portal.hidden = false;
    } else {
        portal.hidden = true;
    }

    applyModal.hidden = false;
    document.body.style.overflow = "hidden"; // lock background scroll
}

function closeApplyModal() {
    applyModal.hidden = true;
    document.body.style.overflow = "";
}

applyClose.addEventListener("click", closeApplyModal);
applyModal.addEventListener("click", (e) => {
    if (e.target === applyModal) closeApplyModal(); // click the dim backdrop to close
});
document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !applyModal.hidden) closeApplyModal();
});

/* ---- small UI helpers ---- */
function setLoading(isLoading) {
    submitBtn.disabled = isLoading;
    submitBtn.textContent = isLoading ? "Searching…" : "Find my schemes";
}
function showStatus(kind, message) {
    statusEl.className = `status ${kind}`;
    statusEl.textContent = message;
    statusEl.hidden = false;
}
function hideStatus() { statusEl.hidden = true; }
function clearResults() {
    resultsEl.innerHTML = "";
    conflictsEl.hidden = true;
    conflictsList.innerHTML = "";
    const actions = document.getElementById("results-actions");
    if (actions) actions.hidden = true;
}

/* =========================================================================
   Download / print results — builds a clean printable page the citizen can
   save as PDF or print. Uses only the data already on screen (no server call).
   ========================================================================= */
function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str == null ? "" : String(str);
    return div.innerHTML;
}

function profileSummary(profile) {
    if (!profile) return "";
    const labels = {
        occupation: "Occupation", age: "Age", gender: "Gender",
        land_holding_acres: "Land (acres)", annual_income: "Annual income (₹)",
        district: "District", is_bpl: "Below Poverty Line", category: "Category",
    };
    const parts = Object.entries(labels)
        .filter(([k]) => profile[k] !== null && profile[k] !== undefined)
        .map(([k, label]) => {
            let v = profile[k];
            if (k === "is_bpl") v = v ? "Yes" : "No";
            return `${label}: ${escapeHtml(v)}`;
        });
    return parts.join(" · ");
}

function downloadResults() {
    if (!lastResults) return;
    const { schemes, profile } = lastResults;
    const lang = currentLanguage();
    const dateStr = new Date().toLocaleDateString();

    const sectionsHtml = schemes.map((s) => {
        const statusLabel = t(`status_label_${s.status}`);
        const docs = (s.requiredDocuments || []).map((d) => `<li>${escapeHtml(d)}</li>`).join("");
        const steps = (s.applicationSteps || []).map((st) => `<li>${escapeHtml(st)}</li>`).join("");
        return `
            <div class="scheme">
                <h3>${escapeHtml(s.schemeName)} <span class="badge">${escapeHtml(statusLabel)}</span></h3>
                <p class="cat">${escapeHtml(s.category)}</p>
                ${s.explanation ? `<p>${escapeHtml(s.explanation)}</p>` : ""}
                ${docs ? `<p class="h">${t("dl_docs")}</p><ul>${docs}</ul>` : ""}
                ${steps ? `<p class="h">${t("dl_steps")}</p><ol>${steps}</ol>` : ""}
                ${s.officialUrl ? `<p class="h">${t("dl_official")}:</p><p><a href="${escapeHtml(s.officialUrl)}">${escapeHtml(s.officialUrl)}</a></p>` : ""}
            </div>`;
    }).join("");

    const html = `<!DOCTYPE html>
<html lang="${lang}"><head><meta charset="UTF-8"/>
<title>${t("dl_title")}</title>
<style>
  body { font-family: system-ui, sans-serif; color: #1f2937; max-width: 720px; margin: 24px auto; padding: 0 20px; line-height: 1.55; }
  h1 { color: #166534; font-size: 22px; margin-bottom: 2px; }
  .meta { color: #6b7280; font-size: 13px; margin: 0 0 4px; }
  .scheme { border: 1px solid #e5e7eb; border-left: 4px solid #1f9d55; border-radius: 10px; padding: 14px 18px; margin: 14px 0; page-break-inside: avoid; }
  .scheme h3 { margin: 0 0 2px; font-size: 17px; }
  .badge { font-size: 11px; background: #dcfce7; color: #166534; padding: 2px 9px; border-radius: 99px; font-weight: 700; vertical-align: middle; }
  .cat { color: #6b7280; font-size: 12px; text-transform: uppercase; margin: 0 0 8px; }
  .h { font-weight: 700; margin: 10px 0 2px; font-size: 13px; }
  ul, ol { margin: 2px 0; padding-left: 22px; font-size: 14px; }
  a { color: #166534; word-break: break-all; }
  .disclaimer { margin-top: 20px; font-size: 12px; color: #6b7280; border-top: 1px solid #e5e7eb; padding-top: 12px; }
  @media print { body { margin: 0; } }
</style></head>
<body>
  <h1>${t("dl_title")}</h1>
  <p class="meta">${t("dl_generated")}: ${escapeHtml(dateStr)}</p>
  ${profile ? `<p class="meta">${t("dl_profile")}: ${profileSummary(profile)}</p>` : ""}
  ${sectionsHtml}
  <p class="disclaimer">${t("dl_disclaimer")}</p>
  <script>window.onload = function(){ setTimeout(function(){ window.print(); }, 300); };<\/script>
</body></html>`;

    // Open a new window with the printable document; it auto-triggers the print/save dialog.
    const win = window.open("", "_blank");
    if (!win) {
        alert("Please allow pop-ups to download your results.");
        return;
    }
    win.document.write(html);
    win.document.close();
}

document.addEventListener("DOMContentLoaded", () => {
    const dlBtn = document.getElementById("download-btn");
    if (dlBtn) dlBtn.addEventListener("click", downloadResults);
});

/* =========================================================================
   Voice input (speech-to-text) and output (text-to-speech)
   ========================================================================= */

const micBtn = document.getElementById("mic-btn");
const micLabel = document.getElementById("mic-label");
const micStatus = document.getElementById("mic-status");

let mediaRecorder = null;
let recordedChunks = [];
let isRecording = false;

function currentLanguage() {
    return document.getElementById("language").value || "en";
}

// Map our language codes to BrowserSpeechSynthesis locale codes.
const TTS_LOCALE = { en: "en-IN", te: "te-IN", hi: "hi-IN" };

// --- Text-to-speech: read an explanation aloud ---
function speak(text, lang) {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel(); // stop anything already speaking
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = TTS_LOCALE[lang] || "en-IN";
    window.speechSynthesis.speak(utterance);
}

// --- Speech-to-text: record mic, send to /api/transcribe, fill the situation box ---
if (micBtn) {
    // Hide the mic entirely if the browser can't record audio.
    if (!navigator.mediaDevices || !window.MediaRecorder) {
        micBtn.hidden = true;
    } else {
        micBtn.addEventListener("click", toggleRecording);
    }
}

async function toggleRecording() {
    if (isRecording) {
        stopRecording();
        return;
    }
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        recordedChunks = [];
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) recordedChunks.push(e.data);
        };
        mediaRecorder.onstop = () => {
            stream.getTracks().forEach((t) => t.stop()); // release the mic
            sendForTranscription();
        };
        mediaRecorder.start();
        isRecording = true;
        micBtn.classList.add("recording");
        micLabel.textContent = "Stop";
        micStatus.textContent = "🔴 Recording… click Stop when done.";
    } catch (err) {
        micStatus.textContent = "Microphone permission denied. You can type instead.";
    }
}

function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        micBtn.classList.remove("recording");
        micLabel.textContent = "Speak";
        micStatus.textContent = "⏳ Transcribing…";
    }
}

async function sendForTranscription() {
    const blob = new Blob(recordedChunks, { type: "audio/webm" });
    const formData = new FormData();
    formData.append("audio", blob, "recording.webm");
    formData.append("language", currentLanguage());

    try {
        const response = await fetch("/api/transcribe", {
            method: "POST",
            headers: authHeaders(),
            body: formData,
        });
        if (response.status === 401) {
            logout();
            return;
        }
        if (!response.ok) {
            const detail = await response.text();
            throw new Error(detail);
        }
        const data = await response.json();
        const box = document.getElementById("situation");
        // Append to whatever is already there, so a second recording adds on.
        box.value = box.value ? `${box.value} ${data.text}` : data.text;
        micStatus.textContent = data.text ? "✅ Added. Review it, then search." : "Nothing was heard — please try again.";
    } catch (err) {
        micStatus.textContent = `Could not transcribe: ${err.message}`;
    }
}
