/* Атлас эпох v3: настоящие карты с зумом (Leaflet 1.9.4, BSD-2, вложен в vendor/).
 * 1) Старая карта Европы 1769 г. — плитки из копии LoC 4000 px (только масштабирование и нарезка).
 * 2) Современная карта (OpenStreetMap, © участники OSM) — те же города по координатам.
 * 3) Карта города: исторический план XIX в. (если есть открытый и привязанный) и современная карта
 *    с метками «где нарисовано» для работ, у которых место изображения установлено.
 * Кнопки «+ / −» в правом верхнем углу, щипок двумя пальцами, двойное касание. */
"use strict";
window.Maps = (() => {
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const OSM = ["https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    { maxZoom: 19, attribution: '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">участники OpenStreetMap</a>' }];
  const ok = () => typeof window.L !== "undefined";
  const cap = (t) => (t ? t.charAt(0).toUpperCase() + t.slice(1) : t);

  // Image map in CRS.Simple: pixel (x,y) of the native tile image <-> LatLng
  function imageMap(el, t, opts = {}) {
    const map = L.map(el, { crs: L.CRS.Simple, zoomControl: false, attributionControl: true, zoomSnap: 0.25,
      maxBoundsViscosity: 0.9, tap: true, ...opts });
    const z = t.max_zoom;
    const sw = map.unproject([0, t.height], z), ne = map.unproject([t.width, 0], z);
    const bounds = L.latLngBounds(sw, ne);
    L.tileLayer(`${t.tiles}/{z}/{x}/{y}.jpg`, { detectRetina: true, minZoom: -2, maxZoom: z + 2, maxNativeZoom: z, noWrap: true, bounds,
      tileSize: t.tile || 256, attribution: t.credit ? esc(t.credit) : "" }).addTo(map);
    L.control.zoom({ position: "topright", zoomInTitle: "Приблизить", zoomOutTitle: "Отдалить" }).addTo(map);
    map.fitBounds(bounds);
    map.setMinZoom(map.getZoom() - 0.5);
    map.setMaxBounds(bounds.pad(0.15));
    map.setMaxZoom(z + 2);
    homeButton(map, () => map.fitBounds(bounds));
    // Re-entering a country route replaces the map container; recalculate tile bounds
    // after layout settles so the old scan loads reliably on iPhone and desktop.
    requestAnimationFrame(() => requestAnimationFrame(() => {
      if (map.getContainer().isConnected) map.invalidateSize({ pan: false, animate: false });
    }));
    return { map, at: (x, y) => map.unproject([x, y], z), bounds };
  }
  function homeButton(map, fn) {
    const C = L.Control.extend({ options: { position: "topright" }, onAdd() {
      const b = L.DomUtil.create("button", "leaflet-bar mhome");
      b.type = "button"; b.title = "Показать всю карту"; b.setAttribute("aria-label", "Показать всю карту"); b.textContent = "⤢";
      L.DomEvent.disableClickPropagation(b); b.onclick = fn; return b; } });
    new C().addTo(map);
  }
  const labelClass = (map, el, base) => {
    const upd = () => { const d = map.getZoom() - base; el.classList.toggle("lz1", d >= 1.4); el.classList.toggle("lz2", d >= 2.9); };
    map.on("zoomend", upd); upd();
  };
  function cityIcon(c) {
    const cls = c.featured ? "featured" : c.benoist ? "benoist" : "other";
    return L.divIcon({ className: `mk dot ${cls}`, iconSize: [26, 26], iconAnchor: [13, 13],
      html: `<i></i><span>${esc(c.name)}</span>` });
  }
  function clusterCityMarkers(map, cities, pos) {
    const rows = cities.map((city) => ({ city, point: pos(city) }))
      .filter((r) => r.point && Number.isFinite(r.point.lat ?? r.point[0]) && Number.isFinite(r.point.lng ?? r.point[1]));
    const active = new Set(rows.map((r) => r.city.id));
    const layer = L.layerGroup().addTo(map);
    const visible = () => rows.filter((r) => active.has(r.city.id));
    function fit() {
      const list = visible(); if (!list.length) return false;
      if (list.length === 1) {
        map.setView(list[0].point, Math.min(map.getMaxZoom(), Math.max(map.getZoom(), map.options.crs === L.CRS.Simple ? 3 : 10)), { animate: false });
      } else {
        map.fitBounds(L.latLngBounds(list.map((r) => r.point)), {
          padding: [40, 40], maxZoom: map.options.crs === L.CRS.Simple ? 3 : 11, animate: false
        });
      }
      return true;
    }
    function render() {
      if (!map.getContainer().isConnected) return;
      layer.clearLayers();
      const zoom = map.getZoom();
      const gridSize = map.getContainer().clientWidth < 520 ? 58 : 74;
      const groups = new Map();
      for (const item of visible()) {
        const px = map.project(item.point, zoom);
        const key = `${Math.floor(px.x / gridSize)}:${Math.floor(px.y / gridSize)}`;
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push({ ...item, px });
      }
      for (const group of groups.values()) {
        if (group.length === 1) {
          const city = group[0].city;
          const marker = L.marker(group[0].point, {
            icon: cityIcon(city), title: city.name, keyboard: true, riseOnHover: true
          }).addTo(layer);
          marker.on("click", () => { location.hash = `#/city/${encodeURIComponent(city.id)}`; });
          if (marker.getElement()) {
            marker.getElement().dataset.id = city.id;
            marker.getElement().dataset.count = "1";
          }
          continue;
        }
        const center = group.reduce((p, r) => [p[0] + r.px.x, p[1] + r.px.y], [0, 0]);
        const ll = map.unproject([center[0] / group.length, center[1] / group.length], zoom);
        const clusterIcon = L.divIcon({
          className: "mk city-cluster", iconSize: [42, 42], iconAnchor: [21, 21],
          html: `<b>${group.length}</b>`
        });
        const marker = L.marker(ll, {
          icon: clusterIcon, keyboard: true, title: `${group.length} городов. Нажмите, чтобы приблизить или выбрать город.`
        }).addTo(layer);
        if (marker.getElement()) marker.getElement().dataset.count = String(group.length);
        const links = group.slice().sort((a, b) => a.city.name.localeCompare(b.city.name, "ru"))
          .map((r) => `<a href="#/city/${encodeURIComponent(r.city.id)}">${esc(r.city.name)}</a>`).join("");
        marker.bindPopup(`<div class="cluster-list"><strong>${group.length} городов</strong>${links}</div>`, { maxWidth: 260 });
        marker.on("click", () => {
          if (map.getZoom() >= map.getMaxZoom() - 0.6) {
            marker.openPopup();
          } else {
            const bounds = L.latLngBounds(group.map((r) => r.point));
            if (bounds.getSouthWest().equals(bounds.getNorthEast())) {
              map.setView(ll, Math.min(map.getMaxZoom(), map.getZoom() + 2));
            } else {
              map.fitBounds(bounds, {
                padding: [48, 48], maxZoom: Math.min(map.getMaxZoom(), map.getZoom() + 2)
              });
            }
          }
        });
      }
    }
    map.on("zoomend", render);
    map.on("moveend", render);
    render();
    return {
      count: () => rows.length,
      visibleCount: () => visible().length,
      fit,
      update(ids) {
        active.clear();
        ids.forEach((id) => active.add(id));
        render();
      },
      refresh: render
    };
  }

  function portal(host, A, onReady) {
    if (!ok()) {
      host.innerHTML = '<p class="note">Карта недоступна. Используйте список стран и городов ниже.</p>'; return;
    }
    const P = A.portal;
    host.innerHTML = `<div class="map-top">
        <div class="mtabs" role="tablist" aria-label="Выбор картографического слоя">
          <button type="button" role="tab" id="tOld" aria-selected="true">Европа · 1769</button>
          <button type="button" role="tab" id="tNew" aria-selected="false">Современная карта · города атласа</button>
        </div>
        <div class="map-actions" role="group" aria-label="Масштаб и область карты">
          <button type="button" id="mapFit">Показать выбранные города</button>
          <button type="button" id="mapWorld">Все города атласа</button>
          <button type="button" id="mapEurope">Европа крупнее</button>
        </div>
        <p class="map-summary" role="status" aria-live="polite" id="mapSummary"></p>
      </div>
      <div class="lmap" id="pmap" aria-label="Историческая карта Европы 1769 года; приблизительные позиции городов"></div>
      <div class="lmap" id="nmap" hidden aria-label="Современная карта мира с групповыми метками городов"></div>
      <p class="map-summary" id="mapTruth">Историческая карта охватывает Европу. Для остальных городов с известными центрами используйте современную карту. Метка города не означает известную точку съёмки художника. <a href="../cities/">Полный мировой указатель, включая города без геопривязки ↗</a></p>
      <details class="map-archive" id="mapArchive">
        <summary>Перелистать другие исторические карты и планы</summary>
        <div class="map-archive-actions" role="group" aria-label="Исторические картографические оригиналы">
          <button type="button" data-sheet="europe" aria-pressed="true">Европа · 1769</button>
          <button type="button" data-sheet="paris" aria-pressed="false">Париж · 1878</button>
        </div>
        <figure><img id="mapSheetImage" src="img/loc-97683588-carte-d-europe-1769_w1000.jpg"
          alt="Историческая карта Европы, 1769 год" loading="lazy" decoding="async">
          <figcaption id="mapSheetCaption">Карта Европы, de L’Isle / Buache, экземпляр Library of Congress, 1769.
            <a id="mapSheetSource" target="_blank" rel="noopener noreferrer" href="https://www.loc.gov/item/97683588/">Архивный оригинал ↗</a></figcaption>
        </figure>
        <p class="map-summary">Другие карты можно листать как отдельные документы. Пока на них нет независимо проверенной геопривязки, маркеры автоматически не накладываются.</p>
      </details>`;
    const sheets = {
      europe: { file: "img/loc-97683588-carte-d-europe-1769_w1000.jpg",
        name: "Карта Европы de L’Isle / Buache, 1769. Library of Congress.",
        src: "https://www.loc.gov/item/97683588/" },
      paris: { file: "img/loc-2012586603-paris-1878.jpg",
        name: "План Парижа и окрестностей, 1878. Library of Congress. Привязка контрольных точек остаётся исследовательской.",
        src: "https://www.loc.gov/item/2012586603/" }
    };
    host.querySelectorAll("[data-sheet]").forEach((button) => button.addEventListener("click", () => {
      const selected = sheets[button.dataset.sheet];
      if (!selected) return;
      document.getElementById("mapSheetImage").src = selected.file;
      document.getElementById("mapSheetImage").alt = selected.name;
      document.getElementById("mapSheetCaption").firstChild.textContent = selected.name + " ";
      document.getElementById("mapSheetSource").href = selected.src;
      host.querySelectorAll("[data-sheet]").forEach((b) =>
        b.setAttribute("aria-pressed", String(b === button)));
    }));
    const t = { ...P.tiles, credit: "Исторический оригинал: Library of Congress, G5700 1724 .L5 TIL" };
    const { map, at } = imageMap(document.getElementById("pmap"), t);
    const k = P.tiles.width / P.width;
    const oldCities = clusterCityMarkers(map, A.cities.filter((c) => Array.isArray(c.xy) && c.xy.length === 2), (c) => at(c.xy[0] * k, c.xy[1] * k));
    labelClass(map, document.getElementById("pmap"), map.getZoom());
    let modern = null, nowCities = null;
    let oldSelected = true;
    let selectedIds = new Set(A.cities.map((c) => c.id));
    let filtered = false;
    const note = () => {
      const total = selectedIds.size, inEurope = oldCities.visibleCount();
      document.getElementById("mapSummary").textContent = oldSelected
        ? `На исторической карте ${inEurope} из ${total} выбранных городов. Остальные доступны на современной карте и в указателе.`
        : `Современная карта: ${nowCities ? nowCities.visibleCount() : total} городов с координатами. Выбирайте кластер, чтобы приблизить.`;
      document.getElementById("mapTruth").hidden = !oldSelected;
    };
    function makeModern() {
      if (modern) return;
      modern = L.map("nmap", { zoomControl: false, zoomSnap: 0.5, worldCopyJump: true });
      L.tileLayer(...OSM).addTo(modern);
      L.control.zoom({ position: "topright", zoomInTitle: "Приблизить", zoomOutTitle: "Отдалить" }).addTo(modern);
      nowCities = clusterCityMarkers(modern, A.cities,
        (c) => c.lat != null && c.lon != null && Number.isFinite(Number(c.lat)) && Number.isFinite(Number(c.lon))
          ? [Number(c.lat), Number(c.lon)] : null);
      nowCities.update(selectedIds);
      nowCities.fit();
      homeButton(modern, () => nowCities.fit());
      labelClass(modern, document.getElementById("nmap"), modern.getZoom());
      modern.on("zoomend", note);
    }
    function show(old) {
      oldSelected = !!old;
      document.getElementById("tOld").setAttribute("aria-selected", String(oldSelected));
      document.getElementById("tNew").setAttribute("aria-selected", String(!oldSelected));
      document.getElementById("pmap").hidden = !oldSelected;
      document.getElementById("nmap").hidden = oldSelected;
      if (oldSelected) {
        map.invalidateSize({ pan: false });
        oldCities.refresh();
      } else {
        makeModern();
        modern.invalidateSize({ pan: false });
        nowCities.refresh();
      }
      note();
    }
    document.getElementById("tOld").onclick = () => show(true);
    document.getElementById("tNew").onclick = () => show(false);
    document.getElementById("mapWorld").onclick = () => {
      selectedIds = new Set(A.cities.map((c) => c.id));
      if (typeof window.cityAtlasReset === "function") window.cityAtlasReset();
      oldCities.update(selectedIds);
      show(false);
      nowCities.update(selectedIds);
      nowCities.fit();
      note();
    };
    document.getElementById("mapEurope").onclick = () => {
      show(false);
      modern.setView([50, 12], 4, { animate: false });
      note();
    };
    document.getElementById("mapFit").onclick = () => {
      if (oldSelected) {
        if (!oldCities.visibleCount()) { show(false); nowCities.fit(); }
        else oldCities.fit();
      } else nowCities.fit();
      note();
    };
    note();
    if (onReady) onReady();
    return {
      setVisible(ids, shouldFit = false) {
        selectedIds = new Set(ids);
        filtered = ids.length < A.cities.length;
        oldCities.update(selectedIds);
        if (nowCities) nowCities.update(selectedIds);
        if (oldSelected && oldCities.visibleCount() === 0 && selectedIds.size) show(false);
        if (shouldFit && selectedIds.size) {
          if (oldSelected) oldCities.fit();
          else if (nowCities) nowCities.fit();
        }
        note();
      },
      showModern: () => show(false),
      showHistoric: () => show(true),
      invalidateSize() {
        map.invalidateSize({ pan: false });
        oldCities.refresh();
        if (modern) {
          modern.invalidateSize({ pan: false });
          nowCities.refresh();
        }
      }
    };
  }

  // ---------- city: historic plan (if any) + modern map, markers where works were drawn
  function city(host, c, sites, thumbOf) {
    if (!ok()) return;
    const plan = c.plan;
    const pts = sites.filter((s) => s.lat != null);
    if (!plan && !pts.length) {
      host.innerHTML = `<div class="lmap small" id="cmap" aria-label="Современная карта: ${esc(c.name)}"></div>
        <p class="mapnote">Где именно рисовали виды этого города, мы ещё устанавливаем. Метка — центр города.</p>`;
      const m = L.map("cmap", { zoomControl: false }).setView([c.lat, c.lon], 13);
      L.tileLayer(...OSM).addTo(m);
      L.control.zoom({ position: "topright", zoomInTitle: "Приблизить", zoomOutTitle: "Отдалить" }).addTo(m);
      L.marker([c.lat, c.lon], { icon: cityIcon(c), keyboard: false }).addTo(m);
      return;
    }
    host.innerHTML = `<div class="mtabs" role="tablist" aria-label="Вид карты города">
        ${plan ? `<button type="button" role="tab" id="cOld" aria-selected="true">План ${esc(plan.year || "XIX в.")}</button>` : ""}
        <button type="button" role="tab" id="cNew" aria-selected="${plan ? "false" : "true"}">Город сегодня</button></div>
      ${plan ? `<div class="lmap" id="cplan" aria-label="${esc(plan.title)}"></div>` : ""}
      <div class="lmap" id="cnow" ${plan ? "hidden" : ""} aria-label="Современная карта: ${esc(c.name)}"></div>
      <p class="mapnote">${pts.length ? `Метки — места, изображённые на работах (${pts.length}); нажмите, чтобы увидеть работу. ` : ""}${plan ? `План: ${esc(plan.title)}, ${esc(plan.credit)}. ${esc(plan.georef_note || "")} <a href="${esc(plan.object_url)}" target="_blank" rel="noopener">карточка ↗</a>` : ""}</p>`;
    const pop = (s) => `<div class="mpop">${s.image ? `<img src="${esc(thumbOf(s.image))}" alt="" loading="lazy" referrerpolicy="no-referrer">` : ""}
      <b>${esc(cap(s.site_ru || s.site_name))}</b><small>${esc(s.title || "")}</small>
      <span class="mlinks"><a href="#w-${esc(s.wid)}" data-w="${esc(s.wid)}">к работе ↓</a><a href="${esc(s.url)}" target="_blank" rel="noopener">у хранителя ↗</a></span></div>`;
    const siteIcon = (s) => L.divIcon({ className: `mk site ${s.kind || ""}`, iconSize: [26, 26], iconAnchor: [13, 13], html: `<i></i><span>${esc(cap(s.site_ru || s.site_name))}</span>` });
    const addSites = (m, pos) => {
      const ms = [];
      const seen = new Map();
      for (const s of pts) {
        let ll = pos(s);
        if (!ll) continue;
        const key = `${ll.lat ?? ll[0]},${ll.lng ?? ll[1]}`;
        const n = seen.get(key) || 0; seen.set(key, n + 1);
        const mk = L.marker(ll, { icon: siteIcon(s), title: s.site_ru || s.site_name, keyboard: false, riseOnHover: true }).addTo(m);
        if (n) mk.setZIndexOffset(-n);
        mk.bindPopup(pop(s), { maxWidth: 240, autoPanPadding: [20, 20] });
        ms.push(mk);
      }
      return ms;
    };
    let now = null;
    const mkNow = () => {
      now = L.map("cnow", { zoomControl: false, zoomSnap: 0.5 });
      L.tileLayer(...OSM).addTo(now);
      L.control.zoom({ position: "topright", zoomInTitle: "Приблизить", zoomOutTitle: "Отдалить" }).addTo(now);
      const ms = addSites(now, (s) => [s.lat, s.lon]);
      const fit = () => (ms.length > 1 ? now.fitBounds(L.featureGroup(ms).getBounds(), { padding: [24, 24], maxZoom: 16 }) : now.setView(ms.length ? ms[0].getLatLng() : [c.lat, c.lon], 15));
      fit(); homeButton(now, fit);
      labelClass(now, document.getElementById("cnow"), now.getZoom());
    };
    if (plan) {
      const { map, at } = imageMap(document.getElementById("cplan"), plan);
      const k = plan.width / (plan.px_width || plan.width);
      addSites(map, (s) => (s.px ? at(s.px[0] * k, s.px[1] * k) : null));
      labelClass(map, document.getElementById("cplan"), map.getZoom());
      const show = (old) => {
        document.getElementById("cOld").setAttribute("aria-selected", String(old));
        document.getElementById("cNew").setAttribute("aria-selected", String(!old));
        document.getElementById("cplan").hidden = !old; document.getElementById("cnow").hidden = old;
        if (old) map.invalidateSize(); else if (!now) mkNow(); else now.invalidateSize();
      };
      document.getElementById("cOld").onclick = () => show(true);
      document.getElementById("cNew").onclick = () => show(false);
    } else mkNow();
  }
  return { portal, city };
})();
