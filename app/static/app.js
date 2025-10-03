// app/static/app.js

// -------- helpers --------
const API = {
  async req(method, path, body) {
    const res = await fetch(`/api${path}`, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    });
    const text = await res.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch { /* leave as text */ }
    if (!res.ok) {
      const msg = data && data.detail ? data.detail : text || `HTTP ${res.status}`;
      throw new Error(msg);
    }
    return data;
  },
  get(path) { return this.req('GET', path); },
  post(path, body) { return this.req('POST', path, body); },
};

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));
const asArray = (x) => (Array.isArray(x) ? x : []);
const fmtMoney = (v, c='EUR') => `${v} ${c}`;

function setStatus(msg, ok=true) {
  const el = $('#status');
  el.textContent = msg;
  el.style.color = ok ? 'inherit' : '#b00020';
}

function option(el, value, label) {
  const o = document.createElement('option');
  o.value = value;
  o.textContent = label ?? value;
  el.appendChild(o);
  return o;
}

// -------- state --------
const state = {
  budgets: [],
  accounts: [],
  categories: [],
  steps: [],
  currentBudgetId: null,
  currentStepId: null,
};

// -------- UI refs --------
const ui = {
  btnHealth: $('#btnHealth'),
  btnReloadEverything: $('#btnReloadEverything'),

  budgetSelect: $('#budgetSelect'),
  budgetName: $('#budgetName'),
  budgetCurrency: $('#budgetCurrency'),
  budgetOwnerId: $('#budgetOwnerId'),
  btnCreateBudget: $('#btnCreateBudget'),

  accountsList: $('#accountsList'),
  categoriesList: $('#categoriesList'),
  accName: $('#accName'),
  accCurrency: $('#accCurrency'),
  btnAddAccount: $('#btnAddAccount'),
  catName: $('#catName'),
  btnAddCategory: $('#btnAddCategory'),

  stepSelect: $('#stepSelect'),
  stepName: $('#stepName'),
  stepStart: $('#stepStart'),
  stepEnd: $('#stepEnd'),
  btnCreateStep: $('#btnCreateStep'),
  btnRefreshStep: $('#btnRefreshStep'),

  copyToStep: $('#copyToStep'),
  btnCopyPlanned: $('#btnCopyPlanned'),

  opKind: $('#opKind'),
  opSign: $('#opSign'),
  opAmount: $('#opAmount'),
  opCurrency: $('#opCurrency'),
  opAcc: $('#opAcc'),
  opAccTo: $('#opAccTo'),
  accToLabel: $('#accToLabel'),
  catRow: $('#catRow'),
  opCat: $('#opCat'),
  opComment: $('#opComment'),
  btnAddOperation: $('#btnAddOperation'),

  summaryBox: $('#summaryBox'),
  feedList: $('#feedList'),
};

// -------- load & render --------
async function loadBudgets() {
  const data = await API.get('/budgets');
  const arr = asArray(data);
  state.budgets = arr;
  const last = arr.slice().sort((a,b)=>b.id-a.id)[0] || null;
  state.currentBudgetId = last ? last.id : null;
  if (!Array.isArray(data)) {
    console.warn('Unexpected /budgets payload:', data);
  }
}

function renderBudgets() {
  const sel = ui.budgetSelect;
  sel.innerHTML = '';
  state.budgets
    .slice()
    .sort((a,b)=>b.id-a.id)
    .forEach(b => option(sel, b.id, `#${b.id} — ${b.name} (${b.currency})`));
  if (state.currentBudgetId) sel.value = String(state.currentBudgetId);
}

async function loadAccountsCategories() {
  const [accRaw, catRaw] = await Promise.all([
    API.get('/accounts'),
    API.get('/categories'),
  ]);
  const allAcc = asArray(accRaw);
  const allCat = asArray(catRaw);
  if (!Array.isArray(accRaw)) console.warn('Unexpected /accounts payload:', accRaw);
  if (!Array.isArray(catRaw)) console.warn('Unexpected /categories payload:', catRaw);
  state.accounts = allAcc.filter(a => a.budget_id === state.currentBudgetId);
  state.categories = allCat.filter(c => c.budget_id === state.currentBudgetId);
}

