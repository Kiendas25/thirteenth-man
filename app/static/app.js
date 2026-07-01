// 13th Man — Frontend Application

const API = '';

// -------------------------------------------------------------------------
// Initialisation
// -------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
  loadAgents();
  loadHistory();

  document.getElementById('task-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submitTask();
    }
  });
});

// -------------------------------------------------------------------------
// Load agents sidebar
// -------------------------------------------------------------------------

async function loadAgents() {
  try {
    const res = await fetch(`${API}/api/agents`);
    const agents = await res.json();
    const container = document.getElementById('agents-list');
    container.innerHTML = agents.map(a => `
      <div class="agent-card" id="agent-${a.id}">
        <div class="name">${a.name}</div>
        <div class="role">${a.role}</div>
      </div>
    `).join('');
  } catch (err) {
    console.error('Failed to load agents:', err);
  }
}

// -------------------------------------------------------------------------
// Load task history
// -------------------------------------------------------------------------

async function loadHistory() {
  try {
    const res = await fetch(`${API}/api/tasks`);
    const tasks = await res.json();
    const container = document.getElementById('history-list');
    if (tasks.length === 0) {
      container.innerHTML = '<p style="font-size: 12px; color: var(--text-dim);">No tasks yet</p>';
      return;
    }
    container.innerHTML = tasks.map(t => `
      <div class="history-item" onclick="loadTaskDetail('${t.id}')">
        <div class="task-text">${escapeHtml(t.final_answer?.substring(0, 60) || t.id)}</div>
        <div class="meta">${t.status} &middot; ${new Date(t.created_at).toLocaleString()}</div>
      </div>
    `).join('');
  } catch (err) {
    console.error('Failed to load history:', err);
  }
}

// -------------------------------------------------------------------------
// Submit task
// -------------------------------------------------------------------------

