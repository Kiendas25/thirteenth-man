const API = '';
let authToken = localStorage.getItem('13m_token');
let currentTaskId = null;
let inputMode = 'text';

// -------------------------------------------------------------------------
// Init
// -------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', async () => {
  // Check auth
  if (authToken) {
    const res = await fetch(`${API}/api/auth/me`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    const data = await res.json();
    if (data.authenticated) {
      showLoggedIn(data.username);
    } else {
      authToken = null;
      localStorage.removeItem('13m_token');
      showAuthModal();
    }
  } else {
    showAuthModal();
  }
  loadAgents();
  loadHistory();
  loadSettings();
});

// -------------------------------------------------------------------------
// Auth
// -------------------------------------------------------------------------

let authMode = 'login';

function showAuthModal() {
  document.getElementById('auth-modal').style.display = 'flex';
}

function hideAuthModal() {
  document.getElementById('auth-modal').style.display = 'none';
}

function authToggle() {
  authMode = authMode === 'login' ? 'register' : 'login';
  document.getElementById('auth-title').textContent =
    authMode === 'login' ? 'Login' : 'Create Account';
  document.getElementById('auth-submit-btn').textContent =
    authMode === 'login' ? 'Login' : 'Register';
  document.getElementById('auth-toggle-text').textContent =
    authMode === 'login' ? 'Create Account' : 'Back to Login';
  document.getElementById('auth-error').style.display = 'none';
}

async function authSubmit() {
  const username = document.getElementById('auth-username').value.trim();
  const password = document.getElementById('auth-password').value;
  const errEl = document.getElementById('auth-error');

  if (!username || !password) {
    errEl.textContent = 'Fill in both fields';
    errEl.style.display = 'block';
    return;
  }

  const endpoint = authMode === 'login' ? '/api/auth/login' : '/api/auth/register';
  try {
    const res = await fetch(`${API}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();

    if (!res.ok) {
      errEl.textContent = data.detail || 'Error';
      errEl.style.display = 'block';
      return;
    }

    if (authMode === 'register') {
      // Auto-login after register
      authMode = 'login';
      await authSubmit();
      return;
    }

    authToken = data.access_token;
    localStorage.setItem('13m_token', authToken);
    showLoggedIn(data.username);
    hideAuthModal();
  } catch (e) {
    errEl.textContent = 'Connection error';
    errEl.style.display = 'block';
  }
}

function authSkip() {
  hideAuthModal();
}

function showLoggedIn(username) {
  document.getElementById('user-info').textContent = username;
  document.getElementById('logout-btn').style.display = 'inline-block';
}

function logout() {
  authToken = null;
  localStorage.removeItem('13m_token');
  document.getElementById('user-info').textContent = '';
  document.getElementById('logout-btn').style.display = 'none';
  showAuthModal();
}

function authHeaders() {
  const h = { 'Content-Type': 'application/json' };
  if (authToken) h['Authorization'] = `Bearer ${authToken}`;
  return h;
}

// -------------------------------------------------------------------------
// Input mode tabs
// -------------------------------------------------------------------------

function setInputMode(mode) {
  inputMode = mode;
  document.getElementById('tab-text').classList.toggle('active', mode === 'text');
  document.getElementById('tab-code').classList.toggle('active', mode === 'code');
  document.getElementById('code-input-area').style.display =
    mode === 'code' ? 'flex' : 'none';
  document.getElementById('task-input').placeholder =
    mode === 'code'
      ? 'Describe what to analyse in this code (or leave blank for full review)...'
      : 'Describe your task... Jarvis will route it to the right specialists and the 13th Man will verify the result.';
}

// -------------------------------------------------------------------------
// Load agents
// -------------------------------------------------------------------------

async function loadAgents() {
  try {
    const res = await fetch(`${API}/api/agents`);
    const agents = await res.json();
    const list = document.getElementById('agents-list');
    list.innerHTML = agents
      .map(
        (a) => `
      <div class="agent-card" id="agent-${a.id}">
        <div class="name">${escapeHtml(a.name)}</div>
        <div class="role">${escapeHtml(a.role)}</div>
      </div>
    `,
      )
      .join('');
  } catch (e) {
    console.error('Failed to load agents', e);
  }
}

// -------------------------------------------------------------------------
// Load settings
// -------------------------------------------------------------------------

async function loadSettings() {
  try {
    const res = await fetch(`${API}/api/settings`);
    const s = await res.json();
    document.getElementById('settings-panel').innerHTML = `
      <div class="setting-row">
        <span class="setting-label">Provider</span>
        <span class="setting-value">${escapeHtml(s.llm_provider)}</span>
      </div>
      <div class="setting-row">
        <span class="setting-label">Model</span>
        <span class="setting-value">${escapeHtml(s.llm_model)}</span>
      </div>
      <div class="setting-row">
        <span class="setting-label">HITL</span>
        <span class="setting-value">${s.require_human_approval ? 'On' : 'Off'}</span>
      </div>
    `;
  } catch (e) {
    console.error('Failed to load settings', e);
  }
}

// -------------------------------------------------------------------------
// Load history
// -------------------------------------------------------------------------

async function loadHistory() {
  try {
    const res = await fetch(`${API}/api/tasks`);
    const tasks = await res.json();
    const list = document.getElementById('history-list');
    if (!tasks.length) {
      list.innerHTML = '<p style="font-size:12px;color:var(--text-dim);">No tasks yet</p>';
      return;
    }
    list.innerHTML = tasks
      .map(
        (t) => `
      <div class="history-item" onclick="loadTask('${t.id}')">
        <div class="task-text">${escapeHtml(t.final_answer?.substring(0, 80) || t.id)}</div>
        <div class="meta">${t.status} - ${t.created_at}</div>
      </div>
    `,
      )
      .join('');
  } catch (e) {
    console.error('Failed to load history', e);
  }
}

// -------------------------------------------------------------------------
// Load previous task
// -------------------------------------------------------------------------

async function loadTask(taskId) {
  try {
    const res = await fetch(`${API}/api/tasks/${taskId}`);
    if (!res.ok) return;
    const data = await res.json();
    currentTaskId = data.task_id;
    renderResponse(data);
    renderVerification(data.verification);
    renderTrace(data.trace);
    renderApprovals(data.approval);
    highlightAgents(data.specialists_used);
    showExportSection();
  } catch (e) {
    console.error('Failed to load task', e);
  }
}

// -------------------------------------------------------------------------
// Submit task
// -------------------------------------------------------------------------

async function submitTask() {
  const input = document.getElementById('task-input');
  const btn = document.getElementById('submit-btn');
  let content = input.value.trim();

  // Code review mode
  if (inputMode === 'code') {
    const code = document.getElementById('code-input').value.trim();
    const lang = document.getElementById('code-language').value;
    if (!code) {
      alert('Please paste code to review');
      return;
    }
    const langLabel = lang || 'code';
    const instruction = content || 'Perform a comprehensive code review. Find bugs, security vulnerabilities, performance issues, and suggest improvements.';
    content = `${instruction}\n\n\`\`\`${langLabel}\n${code}\n\`\`\``;
  }

  if (!content) return;

  btn.disabled = true;
  input.disabled = true;

  const responseArea = document.getElementById('response-area');
  responseArea.innerHTML = `
    <div class="loading">
      <div class="spinner"></div>
      <span>Jarvis is routing your task to specialists...</span>
    </div>
  `;

  document.querySelectorAll('.agent-card.active').forEach((c) => c.classList.remove('active'));

  try {
    const res = await fetch(`${API}/api/tasks`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ content }),
    });

    if (!res.ok) {
      let errMsg = 'Request failed';
      try {
        const err = await res.json();
        errMsg = err.detail || errMsg;
      } catch (_) {
        errMsg = (await res.text()) || errMsg;
      }
      throw new Error(errMsg);
    }

    const data = await res.json();
    currentTaskId = data.task_id;
    renderResponse(data);
    renderVerification(data.verification);
    renderTrace(data.trace);
    renderApprovals(data.approval);
    highlightAgents(data.specialists_used);
    loadHistory();
    showExportSection();
  } catch (err) {
    responseArea.innerHTML = `
      <div class="response-card">
        <h3 style="color: var(--red);">Error</h3>
        <p class="answer">${escapeHtml(err.message)}</p>
      </div>
    `;
  } finally {
    btn.disabled = false;
    input.disabled = false;
  }
}

