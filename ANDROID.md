# Conversion Android (Capacitor) — Scannier

Ce document décrit l'état de la conversion de Scannier en APK Android et les
étapes pour générer et tester l'APK. **Important : l'APK n'a pas pu être compilé
dans l'environnement de développement utilisé (pas de JDK ni Android SDK) ; le
projet est en revanche scoped "build-ready" (tout est configuré pour compiler
d'un seul coup sur une machine équipée d'Android Studio).**

## Architecture retenue

- L'application web (Django sert les templates + le JS statique) est **empaquetée
  dans une WebView Capacitor**. Le frontend ne nécessite aucun refactoring SPA :
  on pointe la WebView vers le frontend **déployé** via `server.url`.
- Caméra (scan QR) : `html5-qrcode` fonctionne dans la WebView Android via
  `getUserMedia` (permission `CAMERA` ajoutée au manifest). Alternative native
  recommandée plus tard : `@capacitor/barcode-scanner`.
- Impression thermique : **impossible en Web Bluetooth dans la WebView Android**
  → on utilise le plugin natif **`cordova-plugin-bluetooth-serial`** (Bluetooth
  **Classic SPP**, le protocole des imprimantes ESC/POS courantes). Le code de
  pont est dans `frontend/static/frontend/js/bluetooth.js` (`printNative`).

## Prérequis (sur la machine qui va compiler l'APK)

- Node.js 18+ (installé)
- **JDK 17** (ex. Temurin/Adoptium) — absent ici
- **Android SDK** + Android Studio, avec :
  - Android Platform 34+ (`android-34`)
  - Build-Tools 34+
  - `ANDROID_HOME` / `ANDROID_SDK_ROOT` positionnées
- Un téléphone Android 8+ (pour les tests réels) ou l'émulateur Android Studio.

## Générer l'APK de debug

1. Déployer le backend Django + frontend sur une URL (ex. `https://caisse.scannier.app`)
   OU le lancer en local pour test : `python manage.py runserver 0.0.0.0:8000`.
2. Renseigner `server.url` dans `capacitor.config.json` :
   - Prod : `"server": { "url": "https://caisse.scannier.app", "cleartext": false }`
   - Test local sur le même réseau : `"server": { "url": "http://192.168.x.x:8000", "cleartext": true }`
     (l'`android:usesCleartextTraffic="true"` est déjà activé dans le manifest pour ce cas)
   - Émulateur : `"server": { "url": "http://10.0.2.2:8000", "cleartext": true }`
3. `npm install` (déjà fait)
4. `npx cap sync android`
5. Build :
   - En ligne de commande : `cd android && ./gradlew assembleDebug`
   - Ou : `npx cap open android` puis **Build > Build Bundle(s) / APK > Build APK** dans Android Studio.
6. APK généré : `android/app/build/outputs/apk/debug/app-debug.apk`

Installer sur le téléphone : `adb install android/app/build/outputs/apk/debug/app-debug.apk`
(ou copier le fichier et l'ouvrir depuis le gestionnaire de fichiers).

## Permissions déclarées (AndroidManifest.xml)

`INTERNET`, `ACCESS_NETWORK_STATE`, `CAMERA`, `BLUETOOTH`, `BLUETOOTH_ADMIN`,
`BLUETOOTH_SCAN` (neverForLocation), `BLUETOOTH_CONNECT`, `ACCESS_FINE_LOCATION`.

## État des tests (honnête)

| Élément | Testé ? | Où | Reste à valider |
| --- | --- | --- | --- |
| Scaffold Capacitor + plugins | Oui | ce repo | — |
| `npx cap add/sync android` | Oui | ce repo | — |
| Compilation APK | **Non** | — | requiert JDK + Android SDK (manquant ici) |
| Scan QR caméra (WebView) | **Non** | émulateur/appareil | valider sur appareil réel (permission caméra) |
| Impression Bluetooth SPP | **Non** | appareil réel | valider avec une vraie imprimante appariée |
| `bluetoothSerial` dans la WebView | **Non** | appareil réel | Cap veut injecter le pont Cordova même pour `server.url` — à confirmer |

## À tester soi-même sur le téléphone (checklist utilisateur)

1. Caméra : ouvrir "Nouvelle vente", activer la caméra, scanner un QR produit →
   la ligne apparaît. Vérifier l'autorisation caméra demandée au 1er lancement.
2. Scan d'un produit `suivre_stock` à stock 0 → avertissement discret "Rupture".
3. Finaliser une vente → ticket à l'écran.
4. Bluetooth : apparier l'imprimante thermique dans les réglages Bluetooth
   Android **avant** le 1er test. Puis "Imprimer" un ticket → sortie papier ESC/POS.
   Si rien ne sort : vérifier que l'imprimante est bien en SPP Classic (et non
   BLE seulement), et qu'elle est appariée.
5. Hors-ligne : couper le réseau, créer une vente, la finaliser → elle doit être
   mise en file locale et synchronisée au retour du réseau.
6. Mode démo : `FRONTEND_USE_MOCK=False` en prod (défaut) ; pour tester sans
   backend, `FRONTEND_USE_MOCK=True` + rebuild.
