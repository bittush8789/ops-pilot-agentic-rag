/* ============================================================
   OpsPilot — Frontend Application Logic
   Vanilla JavaScript SPA
   ============================================================ */

const API_BASE = '';   // Same origin — FastAPI serves both
let currentView = 'dashboard';
let currentRunId = null;
let currentTicketId = null;
let pollInterval = null;

// ── Initialization ─────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  // Bind navigation
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', e => {
      e.preventDefault();
      switchView(item.dataset.view);
    });
  });

  // Initial load
  loadDashboard();
  checkSystemHealth();

  // Auto-refresh pending approvals badge every 10s
  setInterval(refreshApprovalBadge, 10000);
});

// ── View Navigation ─────────────────────────────────────────────

function switchView(view) {
  currentView = view;

  // Update nav
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
  const navEl = document.getElementById(`nav-${view}`);
  if (navEl) navEl.classList.add('active');

  // Update content
  document.querySelectorAll('.view').forEach(el => el.classList.remove('active'));
  const viewEl = document.getElementById(`view-${view}`);
  if (viewEl) viewEl.classList.add('active');

  // Update page title
  const titles = {
    dashboard: 'Dashboard',
    tickets: 'Tickets',
    investigation: 'Investigation',
    approvals: 'Approvals',
    trace: 'Trace',
    audit: 'Audit Log',
  };
  document.getElementById('page-title').textContent = titles[view] || view;

  // Load view data
  switch (view) {
    case 'dashboard':    loadDashboard(); break;
    case 'tickets':      loadTickets(); break;
    case 'approvals':    loadApprovals(); break;
    case 'audit':        loadAuditLog(); break;
  }
}

function refreshCurrentView() {
  switchView(currentView);
}

// ── API helpers ─────────────────────────────────────────────────

async function apiFetch(path, options = {}) {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return await res.json();
  } catch (e) {
    throw e;
  }
}

// ── Health check ─────────────────────────────────────────────────

async function checkSystemHealth() {
  try {
    const health = await apiFetch('/health');
    const dot = document.getElementById('connection-status');
    const dotEl = dot.querySelector('.status-dot');
    if (health.status === 'healthy') {
      dotEl.className = 'status-dot status-dot--green';
      dot.querySelector('span:last-child').textContent = 'System Online';
    } else {
      dotEl.className = 'status-dot status-dot--amber';
      dot.querySelector('span:last-child').textContent = 'System Degraded';
    }
  } catch {
    const dot = document.getElementById('connection-status');
    if (dot) {
      dot.querySelector('.status-dot').className = 'status-dot status-dot--red';
      dot.querySelector('span:last-child').textContent = 'Connection Error';
    }
  }
}

// ── Dashboard ─────────────────────────────────────────────────────

async function loadDashboard() {
  try {
    const stats = await apiFetch('/dashboard/stats');
    document.getElementById('stat-open').textContent = stats.open_tickets;
    document.getElementById('stat-approvals').textContent = stats.pending_approvals;
    document.getElementById('stat-completed').textContent = stats.completed_investigations;
    document.getElementById('stat-actions').textContent = stats.successful_actions;

    // Update badge
    const badge = document.getElementById('badge-approvals');
    if (badge) badge.textContent = stats.pending_approvals;

    // Load recent tickets
    const tickets = await apiFetch('/tickets?limit=8');
    renderDashboardTickets(tickets);
  } catch (e) {
    console.error('Dashboard load failed:', e);
  }
}

function renderDashboardTickets(tickets) {
  const tbody = document.getElementById('dashboard-tickets-body');
  if (!tickets || tickets.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="loading-cell">No tickets found</td></tr>';
    return;
  }
  tbody.innerHTML = tickets.map(t => `
    <tr>
      <td><span class="text-mono">${esc(t.ticket_number)}</span></td>
      <td style="max-width:280px">${esc(t.title)}</td>
      <td>${priorityBadge(t.priority)}</td>
      <td>${statusBadge(t.status)}</td>
      <td><span class="text-muted">${relativeTime(t.created_at)}</span></td>
      <td>
        <button class="btn btn-sm btn-secondary" onclick="openTicketDetail('${t.ticket_id}')">View</button>
      </td>
    </tr>
  `).join('');
}

