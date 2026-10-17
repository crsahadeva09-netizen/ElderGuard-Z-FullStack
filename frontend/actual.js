// Universal Toast Notification
function showToast(message, color = "#10b981") {
  let toast = document.getElementById("app-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "app-toast";
    toast.className = "toast-notice";
    document.body.appendChild(toast);
  }
  toast.innerHTML = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${color};"></span> ${message}`;
  toast.classList.add("show");
  setTimeout(() => {
    toast.classList.remove("show");
  }, 3200);
}

// Download text/csv helper
function downloadTextFile(filename, content, type = "text/plain") {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}


  /* 0. Email/password authentication with Flask session cookies */
const API_BASE_URL = "http://127.0.0.1:5000";

const authOverlay = document.getElementById("auth-overlay");
const appRoot = document.getElementById("appRoot");
const loginStep = document.getElementById("step-phone");
const registerStep = document.getElementById("step-register");
const showRegisterButton = document.getElementById("showRegister");
const showLoginButton = document.getElementById("showLogin");

const loginEmail = document.getElementById("loginEmail");
const loginPassword = document.getElementById("loginPassword");
const loginError = document.getElementById("loginError");
const loginMessage = document.getElementById("loginMessage");
const btnLogin = document.getElementById("btnLogin");

const registerName = document.getElementById("registerName");
const registerPhone = document.getElementById("registerPhone");
const registerEmail = document.getElementById("registerEmail");
const registerPassword = document.getElementById("registerPassword");
const confirmPassword = document.getElementById("confirmPassword");
const registerError = document.getElementById("registerError");
const registerMessage = document.getElementById("registerMessage");
const btnRegister = document.getElementById("btnRegister");

function showAuthStep(step) {
  [loginStep, registerStep].forEach(section => {
    if (section) section.classList.remove("active");
  });
  if (step) step.classList.add("active");
  [loginError, registerError].forEach(el => {
    if (el) { el.textContent = ""; el.style.display = "none"; }
  });
  [loginMessage, registerMessage].forEach(el => {
    if (el) el.textContent = "";
  });
}

function showAuthError(element, message) {
  if (!element) return;
  element.textContent = message;
  element.style.display = "block";
}

async function readApiResponse(response) {
  const raw = await response.text();
  let data = {};
  if (raw) {
    try { data = JSON.parse(raw); }
    catch { throw new Error("The backend returned an invalid response. Check the Flask server."); }
  }
  if (!response.ok) {
    throw new Error(data.message || data.error || data.detail || `Request failed (${response.status}).`);
  }
  return data;
}

function setAuthenticatedUI(user) {
  if (authOverlay) authOverlay.style.display = "none";
  if (appRoot) appRoot.classList.add("unlocked");
  const avatar = document.getElementById("avatarInitials");
  if (avatar && user) {
    const name = String(user.name || user.full_name || user.email || "").trim();
    if (name) {
      avatar.textContent = name.split(/\s+/).slice(0, 2).map(part => part[0]).join("").toUpperCase();
      avatar.title = name;
    }
  }

  // Refresh persisted data whenever the real Flask session is authenticated.
  if (typeof loadTransactions === "function") void loadTransactions();
  if (typeof loadReviewQueue === "function") void loadReviewQueue();
}

function setLoggedOutUI() {
  if (appRoot) appRoot.classList.remove("unlocked");
  if (authOverlay) authOverlay.style.display = "flex";
  showAuthStep(loginStep);
  if (loginPassword) loginPassword.value = "";
  sessionStorage.removeItem("elderguard_auth");
  sessionStorage.removeItem("elderguard_active_tab");
  sessionStorage.removeItem("elderguard_active_title");
}

if (showRegisterButton) {
  showRegisterButton.addEventListener("click", () => {
    showAuthStep(registerStep);
    if (registerName) registerName.focus();
  });
}
if (showLoginButton) {
  showLoginButton.addEventListener("click", () => {
    showAuthStep(loginStep);
    if (loginEmail) loginEmail.focus();
  });
}