// -------------------------------------------------------------------------
// Render response with markdown
// -------------------------------------------------------------------------

function simpleMarkdown(text) {
  if (!text) return '';
  let html = escapeHtml(text);
  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  // Headers
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  // Code blocks
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  // Unordered lists
  html = html.replace(/^\* (.+)$/gm, '<li>$1</li>');
  html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
  // Ordered lists
  html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
  // Wrap consecutive <li> in <ul>
  html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>');
  // Paragraphs (double newline)
  html = html.replace(/\n\n/g, '</p><p>');
  html = '<p>' + html + '</p>';
  // Single newlines to <br> (but not inside pre/code)
  html = html.replace(/\n/g, '<br>');
  // Clean up empty tags
  html = html.replace(/<p><\/p>/g, '');
  html = html.replace(/<p><br>/g, '<p>');
  return html;
}

function renderResponse(data) {
  const responseArea = document.getElementById('response-area');
  const statusBadge = data.status === 'completed'
    ? '<span class="badge passed">Completed</span>'
    : `<span class="badge pending">${escapeHtml(data.status)}</span>`;
  const issuesBadge = data.verification && !data.verification.passed
    ? '<span class="badge failed">Issues Found</span>'
    : data.verification
      ? '<span class="badge passed">Verified</span>'
      : '';

  let specialistsHtml = '';
  if (data.specialist_results && data.specialist_results.length) {
    specialistsHtml = `
      <details style="margin-top: 16px;">
        <summary style="cursor: pointer; font-weight: 600; font-size: 13px; color: var(--accent);">
          Specialist Outputs (${data.specialist_results.length})
        </summary>
        ${data.specialist_results
          .map(
            (r) => `
          <div class="specialist-result" style="margin-top: 8px;">
            <div class="name">${escapeHtml(r.agent_name)}</div>
            <div class="content">${simpleMarkdown(r.content)}</div>
          </div>
        `,
          )
          .join('')}
      </details>
    `;
  }

  responseArea.innerHTML = `
    <div class="response-card">
      <h3>Final Answer ${statusBadge} ${issuesBadge}</h3>
      <div class="answer">${simpleMarkdown(data.final_answer)}</div>
      ${specialistsHtml}
    </div>
  `;
}

