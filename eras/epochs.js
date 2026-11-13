/* Атлас эпох v4 — «Одно место — разные эпохи» и «Мой ракурс».
 * Кадры места: листы XIX века (музеи и Commons), фото места сегодня (Commons), уличные фото Panoramax
 * с точкой и направлением съёмки, и ваши собственные фото. Ваши фото хранятся ТОЛЬКО на этом устройстве
 * (IndexedDB браузера) и никуда не загружаются. Исторические изображения не искажаются: только сопоставление. */
"use strict";
window.Epochs = (() => {
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const safeLink = (u) => (/^https?:\/\//.test(u || "") ? u : "#");
  const cap = (t) => (t ? t.charAt(0).toUpperCase() + t.slice(1) : "");
  const yearOf = (d) => { const m = /(1[4-9]\d\d|20\d\d)/.exec(d || ""); return m ? +m[1] : null; };
  const oldYear = (d) => { const y = yearOf(d); return y && y <= 1930 ? y : null; }; // upload dates are not drawing dates
  const plural = (n, one, few, many) => { const a = Math.abs(n) % 100, b = a % 10;
    return `${n} ${a > 10 && a < 20 ? many : b === 1 ? one : b > 1 && b < 5 ? few : many}`; };
  const KIND = { print: "Лист", photo: "Старое фото", today: "Сегодня", street: "Улица сегодня", mine: "Моё фото" };

  // ---------- private storage (IndexedDB), nothing leaves the device
  const DB = (() => {
    let p = null;
    const open = () => p || (p = new Promise((res, rej) => {
      if (!("indexedDB" in window)) return rej(new Error("no indexedDB"));
      const r = indexedDB.open("city-on-paper-mine", 1);
      r.onupgradeneeded = () => r.result.createObjectStore("photos", { keyPath: "id" });
      r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error);
    }));
    const tx = (mode, fn) => open().then((db) => new Promise((res, rej) => {
      const t = db.transaction("photos", mode); const st = t.objectStore("photos"); const out = fn(st);
      t.oncomplete = () => res(out && "result" in out ? out.result : out); t.onerror = () => rej(t.error);
    }));
    return {
      all: () => tx("readonly", (s) => s.getAll()).catch(() => []),
      put: (rec) => tx("readwrite", (s) => s.put(rec)),
      del: (id) => tx("readwrite", (s) => s.delete(id)),
    };
  })();
  const urls = new Map();
  const blobUrl = (rec) => { if (!urls.has(rec.id)) urls.set(rec.id, URL.createObjectURL(rec.blob)); return urls.get(rec.id); };

  // ---------- EXIF GPS (read locally from the user's own JPEG; nothing is sent anywhere)
  async function exifGps(file) {
    try {
      const v = new DataView(await file.slice(0, 256 * 1024).arrayBuffer());
      if (v.getUint16(0) !== 0xffd8) return null;
      let o = 2;
      while (o < v.byteLength - 4) {
        const marker = v.getUint16(o), len = v.getUint16(o + 2);
        if (marker === 0xffe1 && v.getUint32(o + 4) === 0x45786966) {
          const t = o + 10, le = v.getUint16(t) === 0x4949;
          const u16 = (x) => v.getUint16(x, le), u32 = (x) => v.getUint32(x, le);
          const ifd = (x) => { const n = u16(x); const m = {}; for (let i = 0; i < n; i++) { const e = x + 2 + i * 12; m[u16(e)] = { type: u16(e + 2), count: u32(e + 4), at: e + 8 }; } return m; };
          const ifd0 = ifd(t + u32(t + 4));
          if (!ifd0[0x8825]) return null;
          const g = ifd(t + u32(ifd0[0x8825].at));
          const rat = (e, i) => { const p = t + u32(e.at) + i * 8; return u32(p) / (u32(p + 4) || 1); };
          const dms = (e) => rat(e, 0) + rat(e, 1) / 60 + rat(e, 2) / 3600;
          const ref = (e) => String.fromCharCode(v.getUint8(e.at));
          if (!g[2] || !g[4]) return null;
          let lat = dms(g[2]), lon = dms(g[4]);
          if (g[1] && ref(g[1]) === "S") lat = -lat;
          if (g[3] && ref(g[3]) === "W") lon = -lon;
          const az = g[17] ? rat(g[17], 0) : null;
          return { lat, lon, az };
        }
        o += 2 + len;
      }
    } catch (e) { /* no GPS */ }
    return null;
  }

  // ---------- geometry helpers
  const R = 6371000;
  const bearing = (a, b) => { const p1 = a[0] * Math.PI / 180, p2 = b[0] * Math.PI / 180, dl = (b[1] - a[1]) * Math.PI / 180;
    return (Math.atan2(Math.sin(dl) * Math.cos(p2), Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dl)) * 180 / Math.PI + 360) % 360; };
  const dist = (a, b) => { const dy = (b[0] - a[0]) * Math.PI / 180 * R, dx = (b[1] - a[1]) * Math.PI / 180 * R * Math.cos(a[0] * Math.PI / 180); return Math.hypot(dx, dy); };
  const dest = (a, az, d) => [a[0] + d * Math.cos(az * Math.PI / 180) / R * 180 / Math.PI,
    a[1] + d * Math.sin(az * Math.PI / 180) / (R * Math.cos(a[0] * Math.PI / 180)) * 180 / Math.PI];
  const cone = (cam, site) => { const d = Math.max(40, Math.min(400, dist([cam.lat, cam.lon], site) * 1.15)); const h = (cam.fov || 60) / 2;
    const pts = [[cam.lat, cam.lon]]; for (let k = -h; k <= h; k += h / 4) pts.push(dest([cam.lat, cam.lon], cam.azimuth + k, d)); return pts; };

  // ---------- frames of one place
  function framesOf(c, g, thumb, mine) {
    const byW = new Map((c.sites || []).map((x) => [x.wid, x]));
    const fs = [];
    for (const w of g.works) { const x = byW.get(w); if (x && x.image) fs.push({ kind: /photo|фото/i.test(x.title || "") ? "photo" : "print", img: thumb(x.image), year: oldYear(x.date) || oldYear(x.title), label: x.title, url: x.url, credit: "" }); }
    for (const p of g.prints || []) fs.push({ kind: p.kind === "photograph" || p.kind === "photochrom" ? "photo" : "print", img: thumb(p.image), year: p.year, label: p.title || p.file, url: p.page,
      credit: [p.artist, p.source_institution].filter(Boolean).join(", "), lic: p.license, licUrl: p.license_url });
    const seen = new Set(); const uniq = fs.filter((f) => !seen.has(f.img) && seen.add(f.img));
    uniq.sort((a, b) => (a.year || 1850) - (b.year || 1850));
    if (g.today) uniq.push({ kind: "today", img: thumb(g.today.image), year: yearOf(g.today.date), label: `Сегодня: ${cap(g.name)}`, url: g.today.page,
      credit: `Фото: ${g.today.author || "автор на Commons"}`, lic: g.today.license, licUrl: g.today.license_url });
    for (const s of g.street || []) uniq.push({ kind: "street", img: s.file, year: yearOf(s.date), label: `Улица сегодня: ${cap(g.name)} (${s.camera.distance_m} м)`, url: s.page,
      credit: `Фото: ${s.author}, Panoramax; ${s.note}`, lic: s.license, licUrl: s.license_url, camera: s.camera });
    for (const m of mine) {
      const kind = m.workType === "print" ? "print" : m.workType === "historic_photo" ? "photo" : "mine";
      const author = m.author ? `Автор: ${m.author}` : "Автор не указан";
      uniq.push({ kind, img: blobUrl(m),
        year: m.artYear || yearOf(m.date) || "моё",
        label: m.name || "Моё изображение",
        url: /^https:\/\//.test(m.source || "") ? m.source : "",
        credit: `Личный материал, только на устройстве · ${author}`,
        lic: m.rights || "Права требуют проверки", licUrl: "",
        camera: kind === "mine" && m.lat != null && m.lon != null
          ? { lat: m.lat, lon: m.lon,
              azimuth: m.az ?? bearing([m.lat, m.lon], [g.lat, g.lon]), fov: m.fov || 60 } : null,
        mineId: m.id
      });
    }
    return uniq;
  }

  // ---------- one place: track + compare + angle map + my photo
  async function viewer(host, c, g, thumb, imgTag) {
    const key = `${c.id}|${g.key}`;
    const mine = (await DB.all()).filter((m) => m.place === key).sort((a, b) => a.created - b.created);
    const fs = framesOf(c, g, thumb, mine);
    const lab = (f) => `${f.year || "год?"} · ${KIND[f.kind]}`;
    let a = 0, b = fs.length - 1;
    if (fs.length < 2) b = 0;
    host.innerHTML = `<div class="eptrack" role="list">${fs.map((f, i) => `<button type="button" class="epf ${f.kind}" data-f="${i}" role="listitem" aria-label="${esc(lab(f))}: ${esc(f.label)}">
        ${f.kind === "mine" ? `<img src="${esc(f.img)}" alt="${esc(f.label)}">` : imgTag(f.img, f.label || g.name)}<b>${esc(f.year || "")}</b><small>${esc(KIND[f.kind])}</small></button>`).join("")}
        <button type="button" class="epf add" id="epAdd"><span>＋</span><b>Моё фото</b><small>и точка съёмки</small></button></div>
      <div class="epgrid"><div class="epcmp">
        <div class="ctrls"><label>Было <select id="epA">${fs.map((f, i) => `<option value="${i}">${esc(lab(f))} — ${esc((f.label || "").slice(0, 50))}</option>`).join("")}</select></label>
          <label>Стало <select id="epB">${fs.map((f, i) => `<option value="${i}">${esc(lab(f))} — ${esc((f.label || "").slice(0, 50))}</option>`).join("")}</select></label></div>
        <div class="epstage" id="epstage"><img id="epImB" alt=""><div class="epTop" id="epTop"><img id="epImA" alt=""></div>
          <div class="eph" id="epH2" role="slider" tabindex="0" aria-label="Граница сравнения: стрелки влево и вправо" aria-valuemin="0" aria-valuemax="100" aria-valuenow="50"><span>⇆</span></div>
          <span class="tag l" id="epTagA"></span><span class="tag r" id="epTagB"></span></div>
        <p class="mapnote" id="epCredit"></p></div>
        <div class="epside"><p class="eyebrow">Ракурсы</p><div class="lmap angles" id="epMap" aria-label="Карта ракурсов: место и точки съёмки"></div>
          <p class="mapnote">★ — изображённое место. Конусы — откуда и куда смотрит камера (уличные фото Panoramax и ваши). Для старых листов точка художника обычно неизвестна.</p>
          <div id="epMine"></div></div></div>
      <dialog id="epDlg" class="epdlg" aria-labelledby="epDlgT"><form method="dialog">
        <h2 id="epDlgT">Добавить свою литографию или фотографию: ${esc(cap(g.name))}</h2>
        <p class="mapnote">Изображение хранится только на этом устройстве (IndexedDB). Для старого листа год, автор и права требуют проверки. Точка съёмки не приписывается литографии автоматически.</p>
        <div class="epmetadata">
          <label>Что добавляем <select id="epKind">
            <option value="modern">Моя современная фотография</option>
            <option value="print">Литография / гравюра</option>
            <option value="historic_photo">Старинная фотография</option>
          </select></label>
          <label>Год создания <input id="epWorkYear" type="number" min="1400" max="2100" placeholder="например, 1860"></label>
          <label>Автор или собрание <input id="epArtist" maxlength="120" placeholder="Если известно"></label>
          <label>Архивная ссылка <input id="epSource" type="url" placeholder="https://..." maxlength="1500"></label>
          <label>Права <select id="epRights"><option>Требуют проверки</option><option>CC0 (документировано)</option><option>CC BY (с атрибуцией)</option><option>CC BY-SA (с атрибуцией)</option><option>Моё авторское фото</option></select></label>
        </div>
        <label class="file">Выбрать изображение <input type="file" id="epFile" accept="image/jpeg,image/png,image/webp"></label>
        <div id="epPrev" class="epprev"></div>
        <div id="epLocationGroup"><p class="mapnote">Для современного снимка можно указать точку и направление камеры.</p><div class="lmap pick" id="epPick" aria-label="Карта: нажмите, где вы стояли"></div>
        <div class="coords2"><label>Широта <input id="epLat" inputmode="decimal" placeholder="48.8700"></label><label>Долгота <input id="epLon" inputmode="decimal" placeholder="2.3245"></label>
          <label>Направление, ° <input id="epAz" type="range" min="0" max="359" step="1"><output id="epAzO"></output></label></div>
        <div class="fbrow"><button type="button" class="ghost" id="epGeo">Где я сейчас</button></div></div>
        <div class="fbrow"><button value="cancel" class="ghost">Отмена</button><button type="button" class="solid" id="epSave" disabled>Сохранить на устройстве</button></div>
        <p class="mapnote" id="epMsg" role="status"></p></form></dialog>`;
    const $ = (id) => host.querySelector("#" + id);
    const selA = $("epA"), selB = $("epB"), st = $("epstage"), top = $("epTop"), h = $("epH2");
    selA.value = a; selB.value = b;
    const setPos = (p) => { p = Math.max(0, Math.min(100, p)); top.style.clipPath = `inset(0 ${100 - p}% 0 0)`; h.style.left = p + "%"; h.setAttribute("aria-valuenow", String(Math.round(p))); };
    // angles map
    let amap = null, layers = null;
    const site = [g.lat, g.lon];
    if (window.L) {
      amap = L.map($("epMap"), { zoomControl: false, attributionControl: true }).setView(site, 17);
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OSM</a>' }).addTo(amap);
      L.control.zoom({ position: "topright", zoomInTitle: "Приблизить", zoomOutTitle: "Отдалить" }).addTo(amap);
      L.marker(site, { icon: L.divIcon({ className: "mk star", html: "★", iconSize: [28, 28], iconAnchor: [14, 14] }), keyboard: false, title: cap(g.name) }).addTo(amap);
      layers = L.layerGroup().addTo(amap);
    }
    const drawCones = () => {
      if (!layers) return;
      layers.clearLayers(); const pts = [site];
      fs.forEach((f, i) => { if (!f.camera) return; const on = i === a || i === b;
        const poly = L.polygon(cone(f.camera, site), { color: f.kind === "mine" ? "#a8402a" : "#2c5d73", weight: on ? 3 : 1, fillOpacity: on ? 0.35 : 0.12 }).addTo(layers);
        poly.on("click", () => { b = i; selB.value = b; upd(); }); pts.push([f.camera.lat, f.camera.lon]); });
      if (pts.length > 1) amap.fitBounds(L.latLngBounds(pts).pad(0.25), { maxZoom: 18 });
    };
    const upd = () => {
      const A = fs[a], B = fs[b];
      const ia = $("epImA"), ib = $("epImB");
      ia.src = A.img; ia.alt = `Было: ${lab(A)} — ${A.label}`; ib.src = B.img; ib.alt = `Стало: ${lab(B)} — ${B.label}`;
      $("epTagA").textContent = lab(A); $("epTagB").textContent = lab(B);
      $("epCredit").innerHTML = [A, B].map((f) => `${f.url ? `<a href="${esc(safeLink(f.url))}" target="_blank" rel="noopener">${esc(lab(f))}: источник ↗</a>` : esc(lab(f))}${f.credit ? " · " + esc(f.credit) : ""}${f.lic ? `, ${/^https?:\/\//.test(f.licUrl || "") ? `<a href="${esc(f.licUrl)}" target="_blank" rel="noopener">${esc(f.lic)}</a>` : esc(f.lic)}` : ""}${f.camera ? ` · точка съёмки ${f.camera.lat.toFixed(5)}, ${f.camera.lon.toFixed(5)}, направление ${Math.round(f.camera.azimuth)}°` : ""}`).join("<br>");
      host.querySelectorAll(".epf[data-f]").forEach((x) => x.classList.toggle("on", +x.dataset.f === a || +x.dataset.f === b));
      drawCones();
    };
    selA.onchange = () => { a = +selA.value; upd(); };
    selB.onchange = () => { b = +selB.value; upd(); };
    host.querySelectorAll(".epf[data-f]").forEach((x) => (x.onclick = () => { const i = +x.dataset.f; if (i === a || i === b) return; if (i < b) a = i; else b = i; selA.value = a; selB.value = b; upd(); st.scrollIntoView({ behavior: "smooth", block: "nearest" }); }));
    const move = (e) => { const r = st.getBoundingClientRect(); setPos((e.clientX - r.left) / r.width * 100); };
    st.addEventListener("pointerdown", (e) => { st.setPointerCapture(e.pointerId); move(e); st.onpointermove = move; });
    st.addEventListener("pointerup", () => (st.onpointermove = null));
    h.addEventListener("keydown", (e) => { const v = +h.getAttribute("aria-valuenow"); if (e.key === "ArrowLeft") setPos(v - 5); else if (e.key === "ArrowRight") setPos(v + 5); else if (e.key === "Home") setPos(0); else if (e.key === "End") setPos(100); else return; e.preventDefault(); });
    setPos(50); upd();
    // my photos list
    $("epMine").innerHTML = mine.length ? `<p class="eyebrow">Мои изображения этого места</p>${mine.map((m) => `<p class="mine1"><span>${esc(m.name)}${m.lat != null ? ` · ${m.lat.toFixed(5)}, ${m.lon.toFixed(5)}` : " · без точки"}</span> <button type="button" class="ghost" data-del="${esc(m.id)}">Удалить</button></p>`).join("")}` : "";
    $("epMine").querySelectorAll("[data-del]").forEach((x) => (x.onclick = async () => { await DB.del(x.dataset.del); viewer(host, c, g, thumb, imgTag); }));
    // add my photo
    const dlg = $("epDlg"); let file = null, pick = null, pmk = null, previewUrl = null;
    const isModern = () => $("epKind").value === "modern";
    $("epKind").onchange = () => {
      $("epLocationGroup").hidden = !isModern();
      $("epMsg").textContent = isModern()
        ? "Для современного снимка можно указать позицию и направление камеры."
        : "Для исторической работы точка съёмки неизвестна и автоматически не устанавливается.";
      if (pick && isModern()) setTimeout(() => pick.invalidateSize(), 30);
    };
    const az = $("epAz"), azO = $("epAzO"), latI = $("epLat"), lonI = $("epLon");
    const setPoint = (lat, lon, azv) => {
      latI.value = (+lat).toFixed(6); lonI.value = (+lon).toFixed(6);
      az.value = Math.round(azv ?? bearing([+lat, +lon], site)); azO.textContent = az.value + "°";
      if (pick) { if (pmk) pick.removeLayer(pmk); pmk = L.polygon(cone({ lat: +lat, lon: +lon, azimuth: +az.value, fov: 60 }, site), { color: "#a8402a", fillOpacity: 0.3 }).addTo(pick); }
      $("epSave").disabled = !file;
    };
    az.oninput = () => { azO.textContent = az.value + "°"; if (latI.value && lonI.value) setPoint(latI.value, lonI.value, +az.value); };
    [latI, lonI].forEach((x) => (x.onchange = () => { const la = parseFloat(latI.value), lo = parseFloat(lonI.value); if (isFinite(la) && isFinite(lo) && Math.abs(la) <= 90 && Math.abs(lo) <= 180) setPoint(la, lo); }));
    $("epAdd").onclick = () => {
      dlg.showModal();
      if (window.L && isModern() && !pick) {
        pick = L.map($("epPick"), { zoomControl: false }).setView(site, 17);
        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: "© OSM" }).addTo(pick);
        L.control.zoom({ position: "topright" }).addTo(pick);
        L.marker(site, { icon: L.divIcon({ className: "mk star", html: "★", iconSize: [28, 28], iconAnchor: [14, 14] }), keyboard: false }).addTo(pick);
        pick.on("click", (e) => setPoint(e.latlng.lat, e.latlng.lng));
      }
      setTimeout(() => pick && isModern() && pick.invalidateSize(), 50);
    };
    $("epFile").onchange = async (e) => {
      file = e.target.files[0] || null;
      if (previewUrl) { URL.revokeObjectURL(previewUrl); previewUrl = null; }
      if (!file) { $("epSave").disabled = true; return; }
      if (!["image/jpeg", "image/png", "image/webp"].includes(file.type) || file.size > 15 * 1024 * 1024) {
        $("epMsg").textContent = "Допустимы JPG, PNG и WebP до 15 МБ. Слишком большие и другие файлы не сохраняются.";
        file = null; $("epSave").disabled = true; $("epPrev").replaceChildren(); return;
      }
      previewUrl = URL.createObjectURL(file);
      const im = document.createElement("img");
      im.src = previewUrl; im.alt = "Предпросмотр выбранного изображения";
      $("epPrev").replaceChildren(im);
      if (isModern()) {
        const gps = await exifGps(file);
        if (gps) {
          setPoint(gps.lat, gps.lon, gps.az);
          $("epMsg").textContent = "Точка съёмки взята из GPS файла. Проверьте её на карте.";
          if (pick) pick.setView([gps.lat, gps.lon], 17);
        } else $("epMsg").textContent = "GPS не найден. Поставьте точку на карте или оставьте её пустой.";
      } else $("epMsg").textContent = "Лист будет сохранён без предполагаемой позиции художника.";
      $("epSave").disabled = false;
    };
    $("epGeo").onclick = () => { if (!navigator.geolocation) return; $("epMsg").textContent = "Определяем местоположение…";
      navigator.geolocation.getCurrentPosition((p) => { setPoint(p.coords.latitude, p.coords.longitude); if (pick) pick.setView([p.coords.latitude, p.coords.longitude], 17); $("epMsg").textContent = "Точка — ваше текущее место (только на устройстве)."; },
        () => { $("epMsg").textContent = "Не удалось определить место. Поставьте точку на карте."; }, { enableHighAccuracy: true, timeout: 10000 }); };
    $("epSave").onclick = async () => {
      if (!file) return;
      const la = parseFloat(latI.value), lo = parseFloat(lonI.value);
      const validPoint = isModern() && Number.isFinite(la) && Number.isFinite(lo) && Math.abs(la) <= 90 && Math.abs(lo) <= 180;
      const proposedYear = parseInt($("epWorkYear").value, 10);
      try {
        await DB.put({
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          place: key, city: c.id, cityName: c.name, placeName: cap(g.name),
          name: file.name.slice(0, 80), blob: file,
          workType: $("epKind").value,
          artYear: Number.isInteger(proposedYear) && proposedYear >= 1400 && proposedYear <= 2100 ? proposedYear : null,
          author: $("epArtist").value.trim().slice(0, 120),
          source: $("epSource").value.trim().slice(0, 1500),
          rights: $("epRights").value,
          date: file.lastModified ? new Date(file.lastModified).toISOString().slice(0, 10) : "",
          lat: validPoint ? la : null, lon: validPoint ? lo : null,
          az: validPoint ? +az.value : null, fov: 60, created: Date.now()
        });
        dlg.close();
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        viewer(host, c, g, thumb, imgTag);
      } catch (error) {
        $("epMsg").textContent = "Не удалось сохранить изображение. Проверьте свободное место браузера или возьмите файл меньше 15 МБ.";
      }
    };
  }

  // ---------- gallery of all places (#/epochs)
  function gallery(app, A, thumb, imgTag) {
    const items = [];
    for (const c of A.cities) for (const g of c.epochs || []) {
      const byW = new Map((c.sites || []).map((x) => [x.wid, x]));
      const first = g.works.map((w) => byW.get(w)).find((x) => x && x.image) || (g.prints || [])[0];
      const n = g.works.length + (g.prints || []).length + (g.today ? 1 : 0) + (g.street || []).length;
      if (n < 2 || !first) continue;
      items.push({ c, g, first: first.image, now: g.today ? g.today.image : (g.street || [])[0] ? g.street[0].file : null, n,
        y0: Math.min(...[...g.works.map((w) => oldYear((byW.get(w) || {}).date) || oldYear((byW.get(w) || {}).title) || 9999), ...(g.prints || []).map((p) => p.year || 9999)]) });
    }
    items.sort((x, y) => y.n - x.n);
    const cities = [...new Set(items.map((x) => x.c.name))].sort((a, b) => a.localeCompare(b, "ru"));
    app.innerHTML = `<div class="view"><nav class="crumbs" aria-label="Путь"><a href="#/">Атлас</a> › <span aria-current="page">Эпохи</span></nav>
      <span class="eyebrow">Одно место — разные эпохи</span><h1>Как было — как есть</h1>
      <p class="lede">${plural(items.length, "место", "места", "мест")} в ${plural(cities.length, "городе", "городах", "городах")}: листы XVIII–XIX веков, старые фотографии, снимки сегодня и уличные фото с точкой съёмки. Откройте место, сравните любые два кадра шторкой и добавьте своё фото с точкой, откуда снимали.</p>
      <div class="tools"><label class="sr" for="epq">Поиск места</label><input id="epq" type="search" placeholder="Место или город">
        <select id="epc" aria-label="Город"><option value="">Все города</option>${cities.map((n) => `<option>${esc(n)}</option>`).join("")}</select></div>
      <div class="epgal" id="epgal"></div></div>`;
    const draw = () => {
      const q = document.getElementById("epq").value.trim().toLowerCase(), cf = document.getElementById("epc").value;
      document.getElementById("epgal").innerHTML = items.filter((x) => (!cf || x.c.name === cf) && (!q || (x.g.name + " " + x.c.name).toLowerCase().includes(q))).slice(0, 120).map((x) =>
        `<a class="epcard" href="#/epoch/${esc(x.c.id)}/${encodeURIComponent(x.g.key)}"><span class="pair">${imgTag(thumb(x.first), cap(x.g.name) + ", лист")}${x.now ? (/^now\//.test(x.now) ? `<img src="${esc(x.now)}" alt="${esc(cap(x.g.name))} сегодня" loading="lazy">` : imgTag(thumb(x.now), cap(x.g.name) + " сегодня")) : ""}</span>
          <b>${esc(cap(x.g.name))}</b><small>${esc(x.c.name)} · ${x.y0 < 9999 ? x.y0 + " → сегодня" : "разные годы"} · ${plural(x.n, "кадр", "кадра", "кадров")}</small></a>`).join("") || '<p class="note">Ничего не найдено.</p>';
    };
    document.getElementById("epq").oninput = draw; document.getElementById("epc").onchange = draw; draw();
  }

  // ---------- one place page (#/epoch/<city>/<key>)
  function placePage(app, A, cid, key, thumb, imgTag) {
    const c = A.cities.find((x) => x.id === cid); const g = c && (c.epochs || []).find((x) => x.key === key);
    if (!g) return false;
    app.innerHTML = `<div class="view"><nav class="crumbs" aria-label="Путь"><a href="#/">Атлас</a> › <a href="#/epochs">Эпохи</a> › <a href="#/city/${esc(c.id)}">${esc(c.name)}</a> › <span aria-current="page">${esc(cap(g.name))}</span></nav>
      <span class="eyebrow">${esc(c.name)} · одно место — разные эпохи</span><h1>${esc(cap(g.name))}</h1>
      <p class="lede">Листы и фотографии разных лет, снимки сегодня и ваши фото. Точки съёмки художников обычно не совпадают с современными — это сопоставление, а не наложение; изображения не искажаются.</p>
      <div id="epview"></div></div>`;
    viewer(document.getElementById("epview"), c, g, thumb, imgTag);
    return true;
  }

  // ---------- all my photos (#/mine)
  async function minePage(app) {
    const all = (await DB.all()).sort((a, b) => b.created - a.created);
    app.innerHTML = `<div class="view"><nav class="crumbs" aria-label="Путь"><a href="#/">Атлас</a> › <span aria-current="page">Мой ракурс</span></nav>
      <span class="eyebrow">Только на этом устройстве</span><h1>Мой ракурс</h1>
      <p class="lede">Ваши фото мест из атласа с точкой, откуда вы снимали. Они хранятся в памяти этого браузера и не загружаются на сайт. Чтобы добавить фото, откройте место в разделе <a href="#/epochs">«Эпохи»</a> и нажмите «＋ Моё фото».</p>
      ${all.length ? `<div class="epgal">${all.map((m) => `<a class="epcard" href="#/epoch/${esc(m.city)}/${encodeURIComponent(m.place.split("|").slice(1).join("|"))}"><span class="pair"><img src="${esc(blobUrl(m))}" alt="${esc(m.name)}"></span>
        <b>${esc(m.placeName || "")}</b><small>${esc(m.cityName || "")} · ${m.lat != null ? `${m.lat.toFixed(5)}, ${m.lon.toFixed(5)} · ${Math.round(m.az)}°` : "без точки"}</small></a>`).join("")}</div>
        <p><button type="button" class="morebtn" id="mineExp">Скачать мои точки съёмки (JSON, без фото)</button></p>` : '<p class="note">Пока нет ваших фото.</p>'}</div>`;
    const ex = document.getElementById("mineExp");
    if (ex) ex.onclick = () => { const data = all.map(({ blob, ...r }) => r);
      const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([JSON.stringify({ app: "city-on-paper", kind: "my-viewpoints", items: data }, null, 1)], { type: "application/json" }));
      a.download = "moi-rakursy.json"; a.click(); };
  }
  return { viewer, gallery, placePage, minePage, framesOf };
})();
