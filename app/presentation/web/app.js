let token = localStorage.getItem('token');
let timerInterval = null;
let activeStartTime = null;
let activeType = null;
let baseWorkSeconds = 0;
let baseBreakSeconds = 0;

const authSection = document.getElementById('auth-section');
const appSection = document.getElementById('app-section');
const authError = document.getElementById('auth-error');
const timerDisplay = document.getElementById('timer-display');
const statusBadge = document.getElementById('status-badge');
const historyList = document.getElementById('history-list');
const todayWorkDisplay = document.getElementById('today-work');
const todayBreakDisplay = document.getElementById('today-break');
const todayTotalDisplay = document.getElementById('today-total');

async function apiRequest(url, method = 'GET', body = null) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const options = { method, headers };
  if (body) {
    options.body = JSON.stringify(body);
  }
  const res = await fetch(url, options);
  if (res.status === 401) {
    logout();
    return null;
  }
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || 'Ошибка запроса');
  }
  return data;
}

function formatDuration(ms) {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const hours = String(Math.floor(totalSeconds / 3600)).padStart(2, '0');
  const minutes = String(Math.floor((totalSeconds % 3600) / 60)).padStart(2, '0');
  const seconds = String(totalSeconds % 60).padStart(2, '0');
  return `${hours}:${minutes}:${seconds}`;
}

function parseJwt(token) {
  const parts = token.split('.');
  const base64Url = parts.at(1);
  const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
  return JSON.parse(atob(base64));
}

function renderSummary(elapsedSeconds = 0) {
  const currentWork = baseWorkSeconds + (activeType === 'WORK' ? elapsedSeconds : 0);
  const currentBreak = baseBreakSeconds + (activeType === 'BREAK' ? elapsedSeconds : 0);
  const currentTotal = currentWork + currentBreak;
  todayWorkDisplay.textContent = formatDuration(currentWork * 1000);
  todayBreakDisplay.textContent = formatDuration(currentBreak * 1000);
  todayTotalDisplay.textContent = formatDuration(currentTotal * 1000);
}

function updateTimerTick() {
  if (!activeStartTime) {
    timerDisplay.textContent = '00:00:00';
    renderSummary(0);
    return;
  }
  const diff = Date.now() - activeStartTime.getTime();
  timerDisplay.textContent = formatDuration(diff);
  renderSummary(Math.max(0, Math.floor(diff / 1000)));
}

function setUIState(session) {
  clearInterval(timerInterval);
  if (!session) {
    activeStartTime = null;
    activeType = null;
    statusBadge.textContent = 'Не активно';
    statusBadge.className = 'badge idle';
    timerDisplay.textContent = '00:00:00';
    renderSummary(0);
    return;
  }
  activeStartTime = new Date(session.start_time);
  activeType = session.session_type;
  statusBadge.textContent = session.session_type === 'WORK' ? 'Работа' : 'Перерыв';
  statusBadge.className = `badge ${session.session_type}`;
  updateTimerTick();
  timerInterval = setInterval(updateTimerTick, 1000);
}

async function loadSummary() {
  const summary = await apiRequest('/timer/summary');
  if (!summary) return;
  const currentElapsed = activeStartTime ? Math.max(0, Math.floor((Date.now() - activeStartTime.getTime()) / 1000)) : 0;
  baseWorkSeconds = Math.max(0, summary.work_seconds - (activeType === 'WORK' ? currentElapsed : 0));
  baseBreakSeconds = Math.max(0, summary.break_seconds - (activeType === 'BREAK' ? currentElapsed : 0));
  renderSummary(currentElapsed);
}

async function handleAuth(endpoint) {
  authError.textContent = '';
  const username = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value.trim();
  if (!username || !password) {
    authError.textContent = 'Введите логин и пароль';
    return;
  }
  try {
    const data = await apiRequest(`/auth/${endpoint}`, 'POST', { username, password });
    if (data && data.access_token) {
      token = data.access_token;
      localStorage.setItem('token', token);
      initApp();
    }
  } catch (err) {
    authError.textContent = err.message;
  }
}

function logout() {
  token = null;
  localStorage.removeItem('token');
  clearInterval(timerInterval);
  authSection.classList.remove('hidden');
  appSection.classList.add('hidden');
}

async function loadHistory() {
  const sessions = await apiRequest('/timer/history');
  if (!sessions) return;
  historyList.innerHTML = '';
  sessions.forEach(s => {
    const li = document.createElement('li');
    li.className = 'history-item';
    const start = new Date(s.start_time);
    const end = s.end_time ? new Date(s.end_time) : new Date();
    const duration = formatDuration(end - start);
    const typeLabel = s.session_type === 'WORK' ? '🟢 Работа' : '🟡 Перерыв';
    const timeStr = start.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    li.innerHTML = `<span>${typeLabel} (${timeStr})</span><strong>${s.end_time ? duration : 'Идет...'}</strong>`;
    historyList.appendChild(li);
  });
}

async function initApp() {
  if (!token) {
    authSection.classList.remove('hidden');
    appSection.classList.add('hidden');
    return;
  }
  authSection.classList.add('hidden');
  appSection.classList.remove('hidden');
  try {
    const payload = parseJwt(token);
    document.getElementById('user-display').textContent = `👤 ${payload.username}`;
    const statusData = await apiRequest('/timer/status');
    setUIState(statusData ? statusData.active_session : null);
    await loadSummary();
    await loadHistory();
  } catch (err) {
    logout();
  }
}

document.getElementById('login-btn').addEventListener('click', () => handleAuth('login'));
document.getElementById('register-btn').addEventListener('click', () => handleAuth('register'));
document.getElementById('logout-btn').addEventListener('click', logout);

document.getElementById('work-btn').addEventListener('click', async () => {
  const session = await apiRequest('/timer/work', 'POST');
  setUIState(session);
  await loadSummary();
  await loadHistory();
});

document.getElementById('break-btn').addEventListener('click', async () => {
  const session = await apiRequest('/timer/break', 'POST');
  setUIState(session);
  await loadSummary();
  await loadHistory();
});

document.getElementById('stop-btn').addEventListener('click', async () => {
  await apiRequest('/timer/stop', 'POST');
  setUIState(null);
  await loadSummary();
  await loadHistory();
});

initApp();