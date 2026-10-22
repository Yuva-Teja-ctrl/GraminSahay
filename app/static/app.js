// GraminSahay frontend — calls the /api/navigate endpoint and renders results.
// Optional auth: the navigator works with OR without an account.
// Login is a convenience (to save your profile), never required to get welfare info.
const TOKEN_KEY = "graminsahay_token";
const USER_KEY = "graminsahay_user";
const LANG_KEY = "graminsahay_lang";
const FONT_KEY = "graminsahay_fontsize";

// Helper to resolve API endpoint against custom backend URL (for Vercel -> Render cross-origin deployment)
function apiUrl(path) {
    try {
        const params = new URLSearchParams(window.location.search);
        const paramApi = params.get("api");
        if (paramApi) {
            localStorage.setItem("graminsahay_api_url", paramApi);
        }
    } catch (_) {}
    const base = (window.API_BASE || localStorage.getItem("graminsahay_api_url") || "").trim().replace(/\/$/, "");
    if (base) {
        return `${base}${path.startsWith("/") ? "" : "/"}${path}`;
    }
    return path;
}

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
    window.location.reload();
}

function currentLanguage() {
    const el = document.getElementById("language");
    return (el && el.value) || localStorage.getItem(LANG_KEY) || "en";
}

// Map our language codes to BrowserSpeechSynthesis locale codes.
const TTS_LOCALE = { en: "en-IN", te: "te-IN", hi: "hi-IN" };

/* =========================================================================
   Initialization & Accessibility Font Scaler
   ========================================================================= */
document.addEventListener("DOMContentLoaded", () => {
    // 1. Language switcher & i18n
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

    // 2. Auth state
    const nameEl = document.getElementById("user-name");
    const logoutBtn = document.getElementById("logout-btn");
    const signInLink = document.getElementById("signin-link");
    const user = localStorage.getItem(USER_KEY);

    if (user && getToken()) {
        if (nameEl) {
            nameEl.textContent = `Hi, ${user}`;
            nameEl.hidden = false;
        }
        if (logoutBtn) logoutBtn.hidden = false;
        if (signInLink) signInLink.hidden = true;
        if (logoutBtn) logoutBtn.addEventListener("click", logout);
    } else {
        if (signInLink) signInLink.hidden = false;
        if (logoutBtn) logoutBtn.hidden = true;
    }

    // 3. Accessibility text scaler
    initFontScaler();

    // 4. Persona quick-fill chips
    initPersonaChips();

    // 5. Clear form button
    const clearBtn = document.getElementById("clear-btn");
    if (clearBtn) clearBtn.addEventListener("click", clearForm);

    // 6. Schemes catalog modal
    initCatalogModal();

    // 7. Filter tabs for results
    initFilterTabs();

    // 8. Download results button
    const dlBtn = document.getElementById("download-btn");
    if (dlBtn) dlBtn.addEventListener("click", downloadResults);
});

/* Accessibility Font Scaler (A-, A, A+) */
function initFontScaler() {
    const root = document.documentElement;
    const btnDec = document.getElementById("font-decrease");
    const btnNorm = document.getElementById("font-normal");
    const btnInc = document.getElementById("font-increase");

    const saved = localStorage.getItem(FONT_KEY) || "normal";
    applyFontSize(saved);

    function applyFontSize(size) {
        root.classList.remove("font-large", "font-xlarge");
        [btnDec, btnNorm, btnInc].forEach((b) => b && b.classList.remove("active"));
        if (size === "large") {
            root.classList.add("font-large");
            if (btnInc) btnInc.classList.add("active");
        } else if (size === "xlarge") {
            root.classList.add("font-xlarge");
            if (btnInc) btnInc.classList.add("active");
        } else {
            if (btnNorm) btnNorm.classList.add("active");
        }
        localStorage.setItem(FONT_KEY, size);
    }

    if (btnDec) btnDec.addEventListener("click", () => applyFontSize("normal"));
    if (btnNorm) btnNorm.addEventListener("click", () => applyFontSize("normal"));
    if (btnInc) btnInc.addEventListener("click", () => {
        const cur = localStorage.getItem(FONT_KEY);
        applyFontSize(cur === "large" ? "xlarge" : "large");
    });
}