function renderAccountsCategories() {
  ui.accountsList.innerHTML = '';
  state.accounts.forEach(a => {
    const li = document.createElement('li');
    li.textContent = `#${a.id} ${a.name} (${a.currency})`;
    ui.accountsList.appendChild(li);
  });

  ui.categoriesList.innerHTML = '';
  state.categories.forEach(c => {
    const li = document.createElement('li');
    li.textContent = `#${c.id} ${c.name}`;
    ui.categoriesList.appendChild(li);
  });

  // селекты для операций
  ui.opAcc.innerHTML = '';
  state.accounts.forEach(a => option(ui.opAcc, a.id, `${a.name} (#${a.id})`));
  ui.opAccTo.innerHTML = '';
  state.accounts.forEach(a => option(ui.opAccTo, a.id, `${a.name} (#${a.id})`));
  ui.opCat.innerHTML = '';
  state.categories.forEach(c => option(ui.opCat, c.id, `${c.name} (#${c.id})`));
}

async function loadSteps() {
  if (!state.currentBudgetId) { state.steps = []; state.currentStepId = null; return; }
  const raw = await API.get(`/steps?budget_id=${state.currentBudgetId}`);
  const arr = asArray(raw);
  if (!Array.isArray(raw)) console.warn('Unexpected /steps payload:', raw);
  state.steps = arr;
  const last = arr.slice().sort((a,b)=>b.id-a.id)[0] || null;
  state.currentStepId = last ? last.id : null;
}

function renderSteps() {
  ui.stepSelect.innerHTML = '';
  state.steps
    .slice()
    .sort((a,b)=>b.id-a.id)
    .forEach(s => option(ui.stepSelect, s.id, `#${s.id} ${s.name} ${s.date_start}..${s.date_end}`));
  if (state.currentStepId) ui.stepSelect.value = String(state.currentStepId);

  // селект для копирования
  ui.copyToStep.innerHTML = '';
  state.steps
    .slice()
    .sort((a,b)=>b.id-a.id)
    .forEach(s => option(ui.copyToStep, s.id, `#${s.id} ${s.name}`));
}

async function loadSummaryFeed() {
  if (!state.currentStepId) { ui.summaryBox.textContent = '–'; ui.feedList.innerHTML=''; return; }
  const [sum, feedRaw] = await Promise.all([
    API.get(`/steps/${state.currentStepId}/summary`),
    API.get(`/steps/${state.currentStepId}/feed`),
  ]);
  const feed = asArray(feedRaw);
  if (!Array.isArray(feedRaw)) console.warn('Unexpected /feed payload:', feedRaw);

  ui.summaryBox.textContent =
    `Доходы: ${sum?.total_income ?? 0}\nРасходы: ${sum?.total_expense ?? 0}\nСальдо: ${sum?.net ?? 0}`;

  ui.feedList.innerHTML = '';
  feed.forEach(op => {
    const li = document.createElement('li');
    const title = `[${op.kind}/${op.sign}] ${fmtMoney(op.amount, op.currency)}`;
    const details = [];
    if (op.account_id) details.push(`acc#${op.account_id}`);
    if (op.account_id_to) details.push(`→ acc#${op.account_id_to}`);
    if (op.category_id) details.push(`cat#${op.category_id}`);
    if (op.comment) details.push(`“${op.comment}”`);
    li.textContent = `${title} ${details.length? '— ' + details.join(' ') : ''}`;
    ui.feedList.appendChild(li);
  });
}

async function reloadAll() {
  try {
    setStatus('Загрузка…');
    await loadBudgets();
    renderBudgets();

    await loadAccountsCategories();
    renderAccountsCategories();

    await loadSteps();
    renderSteps();

    await loadSummaryFeed();
    setStatus('Готово');
  } catch (e) {
    console.error(e);
    setStatus(`Ошибка: ${e.message}`, false);
  }
}

async function reloadForBudgetChange() {
  try {
    setStatus('Обновление для выбранного бюджета…');
    state.currentBudgetId = Number(ui.budgetSelect.value);
    await loadAccountsCategories();
    renderAccountsCategories();
    await loadSteps();
    renderSteps();
    await loadSummaryFeed();
    setStatus('Готово');
  } catch (e) {
    console.error(e);
    setStatus(`Ошибка: ${e.message}`, false);
  }
}

async function reloadForStepChange() {
  try {
    setStatus('Обновление шага…');
    state.currentStepId = Number(ui.stepSelect.value);
    await loadSummaryFeed();
    setStatus('Готово');
  } catch (e) {
    console.error(e);
    setStatus(`Ошибка: ${e.message}`, false);
  }
}

// -------- actions --------
ui.btnHealth.addEventListener('click', async () => {
  try {
    const h = await API.get('/health');
    setStatus(`API OK: ${h.status}`);
  } catch (e) {
    setStatus(`API ошибка: ${e.message}`, false);
  }
});

ui.btnReloadEverything.addEventListener('click', reloadAll);
ui.budgetSelect.addEventListener('change', reloadForBudgetChange);
ui.stepSelect.addEventListener('change', reloadForStepChange);
ui.btnRefreshStep.addEventListener('click', reloadForStepChange);

