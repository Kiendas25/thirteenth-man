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
  ['text', 'code', 'github', 'audit'].forEach(m => {
    const tab = document.getElementById(`tab-${m}`);
    if (tab) tab.classList.toggle('active', mode === m);
  });
  document.getElementById('code-input-area').style.display = mode === 'code' ? 'flex' : 'none';
  document.getElementById('github-input-area').style.display = mode === 'github' ? 'flex' : 'none';
  document.getElementById('audit-input-area').style.display = mode === 'audit' ? 'flex' : 'none';

  const taskInput = document.getElementById('task-input');
  const placeholders = {
    text: 'Describe your task... Jarvis will route it to the right specialists and the 13th Man will verify the result.',
    code: 'Describe what to analyse in this code (or leave blank for full review)...',
    github: 'Additional instructions for the repo/PR analysis (optional)...',
    audit: '',
  };
  taskInput.placeholder = placeholders[mode] || placeholders.text;
  taskInput.style.display = mode === 'audit' ? 'none' : 'block';
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

  // GitHub mode
  if (inputMode === 'github') {
    const owner = document.getElementById('gh-owner').value.trim();
    const repo = document.getElementById('gh-repo').value.trim();
    const ref = document.getElementById('gh-ref').value.trim() || 'main';
    const prNum = document.getElementById('gh-pr').value.trim();
    const postComment = document.getElementById('gh-comment').checked;

    if (!owner || !repo) { alert('Enter owner and repo name'); return; }

    btn.disabled = true;
    const responseArea = document.getElementById('response-area');
    responseArea.innerHTML = `<div class="loading"><div class="spinner"></div><span>${prNum ? 'Analysing PR #' + prNum : 'Analysing repository'}...</span></div>`;

    try {
      let url, body;
      if (prNum) {
        url = `${API}/api/github/analyse-pr`;
        body = { owner, repo, pr_number: parseInt(prNum), post_comment: postComment };
      } else {
        url = `${API}/api/github/analyse-repo`;
        body = { owner, repo, ref };
      }
      const res = await fetch(url, { method: 'POST', headers: authHeaders(), body: JSON.stringify(body) });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(err.detail || 'Request failed');
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
      responseArea.innerHTML = `<div class="response-card"><h3 style="color:var(--red);">Error</h3><p class="answer">${escapeHtml(err.message)}</p></div>`;
    } finally { btn.disabled = false; }
    return;
  }

  // AI Audit mode
  if (inputMode === 'audit') {
    const productName = document.getElementById('audit-product-name').value.trim() || 'AI System';
    const description = document.getElementById('audit-description').value.trim();
    const aiOutput = document.getElementById('audit-output').value.trim();

    if (!description) { alert('Describe the AI system to audit'); return; }

    btn.disabled = true;
    const responseArea = document.getElementById('response-area');
    responseArea.innerHTML = `<div class="loading"><div class="spinner"></div><span>Running EU AI Act compliance audit...</span></div>`;

    try {
      const res = await fetch(`${API}/api/audit`, {
        method: 'POST', headers: authHeaders(),
        body: JSON.stringify({ description, ai_output: aiOutput || null, product_name: productName }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(err.detail || 'Audit failed');
      }
      const data = await res.json();
      renderAuditResult(data, productName);
    } catch (err) {
      responseArea.innerHTML = `<div class="response-card"><h3 style="color:var(--red);">Error</h3><p class="answer">${escapeHtml(err.message)}</p></div>`;
    } finally { btn.disabled = false; }
    return;
  }

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

// -------------------------------------------------------------------------
// Audit result renderer
// -------------------------------------------------------------------------

function renderAuditResult(data, productName) {
  const responseArea = document.getElementById('response-area');
  const scoreColor = data.score >= 80 ? 'var(--green)' : data.score >= 50 ? 'var(--orange)' : 'var(--red)';
  const complianceClass = data.overall_compliance === 'compliant' ? 'passed' : data.overall_compliance === 'non_compliant' ? 'failed' : 'pending';

  let findingsHtml = '';
  if (data.findings && data.findings.length) {
    findingsHtml = `
      <table style="width:100%;border-collapse:collapse;margin-top:12px;font-size:12px;">
        <tr style="background:var(--surface-2);">
          <th style="padding:8px;text-align:left;border:1px solid var(--border);">Check</th>
          <th style="padding:8px;text-align:left;border:1px solid var(--border);">Status</th>
          <th style="padding:8px;text-align:left;border:1px solid var(--border);">Evidence</th>
          <th style="padding:8px;text-align:left;border:1px solid var(--border);">Action</th>
        </tr>
        ${data.findings.map(f => {
          const statusColor = f.status === 'pass' ? 'var(--green)' : f.status === 'fail' ? 'var(--red)' : 'var(--orange)';
          return `<tr>
            <td style="padding:6px 8px;border:1px solid var(--border);">${escapeHtml(f.checklist_id)}</td>
            <td style="padding:6px 8px;border:1px solid var(--border);color:${statusColor};font-weight:600;">${f.status.toUpperCase()}</td>
            <td style="padding:6px 8px;border:1px solid var(--border);color:var(--text-dim);">${escapeHtml(f.evidence)}</td>
            <td style="padding:6px 8px;border:1px solid var(--border);color:var(--text-dim);">${escapeHtml(f.recommendation)}</td>
          </tr>`;
        }).join('')}
      </table>`;
  }

  let criticalHtml = '';
  if (data.critical_issues && data.critical_issues.length) {
    criticalHtml = `
      <div style="margin-top:16px;">
        <h3 style="color:var(--red);font-size:13px;">Critical Issues</h3>
        <ul style="margin:8px 0 0 16px;">${data.critical_issues.map(i => `<li style="color:var(--red);font-size:12px;margin-bottom:4px;">${escapeHtml(i)}</li>`).join('')}</ul>
      </div>`;
  }

  let stepsHtml = '';
  if (data.next_steps && data.next_steps.length) {
    stepsHtml = `
      <div style="margin-top:16px;">
        <h3 style="font-size:13px;">Next Steps</h3>
        <ol style="margin:8px 0 0 16px;">${data.next_steps.map(s => `<li style="font-size:12px;margin-bottom:4px;color:var(--text-dim);">${escapeHtml(s)}</li>`).join('')}</ol>
      </div>`;
  }

  responseArea.innerHTML = `
    <div class="response-card">
      <h3>EU AI Act Compliance Audit — ${escapeHtml(productName)}</h3>

      <div style="display:flex;gap:24px;align-items:center;margin:16px 0;padding:16px;background:var(--surface-2);border-radius:8px;">
        <div style="text-align:center;">
          <div style="font-size:48px;font-weight:800;color:${scoreColor};">${data.score}</div>
          <div style="font-size:11px;color:var(--text-dim);">/ 100</div>
        </div>
        <div>
          <div style="margin-bottom:4px;"><span class="badge ${complianceClass}">${data.overall_compliance.replace(/_/g, ' ').toUpperCase()}</span></div>
          <div style="font-size:12px;color:var(--text-dim);">Risk Classification: <strong style="color:var(--text);">${data.risk_classification.toUpperCase()}</strong></div>
        </div>
      </div>

      <div class="answer">${simpleMarkdown(data.summary)}</div>

      ${findingsHtml}
      ${criticalHtml}
      ${stepsHtml}

      <div style="margin-top:16px;">
        <button class="btn-export" onclick="downloadCertificate('${escapeHtml(productName)}')">Download Certificate</button>
      </div>
    </div>
  `;

  // Hide normal verification/trace for audit results
  document.getElementById('verification-panel').innerHTML = '<p style="font-size:12px;color:var(--text-dim);">Audit mode — see main panel</p>';
  document.getElementById('trace-panel').innerHTML = '<p style="font-size:12px;color:var(--text-dim);">Audit mode</p>';
}

async function downloadCertificate(productName) {
  const description = document.getElementById('audit-description').value.trim();
  const aiOutput = document.getElementById('audit-output').value.trim();
  try {
    const res = await fetch(`${API}/api/audit/certificate`, {
      method: 'POST', headers: authHeaders(),
      body: JSON.stringify({ description, ai_output: aiOutput || null, product_name: productName }),
    });
    if (!res.ok) throw new Error('Failed to generate certificate');
    const html = await res.text();
    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `13thman-certificate-${productName}.html`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    alert('Error generating certificate: ' + err.message);
  }
}
