let token = localStorage.getItem('token');
let timerInterval = null;
let activeStartTime = null;
let activeType = null;
let baseWorkSeconds = 0;
let baseBreakSeconds = 0;
let editingSessionId = null;
let editingNormDateStr = null;
let cachedSessions = [];

let userSettings = {
  default_work_minutes: 480,
  default_break_minutes: 40,
  weekend_days: [5, 6]
};
let dailyNormsMap = new Map();

const authSection = document.getElementById('auth-section');
const appSection = document.getElementById('app-section');
const authError = document.getElementById('auth-error');
const timerDisplay = document.getElementById('timer-display');
const statusBadge = document.getElementById('status-badge');
const workBtn = document.getElementById('work-btn');
const breakBtn = document.getElementById('break-btn');
const stopBtn = document.getElementById('stop-btn');
const historyContainer = document.getElementById('history-container');
const todayWorkDisplay = document.getElementById('today-work');
const todayBreakDisplay = document.getElementById('today-break');
const todayTotalDisplay = document.getElementById('today-total');

const tabTimerBtn = document.getElementById('tab-timer-btn');
const tabStatsBtn = document.getElementById('tab-stats-btn');
const viewTimer = document.getElementById('view-timer');
const viewStats = document.getElementById('view-stats');
const weeklyChart = document.getElementById('weekly-chart');

const editModal = document.getElementById('edit-modal');
const modalTitle = document.getElementById('modal-title');
const editTypeInput = document.getElementById('edit-type');
const editStartInput = document.getElementById('edit-start');
const editEndInput = document.getElementById('edit-end');
const editError = document.getElementById('edit-error');

const settingsModal = document.getElementById('settings-modal');
const setWorkTimeInput = document.getElementById('set-work-time');
const setBreakTimeInput = document.getElementById('set-break-time');
const settingsError = document.getElementById('settings-error');

