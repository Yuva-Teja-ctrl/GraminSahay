// GraminSahay frontend — calls the Spring Boot /api/navigate endpoint and renders results.

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
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });

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

function render(data) {
    const schemes = data.schemes || [];
    const conflicts = data.conflicts || [];

    renderUnderstood(data.understoodProfile);
    renderConflicts(conflicts);

    if (schemes.length === 0) {
        showStatus("empty", "No matching schemes found. Try describing your situation differently or adding more details.");
        return;
    }

    hideStatus();
    const eligibleCount = schemes.filter((s) => s.status === "ELIGIBLE").length;
    showStatus("loading",
        `Found ${schemes.length} relevant scheme(s)${eligibleCount ? ` — you appear eligible for ${eligibleCount}.` : "."}`);

    schemes.forEach((scheme) => resultsEl.appendChild(buildCard(scheme)));
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

    const badge = node.querySelector(".badge");
    badge.textContent = STATUS_LABEL[scheme.status] || scheme.status;
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
    fillList(node.querySelector(".documents ul"), scheme.requiredDocuments, node.querySelector(".documents"));
    fillList(node.querySelector(".steps ol"), scheme.applicationSteps, node.querySelector(".steps"));

    const link = node.querySelector(".official-link");
    if (scheme.officialUrl) {
        link.href = scheme.officialUrl;
    } else {
        link.remove();
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
}

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
        const response = await fetch("/api/transcribe", { method: "POST", body: formData });
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