/* =========================================================================
   Interactive Persona Scenarios (One-Click Testing)
   ========================================================================= */
const PERSONAS = {
    farmer: {
        situation: {
            en: "I am a small farmer in Warangal. I own 2 acres of cultivable land and have an annual income of ₹90,000.",
            te: "నేను వరంగల్‌లో చిన్న రైతును. నాకు 2 ఎకరాల వ్యవసాయ భూమి ఉంది, వార్షిక ఆదాయం ₹90,000.",
            hi: "मैं वारंगल का एक छोटा किसान हूँ। मेरे पास 2 एकड़ कृषि भूमि है और वार्षिक आय ₹90,000 है。"
        },
        occupation: "farmer",
        age: "42",
        gender: "male",
        land: "2",
        income: "90000",
        district: "Warangal",
        category: "obc",
        isBpl: "true"
    },
    pension: {
        situation: {
            en: "I am a 68-year-old elderly person from a low-income family in Karimnagar with no steady income.",
            te: "నేను కరీంనగర్‌లో తక్కువ ఆదాయ కుటుంబానికి చెందిన 68 ఏళ్ల వృద్ధుడిని, ఎటువంటి స్థిర ఆదాయం లేదు.",
            hi: "मैं करीमनगर का 68 वर्षीय वृद्ध नागरिक हूँ, गरीब परिवार से हूँ और कोई निश्चित आय नहीं है।"
        },
        occupation: "other",
        age: "68",
        gender: "female",
        land: "0",
        income: "40000",
        district: "Karimnagar",
        category: "general",
        isBpl: "true"
    },
    student: {
        situation: {
            en: "I am a 20-year-old college undergraduate from an OBC family in Nizamabad seeking scholarship for higher education.",
            te: "నేను నిజామాబాద్‌కు చెందిన 20 ఏళ్ల ఓబీసీ డిగ్రీ విద్యార్థిని, కళాశాల చదువు కోసం స్కాలర్‌షిప్ కావాలి.",
            hi: "मैं निजामाबाद का 20 वर्षीय ओबीसी कॉलेज छात्र हूँ, उच्च शिक्षा के लिए छात्रवृत्ति की आवश्यकता है।"
        },
        occupation: "student",
        age: "20",
        gender: "male",
        land: "",
        income: "80000",
        district: "Nizamabad",
        category: "obc",
        isBpl: "true"
    },
    labourer: {
        situation: {
            en: "I am a landless agricultural labourer in Khammam working on daily farm wages with a white ration card.",
            te: "నేను ఖమ్మంలో భూమిలేని వ్యవసాయ కూలీని, తెల్ల రేషన్ కార్డు ఉంది, రోజువారీ కూలీ పనులు చేస్తాను.",
            hi: "मैं खम्मम का भूमिहीन कृषि मज़दूर हूँ, सफ़ेद राशन कार्ड है और दैनिक मज़दूरी पर काम करता हूँ।"
        },
        occupation: "agricultural_labourer",
        age: "36",
        gender: "male",
        land: "0",
        income: "55000",
        district: "Khammam",
        category: "sc",
        isBpl: "true"
    },
    health: {
        situation: {
            en: "I live in Mahabubnagar with a BPL white ration card and my family needs hospital medical financial support for surgery.",
            te: "నేను మహబూబ్‌నగర్‌లో నివసిస్తున్నాను, తెల్ల రేషన్ కార్డు ఉంది, ఆసుపత్రి శస్త్రచికిత్స కోసం ఆర్థిక సహాయం కావాలి.",
            hi: "मैं महबूबनगर में रहता हूँ, बीपीएल सफ़ेद राशन कार्ड है और अस्पताल के इलाज के लिए सहायता चाहिए।"
        },
        occupation: "labourer",
        age: "45",
        gender: "female",
        land: "",
        income: "70000",
        district: "Mahabubnagar",
        category: "general",
        isBpl: "true"
    }
};