// ── Tickets ───────────────────────────────────────────────────────

async function loadTickets() {
  const status   = document.getElementById('filter-status')?.value || '';
  const priority = document.getElementById('filter-priority')?.value || '';

  let url = '/tickets?limit=100';
  if (status)   url += `&status=${status}`;
  if (priority) url += `&priority=${priority}`;

  try {
    const tickets = await apiFetch(url);
    const badge = document.getElementById('badge-tickets');
    if (badge) badge.textContent = tickets.length;

    renderTicketList(tickets);
  } catch (e) {
    document.getElementById('ticket-list').innerHTML =
      `<div class="empty-state"><p>Failed to load tickets: ${e.message}</p></div>`;
  }
}

function renderTicketList(tickets) {
  const list = document.getElementById('ticket-list');
  if (!tickets || tickets.length === 0) {
    list.innerHTML = '<div class="empty-state"><p>No tickets found</p></div>';
    return;
  }
  list.innerHTML = tickets.map(t => `
    <div class="ticket-item" id="ti-${t.ticket_id}" onclick="selectTicket('${t.ticket_id}')">
      <div class="ticket-item-number">${esc(t.ticket_number)}</div>
      <div class="ticket-item-title">${esc(t.title)}</div>
      <div class="ticket-item-meta">
        ${priorityBadge(t.priority)}
        ${statusBadge(t.status)}
        <span class="text-muted text-sm">${relativeTime(t.created_at)}</span>
      </div>
    </div>
  `).join('');
}

async function selectTicket(ticketId) {
  // Highlight selected
  document.querySelectorAll('.ticket-item').forEach(el => el.classList.remove('selected'));
  const el = document.getElementById(`ti-${ticketId}`);
  if (el) el.classList.add('selected');

  currentTicketId = ticketId;

  try {
    const ticket = await apiFetch(`/tickets/${ticketId}`);
    renderTicketDetail(ticket);
  } catch (e) {
    document.getElementById('ticket-detail').innerHTML =
      `<div class="empty-state"><p>Failed to load ticket: ${e.message}</p></div>`;
  }
}

function renderTicketDetail(ticket) {
  const detail = document.getElementById('ticket-detail');

  const customerInfo = ticket.customer
    ? `${esc(ticket.customer.name)} &mdash; ${esc(ticket.customer.email)}`
    : ticket.customer_id || 'Unknown';

  detail.innerHTML = `
    <div class="ticket-detail-header">
      <div class="ticket-detail-number">${esc(ticket.ticket_number)}</div>
      <div class="ticket-detail-title">${esc(ticket.title)}</div>
      <div class="ticket-meta-grid">
        <div class="ticket-meta-item">
          <label>Priority</label>
          <span>${priorityBadge(ticket.priority)}</span>
        </div>
        <div class="ticket-meta-item">
          <label>Status</label>
          <span>${statusBadge(ticket.status)}</span>
        </div>
        <div class="ticket-meta-item">
          <label>Category</label>
          <span>${esc(ticket.category.replace(/_/g,' '))}</span>
        </div>
        <div class="ticket-meta-item">
          <label>Customer</label>
          <span>${customerInfo}</span>
        </div>
        <div class="ticket-meta-item">
          <label>Created</label>
          <span>${formatDate(ticket.created_at)}</span>
        </div>
        <div class="ticket-meta-item">
          <label>Updated</label>
          <span>${relativeTime(ticket.updated_at)}</span>
        </div>
      </div>
    </div>

    <div class="section-label">Description</div>
    <div class="ticket-description">${esc(ticket.description)}</div>

    ${ticket.notes ? `
      <div class="section-label">Notes</div>
      <div class="ticket-notes">${esc(ticket.notes)}</div>
    ` : ''}

    <div class="divider"></div>

    <div class="ticket-actions">
      <button class="btn btn-primary" id="btn-investigate-${ticket.ticket_id}"
        onclick="startInvestigation('${ticket.ticket_id}')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        Investigate
      </button>
      <button class="btn btn-secondary" onclick="loadAuditForTicket('${ticket.ticket_id}')">
        View Audit Trail
      </button>
    </div>
  `;
}

