/* City on Paper — common study desk for every city, not just hand-curated exhibits.
 * User-selected works, original-source credits, multi-frame compare and single-leaf zoom.
 * Different buildings / viewpoints NEVER presented as aligned photographs.
 */
"use strict";
(() => {
  const safe = u => typeof u === "string" && (/^https:\/\//.test(u) ||
    /^(?:\.\.\/assets\/|\.\.\/poc\/|thumbs\/|now\/|img\/)/.test(u)) ? u : "";
  const year = value => {
    const match = /(?:1[5-9]\d{2}|20\d{2})/.exec(String(value || ""));
    return match ? +match[0] : null;
  };
  const el = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  function normalize(raw) {
    const seen = new Set();
    return (raw || []).map((w, n) => {
      const raw0 = w.image || w.file;
      const image = safe(window.Atlas && Atlas.thumb ? Atlas.thumb(raw0) : raw0); // self-hosted preview first
      const source = safe(w.url || w.object_url || w.page);
      const title = w.title_original || w.name || w.title || "Без названия";
      return {
        id: String(n), file: image, url: source,
        title: String(title), year_label: String(w.date || w.date_display || "Без даты"),
        author: String(w.artist || w.maker || w.author || "Автор уточняется"),
        institution: String(w.institution || w.source || "Хранитель уточняется"),
        rights_short: String(w.rights_label || w.license_label || w.license || w.rights || "Права уточняются"),
        technique: String(w.medium || w.technique || ""),
        kind: String(w.kind || "historic"),
        sortYear: year(w.date || w.date_display || title)
      };
    }).filter(w => {
      if (!w.file) return false;
      const key = w.url || w.file;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    }).sort((a, b) => (a.sortYear ?? 9999) - (b.sortYear ?? 9999) ||
      a.title.localeCompare(b.title, "ru"));
  }
  function mount(host, city, works) {
    if (!host) return { records: 0 };
    const items = normalize(works);
    const chosen = new Set(items.slice(0, Math.min(3, items.length)).map(w => w.id));
    host.innerHTML = `
      <div class="citylab-heading"><span class="eyebrow">Доступно в каждом городе</span>
        <h2>Литографии и изображения: составьте своё сравнение</h2>
        <p>Выберите любые доступные листы, фотографии или авторов из коллекции города.
        Один ползунок соединит выбранные кадры по датам. <strong>Это может быть обзор разных мест одного города</strong>,
        а не точное сопоставление одного здания. Для установленного исторического места используйте отдельную
        вкладку «Одно место — разные эпохи».</p></div>
      <div class="citylab-controls">
        <label>Искать по автору, произведению или году
          <input type="search" data-role="search" placeholder="Бенуа, площадь, 1850…" autocomplete="off"></label>
        <span data-role="status" role="status" aria-live="polite"></span>
      </div>
      <div class="citylab-local-photo">
        <label>Добавить свою фотографию к сравниваемым кадрам
          <input type="file" data-role="user-photo" accept="image/*"></label>
        <button type="button" data-role="remove-photo" hidden>Убрать мою фотографию</button>
        <span data-role="photo-status" role="status">Фотография останется только в браузере.
        Она не отправляется в музей и не означает, что исторический ракурс совпадает.</span>
      </div>
      <div class="citylab-results" data-role="results" aria-label="Каталог доступных изображений города"></div>
      <div class="citylab-more"><button type="button" data-role="more" hidden>Показать ещё произведения</button></div>
      <div class="citylab-selected" data-role="selected" role="status" aria-live="polite"></div>
      <div class="citylab-time" data-role="timeline"></div>
      <p class="citylab-warning">Если для города есть только один лист, шторка недоступна,
        зато можно увеличить изображение и проверить подписи и первоисточник.
        Когда появятся исторические фотографии того же места и современные снимки с проверенным ракурсом,
        они получат отдельную историю. Архивные карточки без точной датировки не считаются доказанной хронологией.</p>
      <dialog class="citylab-dialog" data-role="viewer" aria-label="Просмотр произведения крупным планом">
        <div class="citylab-viewer-tools">
          <strong data-role="viewer-title"></strong>
          <button type="button" data-role="zoom-out" aria-label="Уменьшить масштаб">−</button>
          <span data-role="zoom-value">100%</span>
          <button type="button" data-role="zoom-in" aria-label="Увеличить масштаб">+</button>
          <button type="button" data-role="zoom-reset">Сбросить</button>
          <button type="button" data-role="close">Закрыть</button>
        </div>
        <div class="citylab-viewer-stage" data-role="viewer-stage">
          <img data-role="viewer-image" alt="" draggable="false">
        </div>
        <div class="citylab-viewer-facts" data-role="viewer-facts"></div>
      </dialog>`;
    const find = role => host.querySelector(`[data-role="${role}"]`);
    const search = find("search"), results = find("results"),
      selected = find("selected"), timeline = find("timeline"),
      more = find("more"), status = find("status");
    let visibleCount = 18, localObjectURL = null, localFrame = null;
    const countOfSelected = () => items.filter(w => chosen.has(w.id));
    const photoInput = find("user-photo"), removePhoto = find("remove-photo"), photoStatus = find("photo-status");
    function removeLocalPhoto() {
      if (!localFrame) return;
      chosen.delete(localFrame.id);
      const i = items.indexOf(localFrame);
      if (i >= 0) items.splice(i, 1);
      if (localObjectURL) URL.revokeObjectURL(localObjectURL);
      localObjectURL = null; localFrame = null; photoInput.value = "";
      removePhoto.hidden = true;
      photoStatus.textContent = "Личный снимок убран, файл не передавался на сервер.";
      draw(); renderTimeline();
    }
    removePhoto.addEventListener("click", removeLocalPhoto);
    photoInput.addEventListener("change", () => {
      const file = photoInput.files && photoInput.files[0];
      if (!file) return;
      if (!file.type.startsWith("image/") || file.size > 20 * 1024 * 1024) {
        photoInput.value = "";
        photoStatus.textContent = "Нужно изображение размером до 20 МБ.";
        return;
      }
      if (localFrame) {
        chosen.delete(localFrame.id);
        const i = items.indexOf(localFrame);
        if (i >= 0) items.splice(i, 1);
        if (localObjectURL) URL.revokeObjectURL(localObjectURL);
      }
      localObjectURL = URL.createObjectURL(file);
      localFrame = {
        id: "local-photo", file: localObjectURL, url: "",
        title: "Моя фотография: " + file.name,
        year_label: "Снимок посетителя, дата не проверена",
        author: "Посетитель", institution: "Только на устройстве",
        rights_short: "Личный снимок не опубликован",
        technique: "Фотография", kind: "local", sortYear: 9999
      };
      items.push(localFrame); chosen.add(localFrame.id);
      removePhoto.hidden = false;
      photoStatus.textContent = "Фото добавлено локально. Можно сравнить со старинными листами, но совпадение точки съёмки не проверено.";
      draw(); renderTimeline();
    });

    function renderTimeline() {
      const frames = countOfSelected();
      selected.textContent = frames.length
        ? `Выбрано ${frames.length} из ${items.length} доступных изображений.`
        : "Выберите хотя бы одно изображение для изучения.";
      timeline.replaceChildren();
      if (frames.length >= 2) {
        if (!window.CityOnPaperChronoscope) {
          timeline.append(el("p", "note", "Модуль временной шкалы не загрузился."));
          return;
        }
        const area = el("section", "chronoscope");
        area.setAttribute("aria-label", "Пользовательское сравнение произведений города");
        timeline.append(area);
        window.CityOnPaperChronoscope.mount(area, frames);
      } else if (frames.length === 1) {
        const p = el("p", "note", "Один подлинный лист: изучите его увеличенно. Сравнение появится, когда выберете второй.");
        const b = el("button", "citylab-focus", "Увеличить выбранное произведение");
        b.type = "button"; b.addEventListener("click", () => openViewer(frames[0]));
        timeline.append(p, b);
      } else timeline.append(el("p", "note", "Отметьте изображения в каталоге выше."));
    }
    function draw() {
      const query = search.value.toLocaleLowerCase("ru").trim();
      const filtered = items.filter(w => !query || [w.title, w.author, w.year_label, w.institution, w.technique]
        .some(value => value.toLocaleLowerCase("ru").includes(query)));
      results.replaceChildren();
      for (const w of filtered.slice(0, visibleCount)) {
        const item = el("article", "citylab-item");
        const img = el("img", "citylab-thumb");
        img.src = w.file; img.alt = w.title; img.loading = "lazy"; img.decoding = "async";
        img.addEventListener("error", () => { img.hidden = true; });
        const meta = el("div", "citylab-item-meta");
        const h = el("strong", "", w.title);
        const p = el("p", "", `${w.year_label} · ${w.author}`);
        const small = el("small", "", w.institution);
        const actions = el("div", "citylab-actions");
        const label = el("label", "citylab-check");
        const box = el("input");
        box.type = "checkbox"; box.checked = chosen.has(w.id);
        box.setAttribute("aria-label", "Добавить к сравнению: " + w.title);
        box.addEventListener("change", () => {
          if (box.checked) chosen.add(w.id); else chosen.delete(w.id);
          renderTimeline();
        });
        label.append(box, el("span", "", "Сравнить"));
        const view = el("button", "", "Увеличить");
        view.type = "button"; view.addEventListener("click", () => openViewer(w));
        actions.append(label, view);
        if (w.url) {
          const a = el("a", "", "Источник");
          a.href = w.url; a.target = "_blank"; a.rel = "noopener noreferrer";
          actions.append(a);
        }
        meta.append(h, p, small, actions);
        item.append(img, meta); results.append(item);
      }
      status.textContent = `Показано ${Math.min(filtered.length, visibleCount)} из ${filtered.length} по текущему фильтру; всего ${items.length} доступных изображений.`;
      more.hidden = filtered.length <= visibleCount;
      if (!more.hidden) more.textContent = `Показать следующие (${filtered.length - visibleCount})`;
      more.onclick = () => { visibleCount += 18; draw(); };
    }
    const viewer = find("viewer"), bigImg = find("viewer-image"),
      facts = find("viewer-facts"), stage = find("viewer-stage");
    let zoom = 1, vx = 0, vy = 0, pan = null;
    function applyZoom() {
      const bounds = stage.getBoundingClientRect();
      const maxX = Math.max(0, (zoom - 1) * bounds.width / 2);
      const maxY = Math.max(0, (zoom - 1) * bounds.height / 2);
      vx = Math.max(-maxX, Math.min(maxX, vx));
      vy = Math.max(-maxY, Math.min(maxY, vy));
      bigImg.style.transform = `translate(${vx}px,${vy}px) scale(${zoom})`;
      viewer.querySelector('[data-role="zoom-value"]').textContent = Math.round(zoom * 100) + "%";
    }
    function openViewer(w) {
      zoom = 1; vx = 0; vy = 0;
      find("viewer-title").textContent = w.title;
      bigImg.src = w.file; bigImg.alt = w.title;
      facts.replaceChildren();
      for (const [label, text] of [["Год", w.year_label], ["Автор", w.author],
        ["Техника", w.technique || "Уточняется"], ["Хранитель", w.institution],
        ["Права", w.rights_short]]) {
        const p = el("p", ""); const strong = el("strong", "", label + ": ");
        p.append(strong, document.createTextNode(text)); facts.append(p);
      }
      if (w.url) {
        const a = el("a", "", "Посмотреть оригинал у хранителя");
        a.href = w.url; a.target = "_blank"; a.rel = "noopener noreferrer";
        facts.append(a);
      }
      applyZoom();
      if (typeof viewer.showModal === "function") viewer.showModal(); else viewer.open = true;
    }
    find("zoom-in").addEventListener("click", () => { zoom = Math.min(4, zoom + .5); applyZoom(); });
    find("zoom-out").addEventListener("click", () => { zoom = Math.max(1, zoom - .5); applyZoom(); });
    find("zoom-reset").addEventListener("click", () => { zoom = 1; vx = vy = 0; applyZoom(); });
    find("close").addEventListener("click", () => viewer.close());
    viewer.addEventListener("click", e => { if (e.target === viewer) viewer.close(); });
    stage.addEventListener("pointerdown", e => {
      if (zoom <= 1 || (e.button !== undefined && e.button !== 0)) return;
      pan = { x: e.clientX, y: e.clientY, vx, vy, id: e.pointerId };
      stage.setPointerCapture(e.pointerId);
    });
    stage.addEventListener("pointermove", e => {
      if (!pan || pan.id !== e.pointerId) return;
      vx = pan.vx + e.clientX - pan.x;
      vy = pan.vy + e.clientY - pan.y;
      applyZoom();
    });
    for (const event of ["pointerup", "pointercancel", "lostpointercapture"])
      stage.addEventListener(event, () => { pan = null; });
    search.addEventListener("input", () => { visibleCount = 18; draw(); });
    draw(); renderTimeline();
    return { records: items.length, selected: countOfSelected().length };
  }
  window.CityOnPaperCityLab = Object.freeze({ mount, normalize });
})();