function initPersonaChips() {
    const chips = document.querySelectorAll(".persona-chip");
    chips.forEach((chip) => {
        chip.addEventListener("click", () => {
            const pKey = chip.getAttribute("data-persona");
            const data = PERSONAS[pKey];
            if (!data) return;

            const lang = currentLanguage();
            const sitBox = document.getElementById("situation");
            if (sitBox) {
                sitBox.value = data.situation[lang] || data.situation.en;
                sitBox.focus();
                // Visual feedback pulse
                sitBox.style.boxShadow = "0 0 0 4px rgba(16, 185, 129, 0.4)";
                setTimeout(() => { sitBox.style.boxShadow = ""; }, 800);
            }

            // Fill form fields
            const setVal = (id, val) => {
                const el = document.getElementById(id);
                if (el && val !== undefined) el.value = val;
            };
            setVal("occupation", data.occupation || "");
            setVal("age", data.age || "");
            setVal("gender", data.gender || "");
            setVal("landHoldingAcres", data.land || "");
            setVal("annualIncome", data.income || "");
            setVal("district", data.district || "");
            setVal("category", data.category || "");
            setVal("isBpl", data.isBpl || "");

            // Open the optional details accordion to show what was filled
            const details = document.querySelector(".details-accordion");
            if (details) details.open = true;
        });
    });
}

function clearForm() {
    const sitBox = document.getElementById("situation");
    if (sitBox) sitBox.value = "";
    ["occupation", "age", "gender", "landHoldingAcres", "annualIncome", "district", "category", "isBpl"].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.value = "";
    });
    const statusEl = document.getElementById("status");
    if (statusEl) statusEl.hidden = true;
}

/* =========================================================================
   Navigation & API Query
   ========================================================================= */
const form = document.getElementById("navigate-form");
const submitBtn = document.getElementById("submit-btn");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");
const conflictsEl = document.getElementById("conflicts");
const conflictsList = document.getElementById("conflicts-list");

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
    showStatus("loading", "⏳ Finding welfare schemes for your situation…");

    try {
        const response = await fetch(apiUrl("/api/navigate"), {
            method: "POST",
            headers: authHeaders({ "Content-Type": "application/json" }),
            body: JSON.stringify(body),
        });

        if (response.status === 401) {
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
        language: currentLanguage(),
    };
}

let lastResults = null;
let currentFilter = "ALL";

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
        `✨ Found ${schemes.length} relevant scheme(s)${eligibleCount ? ` — you appear eligible for ${eligibleCount}.` : "."}`);

    schemes.forEach((scheme) => resultsEl.appendChild(buildCard(scheme)));

    lastResults = { schemes, profile: data.understoodProfile || null };
    if (actions) actions.hidden = false;

    // Reset filter tabs to ALL
    applyFilter("ALL");

    // Smooth scroll to results
    setTimeout(() => {
        resultsEl.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 100);
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

/* Category icon mapping for civic visual identity */
const CATEGORY_ICONS = {
    agriculture: "🌾",
    pension: "👵",
    education: "🎓",
    health: "🏥",
    healthcare: "🏥",
    housing: "🏠",
    welfare: "🛡️"
};

function buildCard(scheme) {
    const tpl = document.getElementById("scheme-template");
    const node = tpl.content.cloneNode(true);
    const cardEl = node.querySelector(".scheme-card");

    node.querySelector(".scheme-name").textContent = scheme.schemeName;

    // Category with icon
    const catIcon = CATEGORY_ICONS[scheme.category?.toLowerCase()] || "📋";
    const catEl = node.querySelector(".scheme-category");
    catEl.textContent = `${catIcon} ${scheme.category}`;

    // Tint card
    cardEl.classList.add(`s-${scheme.status}`);

    // Badge
    const badge = node.querySelector(".badge");
    badge.textContent = t(`status_label_${scheme.status}`);
    badge.classList.add(scheme.status);

    // Highlight Benefit Callout Banner
    const benefitEl = node.querySelector(".benefit-callout");
    if (scheme.benefits) {
        benefitEl.hidden = false;
        node.querySelector(".b-text").innerHTML = `<strong>${t("benefit_badge")}:</strong> ${scheme.benefits}`;
    } else {
        benefitEl.remove();
    }

    // Explanation & Animated Text-to-Speech
    const explanation = node.querySelector(".scheme-explanation");
    const speakBtn = node.querySelector(".speak-btn");
    if (scheme.explanation) {
        explanation.textContent = scheme.explanation;
        if ("speechSynthesis" in window) {
            speakBtn.hidden = false;
            speakBtn.addEventListener("click", () => {
                speak(scheme.explanation, currentLanguage(), speakBtn);
            });
        }
    } else {
        explanation.remove();
        speakBtn.remove();
    }

    fillList(node.querySelector(".satisfied ul"), scheme.satisfiedConditions, node.querySelector(".satisfied"));
    fillList(node.querySelector(".unmet ul"), scheme.unmetConditions, node.querySelector(".unmet"));
    fillList(node.querySelector(".missing ul"), scheme.informationNeeded, node.querySelector(".missing"));

    const applyBtn = node.querySelector(".apply-btn");
    if (scheme.status === "NOT_ELIGIBLE") {
        applyBtn.remove();
    } else {
        applyBtn.addEventListener("click", () => openApplyModal(scheme));
    }

    return node;
}

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
   Results Filter Tabs
   ========================================================================= */
function initFilterTabs() {
    const tabs = document.querySelectorAll(".filter-tab");
    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            const filter = tab.getAttribute("data-filter");
            applyFilter(filter);
        });
    });
}

