/**
 * map-picker.js
 * Selector interactivo de dirección 100% gratuito y con soporte Online + Offline:
 * - Leaflet local (static/vendor/leaflet/) sin depender de CDN.
 * - Caché automático de mosaicos OpenStreetMap en CacheStorage (lo que ves online queda disponible offline).
 * - Cuadrícula SVG elegante como respaldo offline para zonas no cacheadas.
 * - Catálogo local offline de barrios, vías y puntos de referencia de Boyacá con búsqueda difusa (tolera errores).
 * - Autocompletado en vivo (Photon + Nominatim) cuando hay internet + geocodificación inversa offline por cercanía.
 */
(function () {
  "use strict";

  const TILE_CACHE_NAME = "constru-trans-map-tiles-v1";

  const COORDENADAS_CIUDADES = {
    duitama: [5.8245, -73.0341],
    sogamoso: [5.7143, -72.9339],
    paipa: [5.7801, -73.1171],
    tunja: [5.5353, -73.3678],
    tibasosa: [5.7478, -72.9967],
    nobsa: [5.7694, -72.9403],
    "santa rosa de viterbo": [5.8742, -72.9817],
    belen: [5.9889, -72.9125],
    cerinza: [5.9564, -72.9508],
    firavitoba: [5.6681, -72.9942],
    iza: [5.6122, -72.9803],
    cuitiva: [5.5819, -72.9678],
    tota: [5.5583, -72.9858],
    aquitania: [5.5206, -72.8856],
    mongui: [5.7222, -72.8492],
    mongua: [5.7519, -72.8017],
    topaga: [5.7675, -72.8364],
    corrales: [5.8294, -72.8439],
    busbanza: [5.8386, -72.8842],
    floresta: [5.8594, -72.9219],
    bogota: [4.711, -74.0721],
  };

  // Catálogo local offline de barrios, sectores y referencias de Boyacá
  const LUGARES_LOCALES_OFFLINE = [
    // Duitama
    { nombre: "Barrio Centro", ciudad: "Duitama", lat: 5.8266, lng: -73.0332, sub: "Parque Los Libertadores · Duitama" },
    { nombre: "Barrio Los Robledales", ciudad: "Duitama", lat: 5.8342, lng: -73.0258, sub: "Sector Norte · Duitama" },
    { nombre: "Barrio Solano", ciudad: "Duitama", lat: 5.8221, lng: -73.0292, sub: "Zona Residencial · Duitama" },
    { nombre: "Barrio San José", ciudad: "Duitama", lat: 5.8196, lng: -73.0355, sub: "Sector Sur · Duitama" },
    { nombre: "Barrio La Milagrosa", ciudad: "Duitama", lat: 5.8304, lng: -73.0285, sub: "Sector Nororiental · Duitama" },
    { nombre: "Barrio San Luis", ciudad: "Duitama", lat: 5.8295, lng: -73.0384, sub: "Sector Occidental · Duitama" },
    { nombre: "Barrio Las Américas", ciudad: "Duitama", lat: 5.8178, lng: -73.0315, sub: "Avenida Las Américas · Duitama" },
    { nombre: "Barrio Boyacá", ciudad: "Duitama", lat: 5.8241, lng: -73.0398, sub: "Duitama" },
    { nombre: "Barrio El Carmen", ciudad: "Duitama", lat: 5.8212, lng: -73.0412, sub: "Duitama" },
    { nombre: "Barrio San Fernando", ciudad: "Duitama", lat: 5.8355, lng: -73.0342, sub: "Duitama" },
    { nombre: "Barrio La Florida", ciudad: "Duitama", lat: 5.8318, lng: -73.0421, sub: "Duitama" },
    { nombre: "Barrio Villa del Prado", ciudad: "Duitama", lat: 5.8152, lng: -73.0389, sub: "Duitama" },
    { nombre: "Barrio Simón Bolívar", ciudad: "Duitama", lat: 5.8165, lng: -73.0265, sub: "Duitama" },
    { nombre: "Barrio Camilo Torres", ciudad: "Duitama", lat: 5.8134, lng: -73.0341, sub: "Duitama" },
    { nombre: "Barrio San Vicente", ciudad: "Duitama", lat: 5.8278, lng: -73.0245, sub: "Duitama" },
    { nombre: "Barrio La Perla", ciudad: "Duitama", lat: 5.8331, lng: -73.0311, sub: "Duitama" },
    { nombre: "Barrio Los Alpes", ciudad: "Duitama", lat: 5.8375, lng: -73.0294, sub: "Duitama" },
    { nombre: "Terminal de Transportes Duitama", ciudad: "Duitama", lat: 5.8159, lng: -73.0348, sub: "Avenida Circunvalar · Duitama" },
    { nombre: "Centro Comercial Innovo Plaza", ciudad: "Duitama", lat: 5.8208, lng: -73.0318, sub: "Calle 18 · Duitama" },
    { nombre: "Pueblito Boyacense", ciudad: "Duitama", lat: 5.8124, lng: -73.0418, sub: "Sector Turístico · Duitama" },
    { nombre: "Ciudadela Industrial Duitama", ciudad: "Duitama", lat: 5.8091, lng: -73.0289, sub: "Zona Industrial · Duitama" },
    // Sogamoso
    { nombre: "Barrio Centro", ciudad: "Sogamoso", lat: 5.7143, lng: -72.9339, sub: "Plaza de la Villa · Sogamoso" },
    { nombre: "Barrio San Martín", ciudad: "Sogamoso", lat: 5.7185, lng: -72.9302, sub: "Sogamoso" },
    { nombre: "Barrio El Laguito", ciudad: "Sogamoso", lat: 5.7212, lng: -72.9278, sub: "Parque El Laguito · Sogamoso" },
    { nombre: "Barrio Sucre", ciudad: "Sogamoso", lat: 5.7115, lng: -72.9362, sub: "Sogamoso" },
    { nombre: "Barrio Olaya Herrera", ciudad: "Sogamoso", lat: 5.7168, lng: -72.9388, sub: "Sogamoso" },
    { nombre: "Barrio Santa Bárbara", ciudad: "Sogamoso", lat: 5.7094, lng: -72.9312, sub: "Sogamoso" },
    { nombre: "Barrio Los Rosales", ciudad: "Sogamoso", lat: 5.7245, lng: -72.9261, sub: "Sogamoso" },
    { nombre: "Barrio Universitario", ciudad: "Sogamoso", lat: 5.7042, lng: -72.9421, sub: "UPTC · Sogamoso" },
    { nombre: "Centro Comercial Plaza Barcelona", ciudad: "Sogamoso", lat: 5.7176, lng: -72.9325, sub: "Carrera 11 · Sogamoso" },
    { nombre: "Terminal de Transportes Sogamoso", ciudad: "Sogamoso", lat: 5.7189, lng: -72.9408, sub: "Carrera 17 · Sogamoso" },
    // Paipa
    { nombre: "Barrio Centro", ciudad: "Paipa", lat: 5.7801, lng: -73.1171, sub: "Parque Jaime Rook · Paipa" },
    { nombre: "Sector Lago Sochagota", ciudad: "Paipa", lat: 5.7712, lng: -73.1055, sub: "Zona Hotelera · Paipa" },
    { nombre: "Barrio San Felipe", ciudad: "Paipa", lat: 5.7832, lng: -73.1195, sub: "Paipa" },
    { nombre: "Barrio Los Rosales", ciudad: "Paipa", lat: 5.7775, lng: -73.1214, sub: "Paipa" },
    { nombre: "Termales de Paipa", ciudad: "Paipa", lat: 5.7595, lng: -73.1142, sub: "Vía Pantano de Vargas · Paipa" },
    // Tunja
    { nombre: "Barrio Centro Histórico", ciudad: "Tunja", lat: 5.5353, lng: -73.3678, sub: "Plaza de Bolívar · Tunja" },
    { nombre: "Barrio Las Nieves", ciudad: "Tunja", lat: 5.5382, lng: -73.3652, sub: "Tunja" },
    { nombre: "Barrio Maldonado", ciudad: "Tunja", lat: 5.5415, lng: -73.3635, sub: "Tunja" },
    { nombre: "Barrio Santa Inés", ciudad: "Tunja", lat: 5.5485, lng: -73.3592, sub: "Zona Norte · Tunja" },
    { nombre: "Barrio Los Muiscas", ciudad: "Tunja", lat: 5.5562, lng: -73.3531, sub: "Zona Norte · Tunja" },
    { nombre: "Barrio La Fuente", ciudad: "Tunja", lat: 5.5301, lng: -73.3712, sub: "Tunja" },
    { nombre: "Centro Comercial Viva Tunja", ciudad: "Tunja", lat: 5.5534, lng: -73.3554, sub: "Avenida Universitaria · Tunja" },
    { nombre: "Terminal de Transportes Tunja", ciudad: "Tunja", lat: 5.5322, lng: -73.3608, sub: "Tunja" },
    // Municipios cercanos
    { nombre: "Parque Principal Tibasosa", ciudad: "Tibasosa", lat: 5.7478, lng: -72.9967, sub: "Centro · Tibasosa" },
    { nombre: "Parque Principal Nobsa", ciudad: "Nobsa", lat: 5.7694, lng: -72.9403, sub: "Centro · Nobsa" },
    { nombre: "Sector Nazareth", ciudad: "Nobsa", lat: 5.7582, lng: -72.9495, sub: "Zona Industrial · Nobsa" },
    { nombre: "Parque Principal Santa Rosa de Viterbo", ciudad: "Santa Rosa de Viterbo", lat: 5.8742, lng: -72.9817, sub: "Centro · Santa Rosa de Viterbo" },
    { nombre: "Parque Principal Belén", ciudad: "Belén", lat: 5.9889, lng: -72.9125, sub: "Centro · Belén" },
    { nombre: "Parque Principal Cerinza", ciudad: "Cerinza", lat: 5.9564, lng: -72.9508, sub: "Centro · Cerinza" },
    { nombre: "Parque Principal Firavitoba", ciudad: "Firavitoba", lat: 5.6681, lng: -72.9942, sub: "Centro · Firavitoba" },
    { nombre: "Parque Principal Iza", ciudad: "Iza", lat: 5.6122, lng: -72.9803, sub: "Centro · Iza" },
    { nombre: "Parque Principal Aquitania", ciudad: "Aquitania", lat: 5.5206, lng: -72.8856, sub: "Centro · Aquitania" },
    { nombre: "Parque Principal Monguí", ciudad: "Monguí", lat: 5.7222, lng: -72.8492, sub: "Centro · Monguí" },
  ];

  // Mosaico SVG elegante para modo offline cuando el cuadro aún no está en caché
  const OFFLINE_TILE_SVG =
    "data:image/svg+xml;charset=utf-8," +
    encodeURIComponent(
      '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256">' +
        '<rect width="256" height="256" fill="#0f172a"/>' +
        '<path d="M 64 0 V 256 M 128 0 V 256 M 192 0 V 256 M 0 64 H 256 M 0 128 H 256 M 0 192 H 256" stroke="#1e293b" stroke-width="1"/>' +
        '<path d="M 0 0 H 256 V 256 H 0 Z" fill="none" stroke="#334155" stroke-width="1" stroke-dasharray="4 4"/>' +
        '<text x="128" y="132" text-anchor="middle" fill="#475569" font-family="sans-serif" font-size="11" font-weight="600">Mapa Offline</text>' +
        "</svg>"
    );

  function normalizarClave(str) {
    return (str || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .trim();
  }

  function limpiarDireccion(texto) {
    return (texto || "")
      .replace(/[^\w\sáéíóúÁÉÍÓÚñÑüÜ#.,\-/°]/g, "")
      .replace(/\s+/g, " ")
      .trim()
      .slice(0, 180);
  }

  function distanciaLevenshtein(a, b) {
    if (a === b) return 0;
    if (!a.length) return b.length;
    if (!b.length) return a.length;
    const dp = Array.from({ length: a.length + 1 }, () => new Array(b.length + 1).fill(0));
    for (let i = 0; i <= a.length; i++) dp[i][0] = i;
    for (let j = 0; j <= b.length; j++) dp[0][j] = j;
    for (let i = 1; i <= a.length; i++) {
      for (let j = 1; j <= b.length; j++) {
        const costo = a[i - 1] === b[j - 1] ? 0 : 1;
        dp[i][j] = Math.min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + costo);
      }
    }
    return dp[a.length][b.length];
  }

  function distanciaKm(lat1, lng1, lat2, lng2) {
    const R = 6371;
    const dLat = ((lat2 - lat1) * Math.PI) / 180;
    const dLng = ((lng2 - lng1) * Math.PI) / 180;
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos((lat1 * Math.PI) / 180) *
        Math.cos((lat2 * Math.PI) / 180) *
        Math.sin(dLng / 2) *
        Math.sin(dLng / 2);
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  function extraerCoordenadasDeTexto(texto) {
    if (!texto) return null;
    const match = texto.match(/(-?\d{1,2}\.\d{3,})\s*[, ]\s*(-?\d{1,3}\.\d{3,})/);
    if (!match) return null;
    const lat = parseFloat(match[1]);
    const lng = parseFloat(match[2]);
    if (Number.isNaN(lat) || Number.isNaN(lng)) return null;
    if (lat < -90 || lat > 90 || lng < -180 || lng > 180) return null;
    return [lat, lng];
  }

  function buscarEnCatalogoLocal(queryRaw, ciudadSel) {
    const q = normalizarClave(queryRaw);
    if (!q || q.length < 2) return [];
    const ciudadNorm = normalizarClave(ciudadSel);
    const tokens = q.split(/\s+/).filter(Boolean);

    const puntuados = [];
    for (const lugar of LUGARES_LOCALES_OFFLINE) {
      const textoCompleto = normalizarClave(`${lugar.nombre} ${lugar.sub} ${lugar.ciudad}`);
      const palabras = textoCompleto.split(/\s+/);
      let score = 0;

      if (textoCompleto.includes(q)) score += 10;

      for (const tok of tokens) {
        if (tok.length < 2) continue;
        if (textoCompleto.includes(tok)) {
          score += 5;
        } else {
          // Tolerancia a errores de escritura (ej: "rubleales" -> "robledales")
          let mejorDist = 99;
          for (const pal of palabras) {
            if (Math.abs(pal.length - tok.length) > 3) continue;
            const d = distanciaLevenshtein(tok, pal);
            if (d < mejorDist) mejorDist = d;
          }
          const maxTolerancia = tok.length >= 6 ? 2 : 1;
          if (mejorDist <= maxTolerancia) {
            score += 4 - mejorDist;
          }
        }
      }

      if (score > 0) {
        if (ciudadNorm && normalizarClave(lugar.ciudad) === ciudadNorm) {
          score += 3;
        }
        puntuados.push({ score, lugar });
      }
    }

    puntuados.sort((a, b) => b.score - a.score);
    return puntuados.slice(0, 6).map(({ lugar }) => ({
      lat: lugar.lat,
      lng: lugar.lng,
      titulo: lugar.nombre,
      subtitulo: `${lugar.sub} (Catálogo local)`,
      direccion: `${lugar.nombre}, ${lugar.ciudad}`,
      ciudad: lugar.ciudad,
    }));
  }

  function encontrarLugarCercanoOffline(lat, lng) {
    let mejor = null;
    let menorDist = Infinity;
    for (const lugar of LUGARES_LOCALES_OFFLINE) {
      const d = distanciaKm(lat, lng, lugar.lat, lugar.lng);
      if (d < menorDist) {
        menorDist = d;
        mejor = lugar;
      }
    }
    if (mejor && menorDist <= 12) {
      return {
        texto: `Sector ${mejor.nombre}, ${mejor.ciudad}`,
        ciudad: mejor.ciudad,
      };
    }
    return {
      texto: `Ubicación (${lat.toFixed(5)}, ${lng.toFixed(5)})`,
      ciudad: "",
    };
  }

  function crearCapaConCacheOffline() {
    const OfflineTileLayer = window.L.TileLayer.extend({
      createTile: function (coords, done) {
        const tile = document.createElement("img");
        tile.alt = "";
        tile.setAttribute("role", "presentation");
        const url = this.getTileUrl(coords);

        const usarFallback = function () {
          tile.src = OFFLINE_TILE_SVG;
          done(null, tile);
        };

        if (!("caches" in window)) {
          tile.onload = function () { done(null, tile); };
          tile.onerror = usarFallback;
          tile.src = navigator.onLine ? url : OFFLINE_TILE_SVG;
          return tile;
        }

        caches
          .open(TILE_CACHE_NAME)
          .then(function (cache) {
            return cache.match(url).then(function (cachedResp) {
              if (cachedResp) {
                return cachedResp.blob().then(function (blob) {
                  const objUrl = URL.createObjectURL(blob);
                  tile.onload = function () {
                    URL.revokeObjectURL(objUrl);
                    done(null, tile);
                  };
                  tile.onerror = usarFallback;
                  tile.src = objUrl;
                });
              }
              if (!navigator.onLine) {
                usarFallback();
                return;
              }
              return fetch(url, { mode: "cors" })
                .then(function (netResp) {
                  if (!netResp || !netResp.ok) {
                    usarFallback();
                    return;
                  }
                  cache.put(url, netResp.clone()).catch(function () {});
                  return netResp.blob().then(function (blob) {
                    const objUrl = URL.createObjectURL(blob);
                    tile.onload = function () {
                      URL.revokeObjectURL(objUrl);
                      done(null, tile);
                    };
                    tile.onerror = usarFallback;
                    tile.src = objUrl;
                  });
                })
                .catch(usarFallback);
            });
          })
          .catch(usarFallback);

        return tile;
      },
    });

    return new OfflineTileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
      maxZoom: 19,
      crossOrigin: true,
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    const modalEl = document.getElementById("modalMapa");
    const inputDireccion = document.getElementById("input-direccion");
    const inputLat = document.getElementById("input-latitud");
    const inputLng = document.getElementById("input-longitud");
    const selectCiudad = document.getElementById("select-ciudad");
    const buscadorInput = document.getElementById("buscador-mapa");
    const sugerenciasEl = document.getElementById("mapa-sugerencias");
    const btnBuscar = document.getElementById("btn-buscar-mapa");
    const btnMiUbicacion = document.getElementById("btn-mi-ubicacion");
    const btnConfirmar = document.getElementById("btn-confirmar-ubicacion");
    const previewEl = document.getElementById("preview-direccion");
    const previewEditInput = document.getElementById("mapa-direccion-editable");
    const complementoInput = document.getElementById("mapa-complemento");
    const previewMapsLink = document.getElementById("preview-gmaps-link");
    const badgeConfirmado = document.getElementById("direccion-mapa-badge");
    const badgeMapsLink = document.getElementById("direccion-gmaps-link");
    const modoBadge = document.getElementById("mapa-modo-badge");

    if (!modalEl || !inputDireccion) return;

    let mapa = null;
    let marcador = null;
    let latActual = 5.8245;
    let lngActual = -73.0341;
    let debounceTimer = null;
    let searchAbort = null;

    function actualizarBadgeConexion() {
      if (!modoBadge) return;
      if (navigator.onLine) {
        modoBadge.style.background = "rgba(16,185,129,0.16)";
        modoBadge.style.color = "#34d399";
        modoBadge.style.borderColor = "rgba(16,185,129,0.35)";
        modoBadge.innerHTML = '<i class="bi bi-wifi me-1"></i>En línea (con caché offline)';
      } else {
        modoBadge.style.background = "rgba(245,158,11,0.16)";
        modoBadge.style.color = "#fbbf24";
        modoBadge.style.borderColor = "rgba(245,158,11,0.4)";
        modoBadge.innerHTML = '<i class="bi bi-wifi-off me-1"></i>Modo Offline (Catálogo local)';
      }
    }

    window.addEventListener("online", actualizarBadgeConexion);
    window.addEventListener("offline", actualizarBadgeConexion);

    function obtenerCentroInicial() {
      if (inputLat && inputLng && inputLat.value && inputLng.value) {
        const parsedLat = parseFloat(inputLat.value);
        const parsedLng = parseFloat(inputLng.value);
        if (!Number.isNaN(parsedLat) && !Number.isNaN(parsedLng)) {
          return [parsedLat, parsedLng];
        }
      }
      if (selectCiudad && selectCiudad.value) {
        const clave = normalizarClave(selectCiudad.value);
        if (COORDENADAS_CIUDADES[clave]) {
          return COORDENADAS_CIUDADES[clave];
        }
      }
      return [5.8245, -73.0341];
    }

    function sincronizarCiudadSiAplica(ciudadDetectada) {
      if (!selectCiudad || !ciudadDetectada || selectCiudad.value) return;
      const target = normalizarClave(ciudadDetectada);
      for (const opt of selectCiudad.options) {
        if (opt.value && normalizarClave(opt.value) === target) {
          selectCiudad.value = opt.value;
          selectCiudad.dispatchEvent(new Event("change", { bubbles: true }));
          break;
        }
      }
    }

    function actualizarEnlaceMaps(lat, lng) {
      const url = `https://www.google.com/maps?q=${lat.toFixed(6)},${lng.toFixed(6)}`;
      if (previewMapsLink) {
        previewMapsLink.href = url;
        previewMapsLink.classList.remove("d-none");
      }
      return url;
    }

    function ocultarSugerencias() {
      if (sugerenciasEl) {
        sugerenciasEl.innerHTML = "";
        sugerenciasEl.classList.add("d-none");
      }
    }

    function setDireccionDetectada(texto, coordsText) {
      const limpio = limpiarDireccion(texto);
      if (previewEditInput) {
        previewEditInput.value = limpio;
      }
      if (previewEl) {
        previewEl.innerHTML = limpio
          ? `<i class="bi bi-geo-alt-fill text-warning me-1"></i><strong>Ubicación marcada:</strong> ${limpio}${coordsText ? ` <span class="text-muted">(${coordsText})</span>` : ""}`
          : '<i class="bi bi-info-circle text-warning me-1"></i>Haz clic en el mapa o arrastra el marcador hacia el punto exacto.';
      }
    }

    function construirDireccionDesdeNominatim(data) {
      if (!data) return { texto: "", ciudad: "" };
      const addr = data.address || {};
      const partes = [];

      const poi = addr.amenity || addr.shop || addr.building || addr.leisure || addr.tourism || "";
      const via = addr.road || addr.pedestrian || addr.footway || addr.path || addr.residential || "";
      const numero = addr.house_number ? ` #${addr.house_number}` : "";
      const barrio = addr.neighbourhood || addr.suburb || addr.quarter || addr.hamlet || addr.village || "";
      const ciudad = addr.city || addr.town || addr.municipality || addr.county || "";

      if (via) partes.push(`${via}${numero}`);
      if (barrio && !partes.some((p) => normalizarClave(p).includes(normalizarClave(barrio)))) {
        partes.push(/^barrio\b/i.test(barrio) ? barrio : `Barrio ${barrio}`);
      }
      if (poi && !partes.some((p) => normalizarClave(p).includes(normalizarClave(poi)))) {
        partes.push(poi);
      }

      let texto = partes.join(", ");
      if (!texto && data.display_name) {
        texto = data.display_name.split(",").slice(0, 3).join(", ");
      }
      return { texto: limpiarDireccion(texto), ciudad };
    }

    function formatearSugerenciaPhoton(feat) {
      const p = feat.properties || {};
      const nombre = p.name || "";
      const calle = p.street ? `${p.street}${p.housenumber ? " #" + p.housenumber : ""}` : "";
      const barrio = p.district || p.locality || "";
      const ciudad = p.city || p.county || "";
      const depto = p.state || "";

      const titulo = nombre || calle || barrio || ciudad || "Ubicación";
      const subPartes = [];
      if (calle && normalizarClave(calle) !== normalizarClave(titulo)) subPartes.push(calle);
      if (barrio && normalizarClave(barrio) !== normalizarClave(titulo)) subPartes.push(barrio);
      if (ciudad && normalizarClave(ciudad) !== normalizarClave(titulo)) subPartes.push(ciudad);
      if (depto) subPartes.push(depto);

      const dirPartes = [];
      if (calle) dirPartes.push(calle);
      if (nombre && normalizarClave(nombre) !== normalizarClave(calle) && normalizarClave(nombre) !== normalizarClave(ciudad)) {
        dirPartes.push(nombre);
      }
      if (barrio && !dirPartes.some((d) => normalizarClave(d).includes(normalizarClave(barrio)))) {
        dirPartes.push(/^barrio\b/i.test(barrio) ? barrio : `Barrio ${barrio}`);
      }

      return {
        lat: feat.geometry.coordinates[1],
        lng: feat.geometry.coordinates[0],
        titulo,
        subtitulo: subPartes.join(" · "),
        direccion: limpiarDireccion(dirPartes.join(", ") || titulo),
        ciudad,
      };
    }

    async function obtenerDireccionDesdeCoordenadas(lat, lng, etiquetaPreferida) {
      latActual = lat;
      lngActual = lng;
      actualizarEnlaceMaps(lat, lng);

      // Si estamos offline, resolver inmediatamente con el catálogo local de Boyacá
      if (!navigator.onLine) {
        const cercano = encontrarLugarCercanoOffline(lat, lng);
        sincronizarCiudadSiAplica(cercano.ciudad);
        setDireccionDetectada(etiquetaPreferida || cercano.texto, `${lat.toFixed(4)}, ${lng.toFixed(4)}`);
        return;
      }

      if (previewEl) {
        previewEl.innerHTML =
          '<span class="spinner-border spinner-border-sm text-warning me-2"></span>Consultando dirección exacta...';
      }

      try {
        const res = await fetch(
          `https://nominatim.openstreetmap.org/reverse?format=json&lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lng)}&zoom=18&addressdetails=1&accept-language=es`,
          { headers: { Accept: "application/json" } }
        );
        const data = await res.json();
        const { texto, ciudad } = construirDireccionDesdeNominatim(data);
        sincronizarCiudadSiAplica(ciudad);

        let finalTexto = texto;
        if (etiquetaPreferida && finalTexto && !normalizarClave(finalTexto).includes(normalizarClave(etiquetaPreferida))) {
          finalTexto = limpiarDireccion(`${etiquetaPreferida}, ${finalTexto}`);
        } else if (!finalTexto && etiquetaPreferida) {
          finalTexto = limpiarDireccion(etiquetaPreferida);
        }

        if (finalTexto) {
          setDireccionDetectada(finalTexto, `${lat.toFixed(4)}, ${lng.toFixed(4)}`);
        } else {
          const cercano = encontrarLugarCercanoOffline(lat, lng);
          setDireccionDetectada(cercano.texto, `${lat.toFixed(4)}, ${lng.toFixed(4)}`);
        }
      } catch (_err) {
        const cercano = encontrarLugarCercanoOffline(lat, lng);
        sincronizarCiudadSiAplica(cercano.ciudad);
        setDireccionDetectada(etiquetaPreferida || cercano.texto, `${lat.toFixed(4)}, ${lng.toFixed(4)}`);
      }
    }

    function renderizarSugerencias(items) {
      if (!sugerenciasEl) return;
      if (!items || items.length === 0) {
        sugerenciasEl.innerHTML =
          '<div class="ct-map-suggestion ct-map-suggestion--empty"><i class="bi bi-search me-2"></i>No encontramos coincidencias. Prueba con otro barrio/calle o haz clic directo en el mapa.</div>';
        sugerenciasEl.classList.remove("d-none");
        return;
      }

      sugerenciasEl.innerHTML = "";
      items.forEach(function (item) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "ct-map-suggestion";
        btn.innerHTML = `
          <i class="bi bi-geo-alt-fill ct-map-suggestion__icon"></i>
          <div class="ct-map-suggestion__body">
            <div class="ct-map-suggestion__title"></div>
            <div class="ct-map-suggestion__sub"></div>
          </div>
        `;
        btn.querySelector(".ct-map-suggestion__title").textContent = item.titulo;
        btn.querySelector(".ct-map-suggestion__sub").textContent = item.subtitulo || "Boyacá, Colombia";
        btn.addEventListener("click", function () {
          ocultarSugerencias();
          if (buscadorInput) buscadorInput.value = item.titulo;
          if (mapa && marcador) {
            mapa.setView([item.lat, item.lng], 16);
            marcador.setLatLng([item.lat, item.lng]);
          }
          sincronizarCiudadSiAplica(item.ciudad);
          obtenerDireccionDesdeCoordenadas(item.lat, item.lng, item.direccion);
        });
        sugerenciasEl.appendChild(btn);
      });
      sugerenciasEl.classList.remove("d-none");
    }

    async function buscarLugares(queryRaw, autoSelectFirst) {
      const q = (queryRaw || "").trim();
      if (!q || q.length < 2) {
        ocultarSugerencias();
        return;
      }

      // 1. Coordenadas directas o enlace de Google Maps
      const coords = extraerCoordenadasDeTexto(q);
      if (coords && mapa && marcador) {
        ocultarSugerencias();
        mapa.setView(coords, 17);
        marcador.setLatLng(coords);
        await obtenerDireccionDesdeCoordenadas(coords[0], coords[1]);
        return;
      }

      const ciudadSel = selectCiudad && selectCiudad.value ? selectCiudad.value.trim() : "";
      const locales = buscarEnCatalogoLocal(q, ciudadSel);

      // 2. Modo offline: usar inmediatamente el catálogo local difuso de Boyacá
      if (!navigator.onLine) {
        if (autoSelectFirst && locales.length > 0) {
          ocultarSugerencias();
          const top = locales[0];
          if (mapa && marcador) {
            mapa.setView([top.lat, top.lng], 16);
            marcador.setLatLng([top.lat, top.lng]);
          }
          sincronizarCiudadSiAplica(top.ciudad);
          await obtenerDireccionDesdeCoordenadas(top.lat, top.lng, top.direccion);
        } else {
          renderizarSugerencias(locales);
        }
        return;
      }

      if (searchAbort) searchAbort.abort();
      searchAbort = new AbortController();

      const [biasLat, biasLng] = obtenerCentroInicial();
      const queryBias =
        ciudadSel && !normalizarClave(q).includes(normalizarClave(ciudadSel))
          ? `${q} ${ciudadSel}`
          : q;

      if (autoSelectFirst && btnBuscar) {
        btnBuscar.disabled = true;
        btnBuscar.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
      }

      let remotos = [];
      try {
        const photonUrl = `https://photon.komoot.io/api/?q=${encodeURIComponent(queryBias)}&lat=${biasLat}&lon=${biasLng}&limit=5&lang=default`;
        const pRes = await fetch(photonUrl, { signal: searchAbort.signal });
        if (pRes.ok) {
          const pData = await pRes.json();
          const feats = (pData.features || []).filter(function (f) {
            const cc = (f.properties && f.properties.countrycode) || "";
            return !cc || cc.toUpperCase() === "CO";
          });
          remotos = feats.map(formatearSugerenciaPhoton);
        }

        if (remotos.length === 0) {
          const nomQ =
            ciudadSel && !normalizarClave(q).includes(normalizarClave(ciudadSel))
              ? `${q}, ${ciudadSel}, Boyacá, Colombia`
              : `${q}, Colombia`;
          const nRes = await fetch(
            `https://nominatim.openstreetmap.org/search?format=json&limit=4&countrycodes=co&addressdetails=1&accept-language=es&q=${encodeURIComponent(nomQ)}`,
            { signal: searchAbort.signal, headers: { Accept: "application/json" } }
          );
          if (nRes.ok) {
            const nData = await nRes.json();
            remotos = (nData || []).map(function (lugar) {
              const info = construirDireccionDesdeNominatim(lugar);
              const partes = (lugar.display_name || "").split(",");
              return {
                lat: parseFloat(lugar.lat),
                lng: parseFloat(lugar.lon),
                titulo: partes[0] ? partes[0].trim() : info.texto,
                subtitulo: partes.slice(1, 4).join(",").trim(),
                direccion: info.texto || (partes[0] || "").trim(),
                ciudad: info.ciudad,
              };
            });
          }
        }
      } catch (err) {
        if (err && err.name === "AbortError") return;
      } finally {
        if (autoSelectFirst && btnBuscar) {
          btnBuscar.disabled = false;
          btnBuscar.innerHTML = '<i class="bi bi-search me-1"></i> Buscar';
        }
      }

      // Combinar resultados locales (alta precisión en Boyacá + tolerancia a typos) + remotos sin duplicados
      const combinados = [];
      const vistos = new Set();
      [...locales, ...remotos].forEach(function (it) {
        const key = normalizarClave(`${it.titulo}|${it.ciudad}`);
        if (!vistos.has(key)) {
          vistos.add(key);
          combinados.push(it);
        }
      });

      if (autoSelectFirst && combinados.length > 0) {
        ocultarSugerencias();
        const top = combinados[0];
        if (mapa && marcador) {
          mapa.setView([top.lat, top.lng], 16);
          marcador.setLatLng([top.lat, top.lng]);
        }
        sincronizarCiudadSiAplica(top.ciudad);
        await obtenerDireccionDesdeCoordenadas(top.lat, top.lng, top.direccion);
      } else {
        renderizarSugerencias(combinados.slice(0, 7));
      }
    }

    modalEl.addEventListener("shown.bs.modal", function () {
      actualizarBadgeConexion();
      if (typeof window.L === "undefined") {
        if (previewEl) {
          previewEl.textContent = "No se pudo inicializar el visor del mapa.";
        }
        return;
      }

      const [cLat, cLng] = obtenerCentroInicial();
      latActual = cLat;
      lngActual = cLng;

      if (!mapa) {
        mapa = window.L.map("mapa-selector").setView([cLat, cLng], 15);
        crearCapaConCacheOffline().addTo(mapa);

        marcador = window.L.marker([cLat, cLng], { draggable: true }).addTo(mapa);

        marcador.on("dragend", function () {
          const pos = marcador.getLatLng();
          obtenerDireccionDesdeCoordenadas(pos.lat, pos.lng);
        });

        mapa.on("click", function (e) {
          ocultarSugerencias();
          marcador.setLatLng(e.latlng);
          obtenerDireccionDesdeCoordenadas(e.latlng.lat, e.latlng.lng);
        });
      } else {
        mapa.setView([cLat, cLng], 15);
        marcador.setLatLng([cLat, cLng]);
        setTimeout(function () {
          mapa.invalidateSize();
        }, 120);
      }

      if (previewEditInput && !previewEditInput.value && inputDireccion.value.trim()) {
        previewEditInput.value = inputDireccion.value.trim();
      }
      actualizarEnlaceMaps(cLat, cLng);
      if (buscadorInput) buscadorInput.focus();
    });

    if (buscadorInput) {
      buscadorInput.addEventListener("input", function () {
        clearTimeout(debounceTimer);
        const val = buscadorInput.value.trim();
        if (val.length < 2) {
          ocultarSugerencias();
          return;
        }
        debounceTimer = setTimeout(function () {
          buscarLugares(val, false);
        }, 250);
      });

      buscadorInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
          e.preventDefault();
          clearTimeout(debounceTimer);
          buscarLugares(buscadorInput.value, true);
        } else if (e.key === "Escape") {
          ocultarSugerencias();
        }
      });
    }

    if (btnBuscar) {
      btnBuscar.addEventListener("click", function () {
        clearTimeout(debounceTimer);
        buscarLugares(buscadorInput ? buscadorInput.value : "", true);
      });
    }

    modalEl.addEventListener("click", function (e) {
      if (
        sugerenciasEl &&
        !sugerenciasEl.contains(e.target) &&
        e.target !== buscadorInput &&
        e.target !== btnBuscar
      ) {
        ocultarSugerencias();
      }
    });

    if (btnMiUbicacion) {
      btnMiUbicacion.addEventListener("click", function () {
        if (!navigator.geolocation) {
          if (previewEl) previewEl.textContent = "Tu navegador no soporta geolocalización.";
          return;
        }
        btnMiUbicacion.disabled = true;
        navigator.geolocation.getCurrentPosition(
          function (pos) {
            const lat = pos.coords.latitude;
            const lng = pos.coords.longitude;
            if (mapa && marcador) {
              mapa.setView([lat, lng], 17);
              marcador.setLatLng([lat, lng]);
              obtenerDireccionDesdeCoordenadas(lat, lng);
            }
            btnMiUbicacion.disabled = false;
          },
          function () {
            if (previewEl) {
              previewEl.textContent =
                "No se pudo obtener tu ubicación actual. Permite el acceso al GPS o selecciona un punto en el mapa.";
            }
            btnMiUbicacion.disabled = false;
          },
          { enableHighAccuracy: true, timeout: 8000 }
        );
      });
    }

    if (btnConfirmar) {
      btnConfirmar.addEventListener("click", function () {
        const base = (previewEditInput ? previewEditInput.value : "").trim();
        const extra = (complementoInput ? complementoInput.value : "").trim();
        let direccionFinal = base || `Ubicación ${latActual.toFixed(5)}, ${lngActual.toFixed(5)}`;
        if (extra) {
          direccionFinal = `${direccionFinal}, ${extra}`;
        }
        direccionFinal = limpiarDireccion(direccionFinal);

        inputDireccion.value = direccionFinal;
        inputDireccion.dispatchEvent(new Event("input", { bubbles: true }));
        inputDireccion.dispatchEvent(new Event("change", { bubbles: true }));

        if (inputLat) inputLat.value = latActual.toFixed(6);
        if (inputLng) inputLng.value = lngActual.toFixed(6);

        const gmapsUrl = `https://www.google.com/maps?q=${latActual.toFixed(6)},${lngActual.toFixed(6)}`;
        if (badgeConfirmado && badgeMapsLink) {
          badgeMapsLink.href = gmapsUrl;
          badgeConfirmado.classList.remove("d-none");
        }
      });
    }
  });
})();