async function submitTask() {
  const input = document.getElementById('task-input');
  const btn = document.getElementById('submit-btn');
  const content = input.value.trim();
  if (!content) return;

  btn.disabled = true;
  input.disabled = true;

  // Show loading
  const responseArea = document.getElementById('response-area');
  responseArea.innerHTML = `
    <div class="loading">
      <div class="spinner"></div>
      <span>Jarvis is routing your task to specialists...</span>
    </div>
  `;

  // Clear highlights
  document.querySelectorAll('.agent-card.active').forEach(c => c.classList.remove('active'));

  try {
    const res = await fetch(`${API}/api/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });

    if (!res.ok) {
      let errMsg = 'Request failed';
      try {
        const err = await res.json();
        errMsg = err.detail || errMsg;
      } catch (_) {
        errMsg = await res.text() || errMsg;
      }
      throw new Error(errMsg);
    }

    const data = await res.json();
    renderResponse(data);
    renderVerification(data.verification);
    renderTrace(data.trace);
    renderApprovals(data.approval);
    highlightAgents(data.specialists_used);
    loadHistory();

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
    input.value = '';
    input.focus();
  }
}

// -------------------------------------------------------------------------
// Render response
// -------------------------------------------------------------------------

function renderResponse(data) {
  const responseArea = document.getElementById('response-area');

  let specialistsHtml = '';
  if (data.specialist_results && data.specialist_results.length > 0) {
    specialistsHtml = `
      <div style="margin-top: 16px;">
        <h3 style="font-size: 13px; margin-bottom: 8px;">Specialist Outputs</h3>
        ${data.specialist_results.map(r => `
          <div class="specialist-result">
            <div class="name">${escapeHtml(r.agent_name)}</div>
            <div class="content">${escapeHtml(r.content)}</div>
          </div>
        `).join('')}
      </div>
    `;
  }

  responseArea.innerHTML = `
    <div class="response-card">
      <h3>
        Final Answer
        <span class="badge ${data.status}">${data.status}</span>
        ${data.verification ? `<span class="badge ${data.verification.passed ? 'passed' : 'failed'}">${data.verification.passed ? 'Verified' : 'Issues Found'}</span>` : ''}
      </h3>
      <div class="answer">${escapeHtml(data.final_answer)}</div>
      ${specialistsHtml}
    </div>
  `;
}

// -------------------------------------------------------------------------
// Render verification panel
// -------------------------------------------------------------------------

function renderVerification(v) {
  const panel = document.getElementById('verification-panel');
  if (!v) {
    panel.innerHTML = '<p style="font-size: 12px; color: var(--text-dim);">No verification</p>';
    return;
  }

  let issuesHtml = '';
  if (v.issues && v.issues.length > 0) {
    issuesHtml = `
      <div class="issues">
        <strong>Issues:</strong>
        <ul>${v.issues.map(i => `<li>${escapeHtml(i)}</li>`).join('')}</ul>
      </div>
    `;
  }

  let recsHtml = '';
  if (v.recommendations && v.recommendations.length > 0) {
    recsHtml = `
      <div class="issues" style="margin-top: 8px;">
        <strong>Recommendations:</strong>
        <ul>${v.recommendations.map(r => `<li>${escapeHtml(r)}</li>`).join('')}</ul>
      </div>
    `;
  }

  panel.innerHTML = `
    <div class="verification">
      <div class="header">
        <span class="badge ${v.passed ? 'passed' : 'failed'}">${v.passed ? 'PASSED' : 'FAILED'}</span>
        <span class="badge ${v.risk_level}">${v.risk_level}</span>
      </div>
      <p style="font-size: 12px; margin-top: 8px;">${escapeHtml(v.reasoning)}</p>
      ${issuesHtml}
      ${recsHtml}
    </div>
  `;
}

// -------------------------------------------------------------------------
// Render trace
// -------------------------------------------------------------------------

function renderTrace(trace) {
  const panel = document.getElementById('trace-panel');
  if (!trace || trace.length === 0) {
    panel.innerHTML = '<p style="font-size: 12px; color: var(--text-dim);">No trace</p>';
    return;
  }

  panel.innerHTML = trace.map(t => `
    <div class="trace-entry">
      <span class="agent-name">${escapeHtml(t.agent)}</span>
      <span class="duration">${t.duration_ms}ms</span>
      <div class="detail">${escapeHtml(t.action)}: ${escapeHtml(t.detail)}</div>
    </div>
  `).join('');
}

// -------------------------------------------------------------------------
// Render approvals
// -------------------------------------------------------------------------

function renderApprovals(approval) {
  const panel = document.getElementById('approvals-panel');
  if (!approval) {
    panel.innerHTML = '<p style="font-size: 12px; color: var(--text-dim);">None</p>';
    return;
  }

  panel.innerHTML = `
    <div class="approval-card">
      <div style="font-size: 13px; font-weight: 600;">${escapeHtml(approval.action_description)}</div>
      <div style="font-size: 11px; color: var(--text-dim); margin-top: 4px;">
        Risk: <span class="badge ${approval.risk_level}">${approval.risk_level}</span>
      </div>
      <div class="actions">
        <button class="btn-approve" onclick="resolveApproval('${approval.id}', true)">Approve</button>
        <button class="btn-reject" onclick="resolveApproval('${approval.id}', false)">Reject</button>
      </div>
    </div>
  `;
}

// -------------------------------------------------------------------------
// Resolve approval
// -------------------------------------------------------------------------

async function resolveApproval(id, approved) {
  try {
    await fetch(`${API}/api/approvals/${id}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approved }),
    });
    const panel = document.getElementById('approvals-panel');
    panel.innerHTML = `<p style="font-size: 12px; color: ${approved ? 'var(--green)' : 'var(--red)'};">${approved ? 'Approved' : 'Rejected'}</p>`;
  } catch (err) {
    console.error('Approval error:', err);
  }
}

// -------------------------------------------------------------------------
// Highlight active agents
// -------------------------------------------------------------------------

function highlightAgents(ids) {
  document.querySelectorAll('.agent-card').forEach(c => c.classList.remove('active'));
  if (!ids) return;
  ids.forEach(id => {
    const el = document.getElementById(`agent-${id}`);
    if (el) el.classList.add('active');
  });
}

// -------------------------------------------------------------------------
// Load task detail from history
// -------------------------------------------------------------------------

async function loadTaskDetail(taskId) {
  try {
    const res = await fetch(`${API}/api/tasks/${taskId}`);
    if (!res.ok) return;
    const data = await res.json();
    renderResponse(data);
    renderVerification(data.verification);
    renderTrace(data.trace);
    renderApprovals(data.approval);
    highlightAgents(data.specialists_used);
  } catch (err) {
    console.error('Failed to load task:', err);
  }
}

// -------------------------------------------------------------------------
// Utils
// -------------------------------------------------------------------------

function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