function applyFilter(filter) {
    currentFilter = filter;
    document.querySelectorAll(".filter-tab").forEach((t) => {
        t.classList.toggle("active", t.getAttribute("data-filter") === filter);
    });

    const cards = document.querySelectorAll(".scheme-card");
    cards.forEach((card) => {
        if (filter === "ALL" || card.classList.contains(`s-${filter}`)) {
            card.hidden = false;
        } else {
            card.hidden = true;
        }
    });
}

/* =========================================================================
   Application Guidance Modal
   ========================================================================= */
const applyModal = document.getElementById("apply-modal");
const applyClose = document.getElementById("apply-close");

function openApplyModal(scheme) {
    document.getElementById("apply-title").textContent = scheme.schemeName;

    const docsEl = document.getElementById("apply-docs");
    const progressEl = document.getElementById("apply-docs-progress");
    const meterBar = document.getElementById("apply-meter-bar");
    docsEl.innerHTML = "";
    const docs = scheme.requiredDocuments || [];

    const updateProgress = () => {
        const total = docs.length;
        const done = docsEl.querySelectorAll("input:checked").length;
        const pct = total ? Math.round((done / total) * 100) : 100;
        if (progressEl) progressEl.textContent = total ? `${done} of ${total} documents gathered (${pct}%)` : "";
        if (meterBar) meterBar.style.width = `${pct}%`;
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
    ["gstep_1", "gstep_2", "gstep_3", "gstep_4", "gstep_5",
     "gstep_6", "gstep_7", "gstep_8", "gstep_9", "gstep_10"].forEach((k) => addStep(t(k)));

    const schemeSteps = scheme.applicationSteps || [];
    if (schemeSteps.length) {
        addHeading("apply_scheme_heading");
        schemeSteps.forEach(addStep);
    }

    const portal = document.getElementById("apply-portal");
    if (scheme.officialUrl) {
        portal.href = scheme.officialUrl;
        portal.hidden = false;
    } else {
        portal.hidden = true;
    }

    applyModal.hidden = false;
    document.body.style.overflow = "hidden";
}

function closeApplyModal() {
    applyModal.hidden = true;
    document.body.style.overflow = "";
}

if (applyClose) applyClose.addEventListener("click", closeApplyModal);
if (applyModal) {
    applyModal.addEventListener("click", (e) => {
        if (e.target === applyModal) closeApplyModal();
    });
}
document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
        if (applyModal && !applyModal.hidden) closeApplyModal();
        if (catalogModal && !catalogModal.hidden) closeCatalogModal();
    }
});

/* =========================================================================
   Schemes Catalog Directory Modal (Browse all 15+ schemes anytime)
   ========================================================================= */
const catalogModal = document.getElementById("catalog-modal");
const catalogClose = document.getElementById("catalog-close");
let allCatalogSchemes = [];