const dayNormModal = document.getElementById('day-norm-modal');
const dayNormTitle = document.getElementById('day-norm-title');
const dayWorkTimeInput = document.getElementById('day-work-time');
const dayBreakTimeInput = document.getElementById('day-break-time');
const dayNormError = document.getElementById('day-norm-error');

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
  if (res.status === 204) {
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

function formatSignedDuration(ms) {
  const sign = ms >= 0 ? '+' : '-';
  return `${sign}${formatDuration(Math.abs(ms))}`;
}

function formatShortHours(ms) {
  const hours = ms / 3600000;
  if (hours === 0) return '0ч';
  if (hours < 1) return `${Math.round(ms / 60000)}м`;
  return `${hours.toFixed(1)}ч`;
}

function minutesToTimeInput(mins) {
  const h = String(Math.floor(mins / 60)).padStart(2, '0');
  const m = String(mins % 60).padStart(2, '0');
  return `${h}:${m}`;
}

function timeInputToMinutes(val) {
  const parts = val.split(':');
  return parseInt(parts.at(0), 10) * 60 + parseInt(parts.at(1), 10);
}

function getDateKey(dateObj) {
  const y = dateObj.getFullYear();
  const m = String(dateObj.getMonth() + 1).padStart(2, '0');
  const d = String(dateObj.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function getJsWeekdayAsPython(dateObj) {
  return (dateObj.getDay() + 6) % 7;
}

function getNormForDate(dateObj) {
  const key = getDateKey(dateObj);
  if (dailyNormsMap.has(key)) {
    return dailyNormsMap.get(key);
  }
  const pyDay = getJsWeekdayAsPython(dateObj);
  if (userSettings.weekend_days.includes(pyDay)) {
    return { work_minutes: 0, break_minutes: 0 };
  }
  return {
    work_minutes: userSettings.default_work_minutes,
    break_minutes: userSettings.default_break_minutes
  };
}

function toLocalInputString(isoString) {
  if (!isoString) return '';
  const date = new Date(isoString);
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 19);
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

  const todayNorm = getNormForDate(new Date());
  const workLimitSec = todayNorm.work_minutes * 60;
  const breakLimitSec = todayNorm.break_minutes * 60;

  const isWorkOver = workLimitSec > 0 && currentWork > workLimitSec;
  const isBreakOver = breakLimitSec > 0 && currentBreak > breakLimitSec;

  todayWorkDisplay.classList.toggle('overtime-text', isWorkOver);
  todayBreakDisplay.classList.toggle('overtime-text', isBreakOver);

  if (activeType === 'WORK' && isWorkOver) {
    timerDisplay.classList.add('overtime');
  } else if (activeType === 'BREAK' && isBreakOver) {
    timerDisplay.classList.add('overtime');
  } else {
    timerDisplay.classList.remove('overtime');
  }
}

function updateTimerTick() {
  if (!activeStartTime) {
    timerDisplay.textContent = '00:00:00';
    timerDisplay.classList.remove('overtime');
    renderSummary(0);
    return;
  }
  const diff = Date.now() - activeStartTime.getTime();
  timerDisplay.textContent = formatDuration(diff);
  renderSummary(Math.max(0, Math.floor(diff / 1000)));
}

function setUIState(session) {
  clearInterval(timerInterval);
  workBtn.disabled = false;
  breakBtn.disabled = false;
  stopBtn.disabled = false;
  workBtn.classList.remove('btn-expanded');
  breakBtn.classList.remove('btn-expanded');

  if (!session) {
    activeStartTime = null;
    activeType = null;
    stopBtn.disabled = true;
    statusBadge.textContent = 'Не активно';
    statusBadge.className = 'badge idle';
    timerDisplay.textContent = '00:00:00';
    timerDisplay.classList.remove('overtime');
    renderSummary(0);
    return;
  }

  activeStartTime = new Date(session.start_time);
  activeType = session.session_type;
  statusBadge.textContent = session.session_type === 'WORK' ? 'Работа' : 'Перерыв';
  statusBadge.className = `badge ${session.session_type}`;

  if (session.session_type === 'WORK') {
    workBtn.disabled = true;
    breakBtn.classList.add('btn-expanded');
  } else if (session.session_type === 'BREAK') {
    breakBtn.disabled = true;
    workBtn.classList.add('btn-expanded');
  }

  updateTimerTick();
  timerInterval = setInterval(updateTimerTick, 1000);
}

async function loadSettingsData() {
  const [settings, norms] = await Promise.all([
    apiRequest('/settings'),
    apiRequest('/settings/daily-norms')
  ]);
  if (settings) {
    userSettings = settings;
  }
  dailyNormsMap.clear();
  if (norms) {
    norms.forEach(n => {
      dailyNormsMap.set(n.date_str, {
        work_minutes: n.work_minutes,
        break_minutes: n.break_minutes
      });
    });
  }
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

function openSettingsModal() {
  settingsError.textContent = '';
  setWorkTimeInput.value = minutesToTimeInput(userSettings.default_work_minutes);
  setBreakTimeInput.value = minutesToTimeInput(userSettings.default_break_minutes);
  const checkboxes = document.querySelectorAll('#set-weekends input[type="checkbox"]');
  checkboxes.forEach(cb => {
    cb.checked = userSettings.weekend_days.includes(parseInt(cb.value, 10));
  });
  settingsModal.classList.remove('hidden');
}

function openDayNormModal(dateObj) {
  editingNormDateStr = getDateKey(dateObj);
  dayNormError.textContent = '';
  dayNormTitle.textContent = `Норма на ${formatDayHeader(dateObj)}`;
  const norm = getNormForDate(dateObj);
  dayWorkTimeInput.value = minutesToTimeInput(norm.work_minutes);
  dayBreakTimeInput.value = minutesToTimeInput(norm.break_minutes);
  dayNormModal.classList.remove('hidden');
}

function openAddModal() {
  editingSessionId = null;
  modalTitle.textContent = 'Добавить запись';
  editError.textContent = '';
  editTypeInput.value = 'WORK';
  const now = new Date();
  const hourAgo = new Date(now.getTime() - 3600000);
  editStartInput.value = toLocalInputString(hourAgo.toISOString());
  editEndInput.value = toLocalInputString(now.toISOString());
  editEndInput.disabled = false;
  editModal.classList.remove('hidden');
}

function openEditModal(session) {
  editingSessionId = session.id;
  modalTitle.textContent = 'Редактировать запись';
  editError.textContent = '';
  editTypeInput.value = session.session_type;
  editStartInput.value = toLocalInputString(session.start_time);
  editEndInput.value = session.end_time ? toLocalInputString(session.end_time) : '';
  editEndInput.disabled = !session.end_time;
  editModal.classList.remove('hidden');
}

async function deleteSession(sessionId) {
  if (!confirm('Удалить эту запись?')) return;
  await apiRequest(`/timer/sessions/${sessionId}`, 'DELETE');
  await refreshAll();
}

function formatDayHeader(dateObj) {
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);
  if (dateObj.toDateString() === today.toDateString()) return 'Сегодня';
  if (dateObj.toDateString() === yesterday.toDateString()) return 'Вчера';
  return dateObj.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
}

function renderStats(sessions) {
  const now = new Date();
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const daysMap = new Map();
  const dayNames = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'];

  for (let i = 6; i >= 0; i--) {
    const d = new Date(todayStart);
    d.setDate(todayStart.getDate() - i);
    daysMap.set(getDateKey(d), {
      date: d,
      label: dayNames.at(d.getDay()),
      workMs: 0,
      breakMs: 0
    });
  }

  const dailyTotalsMap = new Map();
  let weekWorkMs = 0;
  let weekBreakMs = 0;
  let monthWorkMs = 0;
  let monthBreakMs = 0;
  const activeDaysSet = new Set();

  const weekLimit = new Date(todayStart);
  weekLimit.setDate(todayStart.getDate() - 6);

  const monthLimit = new Date(todayStart);
  monthLimit.setDate(todayStart.getDate() - 29);

  sessions.forEach(s => {
    const start = new Date(s.start_time);
    const end = s.end_time ? new Date(s.end_time) : now;
    const diff = Math.max(0, end - start);
    const key = getDateKey(start);

    if (!dailyTotalsMap.has(key)) {
      dailyTotalsMap.set(key, { date: new Date(start.getFullYear(), start.getMonth(), start.getDate()), totalMs: 0 });
    }
    dailyTotalsMap.get(key).totalMs += diff;

    if (daysMap.has(key)) {
      const dayItem = daysMap.get(key);
      if (s.session_type === 'WORK') {
        dayItem.workMs += diff;
      } else {
        dayItem.breakMs += diff;
      }
    }

    if (start >= weekLimit) {
      if (s.session_type === 'WORK') {
        weekWorkMs += diff;
      } else {
        weekBreakMs += diff;
      }
    }

    if (start >= monthLimit) {
      activeDaysSet.add(key);
      if (s.session_type === 'WORK') {
        monthWorkMs += diff;
      } else {
        monthBreakMs += diff;
      }
    }
  });

  let weekBalanceMs = 0;
  daysMap.forEach((item, key) => {
    const norm = getNormForDate(item.date);
    const normMs = (norm.work_minutes + norm.break_minutes) * 60000;
    const actualMs = item.workMs + item.breakMs;
    if (actualMs > 0 || normMs > 0) {
      weekBalanceMs += (actualMs - normMs);
    }
  });

  let monthBalanceMs = 0;
  for (let i = 29; i >= 0; i--) {
    const d = new Date(todayStart);
    d.setDate(todayStart.getDate() - i);
    const key = getDateKey(d);
    const norm = getNormForDate(d);
    const normMs = (norm.work_minutes + norm.break_minutes) * 60000;
    const actualMs = dailyTotalsMap.has(key) ? dailyTotalsMap.get(key).totalMs : 0;
    if (actualMs > 0 || normMs > 0) {
      monthBalanceMs += (actualMs - normMs);
    }
  }

  document.getElementById('stat-week-work').textContent = formatDuration(weekWorkMs);
  document.getElementById('stat-week-break').textContent = formatDuration(weekBreakMs);

  const weekBalEl = document.getElementById('stat-week-balance');
  weekBalEl.textContent = formatSignedDuration(weekBalanceMs);
  weekBalEl.className = `summary-value ${weekBalanceMs >= 0 ? 'balance-pos' : 'balance-neg'}`;

  document.getElementById('stat-month-work').textContent = formatDuration(monthWorkMs);
  document.getElementById('stat-month-break').textContent = formatDuration(monthBreakMs);
  document.getElementById('stat-month-total').textContent = formatDuration(monthWorkMs + monthBreakMs);

  const monthBalEl = document.getElementById('stat-month-balance');
  monthBalEl.textContent = formatSignedDuration(monthBalanceMs);
  monthBalEl.className = monthBalanceMs >= 0 ? 'balance-pos' : 'balance-neg';

  document.getElementById('stat-month-days').textContent = String(activeDaysSet.size);

  let maxTotalMs = 3600000;
  daysMap.forEach(item => {
    const total = item.workMs + item.breakMs;
    if (total > maxTotalMs) {
      maxTotalMs = total;
    }
  });

  weeklyChart.innerHTML = '';
  daysMap.forEach(item => {
    const totalMs = item.workMs + item.breakMs;
    const workPct = Math.round((item.workMs / maxTotalMs) * 100);
    const breakPct = Math.round((item.breakMs / maxTotalMs) * 100);

    const col = document.createElement('div');
    col.className = 'chart-col';
    col.innerHTML = `
      <span class="chart-val">${formatShortHours(totalMs)}</span>
      <div class="bars-track">
        <div class="bar-work" style="height: ${workPct}%"></div>
        <div class="bar-break" style="height: ${breakPct}%"></div>
      </div>
      <span class="chart-day">${item.label}</span>
    `;
    weeklyChart.appendChild(col);
  });
}

async function loadHistory() {
  const sessions = await apiRequest('/timer/history');
  if (!sessions) return;
  cachedSessions = sessions;
  renderStats(cachedSessions);
  historyContainer.innerHTML = '';

  const groups = new Map();
  sessions.forEach(s => {
    const startDate = new Date(s.start_time);
    const key = getDateKey(startDate);
    if (!groups.has(key)) {
      groups.set(key, { date: startDate, items: [], workMs: 0, breakMs: 0 });
    }
    const group = groups.get(key);
    group.items.push(s);
    const endDate = s.end_time ? new Date(s.end_time) : new Date();
    const diff = Math.max(0, endDate - startDate);
    if (s.session_type === 'WORK') {
      group.workMs += diff;
    } else {
      group.breakMs += diff;
    }
  });

  groups.forEach(group => {
    const card = document.createElement('div');
    card.className = 'card day-card';

    const header = document.createElement('div');
    header.className = 'day-header';

    const titleRow = document.createElement('div');
    titleRow.className = 'day-title-row';
    const titleSpan = document.createElement('span');
    titleSpan.className = 'day-title';
    titleSpan.textContent = formatDayHeader(group.date);

    const normBtn = document.createElement('button');
    normBtn.className = 'day-norm-btn';
    normBtn.title = 'Норма на этот день';
    normBtn.innerHTML = '<img src="/static/icons/settings.svg" alt="">';
    normBtn.addEventListener('click', () => openDayNormModal(group.date));

    titleRow.appendChild(titleSpan);
    titleRow.appendChild(normBtn);

    const totalMs = group.workMs + group.breakMs;
    const norm = getNormForDate(group.date);
    const normMs = (norm.work_minutes + norm.break_minutes) * 60000;
    const balanceMs = totalMs - normMs;
    const balClass = balanceMs >= 0 ? 'balance-pos' : 'balance-neg';

    const statsDiv = document.createElement('div');
    statsDiv.className = 'day-stats';
    statsDiv.innerHTML = `
      <span class="work-text">Р: ${formatDuration(group.workMs)}</span>
      <span class="break-text">П: ${formatDuration(group.breakMs)}</span>
      <span class="total-text">Всего: ${formatDuration(totalMs)}</span>
      <span class="${balClass}">${formatSignedDuration(balanceMs)}</span>
    `;

    header.appendChild(titleRow);
    header.appendChild(statsDiv);
    card.appendChild(header);

    const list = document.createElement('ul');
    list.className = 'history-list';

    group.items.forEach(s => {
      const li = document.createElement('li');
      li.className = 'history-item';

      const start = new Date(s.start_time);
      const end = s.end_time ? new Date(s.end_time) : new Date();
      const duration = formatDuration(end - start);
      const typeIcon = s.session_type === 'WORK' ? '/static/icons/work.svg' : '/static/icons/break.svg';
      const typeText = s.session_type === 'WORK' ? 'Работа' : 'Перерыв';
      const startStr = start.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      const endStr = s.end_time ? end.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'сейчас';

      const info = document.createElement('div');
      info.className = 'item-info';
      info.innerHTML = `<span class="type-row"><img src="${typeIcon}" class="icon" alt="">${typeText}</span><span class="item-time">${startStr} — ${endStr}</span>`;

      const right = document.createElement('div');
      right.className = 'item-right';

      const durEl = document.createElement('strong');
      durEl.textContent = s.end_time ? duration : 'Идет...';
      right.appendChild(durEl);

      const editBtn = document.createElement('button');
      editBtn.className = 'icon-btn';
      editBtn.innerHTML = '<img src="/static/icons/edit.svg" class="icon" alt="">';
      editBtn.title = 'Редактировать';
      editBtn.addEventListener('click', () => openEditModal(s));
      right.appendChild(editBtn);

      const delBtn = document.createElement('button');
      delBtn.className = 'icon-btn del';
      delBtn.innerHTML = '<img src="/static/icons/trash.svg" class="icon" alt="">';
      delBtn.title = 'Удалить';
      delBtn.addEventListener('click', () => deleteSession(s.id));
      right.appendChild(delBtn);

      li.appendChild(info);
      li.appendChild(right);
      list.appendChild(li);
    });

    card.appendChild(list);
    historyContainer.appendChild(card);
  });
}

function switchTab(tab) {
  if (tab === 'stats') {
    tabTimerBtn.classList.remove('active');
    tabStatsBtn.classList.add('active');
    viewTimer.classList.add('hidden');
    viewStats.classList.remove('hidden');
    renderStats(cachedSessions);
  } else {
    tabStatsBtn.classList.remove('active');
    tabTimerBtn.classList.add('active');
    viewStats.classList.add('hidden');
    viewTimer.classList.remove('hidden');
  }
}

async function refreshAll() {
  await loadSettingsData();
  const statusData = await apiRequest('/timer/status');
  setUIState(statusData ? statusData.active_session : null);
  await loadSummary();
  await loadHistory();
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
    const userDisplay = document.getElementById('user-display');
    userDisplay.className = 'user-badge';
    userDisplay.innerHTML = `<img src="/static/icons/user.svg" class="icon" alt=""><span>${payload.username}</span>`;
    await refreshAll();
  } catch (err) {
    logout();
  }
}

tabTimerBtn.addEventListener('click', () => switchTab('timer'));
tabStatsBtn.addEventListener('click', () => switchTab('stats'));

document.getElementById('login-btn').addEventListener('click', () => handleAuth('login'));
document.getElementById('register-btn').addEventListener('click', () => handleAuth('register'));
document.getElementById('logout-btn').addEventListener('click', logout);
document.getElementById('add-record-btn').addEventListener('click', openAddModal);
document.getElementById('settings-btn').addEventListener('click', openSettingsModal);

workBtn.addEventListener('click', async () => {
  const session = await apiRequest('/timer/work', 'POST');
  setUIState(session);
  await loadSummary();
  await loadHistory();
});

breakBtn.addEventListener('click', async () => {
  const session = await apiRequest('/timer/break', 'POST');
  setUIState(session);
  await loadSummary();
  await loadHistory();
});

stopBtn.addEventListener('click', async () => {
  await apiRequest('/timer/stop', 'POST');
  setUIState(null);
  await loadSummary();
  await loadHistory();
});

document.getElementById('cancel-edit-btn').addEventListener('click', () => {
  editModal.classList.add('hidden');
});

document.getElementById('save-edit-btn').addEventListener('click', async () => {
  editError.textContent = '';
  try {
    const payload = {
      session_type: editTypeInput.value,
      start_time: new Date(editStartInput.value).toISOString()
    };
    if (!editEndInput.disabled && editEndInput.value) {
      payload.end_time = new Date(editEndInput.value).toISOString();
    }
    if (editingSessionId === null) {
      await apiRequest('/timer/sessions', 'POST', payload);
    } else {
      await apiRequest(`/timer/sessions/${editingSessionId}`, 'PATCH', payload);
    }
    editModal.classList.add('hidden');
    await refreshAll();
  } catch (err) {
    editError.textContent = err.message;
  }
});

document.getElementById('cancel-settings-btn').addEventListener('click', () => {
  settingsModal.classList.add('hidden');
});

document.getElementById('save-settings-btn').addEventListener('click', async () => {
  settingsError.textContent = '';
  try {
    const checkboxes = document.querySelectorAll('#set-weekends input[type="checkbox"]:checked');
    const weekendDays = Array.from(checkboxes).map(cb => parseInt(cb.value, 10));
    const payload = {
      default_work_minutes: timeInputToMinutes(setWorkTimeInput.value),
      default_break_minutes: timeInputToMinutes(setBreakTimeInput.value),
      weekend_days: weekendDays
    };
    await apiRequest('/settings', 'PUT', payload);
    settingsModal.classList.add('hidden');
    await refreshAll();
  } catch (err) {
    settingsError.textContent = err.message;
  }
});

document.getElementById('cancel-day-norm-btn').addEventListener('click', () => {
  dayNormModal.classList.add('hidden');
});

document.getElementById('save-day-norm-btn').addEventListener('click', async () => {
  dayNormError.textContent = '';
  try {
    const payload = {
      date_str: editingNormDateStr,
      work_minutes: timeInputToMinutes(dayWorkTimeInput.value),
      break_minutes: timeInputToMinutes(dayBreakTimeInput.value)
    };
    await apiRequest('/settings/daily-norms', 'PUT', payload);
    dayNormModal.classList.add('hidden');
    await refreshAll();
  } catch (err) {
    dayNormError.textContent = err.message;
  }
});

initApp();