async function registerAccount() {
  if (registerError) { registerError.textContent = ""; registerError.style.display = "none"; }
  if (registerMessage) registerMessage.textContent = "";

  const name = registerName?.value.trim() || "";
  const phone = registerPhone?.value.trim() || "";
  const email = registerEmail?.value.trim() || "";
  const password = registerPassword?.value || "";
  const confirm = confirmPassword?.value || "";

  if (!name || !phone || !email || !password || !confirm) {
    showAuthError(registerError, "Please fill in all fields."); return;
  }
  if (!/^[6-9]\d{9}$/.test(phone)) {
    showAuthError(registerError, "Enter a valid 10-digit Indian mobile number."); return;
  }
  if (password.length < 8) {
    showAuthError(registerError, "Password must contain at least 8 characters."); return;
  }
  if (password !== confirm) {
    showAuthError(registerError, "Passwords do not match."); return;
  }

  if (btnRegister) { btnRegister.disabled = true; btnRegister.textContent = "Creating Account..."; }
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ name, phone, email, password })
    });
    await readApiResponse(response);

    if (registerMessage) {
      registerMessage.style.color = "#059669";
      registerMessage.textContent = "Account created successfully. Sign in with your email and password.";
    }
    if (loginEmail) loginEmail.value = email;
    [registerName, registerPhone, registerEmail, registerPassword, confirmPassword]
      .filter(Boolean).forEach(field => { field.value = ""; });

    showToast("Account created. Please sign in.", "#059669");
    showAuthStep(loginStep);
    if (loginEmail) loginEmail.value = email;
    if (loginPassword) loginPassword.focus();
  } catch (error) {
    showAuthError(registerError, error.message === "Failed to fetch"
      ? "Cannot reach Flask. Start the backend and check the API URL."
      : error.message);
  } finally {
    if (btnRegister) { btnRegister.disabled = false; btnRegister.textContent = "Create Account"; }
  }
}

async function loginAccount() {
  if (loginError) { loginError.textContent = ""; loginError.style.display = "none"; }
  if (loginMessage) loginMessage.textContent = "";
  const email = loginEmail?.value.trim() || "";
  const password = loginPassword?.value || "";

  if (!email || !password) {
    showAuthError(loginError, "Enter your email address and password."); return;
  }
  if (btnLogin) { btnLogin.disabled = true; btnLogin.textContent = "Signing In..."; }

  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email, password })
    });
    const data = await readApiResponse(response);
    sessionStorage.setItem("elderguard_auth", "true");
    setAuthenticatedUI(data.user || data);
    showToast("Signed in successfully.", "#059669");
    if (typeof switchTab === "function") switchTab("dashboard", "Dashboard");
  } catch (error) {
    showAuthError(loginError, error.message === "Failed to fetch"
      ? "Cannot reach Flask. Start the backend and check the API URL."
      : error.message);
  } finally {
    if (btnLogin) { btnLogin.disabled = false; btnLogin.textContent = "Sign In"; }
  }
}

if (btnRegister) btnRegister.addEventListener("click", registerAccount);
if (btnLogin) btnLogin.addEventListener("click", loginAccount);

if (loginStep) loginStep.addEventListener("submit", event => {
  event.preventDefault(); loginAccount();
});
if (registerStep) registerStep.addEventListener("submit", event => {
  event.preventDefault(); registerAccount();
});
[loginEmail, loginPassword].filter(Boolean).forEach(field => {
  field.addEventListener("keydown", event => {
    if (event.key === "Enter") { event.preventDefault(); loginAccount(); }
  });
});
[registerName, registerPhone, registerEmail, registerPassword, confirmPassword]
  .filter(Boolean).forEach(field => {
    field.addEventListener("keydown", event => {
      if (event.key === "Enter") { event.preventDefault(); registerAccount(); }
    });
  });

// Restore the actual Flask session; do not trust a browser-side flag by itself.
async function restoreAuthenticatedSession() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
      method: "GET",
      credentials: "include"
    });
    if (!response.ok) { setLoggedOutUI(); return; }
    const data = await readApiResponse(response);
    sessionStorage.setItem("elderguard_auth", "true");
    setAuthenticatedUI(data.user || data);
  } catch (error) {
    setLoggedOutUI();
    console.warn("Could not restore the Flask session:", error);
  }
}
restoreAuthenticatedSession();

// 2. Tab Navigation
const menuButtons = document.querySelectorAll('.menu-item');
const allTabSections = document.querySelectorAll('.tab-section');
const breadcrumb = document.getElementById('topBreadcrumb');

function switchTab(tabName, title) {
  menuButtons.forEach(btn => {
    if (btn.dataset.tab === tabName) btn.classList.add('active');
    else btn.classList.remove('active');
  });

  if (breadcrumb) {
    breadcrumb.textContent = title || tabName.replace("-", " ").toUpperCase();
  }

  allTabSections.forEach(section => {
    section.classList.remove('active');
  });

  const targetSection = document.getElementById(`view-${tabName}`);
  if (targetSection) {
    targetSection.classList.add('active');
  }

  sessionStorage.setItem("elderguard_active_tab", tabName);
  if (title) sessionStorage.setItem("elderguard_active_title", title);
}

menuButtons.forEach(btn => {
  btn.addEventListener('click', () => {
    const tab = btn.dataset.tab;
    const text = btn.innerText.trim().replace(/\d+$/, '').trim();
    switchTab(tab, text);
  });
});

