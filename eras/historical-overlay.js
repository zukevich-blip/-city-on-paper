/* City on Paper: research-only overlay of a 2D historic map, not lithograph perspective.
 * Map: Library of Congress 2012586603; GCPs are not independently verified.
 */
"use strict";
window.HistoricalOverlay = (() => {
  const GEO_URL = "data/paris-1878-research-overlay.json";
  const IGN_WMTS = "https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0" +
    "&LAYER=ORTHOIMAGERY.ORTHOPHOTOS&STYLE=normal&TILEMATRIXSET=PM" +
    "&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&FORMAT=image/jpeg";
  const IGN_CREDIT = 'Ортофото: © <a href="https://www.ign.fr/" target="_blank" rel="noopener">IGN</a>, ' +
    '<a href="https://www.data.gouv.fr/datasets/bd-ortho-r" target="_blank" rel="noopener">' +
    "BD ORTHO (Licence Ouverte 2.0)</a>";
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

  function geographicPixel(px, py, data) {
    const m = data.model, rad = Math.PI / 180;
    const u = px / data.image_width;
    const v = py / data.image_height * data.source_image_height / data.source_image_width;
    const e = m.coef_x_east_m[0] + m.coef_x_east_m[1] * u + m.coef_x_east_m[2] * v;
    const n = m.coef_y_north_m[0] + m.coef_y_north_m[1] * u + m.coef_y_north_m[2] * v;
    return [m.lat0 + n / (m.earth_radius_m * rad),
      m.lon0 + e / (m.earth_radius_m * Math.cos(m.lat0 * rad) * rad)];
  }

  function maskCss(data) {
    if (!data.mask_pixel_polygon || data.mask_pixel_polygon.length < 3) return "none";
    return "polygon(" + data.mask_pixel_polygon.map(([x, y]) =>
      (x * 100 / data.source_image_width).toFixed(4) + "% " +
      (y * 100 / data.source_image_height).toFixed(4) + "%").join(",") + ")";
  }

  function makeAffineLayer(data) {
    return L.Layer.extend({
      initialize() { this._data = data; this._pending = null; },
      onAdd(map) {
        this._map = map;
        const img = L.DomUtil.create("img", "cop-paris-affine", map.getPanes().overlayPane);
        img.src = data.image;
        img.alt = "Исследовательский план Парижа 1878 года, геопривязка приблизительная";
        img.draggable = false;
        img.setAttribute("aria-hidden", "true");
        img.style.position = "absolute";
        img.style.top = "0";
        img.style.left = "0";
        img.style.width = data.image_width + "px";
        img.style.height = data.image_height + "px";
        img.style.maxWidth = "none";
        img.style.pointerEvents = "none";
        img.style.transformOrigin = "0 0";
        img.style.opacity = "0.55";
        img.style.clipPath = maskCss(data);
        this._img = img;
        this._schedule = () => {
          if (this._pending !== null) return;
          this._pending = requestAnimationFrame(() => {
            this._pending = null;
            if (this._map && this._img) this._redraw();
          });
        };
        map.on("zoom move viewreset resize", this._schedule);
        this._redraw();
      },
      onRemove(map) {
        map.off("zoom move viewreset resize", this._schedule);
        if (this._pending !== null) cancelAnimationFrame(this._pending);
        if (this._img) this._img.remove();
        this._pending = null;
        this._img = null;
        this._map = null;
      },
      setOpacity(value) { if (this._img) this._img.style.opacity = String(value); },
      _redraw() {
        const w = data.image_width, h = data.image_height, map = this._map;
        const p0 = map.latLngToLayerPoint(geographicPixel(0, 0, data));
        const px = map.latLngToLayerPoint(geographicPixel(w, 0, data));
        const py = map.latLngToLayerPoint(geographicPixel(0, h, data));
        const a = (px.x - p0.x) / w, b = (px.y - p0.y) / w;
        const c = (py.x - p0.x) / h, d = (py.y - p0.y) / h;
        this._img.style.transform = "matrix(" + [a, b, c, d, p0.x, p0.y].join(",") + ")";
      },
    });
  }

  async function mount(map, streetLayer, cityId) {
    const root = document.getElementById("parisResearch");
    if (!root || typeof L === "undefined") return;
    const base = root.querySelector("#parisBase");
    const toggle = root.querySelector("#paris1878Toggle");
    const opacity = root.querySelector("#paris1878Opacity");
    const opacityBox = root.querySelector("#parisOpacityBox");
    const status = root.querySelector("#parisResearchStatus");
    toggle.disabled = true;

    const ortho = L.tileLayer(IGN_WMTS, { tileSize: 256, maxZoom: 19, maxNativeZoom: 19,
      attribution: IGN_CREDIT });
    let errors = 0;
    ortho.on("tileerror", () => {
      errors++;
      if (errors >= 5 && map.hasLayer(ortho)) {
        map.removeLayer(ortho);
        if (!map.hasLayer(streetLayer)) streetLayer.addTo(map);
        base.value = "street";
        status.textContent = "Аэрофотосъёмка IGN недоступна; показана обычная карта.";
      }
    });
    base.addEventListener("change", () => {
      if (base.value === "ign") {
        errors = 0;
        map.removeLayer(streetLayer);
        ortho.addTo(map);
        status.textContent = "IGN BD ORTHO: год съёмки конкретного участка ещё не подтверждён.";
      } else {
        map.removeLayer(ortho);
        streetLayer.addTo(map);
        status.textContent = "Карта улиц. Исторические точки требуют отдельной проверки.";
      }
    });
    try {
      const response = await fetch(GEO_URL);
      if (!response.ok) throw new Error("HTTP " + response.status);
      const data = await response.json();
      if (data.city_id !== cityId || data.gcps.length !== 15 ||
          data.verification !== "manual_GCP_review_required") throw new Error("Неожиданные данные");
      if (!root.isConnected) return;
      const Layer = makeAffineLayer(data);
      const historic = new Layer();
      const markers = L.layerGroup(data.gcps.map((p) => {
        const circle = L.circleMarker([p.lat, p.lon], { radius: 5, color: "#6f4030",
          weight: 2, fillColor: "#f3d2ad", fillOpacity: 0.9 });
        const confidence = p.confidence === "high" ? "высокая" :
          p.confidence === "medium" ? "средняя" : "низкая";
        const popup = "<strong>" + esc(p.name) + "</strong><p>Опорная точка плана 1878 года. " +
          "Уверенность в выборе: " + confidence + ". Остаток модели: " +
          Number(p.residual_affine_m).toFixed(1) + " м.</p>" +
          "<p>Ручная проверка ещё не завершена. Это не точка съёмки Бенуа.</p>" +
          '<a href="' + esc(data.source_catalogue) +
          '" target="_blank" rel="noopener">Подлинник карты в LoC</a>';
        circle.bindPopup(popup);
        return circle;
      }));
      toggle.disabled = false;
      toggle.addEventListener("change", () => {
        if (toggle.checked) {
          historic.addTo(map);
          markers.addTo(map);
          historic.setOpacity(Number(opacity.value) / 100);
          opacityBox.hidden = false;
          status.textContent = "План 1878: исследовательская привязка по 15 точкам, RMS ≈26 м, не проверена вручную.";
        } else {
          map.removeLayer(historic);
          map.removeLayer(markers);
          opacityBox.hidden = true;
          status.textContent = "Исторический план скрыт.";
        }
      });
      opacity.addEventListener("input", () => historic.setOpacity(Number(opacity.value) / 100));
      status.textContent = "Слой 1878 доступен для исследования, но точки ещё не приняты экспертом.";
    } catch (_error) {
      toggle.disabled = true;
      status.textContent = "Данные исторического плана недоступны; современная карта работает.";
    }
  }
  return { mount, geographicPixel, IGN_WMTS };
})();