function initCatalogModal() {
    const trigger = document.getElementById("open-catalog-btn");
    const searchInput = document.getElementById("catalog-search");

    if (trigger) trigger.addEventListener("click", openCatalogModal);
    if (catalogClose) catalogClose.addEventListener("click", closeCatalogModal);
    if (catalogModal) {
        catalogModal.addEventListener("click", (e) => {
            if (e.target === catalogModal) closeCatalogModal();
        });
    }

    if (searchInput) {
        searchInput.addEventListener("input", (e) => {
            filterCatalog(e.target.value);
        });
    }
}

async function openCatalogModal() {
    catalogModal.hidden = false;
    document.body.style.overflow = "hidden";

    if (allCatalogSchemes.length === 0) {
        try {
            const res = await fetch("/api/schemes");
            if (res.ok) {
                allCatalogSchemes = await res.json();
            } else {
                throw new Error("API route unavailable");
            }
        } catch (err) {
            try {
                const staticRes = await fetch("./telangana_schemes.json");
                if (staticRes.ok) {
                    allCatalogSchemes = await staticRes.json();
                }
            } catch (e) {
                console.warn("Could not fetch schemes directly:", e);
            }
        }
    }
    renderCatalogGrid(allCatalogSchemes);
}

function closeCatalogModal() {
    if (catalogModal) catalogModal.hidden = true;
    document.body.style.overflow = "";
}

function renderCatalogGrid(schemes) {
    const grid = document.getElementById("catalog-grid");
    if (!grid) return;
    grid.innerHTML = "";

    if (!schemes || schemes.length === 0) {
        grid.innerHTML = `<p style="grid-column: 1/-1; text-align: center; color: var(--muted); padding: 20px;">No schemes match your search.</p>`;
        return;
    }

    schemes.forEach((s) => {
        const item = document.createElement("div");
        item.className = "catalog-item-card";
        const catIcon = CATEGORY_ICONS[s.category?.toLowerCase()] || "📋";
        item.innerHTML = `
            <div>
                <span class="scheme-category">${catIcon} ${s.category}</span>
                <h4 style="margin: 8px 0 6px;">${s.name}</h4>
                <p class="catalog-item-desc">${s.description}</p>
            </div>
            ${s.benefits ? `<div class="catalog-item-benefit"><strong>💰 ${t("benefit_badge")}:</strong> ${s.benefits}</div>` : ""}
            <div style="display: flex; justify-content: flex-end; margin-top: 6px;">
                ${s.officialUrl ? `<a href="${s.officialUrl}" target="_blank" rel="noopener" class="auth-nav-link" style="font-size: 0.8rem; padding: 4px 12px;">Official Portal ↗</a>` : ""}
            </div>
        `;
        grid.appendChild(item);
    });
}

function filterCatalog(query) {
    const q = (query || "").toLowerCase().trim();
    if (!q) {
        renderCatalogGrid(allCatalogSchemes);
        return;
    }
    const filtered = allCatalogSchemes.filter((s) => {
        return (
            (s.name && s.name.toLowerCase().includes(q)) ||
            (s.category && s.category.toLowerCase().includes(q)) ||
            (s.benefits && s.benefits.toLowerCase().includes(q)) ||
            (s.description && s.description.toLowerCase().includes(q))
        );
    });
    renderCatalogGrid(filtered);
}

/* =========================================================================
   UI Helpers
   ========================================================================= */