// Restore last active tab if page was reloaded by Live Server
const savedTab = sessionStorage.getItem("elderguard_active_tab");
const savedTitle = sessionStorage.getItem("elderguard_active_title");
if (savedTab) {
  switchTab(savedTab, savedTitle);
}

// 3. Simulator Logic

    // 3. ElderGuard Z - Flask Backend Integration

    const scenarios = {
      normal: {
        customer_id: 101,
        amount: 2500,
        recipient: "Local Grocery"
      },
      new_payee: {
        customer_id: 101,
        amount: 18000,
        recipient: "New Recipient"
      },
      suspicious: {
        customer_id: 101,
        amount: 48500,
        recipient: "Suspicious Recipient"
      }
    };

    const scenarioLabels = document.querySelectorAll(".scenario-label");
    const btnRunScenario = document.getElementById("btnRunScenario");
    let assessmentInProgress = false;

    function ensureSimulatorElements() {
      if (!btnRunScenario) return;

      if (!document.getElementById("simCustomerId")) {
        const form = document.createElement("div");

        form.id = "simTransactionInputs";
        form.style.cssText = "display:grid;gap:12px;margin:18px 0;";

        form.innerHTML = `
          <label style="display:block;font-size:13px;font-weight:700;">
            Customer ID
            <input id="simCustomerId" type="number" min="1" value="101"
              style="display:block;width:100%;padding:10px;margin-top:6px;border:1px solid #e2e8f0;border-radius:8px;">
          </label>

          <label style="display:block;font-size:13px;font-weight:700;">
            Transaction Amount (₹)
            <input id="simAmount" type="number" min="0.01" step="0.01" value="2500"
              style="display:block;width:100%;padding:10px;margin-top:6px;border:1px solid #e2e8f0;border-radius:8px;">
          </label>

          <label style="display:block;font-size:13px;font-weight:700;">
            Recipient Name
            <input id="simRecipient" type="text" maxlength="120" value="Local Grocery"
              style="display:block;width:100%;padding:10px;margin-top:6px;border:1px solid #e2e8f0;border-radius:8px;">
          </label>

          <p style="font-size:12px;color:#64748b;">
            Demo only. This does not transfer real money.
          </p>
        `;

        btnRunScenario.parentElement.insertBefore(form, btnRunScenario);
      }

      let result = document.getElementById("backendAssessmentResult");

      if (!result) {
        result = document.createElement("div");
        result.id = "backendAssessmentResult";
        result.className = "panel-box";
        result.style.cssText =
          "display:none;margin-top:20px;overflow-wrap:anywhere;";

        const decisionBox = document.getElementById("decisionBox");
        const resultParent = decisionBox
          ? decisionBox.parentElement
          : btnRunScenario.parentElement;

        resultParent.appendChild(result);
      }
    }

    function getSelectedScenario() {
      const selected = document.querySelector(
        'input[name="simScenario"]:checked'
      );

      return selected ? selected.value : "normal";
    }

    function fillScenarioInputs() {
      const sample = scenarios[getSelectedScenario()] || scenarios.normal;

      const customer = document.getElementById("simCustomerId");
      const amount = document.getElementById("simAmount");
      const recipient = document.getElementById("simRecipient");

      if (customer) customer.value = sample.customer_id;
      if (amount) amount.value = sample.amount;
      if (recipient) recipient.value = sample.recipient;

      scenarioLabels.forEach(label => {
        const radio = label.querySelector('input[name="simScenario"]');

        label.classList.toggle(
          "active",
          !!radio && radio.checked
        );
      });
    }

    ensureSimulatorElements();

    scenarioLabels.forEach(label => {
      const radio = label.querySelector('input[name="simScenario"]');

      if (radio) {
        radio.addEventListener("change", fillScenarioInputs);

        label.addEventListener("click", () => {
          setTimeout(fillScenarioInputs, 0);
        });
      }
    });

    // Helper to insert assessed transactions into Transactions, Dashboard & Live Monitoring tables
    function renderTransactionRowInDOM(tx) {
      const txTableBody = document.querySelector("#view-transactions .data-table tbody");
      const dashTableBody = document.querySelector("#view-dashboard .data-table tbody");
      const liveTableBody = document.querySelector("#view-live-monitoring .data-table tbody");

      const txRef = String(tx.transaction_id || "TX-104").startsWith("TX-")
        ? String(tx.transaction_id)
        : `TX-${tx.transaction_id}`;

      if (txTableBody && txTableBody.querySelector(`tr[data-tx-id="${txRef}"]`)) {
        return;
      }

      const custLabel = tx.customer_name
        ? `CUST-${tx.customer_id} (${tx.customer_name})`
        : `CUST-${tx.customer_id || 101}`;
      const custShort = `CUST-${tx.customer_id || 101}`;

      const formattedAmt = "₹" + Number(tx.amount || 0).toLocaleString("en-IN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      });

      const riskRaw = String(tx.risk_level || "Low");
      const riskLower = riskRaw.toLowerCase();
      const pillClass = riskLower === "high" ? "high" : riskLower === "medium" ? "medium" : "low";

      const statusRaw = String(tx.transaction_status || tx.status || tx.recommended_action || "Unknown");
      const statusLower = statusRaw.toLowerCase();
      const finalApprovedStatuses = ["approved", "simulated_approved", "settled"];
      const finalCancelledStatuses = ["cancelled", "canceled", "rejected"];
      const statusClass = finalApprovedStatuses.includes(statusLower)
        ? "status-text-app"
        : finalCancelledStatuses.includes(statusLower)
          ? "status-text-hold"
          : riskLower === "high" || statusLower.includes("block") || statusLower.includes("hold")
            ? "status-text-hold"
            : riskLower === "medium" || statusLower.includes("challenge") || statusLower.includes("review") || statusLower.includes("verification") || statusLower.includes("verify")
              ? "status-text-rev"
              : "status-text-app";

      const timestamp = tx.timestamp || new Date().toLocaleString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false
      });

      // 1. Add to Transactions tab table
      if (txTableBody) {
        const tr = document.createElement("tr");
        tr.dataset.txId = txRef;
        tr.innerHTML = `
          <td style="font-weight: 700;">${txRef}</td>
          <td>${timestamp}</td>
          <td>${custLabel}</td>
          <td style="font-weight: 700;">${formattedAmt}</td>
          <td><span class="pill-tag ${pillClass}">${riskRaw}</span></td>
          <td><span class="${statusClass}">${statusRaw}</span></td>
        `;
        txTableBody.prepend(tr);
      }

      // 2. Add to Dashboard Recent Transactions table
      if (dashTableBody) {
        const dashTr = document.createElement("tr");
        dashTr.dataset.txId = txRef;
        dashTr.innerHTML = `
          <td style="font-weight: 700;">${txRef}</td>
          <td>${custShort}</td>
          <td style="font-weight: 700;">${formattedAmt}</td>
          <td><span class="pill-tag ${pillClass}">${riskRaw}</span></td>
          <td><span class="${statusClass}">${statusRaw}</span></td>
        `;
        dashTableBody.prepend(dashTr);
      }

      // 3. Add to Live Monitoring table
      if (liveTableBody) {
        const liveTr = document.createElement("tr");
        liveTr.dataset.txId = txRef;
        const scoreVal = tx.risk_score != null ? tx.risk_score : (riskLower === "high" ? "0.94" : riskLower === "medium" ? "0.62" : "0.08");
        const decColor = riskLower === "high" ? "var(--alert-red)" : riskLower === "medium" ? "var(--alert-yellow)" : "var(--safe-green)";
        liveTr.innerHTML = `
          <td style="color: var(--text-muted); font-size: 0.78rem;">Just now</td>
          <td style="font-weight: 700;">${txRef}</td>
          <td>${custLabel}</td>
          <td>${tx.recipient || "Recipient"}</td>
          <td style="font-weight: 700;">${formattedAmt}</td>
          <td><span class="pill-tag ${pillClass}">Score: ${scoreVal}</span></td>
          <td><strong style="color: ${decColor};">${String(tx.recommended_action || statusRaw).toUpperCase()}</strong></td>
        `;
        liveTableBody.prepend(liveTr);
      }

      // 4. Update Dashboard Summary Numbers
      const statNumbers = document.querySelectorAll("#view-dashboard .stat-number");
      if (statNumbers.length >= 3 && txTableBody) {
        const allRows = txTableBody.querySelectorAll("tr");
        let flaggedCount = 0;
        let holdCount = 0;

        allRows.forEach(row => {
          const riskPill = row.querySelector(".pill-tag");
          const statusSpan = row.querySelector("td:last-child span");
          if (riskPill && (riskPill.classList.contains("high") || riskPill.classList.contains("medium"))) {
            flaggedCount++;
          }
          if (statusSpan && statusSpan.classList.contains("status-text-hold")) {
            holdCount++;
          }
        });

        statNumbers[0].textContent = String(allRows.length);
        statNumbers[1].textContent = String(flaggedCount);
        statNumbers[2].textContent = String(holdCount);
      }
    }

    async function loadTransactions() {
      const txTableBody = document.querySelector("#view-transactions .data-table tbody");
      const dashTableBody = document.querySelector("#view-dashboard .data-table tbody");
      const liveTableBody = document.querySelector("#view-live-monitoring .data-table tbody");

      try {
        const response = await fetch(`${API_BASE_URL}/api/transactions`, {
          method: "GET",
          credentials: "include"
        });
        const data = await readApiResponse(response);
        if (!Array.isArray(data.transactions)) {
          throw new Error("The transactions API did not return a transactions array.");
        }

        // Clear demo/sample rows before rendering the authoritative SQLite records.
        [txTableBody, dashTableBody, liveTableBody]
          .filter(Boolean)
          .forEach(tbody => tbody.replaceChildren());

        data.transactions.forEach(tx => renderTransactionRowInDOM({
          ...tx,
          transaction_status: tx.status,
          timestamp: tx.created_at
        }));
      } catch (error) {
        console.error("Could not load transactions from Flask:", error);
        if (/401|403|Authentication required|Not authenticated/i.test(error.message)) {
          setLoggedOutUI();
          return;
        }
        showToast(`Could not load transactions: ${error.message}`, "#ef4444");
      }
    }

    function showAssessmentResult(data) {
      const result = document.getElementById("backendAssessmentResult");

      if (!result) {
        throw new Error("Assessment result panel was not created.");
      }

      const reasons = Array.isArray(data.reasons)
        ? data.reasons.join(", ")
        : String(data.reasons || "No explanation provided.");

      result.replaceChildren();

      const heading = document.createElement("h3");
      heading.textContent = "Flask Backend Assessment";
      result.appendChild(heading);

      const details = [
        ["Transaction ID", data.transaction_id],
        ["Customer", data.customer_name || data.customer_id],
        [
          "Amount",
          data.amount == null
            ? null
            : "₹" + Number(data.amount).toLocaleString("en-IN")
        ],
        ["Recipient", data.recipient],
        ["Risk Level", data.risk_level],
        ["Risk Score", data.risk_score],
        ["Reasons", reasons],
        ["Recommended Action", data.recommended_action],
        ["Transaction Status", data.transaction_status],
        ["Assessment Type", data.assessment_type]
      ];

      details.forEach(([label, value]) => {
        if (value === undefined || value === null || value === "") return;

        const row = document.createElement("p");
        row.style.cssText = "margin-top:10px;line-height:1.5;";

        const strong = document.createElement("strong");
        strong.textContent = label + ": ";

        const span = document.createElement("span");
        span.textContent = String(value);

        row.append(strong, span);
        result.appendChild(row);
      });

      result.style.display = "block";

      const amountField = document.getElementById("valAmt");
      const riskField = document.getElementById("valRisk");
      const payeeField = document.getElementById("valPayee");
      const velocityField = document.getElementById("valVel");
      const decisionField = document.getElementById("valDecision");
      const reasonField = document.getElementById("valReason");
      const decisionBox = document.getElementById("decisionBox");

      if (amountField && data.amount != null) {
        amountField.textContent =
          "₹" + Number(data.amount).toLocaleString("en-IN");
      }

      if (riskField && data.risk_level != null) {
        riskField.textContent = String(data.risk_level);

        const level = String(data.risk_level).toLowerCase();

        riskField.style.color =
          level === "high" ? "#ef4444" :
          level === "medium" ? "#d97706" :
          "#059669";
      }

      if (payeeField) {
        payeeField.textContent = String(data.recipient || "Not provided");
      }

      if (velocityField) {
        velocityField.textContent =
          data.is_new_recipient === true
            ? "New recipient"
            : "Checked by backend";
      }

      if (decisionField) {
        decisionField.textContent = String(data.recommended_action);
      }

      if (reasonField) {
        reasonField.textContent = reasons;
      }

      if (decisionBox) {
        const level = String(data.risk_level || "").toLowerCase();
        const action = String(data.recommended_action || "").toLowerCase();

        const statusClass =
          level === "high" || action.includes("block") || action.includes("hold")
            ? "block"
            : level === "medium" ||
              action.includes("challenge") ||
              action.includes("review")
              ? "challenge"
              : "approve";

        decisionBox.className = "decision-callout " + statusClass;
      }
    }

    // Restore previous assessment result & transaction rows if Live Server reloaded the page
    const savedAssessment = sessionStorage.getItem("elderguard_last_assessment");
    if (savedAssessment) {
      try {
        showAssessmentResult(JSON.parse(savedAssessment));
      } catch (e) {
        console.error(e);
      }
    }
    if (btnRunScenario) {
      btnRunScenario.addEventListener("click", async (e) => {
        e.preventDefault();
        if (assessmentInProgress) return;

        const customerId = Number(
          document.getElementById("simCustomerId")?.value
        );

        const amount = Number(
          document.getElementById("simAmount")?.value
        );

        const recipient = (
          document.getElementById("simRecipient")?.value || ""
        ).trim();

        const result = document.getElementById("backendAssessmentResult");

        if (!Number.isInteger(customerId) || customerId <= 0) {
          showToast("Enter a valid customer ID.", "#ef4444");
          return;
        }

        if (!Number.isFinite(amount) || amount <= 0) {
          showToast("Enter an amount greater than zero.", "#ef4444");
          return;
        }

        if (!recipient) {
          showToast("Enter a recipient name.", "#ef4444");
          return;
        }

        assessmentInProgress = true;
        btnRunScenario.disabled = true;
        btnRunScenario.textContent = "Assessing...";

        if (result) {
          result.style.display = "block";
          result.textContent = "Waiting for the Flask backend...";
        }

        try {
          const response = await fetch(
            `${API_BASE_URL}/api/transactions/assess`,
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json"
              },
              credentials: "include",
              body: JSON.stringify({
                customer_id: customerId,
                amount: amount,
                recipient: recipient
              })
            }
          );

          const rawResponse = await response.text();

          let data;

          try {
            data = rawResponse ? JSON.parse(rawResponse) : {};
          } catch {
            throw new Error(
              "The API did not return JSON. Check the Flask endpoint."
            );
          }

          if (!response.ok) {
            throw new Error(
              data.error ||
              data.message ||
              `Request failed (${response.status}).`
            );
          }

          if (
            !data ||
            typeof data !== "object" ||
            data.risk_level == null ||
            data.recommended_action == null
          ) {
            throw new Error(
              "Backend response must include risk_level and recommended_action."
            );
          }

          // Save and render new transaction into Transactions, Dashboard & Live Monitoring
          const savedList = JSON.parse(sessionStorage.getItem("elderguard_tx_history") || "[]");
          const txRecord = {
            ...data,
            transaction_id: data.transaction_id || ("TX-" + (104 + savedList.length)),
            customer_id: data.customer_id || customerId,
            amount: data.amount ?? amount,
            recipient: data.recipient || recipient,
            timestamp: new Date().toLocaleString("en-IN", {
              day: "2-digit",
              month: "short",
              year: "numeric",
              hour: "2-digit",
              minute: "2-digit",
              hour12: false
            })
          };
          savedList.push(txRecord);
          sessionStorage.setItem("elderguard_tx_history", JSON.stringify(savedList));
          sessionStorage.setItem("elderguard_last_assessment", JSON.stringify(txRecord));

          showAssessmentResult(txRecord);

          showToast("Assessment received from Flask & added to Transactions.", "#059669");

          await Promise.all([loadTransactions(), loadReviewQueue()]);

        } catch (error) {
          // Do not create a fake success record when the real API request fails.
          if (/401|403|Authentication required|Not authenticated/i.test(error.message)) {
            setLoggedOutUI();
            showToast("Your session has expired. Please sign in again.", "#ef4444");
            return;
          }
          if (result) {
            result.style.display = "block";
            result.textContent = `Backend assessment failed: ${error.message}`;
          }
          showToast(`Backend assessment failed: ${error.message}`, "#ef4444");
          console.error("Flask transaction assessment failed:", error);

        } finally {
          assessmentInProgress = false;
          btnRunScenario.disabled = false;
          btnRunScenario.textContent = "Implement this scenario";
        }
      });
    }


