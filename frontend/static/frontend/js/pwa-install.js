(function () {
  let deferredPrompt = null;
  const installButton = document.getElementById('pwa-install-btn');
  const installBanner = document.getElementById('pwa-install-banner');
  const dismissBannerBtn = document.getElementById('pwa-dismiss-banner');
  const installBtnBanner = document.getElementById('pwa-install-banner-btn');

  function isIOS() {
    return /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
  }

  function isInStandaloneMode() {
    return window.matchMedia('(display-mode: standalone)').matches ||
           window.navigator.standalone === true;
  }

  function isPWAAvailable() {
    return 'serviceWorker' in navigator && 'PushManager' in window;
  }

  function showInstallBanner() {
    if (installBanner && !isInStandaloneMode() && !localStorage.getItem('pwa-banner-dismissed')) {
      installBanner.classList.remove('hidden');
    }
  }

  function hideInstallBanner() {
    if (installBanner) {
      installBanner.classList.add('hidden');
    }
  }

  function showInstallButton() {
    if (installButton && !isInStandaloneMode()) {
      installButton.classList.remove('hidden');
    }
  }

  function hideInstallButton() {
    if (installButton) {
      installButton.classList.add('hidden');
    }
  }

  async function promptInstall() {
    if (!deferredPrompt) {
      showIOSInstructions();
      return;
    }

    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;

    if (outcome === 'accepted') {
      console.log('[PWA] User accepted install');
      hideInstallBanner();
      hideInstallButton();
      localStorage.setItem('pwa-installed', 'true');
    } else {
      console.log('[PWA] User dismissed install');
    }
    deferredPrompt = null;
  }

  function showIOSInstructions() {
    const modal = document.createElement('div');
    modal.id = 'pwa-ios-modal';
    modal.className = 'modal modal-open';
    modal.innerHTML = `
      <div class="modal-box">
        <h3 class="font-bold text-lg mb-4">Installer Scannier sur iOS</h3>
        <p class="mb-4">Pour installer l'application sur votre iPhone ou iPad :</p>
        <ol class="list-decimal list-inside space-y-2 mb-4 text-sm">
          <li>Appuyez sur le bouton <strong>Partager</strong> (carré avec flèche vers le haut)</li>
          <li>Faites défiler vers le bas et sélectionnez <strong>"Sur l'écran d'accueil"</strong></li>
          <li>Appuyez sur <strong>"Ajouter"</strong> en haut à droite</li>
        </ol>
        <div class="flex justify-end">
          <button class="btn btn-primary" onclick="this.closest('.modal').remove()">Compris</button>
        </div>
      </div>
      <div class="modal-backdrop" onclick="this.parentElement.remove()"></div>
    `;
    document.body.appendChild(modal);
  }

  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    showInstallBanner();
    showInstallButton();
  });

  window.addEventListener('appinstalled', () => {
    console.log('[PWA] App installed');
    hideInstallBanner();
    hideInstallButton();
    localStorage.setItem('pwa-installed', 'true');
    deferredPrompt = null;
  });

  if (dismissBannerBtn) {
    dismissBannerBtn.addEventListener('click', () => {
      hideInstallBanner();
      localStorage.setItem('pwa-banner-dismissed', 'true');
    });
  }

  if (installBtnBanner) {
    installBtnBanner.addEventListener('click', promptInstall);
  }

  if (installButton) {
    installButton.addEventListener('click', promptInstall);
  }

  if (isInStandaloneMode()) {
    hideInstallBanner();
    hideInstallButton();
    document.body.classList.add('pwa-standalone');
  }

  if (isIOS() && !isInStandaloneMode() && !localStorage.getItem('pwa-ios-shown')) {
    setTimeout(() => {
      showIOSInstructions();
      localStorage.setItem('pwa-ios-shown', 'true');
    }, 3000);
  }

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      if (navigator.serviceWorker.controller) {
        console.log('[PWA] New service worker activated');
        if (confirm('Une nouvelle version de Scannier est disponible. Voulez-vous recharger ?')) {
          window.location.reload();
        }
      }
    });
  }

  window.PWAInstall = {
    promptInstall,
    showInstallBanner,
    hideInstallBanner,
    showInstallButton,
    hideInstallButton,
    isInStandaloneMode,
    isIOS,
    isPWAAvailable,
  };
})();