let token = localStorage.getItem('token');
let timerInterval = null;
let activeStartTime = null;

const authSection = document.getElementById('auth-section');
const appSection = document.getElementById('app-section');
const authError = document.getElementById('auth-error');
const timerDisplay = document.getElementById('timer-display');
const statusBadge = document.getElementById('status-badge');
const historyList = document.getElementById('history-list');

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

function updateTimerTick() {
  if (!activeStartTime) {
    timerDisplay.textContent = '00:00:00';
    return;
  }
  const diff = Date.now() - activeStartTime.getTime();
  timerDisplay.textContent = formatDuration(diff);
}

function setUIState(session) {
  clearInterval(timerInterval);
  if (!session) {
    activeStartTime = null;
    statusBadge.textContent = 'Не активно';
    statusBadge.className = 'badge idle';
    timerDisplay.textContent = '00:00:00';
    return;
  }
  activeStartTime = new Date(session.start_time);
  statusBadge.textContent = session.session_type === 'WORK' ? 'Работа' : 'Перерыв';
  statusBadge.className = `badge ${session.session_type}`;
  updateTimerTick();
  timerInterval = setInterval(updateTimerTick, 1000);
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

function parseJwt(token) {
  const base64Url = token.split('.')[1];
  const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
  return JSON.parse(atob(base64));
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
  await loadHistory();
});

document.getElementById('break-btn').addEventListener('click', async () => {
  const session = await apiRequest('/timer/break', 'POST');
  setUIState(session);
  await loadHistory();
});

document.getElementById('stop-btn').addEventListener('click', async () => {
  await apiRequest('/timer/stop', 'POST');
  setUIState(null);
  await loadHistory();
});

initApp();