// -------------------------------------------------------------------------
// Verification
// -------------------------------------------------------------------------

function renderVerification(v) {
  const panel = document.getElementById('verification-panel');
  if (!v) {
    panel.innerHTML = '<p style="font-size: 12px; color: var(--text-dim);">No verification yet</p>';
    return;
  }
  const badge = v.passed
    ? '<span class="badge passed">Passed</span>'
    : '<span class="badge failed">Failed</span>';
  const riskBadge = `<span class="badge ${v.risk_level}">${v.risk_level}</span>`;

  let issuesHtml = '';
  if (v.issues && v.issues.length) {
    issuesHtml = `
      <div class="issues" style="margin-top: 8px;">
        <strong style="font-size: 12px;">Issues:</strong>
        <ul>${v.issues.map((i) => `<li>${escapeHtml(i)}</li>`).join('')}</ul>
      </div>
    `;
  }

  let recsHtml = '';
  if (v.recommendations && v.recommendations.length) {
    recsHtml = `
      <div class="issues" style="margin-top: 8px;">
        <strong style="font-size: 12px;">Recommendations:</strong>
        <ul>${v.recommendations.map((r) => `<li>${escapeHtml(r)}</li>`).join('')}</ul>
      </div>
    `;
  }

  panel.innerHTML = `
    <div class="verification">
      <div class="header">${badge} ${riskBadge}</div>
      <p style="font-size: 12px; line-height: 1.5;">${escapeHtml(v.reasoning || '')}</p>
      ${issuesHtml}
      ${recsHtml}
    </div>
  `;
}

// -------------------------------------------------------------------------
// Trace
// -------------------------------------------------------------------------

function renderTrace(trace) {
  const panel = document.getElementById('trace-panel');
  if (!trace || !trace.length) {
    panel.innerHTML = '<p style="font-size: 12px; color: var(--text-dim);">No trace yet</p>';
    return;
  }
  panel.innerHTML = trace
    .map(
      (t) => `
    <div class="trace-entry">
      <span class="agent-name">${escapeHtml(t.agent)}</span>
      <span class="duration">${t.duration_ms}ms</span>
      <div class="detail">${escapeHtml(t.action)}: ${escapeHtml(t.detail)}</div>
    </div>
  `,
    )
    .join('');
}

// -------------------------------------------------------------------------
// Approvals
// -------------------------------------------------------------------------

function renderApprovals(approval) {
  const panel = document.getElementById('approvals-panel');
  if (!approval) {
    panel.innerHTML = '<p style="font-size: 12px; color: var(--text-dim);">None</p>';
    return;
  }
  panel.innerHTML = `
    <div class="approval-card">
      <p style="font-size: 12px;">${escapeHtml(approval.reason)}</p>
      <p style="font-size: 11px; color: var(--text-dim); margin-top:4px;">
        Risk: <span class="badge ${approval.risk_level}">${approval.risk_level}</span>
      </p>
      <div class="actions">
        <button class="btn-approve" onclick="resolveApproval('${approval.id}', true)">Approve</button>
        <button class="btn-reject" onclick="resolveApproval('${approval.id}', false)">Reject</button>
      </div>
    </div>
  `;
}

async function resolveApproval(id, approved) {
  try {
    await fetch(`${API}/api/approvals/${id}`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ approved }),
    });
    renderApprovals(null);
  } catch (e) {
    console.error('Approval error', e);
  }
}

// -------------------------------------------------------------------------
// Highlight active agents
// -------------------------------------------------------------------------

function highlightAgents(used) {
  document.querySelectorAll('.agent-card.active').forEach((c) => c.classList.remove('active'));
  if (!used) return;
  used.forEach((id) => {
    const card = document.getElementById(`agent-${id}`);
    if (card) card.classList.add('active');
  });
}

// -------------------------------------------------------------------------
// Export
// -------------------------------------------------------------------------

function showExportSection() {
  document.getElementById('export-section').style.display = 'block';
}

function exportResult(format) {
  if (!currentTaskId) return;
  window.open(`${API}/api/tasks/${currentTaskId}/export/${format}`, '_blank');
}

// -------------------------------------------------------------------------
// Utils
// -------------------------------------------------------------------------

function escapeHtml(text) {
  if (!text) return '';
  const d = document.createElement('div');
  d.textContent = text;
  return d.innerHTML;
}
