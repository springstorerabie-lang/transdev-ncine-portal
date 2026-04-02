const appTitle = document.getElementById('appTitle');
const announcementBox = document.getElementById('announcementBox');
const ncineInput = document.getElementById('ncineInput');
const lookupBtn = document.getElementById('lookupBtn');
const userMessage = document.getElementById('userMessage');
const naturalAnswer = document.getElementById('naturalAnswer');
const resultGrid = document.getElementById('resultGrid');

function showMessage(text, isError = false) {
  userMessage.textContent = text;
  userMessage.classList.remove('hidden');
  userMessage.style.background = isError ? '#ffe8e8' : '#f1f1f1';
}

function buildNaturalAnswer(item) {
  const name = item.nom_prenom || item.nom || '';
  const ncine = item.ncine || '';
  const mle = item.mle || '';
  const service = item.service || '';
  const cumulCa = item.cumul_ca || '';
  const cumulHr = item.cumul_hr || '';
  const cumulAbs = item.cumul_abs || '';
  const note = item.note || '';
  const lastUpdated = item.last_updated || item.mise_a_jour || '';

  const parts = [];

  if (name) parts.push(`Le collaborateur concerné est ${name}.`);
  if (ncine) parts.push(`Le NCINE enregistré est ${ncine}.`);
  if (mle) parts.push(`Le matricule associé est ${mle}.`);
  if (service) parts.push(`Le service indiqué est ${service}.`);
  if (cumulCa) parts.push(`Le cumul CA est de ${cumulCa}.`);
  if (cumulHr) parts.push(`Le cumul HR est de ${cumulHr}.`);
  if (cumulAbs) parts.push(`Le cumul des absences est de ${cumulAbs}.`);
  if (note) parts.push(`La note associée est : ${note}.`);
  if (lastUpdated) parts.push(`La dernière mise à jour enregistrée est ${lastUpdated}.`);

  return parts.join(' ');
}

function renderNaturalAnswer(text) {
  if (!text) {
    naturalAnswer.classList.add('hidden');
    naturalAnswer.textContent = '';
    return;
  }

  naturalAnswer.textContent = text;
  naturalAnswer.classList.remove('hidden');
}

function renderFields(item, labels = {}) {
  resultGrid.innerHTML = '';

  const entries = Object.entries(item).filter(([, value]) => value !== null && value !== undefined && value !== '');

  entries.forEach(([key, value]) => {
    const label = labels[key] || key;

    const el = document.createElement('div');
    el.className = 'result-card';
    el.innerHTML = `
      <div class="result-label">${label}</div>
      <div class="result-value">${value}</div>
    `;

    resultGrid.appendChild(el);
  });
}

async function loadPublicConfig() {
  const res = await fetch('/api/public/config');
  const data = await res.json();

  appTitle.textContent = data.title || 'Assistant Transdev';

  if (data.announcement_enabled && data.announcement_text) {
    announcementBox.textContent = data.announcement_text;
    announcementBox.classList.remove('hidden');
  } else {
    announcementBox.classList.add('hidden');
  }
}

lookupBtn.addEventListener('click', async () => {
  const ncine = ncineInput.value.trim();

  if (!ncine) {
    showMessage('Veuillez saisir votre NCINE.', true);
    return;
  }

  lookupBtn.disabled = true;
  lookupBtn.textContent = 'Chargement...';
  resultGrid.innerHTML = '';
  renderNaturalAnswer('');

  try {
    const res = await fetch('/api/user/lookup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ncine })
    });

    const data = await res.json();

    if (!res.ok) {
      showMessage(data.detail || 'Aucune donnée trouvée.', true);
      return;
    }

    localStorage.setItem('transdev_ncine', ncine);
    showMessage('Vos informations ont été chargées.');

    renderNaturalAnswer(data.message || buildNaturalAnswer(data.item || {}));
    renderFields(data.item || {}, data.labels || {});
  } catch (error) {
    showMessage('Le serveur est indisponible pour le moment.', true);
  } finally {
    lookupBtn.disabled = false;
    lookupBtn.textContent = 'Afficher mes données';
  }
});

window.addEventListener('DOMContentLoaded', async () => {
  await loadPublicConfig();
  const saved = localStorage.getItem('transdev_ncine');
  if (saved) {
    ncineInput.value = saved;
  }
});
