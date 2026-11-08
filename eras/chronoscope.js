/* City on Paper Chronoscope.
 * A source-preserving, arbitrary-length historical sequence with an independently
 * controllable deep-zoom view. Compare consecutive originals; do not auto-align.
 */
"use strict";
(() => {
  const safeLink = value => /^https:\/\//i.test(value || "") ? value : "";
  const year = text => {
    const m = /(?:1[5-9]\d\d|20\d\d)/.exec(String(text || ""));
    return m ? Number(m[0]) : null;
  };
  const title = item => [item.year_label || "Без даты", item.title || item.alt || ""].filter(Boolean).join(" · ");
  const clamp = (n, low, high) => Math.max(low, Math.min(high, n));
  function mount(host, sourceImages) {
    if (!host) return false;
    const frames = (sourceImages || []).filter(f => f && typeof f.file === "string" && f.file.length)
      .map((f, i) => ({...f, originalIndex: i, sortYear: year(f.year_label || f.date)}))
      .sort((a, b) => (a.sortYear ?? 9999) - (b.sortYear ?? 9999) || a.originalIndex - b.originalIndex);
    if (frames.length < 2) { host.hidden = true; return false; }
    host.hidden = false;
    const selected = new Set(frames.map((_, i) => i));
    host.innerHTML = `
      <div class="cs-heading">
        <div><span class="eyebrow">Исследовательская мастерская · хронология</span>
          <h2>Все эпохи. Любое число кадров.</h2></div>
        <span class="cs-count" data-role="count"></span>
      </div>
      <p class="cs-note">Выберите изображения, которые хотите сравнить, и двигайте единую ленту времени.
        На каждом участке ползунка исходный лист плавно уступает место следующему.
        Можно увеличить архитектурную деталь и перемещать оба изображения совместно.</p>
      <details class="cs-picker" open><summary>Составить свою последовательность</summary>
        <div class="cs-choices" data-role="choices" role="group" aria-label="Выбранные изображения"></div>
        <p class="cs-note">По умолчанию включены все доступные кадры. Нужны минимум два. Последовательность идёт по датам источников, без домысленных промежуточных лет.</p>
      </details>
      <div class="cs-toolbar" role="group" aria-label="Увеличение и перемещение">
        <span>Рассмотреть детали</span>
        <button type="button" data-zoom="out" aria-label="Уменьшить изображение">−</button>
        <span data-role="zoom-value" class="cs-zoom-val">100%</span>
        <button type="button" data-zoom="in" aria-label="Увеличить изображение">+</button>
        <button type="button" data-zoom="reset">Сбросить масштаб</button>
      </div>
      <div class="cs-stage" data-role="stage" aria-label="Сравнение последовательных оригиналов; при увеличении перетаскивайте для просмотра деталей">
        <img data-role="a" alt="" draggable="false">
        <div class="cs-next" data-role="clip"><img data-role="b" alt="" draggable="false"></div>
        <div class="cs-divider" data-role="divider" aria-hidden="true"><span>⇄</span></div>
        <span class="cs-watermark">Исходники без геометрической подгонки</span>
      </div>
      <label class="cs-range-label">Положение на временной шкале
        <input type="range" min="0" step="1" value="0" data-role="range"
          aria-label="Переход между всеми выбранными историческими изображениями">
      </label>
      <div class="cs-keyframes" data-role="keyframes" role="group" aria-label="Перейти к году"></div>
      <p class="cs-status" data-role="status" role="status" aria-live="polite"></p>
      <div class="cs-provenance" data-role="provenance"></div>
      <p class="cs-note cs-warning">Разная камера, рисунок и перспектива могут создать ложное ощущение точного совпадения.
        Здесь нет автоматической реконструкции, искусственных кадров, кадрирования или деформации.
        Увеличение применяется только в браузере и одинаково к обоим изображениям.</p>`;
    const find = name => host.querySelector(`[data-role="${name}"]`);
    const input = find("range"), stage = find("stage"), imgA = find("a"), imgB = find("b");
    const clip = find("clip"), divider = find("divider"), status = find("status");
    let scale = 1, offsetX = 0, offsetY = 0, dragging = null;
    const activeFrames = () => frames.filter((_, i) => selected.has(i));
    function applyZoom() {
      const rect = stage.getBoundingClientRect();
      offsetX = clamp(offsetX, -(scale - 1) * rect.width / 2, (scale - 1) * rect.width / 2);
      offsetY = clamp(offsetY, -(scale - 1) * rect.height / 2, (scale - 1) * rect.height / 2);
      const tr = `translate(${offsetX}px, ${offsetY}px) scale(${scale})`;
      imgA.style.transform = tr;
      imgB.style.transform = tr;
      stage.classList.toggle("is-zoomed", scale > 1);
      find("zoom-value").textContent = Math.round(scale * 100) + "%";
    }
    function scaleTo(next) {
      scale = clamp(next, 1, 4);
      if (scale === 1) { offsetX = 0; offsetY = 0; }
      applyZoom();
    }
    function sourceCard(frame, descriptor) {
      const p = document.createElement("p");
      const b = document.createElement("strong");
      b.textContent = descriptor + ": " + title(frame) + ". ";
      p.append(b, document.createTextNode((frame.institution || "Хранитель уточняется") + ". "));
      const rights = document.createElement("span");
      rights.textContent = frame.rights_short || frame.rights || "Права уточняются";
      p.append(rights);
      const url = safeLink(frame.object_url || frame.url);
      if (url) {
        const a = document.createElement("a");
        a.href = url; a.target = "_blank"; a.rel = "noopener noreferrer";
        a.textContent = "Оригинал в архиве";
        p.append(" · ", a);
      }
      return p;
    }
    function render() {
      const all = activeFrames(), n = all.length;
      if (n < 2) return;
      input.max = String((n - 1) * 100);
      input.value = String(clamp(+input.value || 0, 0, +input.max));
      const loc = (+input.value) / 100, index = Math.min(Math.floor(loc), n - 2);
      const percent = Math.round(clamp((loc - index) * 100, 0, 100));
      const a = all[index], b = all[index + 1];
      if (imgA.getAttribute("src") !== a.file) imgA.src = a.file;
      if (imgB.getAttribute("src") !== b.file) imgB.src = b.file;
      imgA.alt = "Ранний кадр: " + title(a);
      imgB.alt = "Следующий кадр: " + title(b);
      clip.style.clipPath = `inset(0 ${100 - percent}% 0 0)`;
      divider.style.left = percent + "%";
      input.setAttribute("aria-valuetext", `Кадры ${index + 1} и ${index + 2} из ${n}, ${percent}%: ${a.year_label || "без даты"} к ${b.year_label || "без даты"}`);
      status.textContent = `Кадры ${index + 1}–${index + 2} из ${n} · ${a.year_label || "без даты"} → ${b.year_label || "без даты"} · ${percent}%`;
      find("count").textContent = n + " из " + frames.length + " кадров";
      const provenance = find("provenance");
      provenance.replaceChildren(sourceCard(a, "Исходный"), sourceCard(b, "Следующий"));
      find("keyframes").querySelectorAll("button").forEach((button, i) =>
        button.setAttribute("aria-current", String(i === Math.round(loc))));
      applyZoom();
    }
    function rebuildChoices() {
      const choices = find("choices");
      choices.replaceChildren();
      frames.forEach((frame, i) => {
        const label = document.createElement("label");
        label.className = "cs-choice";
        const check = document.createElement("input");
        check.type = "checkbox"; check.checked = selected.has(i);
        check.disabled = selected.size <= 2 && check.checked;
        check.addEventListener("change", () => {
          if (check.checked) selected.add(i); else if (selected.size > 2) selected.delete(i);
          input.value = "0";
          rebuildChoices(); rebuildTimeline();
        });
        const text = document.createElement("span");
        text.textContent = title(frame);
        label.append(check, text);
        choices.append(label);
      });
    }
    function rebuildTimeline() {
      const box = find("keyframes"), active = activeFrames();
      input.max = String((active.length - 1) * 100);
      input.value = String(clamp(+input.value || 0, 0, +input.max));
      box.replaceChildren();
      active.forEach((f, i) => {
        const b = document.createElement("button");
        b.type = "button"; b.textContent = f.year_label || "Без даты";
        b.title = title(f);
        b.setAttribute("aria-label", "Перейти к " + title(f));
        b.addEventListener("click", () => { input.value = String(i * 100); render(); });
        box.append(b);
      });
      render();
    }
    host.querySelector('[data-zoom="in"]').addEventListener("click", () => scaleTo(scale + .5));
    host.querySelector('[data-zoom="out"]').addEventListener("click", () => scaleTo(scale - .5));
    host.querySelector('[data-zoom="reset"]').addEventListener("click", () => scaleTo(1));
    stage.addEventListener("pointerdown", e => {
      if (e.button !== undefined && e.button !== 0) return;
      dragging = { id: e.pointerId, x: e.clientX, y: e.clientY, ox: offsetX, oy: offsetY };
      stage.setPointerCapture(e.pointerId);
      if (scale === 1) {
        const r = stage.getBoundingClientRect(), all = activeFrames();
        input.value = String(Math.round(((all.length - 1) * 100) * clamp((e.clientX - r.left) / r.width, 0, 1)));
        render();
      }
    });
    stage.addEventListener("pointermove", e => {
      if (!dragging || dragging.id !== e.pointerId) return;
      if (scale > 1) {
        offsetX = dragging.ox + (e.clientX - dragging.x);
        offsetY = dragging.oy + (e.clientY - dragging.y);
        applyZoom();
      } else {
        const r = stage.getBoundingClientRect(), all = activeFrames();
        input.value = String(Math.round(((all.length - 1) * 100) * clamp((e.clientX - r.left) / r.width, 0, 1)));
        render();
      }
    });
    ["pointerup", "pointercancel", "lostpointercapture"].forEach(type =>
      stage.addEventListener(type, () => { dragging = null; }));
    input.addEventListener("input", render);
    rebuildChoices(); rebuildTimeline();
    return true;
  }
  window.CityOnPaperChronoscope = Object.freeze({ mount });
})();