async function openTicketDetail(ticketId) {
  switchView('tickets');
  setTimeout(() => selectTicket(ticketId), 100);
}

// ── Investigation ─────────────────────────────────────────────────

async function startInvestigation(ticketId) {
  const btn = document.getElementById(`btn-investigate-${ticketId}`);
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Starting...';
  }

  try {
    const result = await apiFetch(`/agent/investigate/${ticketId}`, {
      method: 'POST',
      body: JSON.stringify({ initiated_by: 'ops-dashboard' }),
    });

    currentRunId = result.run_id;
    currentTicketId = ticketId;

    showToast('Investigation started', 'success');
    switchView('investigation');
    startPollingInvestigation(result.run_id, result.trace_id);

  } catch (e) {
    showToast(`Investigation failed: ${e.message}`, 'error');
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg> Investigate';
    }
  }
}

function startPollingInvestigation(runId, traceId) {
  // Set up progress panel
  const progress = document.getElementById('investigation-progress');
  progress.innerHTML = `
    <div class="progress-header">
      <div class="progress-title">Investigation in Progress</div>
      <div class="progress-trace" id="trace-id-label">Trace: ${esc(traceId || runId)}</div>
    </div>
    <div class="progress-steps" id="progress-steps-list">
      ${renderProgressSteps([], null)}
    </div>
  `;

  document.getElementById('investigation-detail').innerHTML = `
    <div class="empty-state">
      <div class="spinner" style="width:32px;height:32px;border-color:rgba(37,99,235,0.2);border-top-color:#2563eb"></div>
      <p style="margin-top:16px;color:#4a5568">Agent is investigating...</p>
    </div>
  `;

  // Clear any existing poll
  if (pollInterval) clearInterval(pollInterval);

  // Poll every 2 seconds
  pollInterval = setInterval(async () => {
    try {
      const state = await apiFetch(`/agent/state/${runId}`);
      updateInvestigationProgress(state);

      // Stop polling when done
      if (['completed', 'rejected', 'failed'].includes(state.status)) {
        clearInterval(pollInterval);
        pollInterval = null;
      }
    } catch (e) {
      console.warn('Poll failed:', e.message);
    }
  }, 2000);
}

function renderProgressSteps(steps, currentNode) {
  const defaultSteps = [
    { node: 'parse_ticket',              label: 'Ticket Parsed',             status: 'pending' },
    { node: 'create_investigation_plan', label: 'Investigation Plan Created', status: 'pending' },
    { node: 'investigate_customer',      label: 'Customer Lookup',            status: 'pending' },
    { node: 'investigate_transactions',  label: 'Transaction Analysis',       status: 'pending' },
    { node: 'investigate_incidents',     label: 'Incident Search',            status: 'pending' },
    { node: 'investigate_system_events', label: 'System Events Check',        status: 'pending' },
    { node: 'retrieve_runbook',          label: 'Runbook Retrieved',          status: 'pending' },
    { node: 'analyze_findings',          label: 'Findings Analyzed',          status: 'pending' },
    { node: 'generate_recommendation',   label: 'Action Recommended',         status: 'pending' },
    { node: 'validate_action',           label: 'Risk Validated',             status: 'pending' },
    { node: 'human_approval',            label: 'Awaiting Approval',          status: 'pending' },
    { node: 'execute_action',            label: 'Action Executed',            status: 'pending' },
    { node: 'update_ticket',             label: 'Ticket Updated',             status: 'pending' },
    { node: 'audit_result',              label: 'Audit Complete',             status: 'pending' },
  ];

  const displaySteps = steps.length > 0 ? steps : defaultSteps;

  return displaySteps.map(step => {
    const iconMap = {
      pending:   '<span>○</span>',
      running:   '<span>●</span>',
      completed: '<span>✓</span>',
      paused:    '<span>⏸</span>',
      error:     '<span>✗</span>',
    };
    const icon = iconMap[step.status] || '<span>○</span>';
    return `
      <div class="progress-step">
        <div class="step-icon step-icon--${step.status}">${icon}</div>
        <div class="step-label step-label--${step.status}">${esc(step.label)}</div>
      </div>
    `;
  }).join('');
}

