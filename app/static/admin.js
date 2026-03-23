const titleInput = document.getElementById('titleInput');
const announcementInput = document.getElementById('announcementInput');
const announcementToggle = document.getElementById('announcementToggle');
const saveBtn = document.getElementById('saveBtn');
const refreshBtn = document.getElementById('refreshBtn');
const logoutBtn = document.getElementById('logoutBtn');
const loadTopAbsencesBtn = document.getElementById('loadTopAbsencesBtn');
const loadAnomaliesBtn = document.getElementById('loadAnomaliesBtn');
const summarizeTopAbsencesBtn = document.getElementById('summarizeTopAbsencesBtn');
const summarizeAnomaliesBtn = document.getElementById('summarizeAnomaliesBtn');

const adminMessage = document.getElementById('adminMessage');
const topAbsencesMessage = document.getElementById('topAbsencesMessage');
const anomaliesMessage = document.getElementById('anomaliesMessage');
const adminAiMessage = document.getElementById('adminAiMessage');

const usersTable = document.getElementById('usersTable');
const topAbsencesTable = document.getElementById('topAbsencesTable');
const anomaliesTable = document.getElementById('anomaliesTable');
const adminAiOutput = document.getElementById('adminAiOutput');

function showBoxMessage(element, text, isError = false) {
  element.textContent = text;
  element.classList.remove('hidden');
  element.style.background = isError ? '#ffe8e8' : '#f1f1f1';
}

function showMessage(text, isError = false) {
  showBoxMessage(adminMessage, text, isError);
}

function showTopAbsencesMessage(text, isError = false) {
  showBoxMessage(topAbsencesMessage, text, isError);
}

function showAnomaliesMessage(text, isError = false) {
  showBoxMessage(anomaliesMessage, text, isError);
}

function showAdminAiMessage(text, isError = false) {
  showBoxMessage(adminAiMessage, text, isError);
}

function renderTable(tableElement, items) {
  const thead = tableElement.querySelector('thead');
  const tbody = tableElement.querySelector('tbody');

  thead.innerHTML = '';
  tbody.innerHTML = '';

  if (!items.length) return;

  const headers = Object.keys(items[0]);
  const trHead = document.createElement('tr');

  headers.forEach(header => {
    const th = document.createElement('th');
    th.textContent = header;
    trHead.appendChild(th);
  });

  thead.appendChild(trHead);

  items.forEach(item => {
    const tr = document.createElement('tr');

    headers.forEach(header => {
      const td = document.createElement('td');
      td.textContent = item[header] ?? '';
      tr.appendChild(td);
    });

    tbody.appendChild(tr);
  });
}

async function loadTopAbsences() {
  try {
    const res = await fetch('/api/admin/top-absences?limit=10');
    const data = await res.json();

    if (!res.ok) {
      showTopAbsencesMessage(data.detail || 'Impossible de charger les absences.', true);
      renderTable(topAbsencesTable, []);
      return;
    }

    if (!data.items || !data.items.length) {
      showTopAbsencesMessage('Aucune absence significative trouvée.');
      renderTable(topAbsencesTable, []);
      return;
    }

    showTopAbsencesMessage(`Top ${data.count} des collaborateurs avec le plus d'absences.`);
    renderTable(topAbsencesTable, data.items);
  } catch (error) {
    showTopAbsencesMessage('Le serveur est indisponible.', true);
  }
}

async function loadAnomalies() {
  try {
    const res = await fetch('/api/admin/anomalies?limit=100');
    const data = await res.json();

    if (!res.ok) {
      showAnomaliesMessage(data.detail || 'Impossible de charger les anomalies.', true);
      renderTable(anomaliesTable, []);
      return;
    }

    if (!data.items || !data.items.length) {
      showAnomaliesMessage('Aucune anomalie trouvée.');
      renderTable(anomaliesTable, []);
      return;
    }

    showAnomaliesMessage(`${data.count} ligne(s) nécessitent une vérification.`);
    renderTable(anomaliesTable, data.items);
  } catch (error) {
    showAnomaliesMessage('Le serveur est indisponible.', true);
  }
}

async function summarizeAdminData(summaryType, limit) {
  try {
    showAdminAiMessage('Analyse IA en cours...');
    adminAiOutput.value = '';

    const res = await fetch('/api/admin/ai-summary', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        summary_type: summaryType,
        limit: limit,
      }),
    });

    const data = await res.json();

    if (!res.ok) {
      showAdminAiMessage(data.detail || 'Impossible de générer le résumé.', true);
      return;
    }

    adminAiOutput.value = data.summary || '';
    const sourceLabel =
      summaryType === 'top_absences'
        ? 'les plus fortes absences'
        : 'les anomalies';
    showAdminAiMessage(`Résumé IA généré pour ${sourceLabel}.`);
  } catch (error) {
    showAdminAiMessage('Le serveur est indisponible.', true);
  }
}

async function loadAdmin() {
  const me = await fetch('/api/admin/me');
  if (!me.ok) {
    window.location.href = '/admin/login';
    return;
  }

  const configRes = await fetch('/api/admin/config');
  const config = await configRes.json();
  titleInput.value = config.title || '';
  announcementInput.value = config.announcement_text || '';
  announcementToggle.checked = !!config.announcement_enabled;

  const usersRes = await fetch('/api/admin/users');
  const users = await usersRes.json();
  renderTable(usersTable, users.items || []);

  await loadTopAbsences();
}

saveBtn.addEventListener('click', async () => {
  try {
    const res = await fetch('/api/admin/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: titleInput.value,
        announcement_text: announcementInput.value,
        announcement_enabled: announcementToggle.checked,
      })
    });

    const data = await res.json();
    if (!res.ok) {
      showMessage(data.detail || 'Impossible d\'enregistrer.', true);
      return;
    }

    showMessage(data.message || 'Modifications enregistrées.');
  } catch (error) {
    showMessage('Le serveur est indisponible.', true);
  }
});

refreshBtn.addEventListener('click', async () => {
  try {
    const res = await fetch('/api/admin/refresh', { method: 'POST' });
    const data = await res.json();

    if (!res.ok) {
      showMessage(data.detail || 'Actualisation impossible.', true);
      return;
    }

    showMessage(data.message || 'Données actualisées.');
    await loadAdmin();
    renderTable(anomaliesTable, []);
    anomaliesMessage.classList.add('hidden');
    adminAiOutput.value = '';
    adminAiMessage.classList.add('hidden');
  } catch (error) {
    showMessage('Le serveur est indisponible.', true);
  }
});

logoutBtn.addEventListener('click', async () => {
  await fetch('/api/admin/logout', { method: 'POST' });
  window.location.href = '/admin/login';
});

if (loadTopAbsencesBtn) {
  loadTopAbsencesBtn.addEventListener('click', loadTopAbsences);
}

if (loadAnomaliesBtn) {
  loadAnomaliesBtn.addEventListener('click', loadAnomalies);
}

if (summarizeTopAbsencesBtn) {
  summarizeTopAbsencesBtn.addEventListener('click', () => {
    summarizeAdminData('top_absences', 10);
  });
}

if (summarizeAnomaliesBtn) {
  summarizeAnomaliesBtn.addEventListener('click', () => {
    summarizeAdminData('anomalies', 100);
  });
}

window.addEventListener('DOMContentLoaded', loadAdmin);