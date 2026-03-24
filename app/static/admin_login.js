document.addEventListener('DOMContentLoaded', () => {
  const adminUser = document.getElementById('adminUser');
  const adminPass = document.getElementById('adminPass');
  const adminLoginBtn = document.getElementById('adminLoginBtn');
  const adminLoginMessage = document.getElementById('adminLoginMessage');

  function showAdminMessage(text, isError = false) {
    adminLoginMessage.textContent = text;
    adminLoginMessage.classList.remove('hidden');
    adminLoginMessage.style.background = isError ? '#ffe8e8' : '#f1f1f1';
  }

  async function submitLogin() {
    adminLoginBtn.disabled = true;
    adminLoginBtn.textContent = 'Connexion...';

    try {
      const res = await fetch('/api/admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: adminUser.value.trim(),
          password: adminPass.value
        })
      });

      const data = await res.json();

      if (!res.ok) {
        showAdminMessage(data.detail || 'Connexion impossible.', true);
        return;
      }

      window.location.href = '/admin';
    } catch (error) {
      showAdminMessage('Le serveur est indisponible.', true);
    } finally {
      adminLoginBtn.disabled = false;
      adminLoginBtn.textContent = 'Se connecter';
    }
  }

  adminLoginBtn.addEventListener('click', submitLogin);

  adminPass.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      submitLogin();
    }
  });

  adminUser.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      submitLogin();
    }
  });
});