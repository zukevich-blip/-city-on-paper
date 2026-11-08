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

  // Image map in CRS.Simple: pixel (x,y) of the native tile image <-> LatLng
  function imageMap(el, t, opts = {}) {
    const map = L.map(el, { crs: L.CRS.Simple, zoomControl: false, attributionControl: true, zoomSnap: 0.25,
      maxBoundsViscosity: 0.9, tap: true, ...opts });
    const z = t.max_zoom;
    const sw = map.unproject([0, t.height], z), ne = map.unproject([t.width, 0], z);
    const bounds = L.latLngBounds(sw, ne);
    L.tileLayer(`${t.tiles}/{z}/{x}/{y}.jpg`, { minZoom: -2, maxZoom: z + 2, maxNativeZoom: z, noWrap: true, bounds,
      tileSize: t.tile || 256, attribution: t.credit ? esc(t.credit) : "" }).addTo(map);
    L.control.zoom({ position: "topright", zoomInTitle: "Приблизить", zoomOutTitle: "Отдалить" }).addTo(map);
    map.fitBounds(bounds);
    map.setMinZoom(map.getZoom() - 0.5);
    map.setMaxBounds(bounds.pad(0.15));
    map.setMaxZoom(z + 2);
    homeButton(map, () => map.fitBounds(bounds));
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
  function addCities(map, cities, pos) {
    const out = [];
    for (const c of cities) {
      const ll = pos(c);
      if (!ll) continue;
      const m = L.marker(ll, { icon: cityIcon(c), title: c.name, keyboard: false, riseOnHover: true }).addTo(map);
      m.on("click", () => { location.hash = `#/city/${c.id}`; });
      m.getElement && m.getElement() && (m.getElement().dataset.id = c.id);
      out.push(m);
    }
    return out;
  }

  // ---------- portal: old map + modern map tabs
  function portal(host, A, onReady) {
    if (!ok()) { host.innerHTML = '<p class="note">Карта не загрузилась. Список городов ниже.</p>'; return; }
    const P = A.portal;
    host.innerHTML = `<div class="mtabs" role="tablist" aria-label="Вид карты">
        <button type="button" role="tab" id="tOld" aria-selected="true">Карта Европы 1769 г.</button>
        <button type="button" role="tab" id="tNew" aria-selected="false">Современная карта</button></div>
      <div class="lmap" id="pmap" aria-label="Старая карта Европы с метками городов. Кнопки приближения — в правом верхнем углу."></div>
      <div class="lmap" id="nmap" hidden aria-label="Современная карта с метками городов"></div>`;
    const t = { ...P.tiles, credit: "Карта: Library of Congress, G5700 1724 .L5 TIL" };
    const { map, at } = imageMap(document.getElementById("pmap"), t);
    const k = P.tiles.width / P.width;
    addCities(map, A.cities.filter((c) => c.xy), (c) => at(c.xy[0] * k, c.xy[1] * k));
    labelClass(map, document.getElementById("pmap"), map.getZoom());
    let nmap = null;
    const show = (old) => {
      document.getElementById("tOld").setAttribute("aria-selected", String(old));
      document.getElementById("tNew").setAttribute("aria-selected", String(!old));
      document.getElementById("pmap").hidden = !old;
      document.getElementById("nmap").hidden = old;
      if (old) { map.invalidateSize(); return; }
      if (!nmap) {
        nmap = L.map("nmap", { zoomControl: false, zoomSnap: 0.5 });
        L.tileLayer(...OSM).addTo(nmap);
        L.control.zoom({ position: "topright", zoomInTitle: "Приблизить", zoomOutTitle: "Отдалить" }).addTo(nmap);
        const ms = addCities(nmap, A.cities, (c) => (c.lat != null ? [c.lat, c.lon] : null));
        const b = L.featureGroup(ms).getBounds();
        nmap.fitBounds(b, { padding: [10, 10] });
        homeButton(nmap, () => nmap.fitBounds(b, { padding: [10, 10] }));
        labelClass(nmap, document.getElementById("nmap"), nmap.getZoom());
        onReady && onReady();
      } else nmap.invalidateSize();
    };
    document.getElementById("tOld").onclick = () => show(true);
    document.getElementById("tNew").onclick = () => show(false);
    onReady && onReady();
    return map;
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
      <b>${esc(s.site_ru || s.site_name)}</b><small>${esc(s.title || "")}</small>
      <a href="#w-${esc(s.wid)}" data-w="${esc(s.wid)}">к работе ↓</a> · <a href="${esc(s.url)}" target="_blank" rel="noopener">у хранителя ↗</a></div>`;
    const siteIcon = (s) => L.divIcon({ className: `mk site ${s.kind || ""}`, iconSize: [26, 26], iconAnchor: [13, 13], html: `<i></i><span>${esc(s.site_ru || s.site_name)}</span>` });
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