function updateInvestigationProgress(state) {
  const stepsList = document.getElementById('progress-steps-list');
  if (stepsList && state.steps) {
    stepsList.innerHTML = renderProgressSteps(state.steps, state.current_node);
  }

  const detail = document.getElementById('investigation-detail');

  if (state.status === 'paused' && state.pending_action) {
    // Show approval panel
    renderApprovalPanel(state.pending_action, state);
    // Update trace view too
    updateTraceView(state);

  } else if (state.status === 'completed') {
    detail.innerHTML = `
      <div style="text-align:center;padding:40px">
        <div style="width:56px;height:56px;background:#ecfdf5;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 16px">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
        </div>
        <div style="font-size:18px;font-weight:700;color:#1a202c;margin-bottom:8px">Investigation Complete</div>
        <div style="color:#718096;font-size:14px">Action executed and ticket updated successfully.</div>
        <div style="margin-top:20px">
          <button class="btn btn-secondary" onclick="loadAuditForTicket('${state.ticket_id}')">
            View Audit Trail
          </button>
        </div>
      </div>
    `;
    showToast('Investigation completed successfully', 'success');
    loadDashboard();

  } else if (state.status === 'rejected') {
    detail.innerHTML = `
      <div style="text-align:center;padding:40px">
        <div style="width:56px;height:56px;background:#fef2f2;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 16px">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </div>
        <div style="font-size:18px;font-weight:700;color:#1a202c;margin-bottom:8px">Action Rejected</div>
        <div style="color:#718096;font-size:14px">The recommended action was rejected. Ticket returned to open.</div>
      </div>
    `;

  } else if (state.status === 'failed') {
    detail.innerHTML = `
      <div style="text-align:center;padding:40px">
        <div style="color:#dc2626;font-size:16px;font-weight:600">Investigation Failed</div>
        <div style="color:#718096;font-size:13px;margin-top:8px">${esc(state.error || 'Unknown error')}</div>
      </div>
    `;
  }
}

function renderApprovalPanel(action, state) {
  const detail = document.getElementById('investigation-detail');

  const riskClass = `risk-${action.risk_level || 'medium'}`;
  const riskLabel = (action.risk_level || 'medium').toUpperCase();

  // Parse findings from snapshot if available
  const snapshot = state.recommendation || {};
  const actionType = action.action_type.replace(/_/g, ' ');

  detail.innerHTML = `
    <div class="recommendation-panel">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:20px">
        <div style="width:8px;height:8px;border-radius:50%;background:#d97706;box-shadow:0 0 0 3px #fef3c7"></div>
        <span style="font-size:13px;font-weight:600;color:#d97706">APPROVAL REQUIRED</span>
      </div>

      <div class="recommendation-title">Recommended Action</div>

      <div class="recommendation-action">
        <div class="recommendation-action-type">${esc(actionType)}</div>
        <div class="recommendation-action-desc">${esc(action.description)}</div>
      </div>

      <div class="section-label" style="margin-top:20px">Why?</div>
      <ul class="evidence-list">
        ${action.reason
          ? action.reason.split('\n').filter(l => l.trim()).map(line =>
              `<li class="evidence-item"><div class="evidence-bullet"></div><span>${esc(line)}</span></li>`
            ).join('')
          : '<li class="evidence-item"><div class="evidence-bullet"></div><span>See investigation findings above</span></li>'
        }
      </ul>

      <div style="margin-top:16px;display:flex;align-items:center;gap:12px">
        <span class="section-label" style="margin:0">Risk Level</span>
        <span class="risk-indicator ${riskClass}">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
          ${riskLabel}
        </span>
      </div>

      <div style="background:#fffbeb;border:1px solid #fcd34d;border-radius:8px;padding:12px 16px;margin-top:16px;font-size:13px;color:#92400e">
        This action requires your approval before it will be executed.
        Carefully review the evidence before approving.
      </div>

      <div class="approval-buttons">
        <button class="btn btn-lg btn-danger" onclick="submitDecision('${action.action_id}', 'reject')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          Reject
        </button>
        <button class="btn btn-lg btn-success" onclick="submitDecision('${action.action_id}', 'approve')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
          Approve
        </button>
      </div>
    </div>
  `;
}

