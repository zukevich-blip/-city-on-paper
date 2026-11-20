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

  // Explicit place joins. A similar title, nearby camera or newer image alone does not establish a fit.
  const madeleine = ["madeleine-benoist-carnavalet", "madeleine-ph-benoist", "madeleine-barescut-carnavalet"];
  const ponteVecchio = ["florence-ponte-vecchio-silvestre", "florence-ponte-vecchio"];
  const sanFrancesco = ["naples-san-francesco-di-paola"];
  const atlasPairs = new Map([
    ["Q330564", madeleine], ["Q208633", ponteVecchio], ["Q241410", sanFrancesco],
  ]);
  const archivePairs = new Map([
    ["loc-2016652452", madeleine], ["loc-2024722637", ponteVecchio], ["loc-2001700916", sanFrancesco],
  ]);
  const pairFolder = "../poc/compare/pairs/";
  const pairCache = new Map();
  const fileName = (name) => typeof name === "string" && /^[\w.-]+\.jpg$/i.test(name);
  const coords = (value, count) => Array.isArray(value) && value.length === count && value.every(Number.isFinite);
  function canOverlay(pair) {
    const fit = pair?.alignment;
    return pair?.status === "candidate_real_pair" && /^[\w-]+$/.test(pair.id) &&
      [pair.historic, pair.photo].every((image) => fileName(image?.file) &&
        coords(image.size, 2) && image.size.every((size) => size > 0)) &&
      ["high", "medium", "low"].includes(fit?.confidence) &&
      Array.isArray(fit.H) && fit.H.length === 3 && fit.H.every((row) => coords(row, 3)) &&
      Array.isArray(fit.valid_region_historic) && fit.valid_region_historic.length >= 3 &&
      fit.valid_region_historic.every((point) => coords(point, 2));
  }
  function canCompare(pair) {
    return pair?.status === "candidate_real_pair" && /^[\w-]+$/.test(pair.id) &&
      [pair.historic, pair.photo].every((image) => fileName(image?.file) &&
        coords(image.size, 2) && image.size.every((size) => size > 0));
  }
  async function loadPair(id) {
    if (!pairCache.has(id)) {
      pairCache.set(id, fetch(pairFolder + id + ".json")
        .then((response) => response.ok ? response.json() : null)
        .then((pair) => canCompare(pair) && pair.id === id ? pair : null)
        .catch(() => null));
    }
    const pair = await pairCache.get(id);
    if (!pair) pairCache.delete(id);
    return pair;
  }

  async function mountVerified(host, ids) {
    if (!host || !ids?.length) return;
    const pairs = (await Promise.all(ids.map(loadPair))).filter(Boolean);
    if (!host.isConnected || !pairs.length) return;
    host.hidden = false;
    host.classList.add("ep-verified");
    host.innerHTML = `
      <h2>Два времени одного места</h2>
      <p class="ep-verified-intro">Перетаскивайте границу: слева старый лист, справа фотография. Кадры показаны целиком. Геометрическая подгонка доступна только там, где заданы опорные точки; её точность может быть ограниченной.</p>
      ${pairs.length > 1 ? `<label class="ep-verified-choice">Какой лист сравнить
        <select data-verified-pair>${pairs.map((pair) => {
          const title = pair.id === "madeleine-ph-benoist" ? "Филипп Бенуа · Библиотека Конгресса"
            : pair.id === "madeleine-benoist-carnavalet" ? "Филипп Бенуа · музей Карнавале"
            : pair.id === "madeleine-barescut-carnavalet" ? "Эстель де Барескю · музей Карнавале" : pair.historic.title;
          return `<option value="${esc(pair.id)}">${esc(title)}</option>`;
        }).join("")}</select></label>` : ""}
      <div class="ep-verified-modes" role="group" aria-label="Вид сравнения">
        <button type="button" data-verified-mode="curtain" aria-pressed="true">Шторка</button>
        <button type="button" data-verified-mode="then" aria-pressed="false">Рисунок</button>
        <button type="button" data-verified-mode="now" aria-pressed="false">Фото</button>
        <button type="button" data-verified-mode="fit" aria-pressed="false">Совместить</button>
      </div>
      <div class="ep-verified-stage">
        <img data-verified-old alt="" decoding="async">
        <img data-verified-raw alt="" decoding="async" hidden>
        <div class="ep-verified-mask" hidden><img data-verified-fit alt="" decoding="async"></div>
        <div class="ep-verified-curtain" hidden><img data-verified-curtain alt="" decoding="async"></div>
        <svg class="ep-verified-outline" aria-hidden="true" hidden><polygon fill="none" stroke="#fff7dc" stroke-width="2" stroke-dasharray="5 3" vector-effect="non-scaling-stroke"/></svg>
        <div class="ep-verified-handle" role="slider" tabindex="0" aria-label="Слева исторический вид, справа фотография" aria-valuemin="0" aria-valuemax="100" aria-valuenow="50"><span aria-hidden="true">‹  ›</span></div>
      </div>
      <div class="ep-verified-legend"><span>СЛЕВА · РИСУНОК</span><span>СПРАВА · ФОТО</span></div>
      <p class="ep-verified-caption" role="status"></p>
      <div class="ep-verified-credits"></div>`;
    const get = (query) => host.querySelector(query);
    const picker = get("[data-verified-pair]");
    const stage = get(".ep-verified-stage"), mask = get(".ep-verified-mask");
    const outline = get(".ep-verified-outline"), curtain = get(".ep-verified-curtain");
    const handle = get(".ep-verified-handle");
    const old = get("[data-verified-old]"), raw = get("[data-verified-raw]");
    const fit = get("[data-verified-fit]"), curtainImage = get("[data-verified-curtain]");
    let current = pairs[0], mode = "curtain", split = 50;

    function resize() {
      if (!canOverlay(current)) return;
      const [[a, b, c], [d, e, f], [g, h, i]] = current.alignment.H;
      fit.style.transform = `scale(${stage.clientWidth / current.historic.size[0]}) matrix3d(${a},${d},0,${g},${b},${e},0,${h},0,0,1,0,${c},${f},0,${i})`;
    }
    function show() {
      const fitAllowed = canOverlay(current);
      if (!fitAllowed && mode === "fit") mode = "curtain";
      old.hidden = mode === "now";
      raw.hidden = mode !== "now";
      mask.hidden = outline.hidden = mode !== "fit";
      curtain.hidden = handle.hidden = mode !== "curtain";
      curtain.style.clipPath = `inset(0 0 0 ${split}%)`;
      handle.style.left = split + "%";
      handle.setAttribute("aria-valuenow", String(Math.round(split)));
      handle.setAttribute("aria-valuetext", `${Math.round(split)}% старый вид, ${Math.round(100 - split)}% фотография`);
      const fitBtn = get('[data-verified-mode="fit"]');
      fitBtn.disabled = !fitAllowed;
      fitBtn.title = fitAllowed ? "Совмещение только внутри проверенного контура" :
        "Геометрия не подтверждена: здесь возможны только сравнение и шторка";
      host.querySelectorAll("[data-verified-mode]").forEach((button) =>
        button.setAttribute("aria-pressed", String(button.dataset.verifiedMode === mode)));
      get(".ep-verified-caption").textContent = mode === "fit"
        ? "Фото подогнано только в пределах пунктирного контура. Совпадение остальной части вида не подтверждено."
        : mode === "now" ? `Фото целиком, без подгонки · ${current.photo.date || "дата съёмки не указана"}`
        : mode === "curtain" ? `Граница ${Math.round(split)}% · слева старый рисунок, справа фото. Пропорции сохранены, точка съёмки может отличаться.`
        : `${current.historic.title} · ${current.historic.date || "дата не установлена"}`;
      if (mode === "fit") resize();
    }
    function select(pair) {
      current = pair;
      const { historic, photo, alignment } = pair;
      const [w, h] = historic.size;
      const [pw, ph] = photo.size;
      stage.style.setProperty("--ep-frame-ratio", String(w / h));
      old.src = pairFolder + historic.file;
      old.alt = historic.title;
      raw.src = fit.src = curtainImage.src = pairFolder + photo.file;
      raw.alt = photo.title;
      curtainImage.alt = "Фото без геометрической подгонки: " + photo.title;
      fit.alt = "Подогнанное по опорным точкам фото: " + photo.title;
      fit.style.width = pw + "px";
      fit.style.height = ph + "px";
      const points = alignment?.valid_region_historic;
      mask.style.clipPath = Array.isArray(points) && points.length > 2
        ? `polygon(${points.map(([x, y]) => `${100 * x / w}% ${100 * y / h}%`).join(", ")})` : "";
      outline.setAttribute("viewBox", `0 0 ${w} ${h}`);
      outline.querySelector("polygon").setAttribute("points",
        Array.isArray(points) ? points.map((point) => point.join(",")).join(" ") : "");
      const link = (url, label) => /^https?:\/\//.test(url || "")
        ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(label)}</a>` : "";
      get(".ep-verified-credits").innerHTML = `<p>${esc(historic.credit || historic.holding || "")}
        · ${link(historic.object_url, "Исторический оригинал")}</p><p>${esc(photo.credit || photo.author || "")}
        · ${link(photo.license_url, photo.license || "Лицензия")} · ${link(photo.object_url, "Источник фото")}
        · <a href="${pairFolder + photo.file}" target="_blank" rel="noopener">Фото без подгонки</a></p>
        <p><a href="../poc/compare/?view=originals#${pair.id}">Открыть полное сравнение и источники →</a></p>`;
      split = 50;
      mode = "curtain";
      show();
    }
    if (picker) picker.onchange = () => select(pairs.find((pair) => pair.id === picker.value) || pairs[0]);
    host.querySelectorAll("[data-verified-mode]").forEach((button) => {
      button.onclick = () => { mode = button.dataset.verifiedMode; show(); };
    });
    let pointer = null;
    function moveCurtain(clientX) {
      const bounds = stage.getBoundingClientRect();
      if (!bounds.width) return;
      split = Math.max(0, Math.min(100, (clientX - bounds.left) / bounds.width * 100));
      show();
    }
    stage.addEventListener("pointerdown", (event) => {
      if (mode !== "curtain") return;
      pointer = event.pointerId;
      stage.setPointerCapture(pointer);
      moveCurtain(event.clientX);
    });
    stage.addEventListener("pointermove", (event) => {
      if (pointer === event.pointerId && mode === "curtain") moveCurtain(event.clientX);
    });
    ["pointerup", "pointercancel", "lostpointercapture"].forEach((kind) =>
      stage.addEventListener(kind, () => { pointer = null; }));
    handle.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      split = event.key === "Home" ? 0 : event.key === "End" ? 100
        : Math.max(0, Math.min(100, split + (event.key === "ArrowRight" ? 5 : -5)));
      show();
    });
    const observer = new ResizeObserver(() => {
      if (!stage.isConnected) observer.disconnect();
      else if (mode === "fit") resize();
    });
    observer.observe(stage);
    select(current);
  }

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
        year: m.artYear || (kind === "mine" ? yearOf(m.date) : null) || "дата не установлена",
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
    const sessionKey = `city-on-paper-compare-v2:${key}`;
    let session = null;
    try { session = JSON.parse(localStorage.getItem(sessionKey) || "null"); } catch { /* private mode */ }
    const validIndex = (x, fallback) => Number.isInteger(x) && x >= 0 && x < fs.length ? x : fallback;
    let a = validIndex(session?.a, 0), b = validIndex(session?.b, fs.length - 1);
    if (fs.length < 2) b = 0;
    host.innerHTML = `<div data-verified-view hidden></div><div class="eptrack" role="group" aria-label="Кадры временной шкалы">${fs.map((f, i) => `<button type="button" class="epf ${f.kind}" data-f="${i}" aria-label="${esc(lab(f))}: ${esc(f.label)}">
        ${f.kind === "mine" ? `<img src="${esc(f.img)}" alt="${esc(f.label)}">` : imgTag(f.img, f.label || g.name)}<b>${esc(f.year || "")}</b><small>${esc(KIND[f.kind])}</small></button>`).join("")}
        <button type="button" class="epf add" id="epAdd"><span>＋</span><b>Моё фото</b><small>и точка съёмки</small></button></div>
      <div class="epgrid"><div class="epcmp">
        <div class="ctrls"><label>Было <select id="epA">${fs.map((f, i) => `<option value="${i}">${esc(lab(f))} — ${esc((f.label || "").slice(0, 50))}</option>`).join("")}</select></label>
          <label>Стало <select id="epB">${fs.map((f, i) => `<option value="${i}">${esc(lab(f))} — ${esc((f.label || "").slice(0, 50))}</option>`).join("")}</select></label></div>
        <div class="ep-modes" role="group" aria-label="Способ сравнения">
          <button type="button" data-compare-mode="slider" aria-pressed="true">Шторка</button>
          <button type="button" data-compare-mode="side" aria-pressed="false">Рядом</button>
          <button type="button" data-compare-mode="opacity" aria-pressed="false">Прозрачность</button>
          <button type="button" data-compare-mode="flip" aria-pressed="false">A/B</button>
        </div>
        <div class="ep-mode-tools">
          <label id="epAmountWrap" for="epAmount">Граница / прозрачность, % <input type="range" id="epAmount" min="0" max="100" value="50"></label>
          <button type="button" id="epFlipBtn" hidden>Показать другой кадр</button>
          <button type="button" id="epExport">Сохранить сравнение (JSON)</button>
        </div>
        <p class="ep-caution" id="epCaution">Оба кадра без искажения. Положение шторки не означает точного совпадения ракурса.</p>
         <p class="ep-curtain-readout" id="epReadout" role="status">Слева исторический вид · справа новый вид</p>
        <div class="epstage" id="epstage"><img id="epImB" alt=""><div class="epTop" id="epTop"><img id="epImA" alt=""></div>
          <div class="eph" id="epH2" role="slider" tabindex="0" aria-label="Граница сравнения: стрелки влево и вправо" aria-valuemin="0" aria-valuemax="100" aria-valuenow="50"><span>⇆</span></div>
          <span class="tag l" id="epTagA"></span><span class="tag r" id="epTagB"></span></div>
        <div class="ep-side" id="epSide" hidden>
          <figure><img id="epSideA" alt=""><figcaption id="epSideCapA"></figcaption></figure>
          <figure><img id="epSideB" alt=""><figcaption id="epSideCapB"></figcaption></figure>
        </div>
        <p class="mapnote" id="epCredit"></p></div>
        <div class="epside"><p class="eyebrow">Откуда смотрели</p><div class="lmap angles" id="epMap" aria-label="Карта: место и точки съёмки"></div>
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
    mountVerified(host.querySelector("[data-verified-view]"), atlasPairs.get(g.key));
    const selA = $("epA"), selB = $("epB"), st = $("epstage"), top = $("epTop"), h = $("epH2");
    selA.value = a; selB.value = b;
    let mode = ["slider", "side", "opacity", "flip"].includes(session?.mode) ? session.mode : "slider";
    let ratio = Number.isFinite(session?.ratio) ? Math.max(0, Math.min(100, session.ratio)) : 50;
    let flipA = false;
    const store = () => {
      try { localStorage.setItem(sessionKey, JSON.stringify({ a, b, mode, ratio })); }
      catch { /* storage may be disabled */ }
    };
    const showMode = () => {
      const side = mode === "side", op = mode === "opacity", flip = mode === "flip";
      st.hidden = side;
      $("epSide").hidden = !side;
      $("epAmountWrap").hidden = side || flip;
      $("epFlipBtn").hidden = !flip;
      h.hidden = side || op || flip;
      top.style.clipPath = mode === "slider" ? `inset(0 ${100 - ratio}% 0 0)` : "none";
      top.style.opacity = op ? String(ratio / 100) : flip ? String(flipA ? 1 : 0) : "1";
      h.style.left = ratio + "%";
      h.setAttribute("aria-valuenow", String(Math.round(ratio)));
      h.setAttribute("aria-valuetext", `${Math.round(ratio)}% первый кадр, ${Math.round(100 - ratio)}% второй кадр`);
      $("epAmount").value = String(Math.round(ratio));
      const first = fs[a], last = fs[b];
      $("epReadout").textContent = mode === "slider"
        ? `Слева ${lab(first)} · справа ${lab(last)} · граница ${Math.round(ratio)}%`
        : mode === "opacity" ? `Прозрачность ${Math.round(ratio)}% · кадры геометрически не подогнаны`
        : mode === "flip" ? "Режим A/B: переключайте кадры без наложения" : "Оба кадра целиком, в оригинальных пропорциях";
      $("epCaution").textContent = mode === "side"
        ? "Каждый кадр целиком и в собственном формате. Можно сравнить композицию, даже если ракурсы отличаются."
        : "Шторка показывает два самостоятельных изображения. Деформация не применяется; совпадение линии не доказывает одинаковый ракурс.";
      host.querySelectorAll("[data-compare-mode]").forEach((btn) =>
        btn.setAttribute("aria-pressed", String(btn.dataset.compareMode === mode)));
    };
    const setPos = (p) => {
      ratio = Math.max(0, Math.min(100, p));
      showMode(); store();
    };
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
      $("epSideA").src = A.img; $("epSideA").alt = ia.alt;
      $("epSideB").src = B.img; $("epSideB").alt = ib.alt;
      $("epSideCapA").textContent = `${lab(A)} · ${A.label}`;
      $("epSideCapB").textContent = `${lab(B)} · ${B.label}`;
      $("epTagA").textContent = lab(A); $("epTagB").textContent = lab(B);
      $("epCredit").innerHTML = [A, B].map((f) => `${f.url ? `<a href="${esc(safeLink(f.url))}" target="_blank" rel="noopener">${esc(lab(f))}: источник ↗</a>` : esc(lab(f))}${f.credit ? " · " + esc(f.credit) : ""}${f.lic ? `, ${/^https?:\/\//.test(f.licUrl || "") ? `<a href="${esc(f.licUrl)}" target="_blank" rel="noopener">${esc(f.lic)}</a>` : esc(f.lic)}` : ""}${f.camera ? ` · точка съёмки ${f.camera.lat.toFixed(5)}, ${f.camera.lon.toFixed(5)}, направление ${Math.round(f.camera.azimuth)}°` : ""}`).join("<br>");
      host.querySelectorAll(".epf[data-f]").forEach((x) => x.classList.toggle("on", +x.dataset.f === a || +x.dataset.f === b));
      drawCones();
      showMode(); store();
    };
    host.querySelectorAll("[data-compare-mode]").forEach((btn) => btn.onclick = () => {
      mode = btn.dataset.compareMode; flipA = false; showMode(); store();
    });
    $("epAmount").oninput = (event) => setPos(Number(event.target.value));
    $("epFlipBtn").onclick = () => { flipA = !flipA; showMode(); };
    $("epExport").onclick = () => {
      const summary = [fs[a], fs[b]].map((frame) => ({
        kind: frame.kind, year: frame.year, title: frame.label,
        source: frame.mineId ? null : frame.url || null, rights: frame.lic || "уточняются",
        local_image: Boolean(frame.mineId)
      }));
      const payload = { schema: "city-on-paper/compare-session/v1",
        city: c.name, place: g.name, mode, ratio, viewport_status: "viewpoint_unverified",
        selected_frames: summary, note: "Локальные изображения не включены в JSON. Исторический оригинал неизменён." };
      const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }));
      const link = document.createElement("a"); link.href = url;
      link.download = "city-on-paper-comparison.json"; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    };
    selA.onchange = () => { a = +selA.value; upd(); };
    selB.onchange = () => { b = +selB.value; upd(); };
    host.querySelectorAll(".epf[data-f]").forEach((x) => (x.onclick = () => { const i = +x.dataset.f; if (i === a || i === b) return; if (i < b) a = i; else b = i; selA.value = a; selB.value = b; upd(); st.scrollIntoView({ behavior: "smooth", block: "nearest" }); }));
    const move = (e) => { const r = st.getBoundingClientRect(); setPos((e.clientX - r.left) / r.width * 100); };
    st.addEventListener("pointerdown", (e) => { st.setPointerCapture(e.pointerId); move(e); st.onpointermove = move; });
    ["pointerup", "pointercancel", "lostpointercapture"].forEach(kind =>
      st.addEventListener(kind, () => (st.onpointermove = null)));
    h.addEventListener("keydown", (e) => { const v = +h.getAttribute("aria-valuenow"); if (e.key === "ArrowLeft") setPos(v - 5); else if (e.key === "ArrowRight") setPos(v + 5); else if (e.key === "Home") setPos(0); else if (e.key === "End") setPos(100); else return; e.preventDefault(); });
    setPos(ratio); upd();
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
      <p class="lede">Рассмотрите листы и фотографии разных лет. Выберите два кадра или добавьте свой снимок с этого места.</p>
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
  const mountArchiveVerified = (host, pictures) =>
    mountVerified(host, pictures?.map((image) => archivePairs.get(image.id)).find(Boolean));
  return { viewer, gallery, placePage, minePage, framesOf, mountArchiveVerified };
})();
