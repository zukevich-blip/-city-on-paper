/* Finding a modern view of a place: Panoramax (IGN France and the federation), Wikimedia Commons geosearch, and your own photo
 * (kept in the browser, never uploaded). Three different coordinates are never mixed: the BUILDING point (approximate, from a
 * geocoder), the CAMERA of a candidate photo (its own GPS) and, if known, the artist's standpoint (not used here). Candidates are
 * ranked by distance and by how well the camera's compass heading points at the building. Showing two independent pictures side
 * by side is not an alignment: geometric fitting stays with the verified control-point tools. */
(function () {
  const B = (window.CoPBook = window.CoPBook || { routes: {} });
  const E = (s) => B.esc(s);
  const R = 6371000, rad = (d) => (d * Math.PI) / 180, deg = (r) => (r * 180) / Math.PI;
  const dist = (a, b) => { const dl = rad(b.lat - a.lat), dn = rad(b.lon - a.lon), x = Math.sin(dl / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dn / 2) ** 2; return 2 * R * Math.asin(Math.sqrt(x)); };
  const bearing = (a, b) => { const y = Math.sin(rad(b.lon - a.lon)) * Math.cos(rad(b.lat)), x = Math.cos(rad(a.lat)) * Math.sin(rad(b.lat)) - Math.sin(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.cos(rad(b.lon - a.lon)); return (deg(Math.atan2(y, x)) + 360) % 360; };
  const angDiff = (a, b) => Math.abs(((a - b + 540) % 360) - 180);
  B.angleMath = { dist, bearing, angDiff };

  const SOURCES = [
    ["Panoramax IGN France", (p) => `https://panoramax.ign.fr/api/search?place_position=${p.lon},${p.lat}&place_distance=0-${p.r}&limit=24`],
    ["Panoramax (федерация)", (p) => `https://api.panoramax.xyz/api/search?place_position=${p.lon},${p.lat}&place_distance=0-${p.r}&limit=24`],
  ];
  const fetchJson = async (url, ms = 9000) => { const c = new AbortController(), t = setTimeout(() => c.abort(), ms); try { const r = await fetch(url, { signal: c.signal }); if (!r.ok) throw new Error("HTTP " + r.status); return await r.json(); } finally { clearTimeout(t); } };

  async function panoramax(name, urlFn, place) {
    const j = await fetchJson(urlFn(place));
    return (j.features || []).map((f) => {
      const [lon, lat] = (f.geometry || {}).coordinates || [], pr = f.properties || {}, a = f.assets || {};
      if (lat == null) return null;
      const href = (a.sd || a.hd || a.thumb || {}).href, th = (a.thumb || a.sd || {}).href;
      return { src: name, id: f.id, lat, lon, az: pr["view:azimuth"] != null ? Number(pr["view:azimuth"]) : null, date: (pr.datetimetz || pr.datetime || "").slice(0, 10), who: pr["geovisio:producer"] || "автор не указан", licence: pr.license || "см. страницу снимка", img: href, th: th || href, page: f.id ? `https://api.panoramax.xyz/api/collections/${f.collection}/items/${f.id}` : null };
    }).filter((c) => c && c.img);
  }
  async function commons(place) {
    const u = `https://commons.wikimedia.org/w/api.php?action=query&list=geosearch&gscoord=${place.lat}|${place.lon}&gsradius=${Math.min(place.r, 1000)}&gsnamespace=6&gslimit=20&format=json&origin=*`;
    const g = await fetchJson(u); const hits = (g.query && g.query.geosearch) || []; if (!hits.length) return [];
    const info = await fetchJson(`https://commons.wikimedia.org/w/api.php?action=query&prop=imageinfo&iiprop=url|extmetadata&iiurlwidth=640&titles=${encodeURIComponent(hits.map((h) => h.title).join("|"))}&format=json&origin=*`);
    const pages = Object.values((info.query && info.query.pages) || {});
    return hits.map((h) => { const pg = pages.find((x) => x.title === h.title), ii = pg && pg.imageinfo && pg.imageinfo[0]; if (!ii) return null; const m = ii.extmetadata || {};
      return { src: "Wikimedia Commons", id: h.pageid, lat: h.lat, lon: h.lon, az: null, date: ((m.DateTimeOriginal || {}).value || "").replace(/<[^>]+>/g, "").slice(0, 10), who: ((m.Artist || {}).value || "автор не указан").replace(/<[^>]+>/g, "").slice(0, 60), licence: ((m.LicenseShortName || {}).value || "см. страницу файла"), img: ii.thumburl || ii.url, th: ii.thumburl || ii.url, page: ii.descriptionurl }; }).filter(Boolean);
  }
  const rank = (c, place) => { const d = dist(place, c), look = c.az == null ? null : angDiff(c.az, bearing(c, place)); return { ...c, d: Math.round(d), look, score: d + (look == null ? 40 : Math.min(look, 90) * 1.2) }; };

  B.mountAngles = function (host, place) {
    if (!host || !place || !Number.isFinite(place.lat)) return;
    host.innerHTML = `<h2>Найти фото сегодня</h2><p class="small">Координаты здания приблизительные (${E(place.basis || "геокодер")}); у каждого снимка свои координаты камеры. Снимки подбираются по расстоянию и по тому, смотрит ли камера на здание. Рядом показываются два отдельных кадра: это не совмещение.</p>
      <div class="lt-tool angctl"><label for="angR"><span class="lt-legend">Радиус поиска</span> <b id="angRv">150</b> м</label><input id="angR" type="range" min="50" max="500" step="50" value="150"><button type="button" class="btn" id="angGo">Искать снимки рядом</button><label class="btn ghost angup" for="angFile">Моё фото</label><input id="angFile" type="file" accept="image/*" hidden></div>
      <p class="small" id="angNote" role="status"></p><div class="angres" id="angRes" role="list"></div><div class="angcmp" id="angCmp" hidden></div>`;
    const R_ = document.getElementById("angR"), note = document.getElementById("angNote"), res = document.getElementById("angRes"), cmp = document.getElementById("angCmp");
    R_.addEventListener("input", () => { document.getElementById("angRv").textContent = R_.value; });
    const show = (c) => { cmp.hidden = false; cmp.innerHTML = `<div class="curtain" id="angCurtain"><img class="cA" src="${E(place.image)}" alt="${E(place.title)}"><div class="cB"><img src="${E(c.img)}" alt="Фото сегодня"></div><input type="range" id="angRange" min="0" max="100" value="50" aria-label="Шторка между рисунком и фото"></div><p class="small">${E(c.who)}${c.date ? ", " + E(c.date) : ""}, ${E(c.licence)}. ${c.page ? `<a href="${E(c.page)}" target="_blank" rel="noopener">страница снимка ↗</a>` : "Снимок только у вас в браузере."} Два независимых кадра, перспективы не совпадают.</p>`;
      const cb = cmp.querySelector(".cB"); cb.style.clipPath = "inset(0 0 0 50%)"; cmp.querySelector("#angRange").addEventListener("input", (e) => { cb.style.clipPath = `inset(0 0 0 ${e.target.value}%)`; }); cmp.scrollIntoView({ block: "nearest" }); };
    document.getElementById("angFile").addEventListener("change", (e) => { const f = e.target.files[0]; if (f) show({ img: URL.createObjectURL(f), who: "Ваше фото", licence: "остаётся на вашем устройстве", date: "", page: null }); });
    document.getElementById("angGo").addEventListener("click", async () => {
      const p = { ...place, r: Number(R_.value) }; res.innerHTML = ""; note.textContent = "Ищу в Panoramax и Wikimedia Commons…";
      const jobs = [...SOURCES.map(([n, f]) => panoramax(n, f, p).then((l) => [n, l])), commons(p).then((l) => ["Wikimedia Commons", l])];
      const out = await Promise.allSettled(jobs); let all = [], bad = [];
      out.forEach((r, i) => { const n = i < SOURCES.length ? SOURCES[i][0] : "Wikimedia Commons"; if (r.status === "fulfilled") all = all.concat(r.value[1]); else bad.push(n); });
      const seen = new Set(); all = all.filter((c) => { const k = c.src + c.id; if (seen.has(k)) return false; seen.add(k); return true; }).map((c) => rank(c, p)).sort((a, b) => a.score - b.score).slice(0, 18);
      note.textContent = all.length ? `${B.plural(all.length, "кандидат", "кандидата", "кандидатов")}, лучшие первыми.${bad.length ? " Не ответили: " + bad.join(", ") + "." : ""}` : `Ничего не найдено в радиусе ${p.r} м.${bad.length ? " Не ответили: " + bad.join(", ") + "." : ""} Можно добавить своё фото.`;
      res.innerHTML = all.map((c, i) => `<button type="button" class="angc" data-i="${i}" role="listitem"><img src="${E(c.th)}" alt="" loading="lazy"><span><b>${E(c.src)}</b>${c.d} м от здания${c.look == null ? ", направление не указано" : c.look <= 35 ? `, камера смотрит на здание (±${Math.round(c.look)}°)` : `, камера смотрит в сторону (${Math.round(c.look)}° от здания)`}<i>${E(c.who)}${c.date ? " · " + E(c.date) : ""} · ${E(c.licence)}</i></span></button>`).join("");
      res.querySelectorAll(".angc").forEach((b) => b.addEventListener("click", () => show(all[Number(b.dataset.i)])));
      window.__angles = all;
    });
  };
})();