async function submitDecision(actionId, decision) {
  const endpoint = decision === 'approve'
    ? `/approvals/${actionId}/approve`
    : `/approvals/${actionId}/reject`;

  try {
    await apiFetch(endpoint, {
      method: 'POST',
      body: JSON.stringify({ approved_by: 'ops-engineer' }),
    });

    const msg = decision === 'approve'
      ? 'Action approved — executing...'
      : 'Action rejected';
    showToast(msg, decision === 'approve' ? 'success' : 'warning');

    // Continue polling to show execution progress
    if (currentRunId) {
      startPollingInvestigation(currentRunId, '');
    }

    // Refresh approvals badge
    refreshApprovalBadge();

  } catch (e) {
    showToast(`Failed: ${e.message}`, 'error');
  }
}

// ── Approvals View ─────────────────────────────────────────────────

async function loadApprovals() {
  try {
    const approvals = await apiFetch('/approvals');
    const badge = document.getElementById('approval-count-badge');
    if (badge) badge.textContent = approvals.length;

    renderApprovalsList(approvals);
  } catch (e) {
    document.getElementById('approvals-list').innerHTML =
      `<div class="empty-state"><p>Failed to load: ${e.message}</p></div>`;
  }
}

function renderApprovalsList(approvals) {
  const container = document.getElementById('approvals-list');

  if (!approvals || approvals.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        <p>No pending approvals — all clear!</p>
      </div>
    `;
    return;
  }

  container.innerHTML = approvals.map(a => `
    <div class="approval-card" id="approval-${a.action_id}">
      <div class="approval-card-header">
        <div>
          <div class="approval-action-label">${esc(a.action_type.replace(/_/g,' '))}</div>
          <div class="approval-description">${esc(a.description)}</div>
        </div>
        <span class="risk-indicator risk-${a.risk_level}" style="margin:0">
          ${a.risk_level.toUpperCase()}
        </span>
      </div>
      ${a.reason ? `<div class="approval-reason">${esc(a.reason.slice(0,200))}</div>` : ''}
      <div class="approval-meta">
        <span>Ticket: <span class="text-mono">${esc(a.ticket_id.slice(0,12))}...</span></span>
        <span>•</span>
        <span>${relativeTime(a.created_at)}</span>
      </div>
      <div class="approval-actions">
        <button class="btn btn-danger btn-sm" onclick="quickDecision('${a.action_id}','reject')">
          Reject
        </button>
        <button class="btn btn-success btn-sm" onclick="quickDecision('${a.action_id}','approve')">
          Approve
        </button>
      </div>
    </div>
  `).join('');
}

async function quickDecision(actionId, decision) {
  const card = document.getElementById(`approval-${actionId}`);
  if (card) card.style.opacity = '0.5';

  await submitDecision(actionId, decision);
  setTimeout(loadApprovals, 500);
}

async function refreshApprovalBadge() {
  try {
    const approvals = await apiFetch('/approvals');
    const count = approvals.length;
    ['badge-approvals', 'approval-count-badge'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.textContent = count;
    });
  } catch {}
}

// ── Trace View ─────────────────────────────────────────────────────

function updateTraceView(state) {
  const traceLabel = document.getElementById('trace-id-display');
  if (traceLabel) traceLabel.textContent = `Trace: ${state.trace_id || state.run_id || '—'}`;

  const timeline = document.getElementById('trace-timeline');
  if (!state.steps || state.steps.length === 0) return;

  timeline.innerHTML = `<div class="trace-timeline">
    ${state.steps.map((step, i) => {
      const dotClass = {
        completed: 'trace-dot--completed',
        running:   'trace-dot--running',
        paused:    'trace-dot--paused',
        error:     'trace-dot--error',
        pending:   'trace-dot--pending',
      }[step.status] || 'trace-dot--pending';

      const statusText = {
        completed: '✓ Completed',
        running:   '● Running',
        paused:    '⏸ Paused',
        error:     '✗ Error',
        pending:   '○ Pending',
      }[step.status] || '○ Pending';

      return `
        <div class="trace-step" id="trace-step-${step.node}" onclick="this.classList.toggle('expanded')">
          <div class="trace-step-line">
            <div class="trace-dot ${dotClass}"></div>
            ${i < state.steps.length - 1 ? '<div class="trace-connector"></div>' : ''}
          </div>
          <div style="flex:1;margin-bottom:8px">
            <div class="trace-content">
              <div class="trace-step-name">${esc(step.label)}</div>
              <div class="trace-step-meta">${statusText}${step.duration_ms ? ` • ${step.duration_ms}ms` : ''}</div>
              ${step.result_summary ? `
                <div class="trace-step-detail">${esc(step.result_summary)}</div>
              ` : ''}
            </div>
          </div>
        </div>
      `;
    }).join('')}
  </div>`;
}

// ── Audit Log ─────────────────────────────────────────────────────

async function loadAuditLog() {
  try {
    const logs = await apiFetch('/audit?limit=100');
    renderAuditLog(logs);
  } catch (e) {
    document.getElementById('audit-log-body').innerHTML =
      `<tr><td colspan="5" class="loading-cell">Failed: ${e.message}</td></tr>`;
  }
}

async function loadAuditForTicket(ticketId) {
  switchView('audit');
  try {
    const logs = await apiFetch(`/audit/${ticketId}`);
    renderAuditLog(logs);
  } catch (e) {
    document.getElementById('audit-log-body').innerHTML =
      `<tr><td colspan="5" class="loading-cell">Failed: ${e.message}</td></tr>`;
  }
}

function renderAuditLog(logs) {
  const tbody = document.getElementById('audit-log-body');
  if (!logs || logs.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" class="loading-cell">No audit events found</td></tr>';
    return;
  }
  tbody.innerHTML = logs.map(l => `
    <tr>
      <td class="text-mono text-muted text-sm">${formatDate(l.timestamp)}</td>
      <td><span class="event-tag">${esc(l.event_type)}</span></td>
      <td>${esc(l.actor)}</td>
      <td class="text-mono text-sm">${l.ticket_id ? l.ticket_id.slice(0,8)+'...' : '—'}</td>
      <td>
        ${l.details && Object.keys(l.details).length > 0
          ? `<button class="btn btn-sm btn-secondary" onclick='showDetails(${JSON.stringify(JSON.stringify(l.details))})'>Details</button>`
          : '—'
        }
      </td>
    </tr>
  `).join('');
}

function showDetails(detailsJson) {
  try {
    const details = JSON.parse(detailsJson);
    openModal('Event Details', `<pre style="font-family:var(--font-mono);font-size:12px;white-space:pre-wrap">${JSON.stringify(details, null, 2)}</pre>`);
  } catch {
    openModal('Event Details', detailsJson);
  }
}

// ── Modal ─────────────────────────────────────────────────────────

function openModal(title, body) {
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-body').innerHTML = body;
  document.getElementById('modal-overlay').classList.add('open');
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('open');
}

// ── Toast ─────────────────────────────────────────────────────────

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast toast--${type}`;
  toast.innerHTML = `
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      ${type === 'success' ? '<polyline points="20 6 9 17 4 12"/>'
       : type === 'error'   ? '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>'
       : type === 'warning' ? '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>'
       : '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/>'}
    </svg>
    <span>${esc(message)}</span>
  `;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

// ── Helpers ─────────────────────────────────────────────────────────

function esc(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function priorityBadge(priority) {
  const classes = {
    critical: 'priority-critical',
    high:     'priority-high',
    medium:   'priority-medium',
    low:      'priority-low',
  };
  return `<span class="priority-badge ${classes[priority] || ''}">${esc(priority)}</span>`;
}

function statusBadge(status) {
  return `<span class="status-badge status-${esc(status)}">${esc(status.replace(/_/g,' '))}</span>`;
}

function formatDate(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  return d.toLocaleString('en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
  });
}

function relativeTime(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  const now = new Date();
  const diff = Math.floor((now - d) / 1000);

  if (diff < 60)   return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff/60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff/3600)}h ago`;
  return `${Math.floor(diff/86400)}d ago`;
}