ui.btnCreateBudget.addEventListener('click', async () => {
  try {
    const name = ui.budgetName.value.trim();
    const currency = ui.budgetCurrency.value.trim() || 'EUR';
    const owner_user_id = Number(ui.budgetOwnerId.value || 1);
    if (!name) throw new Error('Введите название бюджета');
    await API.post('/budgets', { name, currency, owner_user_id });
    await reloadAll();
    setStatus('Бюджет создан');
  } catch (e) {
    setStatus(`Ошибка создания бюджета: ${e.message}`, false);
  }
});

ui.btnAddAccount.addEventListener('click', async () => {
  try {
    if (!state.currentBudgetId) throw new Error('Не выбран бюджет');
    const name = ui.accName.value.trim();
    const currency = ui.accCurrency.value.trim() || 'EUR';
    if (!name) throw new Error('Введите название счёта');
    await API.post('/accounts', { budget_id: state.currentBudgetId, name, currency });
    await loadAccountsCategories();
    renderAccountsCategories();
    setStatus('Счёт добавлен');
  } catch (e) {
    setStatus(`Ошибка добавления счёта: ${e.message}`, false);
  }
});

ui.btnAddCategory.addEventListener('click', async () => {
  try {
    if (!state.currentBudgetId) throw new Error('Не выбран бюджет');
    const name = ui.catName.value.trim();
    if (!name) throw new Error('Введите название категории');
    await API.post('/categories', { budget_id: state.currentBudgetId, name });
    await loadAccountsCategories();
    renderAccountsCategories();
    setStatus('Категория добавлена');
  } catch (e) {
    setStatus(`Ошибка добавления категории: ${e.message}`, false);
  }
});

ui.btnCreateStep.addEventListener('click', async () => {
  try {
    if (!state.currentBudgetId) throw new Error('Не выбран бюджет');
    const name = ui.stepName.value.trim() || `Шаг ${new Date().toISOString().slice(0,10)}`;
    const date_start = ui.stepStart.value || new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().slice(0,10);
    const endDate = ui.stepEnd.value ||
      new Date(new Date(new Date().getFullYear(), new Date().getMonth()+1, 0)).toISOString().slice(0,10);
    await API.post('/steps', {
      budget_id: state.currentBudgetId,
      granularity: 'month',
      name,
      date_start,
      date_end: endDate,
    });
    await loadSteps();
    renderSteps();
    setStatus('Шаг создан');
  } catch (e) {
    setStatus(`Ошибка создания шага: ${e.message}`, false);
  }
});

ui.opSign.addEventListener('change', () => {
  const sign = ui.opSign.value;
  const isTransfer = sign === 'transfer';
  ui.opAccTo.classList.toggle('hidden', !isTransfer);
  ui.accToLabel.classList.toggle('hidden', !isTransfer);
  ui.catRow.classList.toggle('hidden', isTransfer);
});

ui.btnAddOperation.addEventListener('click', async () => {
  try {
    if (!state.currentStepId) throw new Error('Не выбран шаг');
    const payload = {
      step_id: state.currentStepId,
      kind: ui.opKind.value,
      sign: ui.opSign.value,
      amount: String(Number(ui.opAmount.value || 0).toFixed(2)),
      currency: ui.opCurrency.value.trim() || 'EUR',
      account_id: Number(ui.opAcc.value),
      comment: ui.opComment.value.trim() || null,
    };
    if (payload.sign === 'transfer') {
      payload.account_id_to = Number(ui.opAccTo.value);
    } else {
      payload.category_id = Number(ui.opCat.value);
    }
    await API.post('/operations', payload);
    await loadSummaryFeed();
    setStatus('Операция добавлена');
  } catch (e) {
    setStatus(`Ошибка добавления операции: ${e.message}`, false);
  }
});

ui.btnCopyPlanned.addEventListener('click', async () => {
  try {
    if (!state.currentStepId) throw new Error('Не выбран исходный шаг');
    const to_step_id = Number(ui.copyToStep.value);
    if (!to_step_id) throw new Error('Выберите целевой шаг');
    const res = await API.post(`/steps/${state.currentStepId}/copy_planned`, { to_step_id });
    await loadSummaryFeed();
    setStatus(`Скопировано плановых: ${res?.copied ?? 0}`);
  } catch (e) {
    setStatus(`Ошибка копирования: ${e.message}`, false);
  }
});

// -------- init --------
window.addEventListener('DOMContentLoaded', async () => {
  ui.opSign.dispatchEvent(new Event('change'));
  await reloadAll();
});