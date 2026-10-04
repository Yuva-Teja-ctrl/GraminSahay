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
    };
}

function render(data) {
    const schemes = data.schemes || [];
    const conflicts = data.conflicts || [];

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

function buildCard(scheme) {
    const tpl = document.getElementById("scheme-template");
    const node = tpl.content.cloneNode(true);

    node.querySelector(".scheme-name").textContent = scheme.schemeName;
    node.querySelector(".scheme-category").textContent = scheme.category;

    const badge = node.querySelector(".badge");
    badge.textContent = STATUS_LABEL[scheme.status] || scheme.status;
    badge.classList.add(scheme.status);

    const explanation = node.querySelector(".scheme-explanation");
    if (scheme.explanation) {
        explanation.textContent = scheme.explanation;
    } else {
        explanation.remove();
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
