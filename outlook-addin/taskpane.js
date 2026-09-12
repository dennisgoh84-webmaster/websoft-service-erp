// Websoft Incidents -- Outlook Add-in taskpane logic.
// See README.md for what this can and can't do without a real
// Microsoft 365 tenant/HTTPS host to actually sideload and test against.

// EDIT THIS before hosting: the deployed app's own origin (same host
// that serves the React app and its /api/* routes -- see
// docker-compose.yml's frontend/nginx service). Left as a relative
// path works too if this add-in is hosted on that exact same origin.
const API_BASE = "/api";

const els = {
  loginPanel: document.getElementById("login-panel"),
  appPanel: document.getElementById("app-panel"),
  resultPanel: document.getElementById("result-panel"),
  resultText: document.getElementById("result-text"),
  email: document.getElementById("email"),
  password: document.getElementById("password"),
  loginButton: document.getElementById("login-button"),
  loginError: document.getElementById("login-error"),
  emailSummary: document.getElementById("email-summary"),
  convertIncidentButton: document.getElementById("convert-incident-button"),
  convertJobOrderButton: document.getElementById("convert-job-order-button"),
  actionError: document.getElementById("action-error"),
};

function getToken() {
  return sessionStorage.getItem("websoft_token");
}

function setToken(token) {
  sessionStorage.setItem("websoft_token", token);
}

// This app's existing login (app/routers/auth.py) -- the same
// email/password every staff member already signs into the desktop
// app with. Deliberately NOT Azure AD / Office SSO: see README.md for
// why that's left as a later, optional enhancement rather than a
// requirement to get this working at all.
async function login(email, password) {
  const body = new URLSearchParams();
  body.set("username", email);
  body.set("password", password);
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Sign-in failed.");
  if (data.status === "otp_required") {
    // This add-in doesn't have an OTP entry step (yet) -- a known
    // limitation, not silently ignored. Sign in from the desktop app
    // first, or ask Dennis to disable email OTP for add-in use, until
    // this is built.
    throw new Error("This account needs an email OTP code to sign in, which this add-in doesn't support yet.");
  }
  if (data.status === "must_change_password") {
    throw new Error("This account must set its own password first -- sign into the desktop app once, then come back here.");
  }
  return data.access_token;
}

async function apiPost(path, payload) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getToken()}`,
    },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Request failed.");
  return data;
}

function currentEmailPayload() {
  const item = Office.context.mailbox.item;
  return new Promise((resolve) => {
    item.body.getAsync(Office.CoercionType.Text, (bodyResult) => {
      resolve({
        sender_name: item.from ? item.from.displayName : "",
        sender_email: item.from ? item.from.emailAddress : "",
        subject: item.subject || "(no subject)",
        body: bodyResult.status === Office.AsyncResultStatus.Succeeded ? bodyResult.value : "",
      });
    });
  });
}

function showResult(text) {
  els.resultPanel.style.display = "block";
  els.resultText.textContent = text;
}

Office.onReady(() => {
  const token = getToken();
  if (token) {
    els.loginPanel.style.display = "none";
    els.appPanel.style.display = "block";
  } else {
    els.loginPanel.style.display = "block";
  }

  currentEmailPayload().then((payload) => {
    els.emailSummary.textContent = `From: ${payload.sender_name} <${payload.sender_email}>\nSubject: ${payload.subject}`;
  });

  els.loginButton.addEventListener("click", async () => {
    els.loginError.textContent = "";
    els.loginButton.disabled = true;
    try {
      const token = await login(els.email.value, els.password.value);
      setToken(token);
      els.loginPanel.style.display = "none";
      els.appPanel.style.display = "block";
    } catch (err) {
      els.loginError.textContent = err.message;
    } finally {
      els.loginButton.disabled = false;
    }
  });

  els.convertIncidentButton.addEventListener("click", async () => {
    els.actionError.textContent = "";
    els.convertIncidentButton.disabled = true;
    try {
      const payload = await currentEmailPayload();
      const incident = await apiPost("/incidents/from-email", payload);
      showResult(`Logged as ${incident.incident_number}.`);
    } catch (err) {
      els.actionError.textContent = err.message;
    } finally {
      els.convertIncidentButton.disabled = false;
    }
  });

  els.convertJobOrderButton.addEventListener("click", async () => {
    els.actionError.textContent = "";
    els.convertJobOrderButton.disabled = true;
    try {
      const payload = await currentEmailPayload();
      const result = await apiPost("/incidents/from-email/convert-to-job-order", payload);
      if (result.job_order_created) {
        showResult(`Job Order created from ${result.incident.incident_number}.`);
      } else {
        // Confirmed 2026-09-12: falls back to a plain Incident rather
        // than failing outright -- shown here, not hidden.
        showResult(`No Job Order created -- logged as ${result.incident.incident_number} instead.\nReason: ${result.fallback_reason}`);
      }
    } catch (err) {
      els.actionError.textContent = err.message;
    } finally {
      els.convertJobOrderButton.disabled = false;
    }
  });
});
