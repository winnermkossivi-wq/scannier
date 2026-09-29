/* bluetooth.js - Impression de tickets sur imprimante thermique ESC/POS.
    Parcours :
    1) Si un bridge natif Capacitor est present (build mobile), on l'utilise
       (POINT CAPACITOR ci-dessous : unique point d'integration native).
    2) Sinon on tente le Web Bluetooth (Chrome/Edge de bureau / Android WebView).
       Limitations connues : NON supporte sur iOS Safari ; necessite HTTPS ou
       localhost ; l'appareil doit etre apparie/preselectionne via l'OS.
    3) Repli : fenetre d'impression navigateur (CSS thermique). */
(function () {
  // Services/characteristiques ESC/POS les plus courants (non exclusif).
  const UUIDS = [
    "000018f0-0000-1000-8000-00805f9b34fb",
    "49535343-fe7d-4ae5-8fa9-9fafd205e455",
    "00001101-0000-1000-8000-00805f9b34fb",
  ];

  let device = null;
  let server = null;

  function buildEscPos(ticket) {
    const out = [];
    out.push(0x1b, 0x40); // init
    out.push(0x1b, 0x61, 0x01); // center
    out.push(0x1b, 0x45, 0x01); // bold on
    out.push(...str("SCANNIER - TICKET"));
    out.push(0x1b, 0x45, 0x00); // bold off
    out.push(...str(""));
    out.push(0x1b, 0x61, 0x00); // left
    (ticket.lignes || []).forEach(function (l) {
      const line = pad(l.nom, " " + fmt(l.prix * l.quantite));
      out.push(...str(line));
    });
    out.push(...str("--------------------------------"));
    out.push(0x1b, 0x45, 0x01);
    out.push(...str(pad("TOTAL", fmt(ticket.total))));
    out.push(0x1b, 0x45, 0x00);
    out.push(...str(""));
    out.push(...str("Preuve: " + (ticket.hash_preuve || "")));
    out.push(...str("ID: " + (ticket.id_unique || "")));
    out.push(0x1b, 0x61, 0x01);
    out.push(...str("Merci pour votre achat !"));
    out.push(0x1b, 0x61, 0x00);
    out.push(0x0a, 0x0a, 0x0a);
    out.push(0x1d, 0x56, 0x00); // cut
    return new Uint8Array(out);
  }

  function str(s) {
    const a = [];
    for (let i = 0; i < s.length; i++) a.push(s.charCodeAt(i) & 0xff);
    a.push(0x0a);
    return a;
  }
  function fmt(n) {
    return parseFloat(n || 0).toFixed(2) + " FCFA";
  }
  function pad(left, right) {
    const width = 32;
    left = String(left).slice(0, width - right.length - 1);
    return left + " " + right;
  }

  // --- POINT CAPACITOR / natif (impression Bluetooth Classic SPP) ---
  // Dans un build mobile (Capacitor + cordova-plugin-bluetooth-serial), c'est
  // LA SEULE fonction a brancher : elle recoit les octets ESC/POS deja prets
  // (Uint8Array) et les envoie a l'imprimante thermique via le plugin natif.
  // Rien d'autre dans le code frontend ne doit parler a une imprimante native.
  // L'API Web Bluetooth ci-dessous est une solution de secours navigateur
  // (non supportee dans la WebView Android de Capacitor).
  //
  // Prerequis : l'imprimante doit etre APPARIEE dans les parametres Bluetooth
  // de l'Android AVANT le premier usage (le plugin SPP ne fait pas d'appairage).
  function printNative(bytes) {
    const bs = window.bluetoothSerial;
    if (!bs || typeof bs.list !== "function") return null; // pas de bridge natif
    return new Promise(function (resolve, reject) {
      bs.list(
        function (devices) {
          const liste = Array.isArray(devices) ? devices : [];
          if (!liste.length) {
            reject(new Error("Aucune imprimante Bluetooth appairee trouvee"));
            return;
          }
          // Heuristique : privilegier un nom de type imprimante thermique.
          const cible =
            liste.find(function (d) {
              const n = (d.name || "").toLowerCase();
              return /printer|imprim|esc|pos|thermal|roll|blue|hm-|mpt|tps|gprinter/.test(n);
            }) || liste[0];
          bs.connect(
            cible.address,
            function () {
              const ab = bytes.buffer.slice(
                bytes.byteOffset,
                bytes.byteOffset + bytes.byteLength
              );
              bs.write(
                ab,
                function () {
                  setTimeout(function () {
                    bs.disconnect(function () {}, function () {});
                  }, 200);
                  resolve();
                },
                function (err) {
                  bs.disconnect(function () {}, function () {});
                  reject(new Error("Ecriture ESC/POS echouee : " + err));
                }
              );
            },
            function (err) {
              reject(
                new Error(
                  "Connexion impossible a " + (cible.name || cible.address) + " : " + err
                )
              );
            }
          );
        },
        function (err) {
          reject(new Error("Liste des peripheriques Bluetooth echouee : " + err));
        }
      );
    });
  }

  function getWritableCharacteristic(srv) {
    return srv.getPrimaryServices().then(function (services) {
      const tried = [];
      return (function next(i) {
        if (i >= services.length) return Promise.reject(new Error("Aucune caracteristique inscriptible"));
        return services[i]
          .getCharacteristics()
          .then(function (chars) {
            for (const c of chars) {
              if (c.properties && (c.properties.write || c.properties.writeWithoutResponse))
                return c;
            }
            return next(i + 1);
          })
          .catch(function () {
            return next(i + 1);
          });
      })(0);
    });
  }

  function connect() {
    if (device && server && server.connected) return Promise.resolve();
    return navigator.bluetooth
      .requestDevice({ acceptAllDevices: true, optionalServices: UUIDS })
      .then(function (d) {
        device = d;
        return d.gatt.connect();
      })
      .then(function (s) {
        server = s;
        return server;
      });
  }

  function writeChunks(characteristic, bytes) {
    const size = 20;
    let i = 0;
    function step() {
      if (i >= bytes.length) return Promise.resolve();
      const chunk = bytes.subarray(i, i + size);
      i += chunk.length;
      return characteristic.writeValue(chunk).then(step);
    }
    return step();
  }

  async function printWebBluetooth(ticket) {
    const bytes = buildEscPos(ticket);
    const native = printNative(bytes);
    if (native) return native;
    if (!navigator.bluetooth) throw new Error("Web Bluetooth non supporte");
    await connect();
    const characteristic = await getWritableCharacteristic(server);
    await writeChunks(characteristic, bytes);
  }

  function printFallback(ticket) {
    const w = window.open("", "_blank");
    const lignes = (ticket.lignes || [])
      .map(function (l) {
        return "<div class='row'><span>" + esc(l.nom) + "</span><span>" + fmt(l.prix * l.quantite) + "</span></div>";
      })
      .join("");
    w.document.write(
      "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Ticket</title><style>" +
        "body{font-family:'Courier New',monospace;width:80mm;margin:0;padding:8px;font-size:13px;}" +
        ".row{display:flex;justify-content:space-between;}.total{font-weight:bold;border-top:1px dashed #2563eb;margin-top:6px;padding-top:4px;}" +
        ".center{text-align:center;}</style></head><body>" +
        "<div class='center'><b>SCANNIER - TICKET</b></div>" +
        lignes +
        "<div class='row total'><span>TOTAL</span><span>" + fmt(ticket.total) + "</span></div>" +
        "<div>Preuve: " + esc(ticket.hash_preuve || "") + "</div>" +
        "<div>ID: " + esc(ticket.id_unique || "") + "</div>" +
        "<div class='center'>Merci pour votre achat !</div></body></html>"
    );
    w.document.close();
    setTimeout(function () {
      w.print();
    }, 300);
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  window.BluetoothPrinter = {
    // Imprime le ticket : natif -> Web Bluetooth -> repli navigateur.
    async print(ticket) {
      try {
        await printWebBluetooth(ticket);
        return { ok: true, methode: "bluetooth" };
      } catch (e) {
        printFallback(ticket);
        return { ok: true, methode: "fallback", note: e.message };
      }
    },
  };
})();
