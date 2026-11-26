/**
 * conductor-ruta.js
 * Navegador de ruta estilo Google Maps para Conductores de Constru-Trans:
 * - Leaflet local + CacheStorage de mosaicos OSM + cuadrícula SVG offline.
 * - Trazado de ruta real por carretera con OSRM (gratuito, sin API key) + indicaciones paso a paso en español.
 * - Origen automático desde GPS del conductor o Bodega Constru-Trans (Duitama).
 * - Botones directos a Google Maps y Waze con destino exacto.
 */
(function () {
  "use strict";

  const TILE_CACHE_NAME = "constru-trans-map-tiles-v1";
  const BODEGA_DEFAULT = { lat: 5.8245, lng: -73.0341, label: "Bodega Constru-Trans (Duitama)" };

  const CIUDADES_COORDS = {
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
    aquitania: [5.5206, -72.8856],
    mongui: [5.7222, -72.8492],
    bogota: [4.711, -74.0721],
  };

  const OFFLINE_TILE_SVG =
    "data:image/svg+xml;charset=utf-8," +
    encodeURIComponent(
      '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256">' +
        '<rect width="256" height="256" fill="#0f172a"/>' +
        '<path d="M 64 0 V 256 M 128 0 V 256 M 192 0 V 256 M 0 64 H 256 M 0 128 H 256 M 0 192 H 256" stroke="#1e293b" stroke-width="1"/>' +
        '<text x="128" y="132" text-anchor="middle" fill="#475569" font-family="sans-serif" font-size="11" font-weight="600">Mapa Offline</text>' +
        "</svg>"
    );

  function norm(s) {
    return (s || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .trim();
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

  function formatearDistancia(metros) {
    if (metros >= 1000) return `${(metros / 1000).toFixed(1)} km`;
    return `${Math.round(metros)} m`;
  }

  function formatearDuracion(segundos) {
    const mins = Math.max(1, Math.round(segundos / 60));
    if (mins >= 60) {
      const h = Math.floor(mins / 60);
      const m = mins % 60;
      return m > 0 ? `${h} h ${m} min` : `${h} h`;
    }
    return `${mins} min`;
  }

  function traducirManiobra(step) {
    const m = step.maneuver || {};
    const type = m.type || "";
    const mod = m.modifier || "";
    const calle = step.name ? ` por ${step.name}` : "";

    const modMap = {
      left: "a la izquierda",
      right: "a la derecha",
      "slight left": "levemente a la izquierda",
      "slight right": "levemente a la derecha",
      "sharp left": "cerrado a la izquierda",
      "sharp right": "cerrado a la derecha",
      uturn: "en U",
      straight: "recto",
    };
    const dirTxt = modMap[mod] || "";

    let icono = "bi-arrow-up";
    if (mod.includes("left")) icono = "bi-arrow-90deg-left";
    else if (mod.includes("right")) icono = "bi-arrow-90deg-right";
    else if (type === "arrive") icono = "bi-geo-alt-fill";
    else if (type === "depart") icono = "bi-play-fill";
    else if (type === "roundabout" || type === "rotary") icono = "bi-arrow-repeat";

    let texto = "";
    if (type === "depart") {
      texto = `Inicia el recorrido${calle || " hacia la vía principal"}`;
    } else if (type === "arrive") {
      texto = `Has llegado al destino${calle}`;
    } else if (type === "roundabout" || type === "rotary") {
      const exit = m.exit ? ` toma la salida ${m.exit}` : " continúa";
      texto = `En la glorieta,${exit}${calle}`;
    } else if (type === "merge") {
      texto = `Incorpórate${dirTxt ? " " + dirTxt : ""}${calle}`;
    } else if (dirTxt && dirTxt !== "recto") {
      texto = `Gira ${dirTxt}${calle}`;
    } else {
      texto = `Continúa recto${calle}`;
    }

    return { texto, icono, distancia: formatearDistancia(step.distance || 0) };
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
            return cache.match(url).then(function (cached) {
              if (cached) {
                return cached.blob().then(function (blob) {
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
                .then(function (resp) {
                  if (!resp || !resp.ok) {
                    usarFallback();
                    return;
                  }
                  cache.put(url, resp.clone()).catch(function () {});
                  return resp.blob().then(function (blob) {
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

  async function geocodificarDestino(direccion, ciudad) {
    const dir = (direccion || "").trim();
    const ciu = (ciudad || "").trim();

    // ¿Ya trae coordenadas explícitas?
    const coordMatch = dir.match(/(-?\d{1,2}\.\d{3,})\s*[, ]\s*(-?\d{1,3}\.\d{3,})/);
    if (coordMatch) {
      return { lat: parseFloat(coordMatch[1]), lng: parseFloat(coordMatch[2]), aproximado: false };
    }

    const ciudadFallback = CIUDADES_COORDS[norm(ciu)] || CIUDADES_COORDS.duitama;

    if (!navigator.onLine || !dir) {
      return { lat: ciudadFallback[0], lng: ciudadFallback[1], aproximado: true };
    }

    const query = ciu && !norm(dir).includes(norm(ciu)) ? `${dir}, ${ciu}, Boyacá, Colombia` : `${dir}, Colombia`;

    try {
      const pUrl = `https://photon.komoot.io/api/?q=${encodeURIComponent(query)}&lat=${ciudadFallback[0]}&lon=${ciudadFallback[1]}&limit=1`;
      const pRes = await fetch(pUrl);
      if (pRes.ok) {
        const pData = await pRes.json();
        if (pData.features && pData.features.length > 0) {
          const [lng, lat] = pData.features[0].geometry.coordinates;
          return { lat, lng, aproximado: false };
        }
      }
    } catch (_e) {}

    try {
      const nUrl = `https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=co&q=${encodeURIComponent(query)}`;
      const nRes = await fetch(nUrl, { headers: { Accept: "application/json" } });
      if (nRes.ok) {
        const nData = await nRes.json();
        if (nData && nData.length > 0) {
          return { lat: parseFloat(nData[0].lat), lng: parseFloat(nData[0].lon), aproximado: false };
        }
      }
    } catch (_e) {}

    return { lat: ciudadFallback[0], lng: ciudadFallback[1], aproximado: true };
  }

  function crearPinIcon(clase, iconoBootstrap) {
    return window.L.divIcon({
      className: "ct-route-divicon",
      html: `<div class="ct-route-pin ${clase}"><i class="bi ${iconoBootstrap}"></i></div>`,
      iconSize: [34, 34],
      iconAnchor: [17, 17],
    });
  }

  function inicializarNavegadorRuta(container) {
    if (!container || typeof window.L === "undefined") return null;

    const mapEl = container.querySelector("[data-route-map]");
    const etaTimeEl = container.querySelector("[data-route-time]");
    const etaDistEl = container.querySelector("[data-route-dist]");
    const statusEl = container.querySelector("[data-route-status]");
    const stepsEl = container.querySelector("[data-route-steps]");
    const btnGps = container.querySelector("[data-route-gps]");
    const linkGmaps = container.querySelector("[data-route-gmaps]");
    const linkWaze = container.querySelector("[data-route-waze]");
    const destLabelEl = container.querySelector("[data-route-dest-label]");

    if (!mapEl) return null;

    let mapa = null;
    let origenMarker = null;
    let destinoMarker = null;
    let rutaLayer = null;
    let origenActual = { ...BODEGA_DEFAULT };
    let destinoActual = null;
    let direccionActual = container.dataset.direccion || "";
    let ciudadActual = container.dataset.ciudad || "";

    function ensureMap(lat, lng) {
      if (!mapa) {
        mapa = window.L.map(mapEl).setView([lat, lng], 14);
        crearCapaConCacheOffline().addTo(mapa);
      } else {
        setTimeout(() => mapa.invalidateSize(), 120);
      }
    }

    function actualizarBotonesExternos() {
      if (!destinoActual) return;
      const destParam = destinoActual.aproximado && direccionActual
        ? encodeURIComponent(`${direccionActual}${ciudadActual ? ", " + ciudadActual : ""}, Boyacá, Colombia`)
        : `${destinoActual.lat.toFixed(6)},${destinoActual.lng.toFixed(6)}`;

      if (linkGmaps) {
        linkGmaps.href = `https://www.google.com/maps/dir/?api=1&destination=${destParam}&travelmode=driving`;
      }
      if (linkWaze) {
        linkWaze.href = `https://waze.com/ul?ll=${destinoActual.lat.toFixed(6)},${destinoActual.lng.toFixed(6)}&navigate=yes`;
      }
    }

    function renderizarPasos(pasos) {
      if (!stepsEl) return;
      stepsEl.innerHTML = "";
      pasos.forEach(function (p) {
        const li = document.createElement("li");
        li.className = "ct-route-step";
        li.innerHTML = `
          <span class="ct-route-step__icon"><i class="bi ${p.icono}"></i></span>
          <div>
            <div>${p.texto}</div>
            ${p.distancia ? `<span class="ct-route-step__dist">${p.distancia}</span>` : ""}
          </div>
        `;
        stepsEl.appendChild(li);
      });
    }

    async function trazarRuta() {
      if (!destinoActual) return;
      ensureMap(destinoActual.lat, destinoActual.lng);

      if (origenMarker) mapa.removeLayer(origenMarker);
      if (destinoMarker) mapa.removeLayer(destinoMarker);
      if (rutaLayer) mapa.removeLayer(rutaLayer);

      origenMarker = window.L.marker([origenActual.lat, origenActual.lng], {
        icon: crearPinIcon("ct-route-pin--origin", "bi-truck"),
      })
        .addTo(mapa)
        .bindPopup(`<strong>Origen:</strong> ${origenActual.label}`);

      destinoMarker = window.L.marker([destinoActual.lat, destinoActual.lng], {
        icon: crearPinIcon("ct-route-pin--dest", "bi-geo-alt-fill"),
      })
        .addTo(mapa)
        .bindPopup(`<strong>Destino:</strong> ${direccionActual || "Entrega"}`);

      actualizarBotonesExternos();

      // Intentar trazado real por carretera con OSRM si hay conexión
      if (navigator.onLine) {
        if (statusEl) statusEl.textContent = "Calculando ruta óptima...";
        try {
          const osrmUrl = `https://router.project-osrm.org/route/v1/driving/${origenActual.lng},${origenActual.lat};${destinoActual.lng},${destinoActual.lat}?overview=full&geometries=geojson&steps=true`;
          const res = await fetch(osrmUrl);
          if (res.ok) {
            const data = await res.json();
            if (data.routes && data.routes.length > 0) {
              const route = data.routes[0];
              const latlngs = route.geometry.coordinates.map(([lng, lat]) => [lat, lng]);
              rutaLayer = window.L.polyline(latlngs, {
                color: "#3b82f6",
                weight: 6,
                opacity: 0.9,
                lineJoin: "round",
              }).addTo(mapa);

              mapa.fitBounds(rutaLayer.getBounds(), { padding: [36, 36] });

              if (etaTimeEl) etaTimeEl.textContent = formatearDuracion(route.duration);
              if (etaDistEl) etaDistEl.textContent = formatearDistancia(route.distance);
              if (statusEl) {
                statusEl.textContent = destinoActual.aproximado
                  ? "Ruta calculada (destino aproximado por ciudad)"
                  : "Ruta en tiempo real";
              }

              const steps = [];
              (route.legs || []).forEach((leg) => {
                (leg.steps || []).forEach((st) => {
                  steps.push(traducirManiobra(st));
                });
              });
              renderizarPasos(
                steps.length
                  ? steps
                  : [{ icono: "bi-geo-alt-fill", texto: `Dirígete hacia ${direccionActual}`, distancia: formatearDistancia(route.distance) }]
              );
              return;
            }
          }
        } catch (_e) {}
      }

      // Respaldo offline / sin OSRM: línea directa + estimación aproximada
      const dKm = distanciaKm(origenActual.lat, origenActual.lng, destinoActual.lat, destinoActual.lng);
      const minsEst = Math.max(3, Math.round((dKm / 35) * 60));
      rutaLayer = window.L.polyline(
        [
          [origenActual.lat, origenActual.lng],
          [destinoActual.lat, destinoActual.lng],
        ],
        { color: "#f59e0b", weight: 4, dashArray: "8 8", opacity: 0.9 }
      ).addTo(mapa);

      mapa.fitBounds(rutaLayer.getBounds(), { padding: [40, 40] });
      if (etaTimeEl) etaTimeEl.textContent = `~${minsEst} min`;
      if (etaDistEl) etaDistEl.textContent = `${dKm.toFixed(1)} km`;
      if (statusEl) statusEl.textContent = navigator.onLine ? "Ruta directa estimada" : "Modo Offline (ruta directa)";

      renderizarPasos([
        { icono: "bi-truck", texto: `Salida desde ${origenActual.label}`, distancia: "" },
        {
          icono: "bi-geo-alt-fill",
          texto: `Destino: ${direccionActual}${ciudadActual ? " (" + ciudadActual + ")" : ""}`,
          distancia: `Distancia directa: ${dKm.toFixed(1)} km`,
        },
      ]);
    }

    async function cargarRuta(direccion, ciudad) {
      direccionActual = direccion || direccionActual;
      ciudadActual = ciudad || ciudadActual;
      if (destLabelEl) {
        destLabelEl.textContent = `${direccionActual}${ciudadActual ? " · " + ciudadActual : ""}`;
      }
      if (statusEl) statusEl.textContent = "Ubicando destino...";
      destinoActual = await geocodificarDestino(direccionActual, ciudadActual);
      await trazarRuta();
    }

    if (btnGps) {
      btnGps.addEventListener("click", function () {
        if (!navigator.geolocation) {
          if (statusEl) statusEl.textContent = "GPS no disponible en este navegador.";
          return;
        }
        btnGps.disabled = true;
        if (statusEl) statusEl.textContent = "Obteniendo tu ubicación GPS...";
        navigator.geolocation.getCurrentPosition(
          function (pos) {
            origenActual = {
              lat: pos.coords.latitude,
              lng: pos.coords.longitude,
              label: "Mi ubicación actual (GPS)",
            };
            trazarRuta();
            btnGps.disabled = false;
          },
          function () {
            if (statusEl) statusEl.textContent = "No se pudo leer el GPS; usando Bodega Duitama.";
            btnGps.disabled = false;
          },
          { enableHighAccuracy: true, timeout: 8000 }
        );
      });
    }

    return {
      cargarRuta,
      invalidate: function () {
        if (mapa) setTimeout(() => mapa.invalidateSize(), 150);
      },
    };
  }

  document.addEventListener("DOMContentLoaded", function () {
    // 1. Mapa embebido en detalle_entrega_conductor.html
    const embedded = document.getElementById("ct-conductor-route-card");
    if (embedded) {
      const nav = inicializarNavegadorRuta(embedded);
      if (nav) {
        nav.cargarRuta(embedded.dataset.direccion, embedded.dataset.ciudad);
      }
    }

    // 2. Modal reutilizable "Cómo llegar" en pedidos_conductor.html
    const modalEl = document.getElementById("modalRutaConductor");
    if (modalEl) {
      const navModal = inicializarNavegadorRuta(modalEl);
      let pendienteDir = "";
      let pendienteCiudad = "";

      document.querySelectorAll(".ct-btn-como-llegar").forEach(function (btn) {
        btn.addEventListener("click", function () {
          pendienteDir = btn.dataset.direccion || "";
          pendienteCiudad = btn.dataset.ciudad || "";
          const tituloEl = modalEl.querySelector("[data-route-modal-title]");
          if (tituloEl && btn.dataset.pedido) {
            tituloEl.textContent = `Cómo llegar · Pedido #CT-${btn.dataset.pedido}`;
          }
        });
      });

      modalEl.addEventListener("shown.bs.modal", function () {
        if (navModal) {
          navModal.cargarRuta(pendienteDir, pendienteCiudad);
          navModal.invalidate();
        }
      });
    }
  });
})();
