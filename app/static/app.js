const $ = (sel) => document.querySelector(sel);
const apiBase = location.origin; // тот же хост, что и бэкенд
const state = {
  budgets: [],
  accounts: [],
  categories: [],
  steps: [],
  currentBudgetId: +localStorage.getItem('budgetId') || 1,
  currentStepId: +localStorage.getItem('stepId') || null,
};

const statusEl = $('#status');

async function api(path, opts={}) {
  const res = await fetch(`${apiBase}${path}`, {
    headers: { 'Content-Type':'application/json' },
    ...opts,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${path}`);
  const text = await res.text();
  try { return JSON.parse(text); } catch { return text; }
}

function fmtMoney(amount, curr) {
  return `${amount} ${curr}`;
}

function setStatus(text) {
  statusEl.textContent = text;
}

function fillSelect(sel, items, getVal, getText) {
  sel.innerHTML = '';
  for (const it of items) {
    const opt = document.createElement('option');
    opt.value = getVal(it);
    opt.textContent = getText(it);
    sel.appendChild(opt);
  }
}

function filterByBudget(list) {
  return list.filter(x => x.budget_id === state.currentBudgetId);
}

// ------- загрузка справочников -------
async function loadBudgets() {
  state.budgets = await api('/budgets');
  fillSelect($('#budgetSelect'), state.budgets, x => x.id, x => `#${x.id} ${x.name} (${x.currency})`);
  if (!state.currentBudgetId && state.budgets.length) state.currentBudgetId = state.budgets[0].id;
  $('#budgetSelect').value = state.currentBudgetId;
}

async function loadAccounts() {
  const all = await api('/accounts');
  state.accounts = filterByBudget(all);
  const text = state.accounts.map(a => `#${a.id} ${a.name} (${a.currency})`).join('\n') || '—';
  $('#accountsList').innerHTML = text.split('\n').map(li => `<li>${li}</li>`).join('');
  fillSelect($('#opAcc'), state.accounts, x => x.id, x => `${x.name} (#${x.id})`);
  fillSelect($('#opAccTo'), state.accounts, x => x.id, x => `${x.name} (#${x.id})`);
}

async function loadCategories() {
  const all = await api('/categories');
  state.categories = filterByBudget(all);
  const text = state.categories.map(c => `#${c.id} ${c.name}`).join('\n') || '—';
  $('#categoriesList').innerHTML = text.split('\n').map(li => `<li>${li}</li>`).join('');
  fillSelect($('#opCat'), state.categories, x => x.id, x => `${x.name} (#${x.id})`);
}

async function loadSteps() {
  state.steps = await api(`/steps?budget_id=${state.currentBudgetId}`);
  fillSelect($('#stepSelect'), state.steps, x => x.id, x => `#${x.id} ${x.name}`);
  fillSelect($('#copyToStep'), state.steps, x => x.id, x => `#${x.id} ${x.name}`);

  if (!state.currentStepId && state.steps.length) state.currentStepId = state.steps[0].id;
  $('#stepSelect').value = state.currentStepId ?? '';
}

// ------- действия над шагом -------
async function refreshStepData() {
  if (!state.currentStepId) return;
  const sum = await api(`/steps/${state.currentStepId}/summary`);
  $('#summaryBox').textContent = `Доходы: ${sum.total_income}\nРасходы: ${sum.total_expense}\nИтого: ${sum.net}`;

  const feed = await api(`/steps/${state.currentStepId}/feed`);
  $('#feedList').innerHTML = feed.map(op => {
    const what = op.sign === 'transfer'
      ? `Перевод ${fmtMoney(op.amount, op.currency)} (#${op.account_id} → #${op.account_id_to})`
      : `${op.sign === 'expense' ? 'Расход' : 'Доход'} ${fmtMoney(op.amount, op.currency)} [кат. ${op.category_id ?? '—'}]`;
    return `<li><strong>#${op.id}</strong> ${what}<br><small>${op.comment ?? ''}</small></li>`;
  }).join('');
}

// ------- формы -------
function computeDefaultMonth() {
  const d = new Date();
  const y = d.getFullYear(), m = d.getMonth(); // текущий
  const start = new Date(y, m, 1);
  const end = new Date(y, m + 1, 0);
  const toISO = (dt) => dt.toISOString().slice(0,10);
  $('#stepName').value = `Месяц ${toISO(start).slice(0,7)}`;
  $('#stepStart').value = toISO(start);
  $('#stepEnd').value = toISO(end);
}

function updateOpFormVisibility() {
  const sign = $('#opSign').value;
  const isTransfer = sign === 'transfer';
  $('#accToLabel').classList.toggle('hidden', !isTransfer);
  $('#opAccTo').classList.toggle('hidden', !isTransfer);
  $('#catRow').classList.toggle('hidden', isTransfer);
}

// ------- события UI -------
async function onBudgetChanged() {
  state.currentBudgetId = +$('#budgetSelect').value;
  localStorage.setItem('budgetId', String(state.currentBudgetId));
  setStatus(`Бюджет #${state.currentBudgetId}`);
  await Promise.all([loadAccounts(), loadCategories(), loadSteps()]);
  state.currentStepId = +$('#stepSelect').value || null;
  localStorage.setItem('stepId', String(state.currentStepId || ''));
  await refreshStepData();
}

async function onCreateBudget() {
  const name = $('#budgetName').value.trim();
  const currency = $('#budgetCurrency').value.trim() || 'EUR';
  const owner = +$('#budgetOwnerId').value || 1;
  const b = await api('/budgets', { method:'POST', body: JSON.stringify({ name, currency, owner_user_id: owner }) });
  setStatus(`Создан бюджет #${b.id}`);
  await loadBudgets();
  $('#budgetSelect').value = b.id;
  await onBudgetChanged();
}

async function onAddAccount() {
  const name = $('#accName').value.trim();
  const currency = $('#accCurrency').value.trim() || 'EUR';
  const a = await api('/accounts', { method:'POST', body: JSON.stringify({ budget_id: state.currentBudgetId, name, currency }) });
  setStatus(`Счёт #${a.id} создан`);
  await loadAccounts();
}

async function onAddCategory() {
  const name = $('#catName').value.trim();
  const c = await api('/categories', { method:'POST', body: JSON.stringify({ budget_id: state.currentBudgetId, name }) });
  setStatus(`Категория #${c.id} создана`);
  await loadCategories();
}

async function onCreateStep() {
  const name = $('#stepName').value.trim();
  const date_start = $('#stepStart').value;
  const date_end = $('#stepEnd').value;
  const payload = { budget_id: state.currentBudgetId, granularity:'month', name, date_start, date_end };
  const s = await api('/steps', { method:'POST', body: JSON.stringify(payload) });
  setStatus(`Шаг #${s.id} создан`);
  await loadSteps();
  $('#stepSelect').value = s.id;
  state.currentStepId = s.id;
  localStorage.setItem('stepId', String(state.currentStepId));
  await refreshStepData();
}

async function onStepChanged() {
  state.currentStepId = +$('#stepSelect').value || null;
  localStorage.setItem('stepId', String(state.currentStepId || ''));
  await refreshStepData();
}

async function onCopyPlanned() {
  const toId = +$('#copyToStep').value;
  if (!state.currentStepId || !toId) return;
  const res = await api(`/steps/${state.currentStepId}/copy_planned`, {
    method:'POST', body: JSON.stringify({ to_step_id: toId })
  });
  setStatus(`Скопировано: ${res.copied}`);
  await refreshStepData();
}

async function onAddOperation() {
  if (!state.currentStepId) return alert('Выберите шаг');
  const kind = $('#opKind').value;
  const sign = $('#opSign').value;
  const amount = ($('#opAmount').value || '').trim();
  const currency = $('#opCurrency').value.trim() || 'EUR';
  const account_id = +$('#opAcc').value;
  const account_id_to = $('#opAccTo').classList.contains('hidden') ? null : +$('#opAccTo').value;
  const category_id = $('#catRow').classList.contains('hidden') ? null : +$('#opCat').value;
  const comment = $('#opComment').value;
  const payload = { step_id: state.currentStepId, kind, sign, amount, currency, account_id, account_id_to, category_id, comment };
  await api('/operations', { method:'POST', body: JSON.stringify(payload) });
  setStatus('Операция добавлена');
  $('#opAmount').value = '';
  $('#opComment').value = '';
  await refreshStepData();
}

// ------- инициализация -------
async function init() {
  $('#btnHealth').onclick         = async () => { const r = await api('/health'); setStatus(JSON.stringify(r)); };
  $('#btnReloadEverything').onclick = onBudgetChanged;
  $('#budgetSelect').onchange     = onBudgetChanged;

  $('#btnCreateBudget').onclick   = onCreateBudget;

  $('#btnAddAccount').onclick     = onAddAccount;
  $('#btnAddCategory').onclick    = onAddCategory;

  $('#btnCreateStep').onclick     = onCreateStep;
  $('#stepSelect').onchange       = onStepChanged;
  $('#btnRefreshStep').onclick    = refreshStepData;
  $('#btnCopyPlanned').onclick    = onCopyPlanned;

  $('#btnAddOperation').onclick   = onAddOperation;
  $('#opSign').onchange           = updateOpFormVisibility;

  computeDefaultMonth();
  updateOpFormVisibility();

  await loadBudgets();
  if (!state.currentBudgetId && state.budgets.length) state.currentBudgetId = state.budgets[0].id;
  $('#budgetSelect').value = state.currentBudgetId;

  await onBudgetChanged();
}

init().catch(e => setStatus(`Ошибка инициализации: ${e.message}`));
JS