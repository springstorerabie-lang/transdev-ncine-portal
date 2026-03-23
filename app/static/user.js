const appTitle = document.getElementById('appTitle');
const announcementBox = document.getElementById('announcementBox');
const ncineInput = document.getElementById('ncineInput');
const lookupBtn = document.getElementById('lookupBtn');
const userMessage = document.getElementById('userMessage');
const resultGrid = document.getElementById('resultGrid');
const aiAnswer = document.getElementById('aiAnswer');

function showMessage(text, isError = false) {
  userMessage.textContent = text;
  userMessage.classList.remove('hidden');
  userMessage.style.background = isError ? '#ffe8e8' : '#f1f1f1';
}

function renderFields(item) {
  resultGrid.innerHTML = '';
  Object.entries(item).forEach(([key, value]) => {
    const el = document.createElement('div');
    el.className = 'field';
    el.innerHTML = `<strong>${key}</strong><div>${value || ''}</div>`;
    resultGrid.appendChild(el);
  });
}

function renderAiAnswer(text) {
  if (!text) {
    aiAnswer.classList.add('hidden');
    aiAnswer.innerHTML = '';
    return;
  }
  aiAnswer.innerHTML = text.replace(/\n/g, '<br>');
  aiAnswer.classList.remove('hidden');
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
  renderAiAnswer('');

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
    renderAiAnswer(data.message || '');
    renderFields(data.item);
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