function setLoading(isLoading) {
    submitBtn.disabled = isLoading;
    submitBtn.innerHTML = isLoading ? "⏳ Searching…" : "🔍 Find my schemes";
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
   Download / Print Results
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
                ${s.benefits ? `<p><strong>${t("benefit_badge")}:</strong> ${escapeHtml(s.benefits)}</p>` : ""}
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
  body { font-family: system-ui, sans-serif; color: #1f2937; max-width: 760px; margin: 24px auto; padding: 0 20px; line-height: 1.55; }
  h1 { color: #064e3b; font-size: 24px; margin-bottom: 2px; }
  .meta { color: #64748b; font-size: 13px; margin: 0 0 6px; }
  .scheme { border: 1.5px solid #e2e8f0; border-left: 5px solid #059669; border-radius: 12px; padding: 16px 20px; margin: 16px 0; page-break-inside: avoid; }
  .scheme h3 { margin: 0 0 4px; font-size: 18px; color: #0f172a; }
  .badge { font-size: 11px; background: #dcfce7; color: #065f46; padding: 3px 10px; border-radius: 99px; font-weight: 700; vertical-align: middle; }
  .cat { color: #059669; font-size: 12px; font-weight: 700; text-transform: uppercase; margin: 0 0 8px; }
  .h { font-weight: 700; margin: 12px 0 4px; font-size: 13.5px; }
  ul, ol { margin: 2px 0; padding-left: 22px; font-size: 14px; }
  a { color: #059669; word-break: break-all; }
  .disclaimer { margin-top: 24px; font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0; padding-top: 14px; }
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

    const win = window.open("", "_blank");
    if (!win) {
        alert("Please allow pop-ups to download your results.");
        return;
    }
    win.document.write(html);
    win.document.close();
}

/* =========================================================================
   Voice Input & Speech Output
   ========================================================================= */
const micBtn = document.getElementById("mic-btn");
const micLabel = document.getElementById("mic-label");
const micStatus = document.getElementById("mic-status");

let mediaRecorder = null;
let recordedChunks = [];
let isRecording = false;
let speechRecognizer = null;

// Text-to-speech with animated equalizer feedback
function speak(text, lang, btnEl) {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();

    if (btnEl) btnEl.classList.add("speaking");

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = TTS_LOCALE[lang] || "en-IN";
    utterance.onend = () => { if (btnEl) btnEl.classList.remove("speaking"); };
    utterance.onerror = () => { if (btnEl) btnEl.classList.remove("speaking"); };

    window.speechSynthesis.speak(utterance);
}

// Voice input with Web Speech API instant recognition & fallback to /api/transcribe
if (micBtn) {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRec) {
        speechRecognizer = new SpeechRec();
        speechRecognizer.continuous = false;
        speechRecognizer.interimResults = false;

        speechRecognizer.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            const box = document.getElementById("situation");
            box.value = box.value ? `${box.value} ${transcript}` : transcript;
            micStatus.textContent = "✅ Recognized! Review your situation, then search.";
        };

        speechRecognizer.onerror = (e) => {
            console.warn("Web Speech API error, falling back to MediaRecorder", e);
            micStatus.textContent = "Switching to direct recording…";
            toggleMediaRecorder();
        };

        speechRecognizer.onend = () => {
            isRecording = false;
            micBtn.classList.remove("recording");
            micLabel.textContent = t("speak");
        };

        micBtn.addEventListener("click", () => {
            if (isRecording) {
                speechRecognizer.stop();
                isRecording = false;
                micBtn.classList.remove("recording");
                micLabel.textContent = t("speak");
                micStatus.textContent = "";
            } else {
                try {
                    const lang = currentLanguage();
                    speechRecognizer.lang = TTS_LOCALE[lang] || "en-IN";
                    speechRecognizer.start();
                    isRecording = true;
                    micBtn.classList.add("recording");
                    micLabel.textContent = "Stop";
                    micStatus.textContent = "🔴 Listening… Speak now.";
                } catch (e) {
                    toggleMediaRecorder();
                }
            }
        });
    } else if (navigator.mediaDevices && window.MediaRecorder) {
        micBtn.addEventListener("click", toggleMediaRecorder);
    } else {
        micBtn.hidden = true;
    }
}

async function toggleMediaRecorder() {
    if (isRecording) {
        stopMediaRecorder();
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
            stream.getTracks().forEach((t) => t.stop());
            sendForTranscription();
        };
        mediaRecorder.start();
        isRecording = true;
        micBtn.classList.add("recording");
        micLabel.textContent = "Stop";
        micStatus.textContent = "🔴 Recording… Click Stop when done.";
    } catch (err) {
        micStatus.textContent = "Microphone permission denied. You can type instead.";
    }
}

function stopMediaRecorder() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        micBtn.classList.remove("recording");
        micLabel.textContent = t("speak");
        micStatus.textContent = "⏳ Transcribing audio…";
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
        box.value = box.value ? `${box.value} ${data.text}` : data.text;
        micStatus.textContent = data.text ? "✅ Added. Review your situation, then search." : "Nothing was heard — please try again.";
    } catch (err) {
        micStatus.textContent = `Could not transcribe: ${err.message}`;
    }
}