// 4. Database-backed Review Queue Operations
const reviewQueueContainer = document.getElementById("reviewQueueContainer");
const reviewBadge = document.getElementById("reviewBadge");
const PENDING_REVIEW_STATUSES = new Set([
  "PENDING_REVIEW",
  "PENDING_VERIFICATION",
  "HOLD_FOR_REVIEW",
  "VERIFY_RECIPIENT"
]);

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, character => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  })[character]);
}

async function fetchBackendTransactions() {
  const response = await fetch(`${API_BASE_URL}/api/transactions`, {
    method: "GET",
    credentials: "include"
  });
  const data = await readApiResponse(response);
  if (!Array.isArray(data.transactions)) {
    throw new Error("The transactions API did not return a transactions array.");
  }
  return data.transactions;
}

async function loadReviewQueue() {
  if (!reviewQueueContainer) return;

  try {
    const transactions = await fetchBackendTransactions();
    const pending = transactions.filter(tx =>
      PENDING_REVIEW_STATUSES.has(String(tx.status || "").toUpperCase())
    );

    if (reviewBadge) {
      reviewBadge.textContent = `${pending.length} PENDING REVIEW`;
    }

    if (pending.length === 0) {
      reviewQueueContainer.innerHTML = `
        <div class="panel-box">
          <h3>No pending transactions</h3>
          <p style="margin-top:8px;color:var(--text-muted);">
            Transactions requiring review will appear here after backend assessment.
          </p>
        </div>`;
      return;
    }

    reviewQueueContainer.innerHTML = pending.map(tx => {
      const id = Number(tx.transaction_id);
      const risk = String(tx.risk_level || "UNKNOWN").toUpperCase();
      const riskClass = risk === "HIGH" ? "high" : risk === "MEDIUM" ? "medium" : "low";
      const amount = "₹" + Number(tx.amount || 0).toLocaleString("en-IN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      });
      const timestamp = tx.created_at || "Timestamp unavailable";

      return `
        <div class="panel-box" style="margin-bottom:16px;">
          <div class="panel-head">
            <div>
              <h3>Transaction TX-${id}</h3>
              <p>Customer: CUST-${escapeHtml(tx.customer_id)} · Recipient: ${escapeHtml(tx.recipient || "Not provided")}</p>
              <p style="margin-top:4px;">Created: ${escapeHtml(timestamp)} · Status: ${escapeHtml(tx.status)}</p>
            </div>
            <span class="pill-tag ${riskClass}">${escapeHtml(risk)} RISK</span>
          </div>
          <div class="eval-spec" style="margin:16px 0;">
            <div class="lbl">Attempted Transfer</div>
            <div class="val" style="color:var(--alert-red);">${amount}</div>
          </div>
          <div style="display:flex;gap:12px;justify-content:flex-end;flex-wrap:wrap;">
            <button type="button" class="btn-outline btn-danger-outline"
              data-review-action="cancel" data-transaction-id="${id}">Cancel Transfer</button>
            <button type="button" class="btn-assess"
              data-review-action="approve" data-transaction-id="${id}">Approve Transaction</button>
          </div>
        </div>`;
    }).join("");
  } catch (error) {
    console.error("Could not load the review queue from Flask:", error);
    if (/401|403|Authentication required|Not authenticated/i.test(error.message)) {
      reviewQueueContainer.innerHTML = `
        <div class="panel-box"><p>Please sign in to view pending transactions.</p></div>`;
      setLoggedOutUI();
      return;
    }
    reviewQueueContainer.innerHTML = `
      <div class="panel-box"><p style="color:var(--alert-red);">Could not load review queue: ${escapeHtml(error.message)}</p></div>`;
  }
}

if (reviewQueueContainer) {
  reviewQueueContainer.addEventListener("click", async event => {
    const button = event.target.closest("button[data-review-action]");
    if (!button || button.disabled) return;

    const transactionId = Number(button.dataset.transactionId);
    const action = button.dataset.reviewAction;
    if (!Number.isInteger(transactionId) || transactionId <= 0 || !["approve", "cancel"].includes(action)) {
      showToast("Invalid review action or transaction ID.", "#ef4444");
      return;
    }

    const verb = action === "approve" ? "approve" : "cancel";
    if (!confirm(`Confirm ${verb} for transaction TX-${transactionId}?`)) return;

    button.disabled = true;
    const originalText = button.textContent;
    button.textContent = action === "approve" ? "Approving..." : "Cancelling...";

    try {
      const response = await fetch(`${API_BASE_URL}/api/transactions/${transactionId}/${action}`, {
        method: "POST",
        credentials: "include"
      });
      const data = await readApiResponse(response);
      showToast(data.message || `Transaction TX-${transactionId} ${action}d.`, "#059669");

      // Approved/cancelled records disappear from the pending queue but remain in history.
      await Promise.all([loadReviewQueue(), loadTransactions()]);
    } catch (error) {
      if (/401|403|Authentication required|Not authenticated/i.test(error.message)) {
        setLoggedOutUI();
        showToast("Your session has expired. Please sign in again.", "#ef4444");
        return;
      }
      showToast(`Could not ${verb} transaction: ${error.message}`, "#ef4444");
      console.error(`Could not ${verb} transaction:`, error);
      button.disabled = false;
      button.textContent = originalText;
    }
  });
}

// 5. Export CSV & Download Audit Log
const exportCsvBtn = document.querySelector("#view-transactions .btn-outline");
if (exportCsvBtn) {
  exportCsvBtn.addEventListener('click', () => {
    const rows = document.querySelectorAll("#view-transactions .data-table tr");
    const csvLines = [];
    rows.forEach(row => {
      const cols = Array.from(row.querySelectorAll("th, td")).map(col =>
        `"${col.textContent.trim().replace(/"/g, '""')}"`
      );
      if (cols.length) csvLines.push(cols.join(","));
    });
    downloadTextFile("elderguard_transactions.csv", csvLines.join("\n") + "\n", "text/csv");
    showToast("Transactions CSV downloaded.");
  });
}

const btnDownloadAudit = document.getElementById('btnDownloadAudit');
if (btnDownloadAudit) {
  btnDownloadAudit.addEventListener('click', () => {
    const logContent =
      "=== ELDERGUARD Z REGULATORY AUDIT LOG ===\n" +
      "Export Date: " + new Date().toISOString() + "\n\n" +
      "[2026-10-14 16:15:02] Engine: ElderGuard-Engine-v2 | Ref: TX-103 | Event: CHALLENGE_ISSUED | Hash: 8f2a...c014\n" +
      "[2026-10-14 15:40:48] Engine: RuleEngine-Vulnerability | Ref: TX-102 | Event: AUTO_HOLD_TRANSACTION | Hash: 4e99...1bfa\n" +
      "[2026-10-14 14:22:10] Engine: ElderGuard-Engine-v2 | Ref: TX-101 | Event: TRANSACTION_APPROVED | Hash: 7c01...8811\n";
    downloadTextFile("audit_trail_immutable.log", logContent, "text/plain");
    showToast("Immutable audit trail downloaded.");
  });
}

// 6. Register Customer Prompt
const btnRegisterCustomer = document.getElementById('btnRegisterCustomer');
if (btnRegisterCustomer) {
  btnRegisterCustomer.addEventListener('click', () => {
    const name = prompt("Enter Senior Customer Full Name:", "Kamla Devi");
    if (!name) return;
    const age = prompt("Enter Age:", "74");
    const guardian = prompt("Enter Designated Guardian Name & Relationship:", "Rakesh Devi (Son)");

    const tableBody = document.querySelector('#customersTable tbody');
    if (tableBody) {
      const newRow = document.createElement('tr');
      const custId = "CUST-" + Math.floor(100 + Math.random() * 900);
      newRow.innerHTML = `
        <td style="font-weight: 700;">${name} (${custId})</td>
        <td>${age || "70"}</td>
        <td>${guardian || "Designated Nominee"}</td>
        <td><span class="pill-tag low">Protected Baseline</span></td>
        <td><strong style="color: var(--safe-green);">Healthy</strong></td>
      `;
      tableBody.prepend(newRow);
      showToast(`Registered account profile for ${name} (${custId}).`);
    }
  });
}

// 7. Settings Actions, Sensitivity Feedback & Log Out Option
const btnSaveSettings = document.getElementById('btnSaveSettings');
if (btnSaveSettings) {
  btnSaveSettings.addEventListener('click', () => {
    btnSaveSettings.textContent = "Saved ✓";
    showToast("Security policies and thresholds updated successfully.");
    setTimeout(() => {
      btnSaveSettings.textContent = "Save Changes";
    }, 2000);
  });
}

const sensitivityRange = document.getElementById('sensitivityRange');
if (sensitivityRange) {
  sensitivityRange.addEventListener('input', (e) => {
    showToast(`Anomaly sensitivity set to: ${e.target.value} / 10`, "#0284c7");
  });
}

// Bind logout to the Flask session endpoint.
function ensureLogoutInSettings() {
  const settingsPanel = document.querySelector("#view-settings .panel-box");
  if (!settingsPanel) return;

  let btnLogout = document.getElementById("btnLogout");
  if (!btnLogout) {
    const logoutRow = document.createElement("div");
    logoutRow.className = "setting-row";
    logoutRow.innerHTML = `
      <div class="setting-info">
        <h4>Operator Session Control</h4>
        <p>End the current authenticated session and lock the ElderGuard Z dashboard.</p>
      </div>
      <button type="button" class="btn-outline btn-danger-outline" id="btnLogout">Log Out</button>
    `;
    settingsPanel.appendChild(logoutRow);
    btnLogout = document.getElementById("btnLogout");
  }

  if (btnLogout && !btnLogout.dataset.bound) {
    btnLogout.dataset.bound = "true";
    btnLogout.addEventListener("click", async () => {
      btnLogout.disabled = true;
      try {
        const response = await fetch(`${API_BASE_URL}/api/auth/logout`, {
          method: "POST",
          credentials: "include"
        });
        // Lock the UI even if the server session has already expired.
        if (!response.ok && response.status !== 401) {
          const data = await readApiResponse(response);
          throw new Error(data.message || data.error || "Logout failed.");
        }
        setLoggedOutUI();
        if (typeof switchTab === "function") switchTab("dashboard", "Dashboard");
        showToast("Logged out safely. Session locked.", "#ef4444");
      } catch (error) {
        showToast(error.message === "Failed to fetch"
          ? "Could not contact Flask. Check the backend, then try logging out again."
          : error.message, "#ef4444");
      } finally {
        btnLogout.disabled = false;
      }
    });
  }
}

ensureLogoutInSettings();