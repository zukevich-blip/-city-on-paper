/* City on Paper: reversible three-epoch historical comparison.
 * Native browser controls; no third-party slider dependency or source alterations.
 * A→B over 0–50%, B→C over 50–100%. Source images are never warped.
 */
"use strict";
(function () {
  const safeURL = (s) => typeof s === "string" && /^https:\/\//i.test(s) ? s : "";
  const parseYear = (s) => {
    const match = /(?:1[5-9]\d{2}|20\d{2})/.exec(String(s || ""));
    return match ? Number(match[0]) : null;
  };
  const label = (x) => [x.year_label || "Дата неизвестна", x.title || ""].filter(Boolean).join(" · ");

  function mount(host, pictures) {
    if (!host) return false;
    const frames = (pictures || []).filter(x => x && x.file && typeof x.file === "string")
      .map((frame, originalIndex) => ({ ...frame, originalIndex, sortYear: parseYear(frame.year_label || frame.date) }))
      .sort((a, b) => (a.sortYear ?? 9999) - (b.sortYear ?? 9999) || a.originalIndex - b.originalIndex);
    if (frames.length < 3) {
      host.hidden = true;
      return false;
    }

    host.hidden = false;
    host.innerHTML = `
      <div class="cp3-title"><div><span class="eyebrow">Лента времени · эксперимент</span>
        <h2>Три эпохи. Один ползунок.</h2></div>
        <span class="cp3-mark">Без подмены оригиналов</span></div>
      <p class="cp3-lead">От литографии через промежуточный снимок к современному виду.
        Перемещайте ползунок: слева ранняя эпоха, посередине следующая, справа последняя.
        Можно выбрать любые три доступных изображения.</p>
      <div class="cp3-selects" role="group" aria-label="Три кадра для сравнения">
        <label>Старая эпоха <select data-role="first"></select></label>
        <label>Промежуточная <select data-role="middle"></select></label>
        <label>Новая эпоха <select data-role="last"></select></label>
      </div>
      <div class="cp3-upload">
        <label for="cp3Upload">Своя фотография с того же места <input id="cp3Upload" data-role="upload-photo" type="file" accept="image/*"></label>
        <button type="button" data-role="remove-photo" hidden>Убрать мой снимок</button>
        <span data-role="photo-status" role="status" aria-live="polite">Снимок останется в браузере: мы его не получаем и не публикуем.</span>
      </div>
      <div class="cp3-stage" data-role="stage" aria-label="Сравнение трёх изображений без деформации">
        <img data-role="image-first" alt="" draggable="false">
        <div class="cp3-layer" data-role="layer-middle"><img data-role="image-middle" alt="" draggable="false"></div>
        <div class="cp3-layer" data-role="layer-last"><img data-role="image-last" alt="" draggable="false"></div>
        <div class="cp3-guide" data-role="guide" aria-hidden="true"><span>◀ ▶</span></div>
        <span class="cp3-corner">Исторические оригиналы не искажены</span>
      </div>
      <input data-role="position" type="range" min="0" max="100" step="1" value="50"
        aria-label="Положение ползунка времени от старого изображения к современному">
      <div class="cp3-ends" aria-hidden="true">
        <button type="button" data-go="0">Сначала</button>
        <button type="button" data-go="50">Середина</button>
        <button type="button" data-go="100">Сегодня</button>
      </div>
      <div data-role="phase" class="cp3-phase" role="status" aria-live="polite"></div>
      <div data-role="sources" class="cp3-sources"></div>
      <p class="cp3-caution">Важно: на этих кадрах могут отличаться угол обзора, высота и положение камеры.
        Плавный переход помогает увидеть перемены, но не доказывает совпадение ракурсов
        или точность реконструкции. Годы и авторство указаны по сведениям источников.</p>`;

    const find = (role) => host.querySelector(`[data-role="${role}"]`);
    const selectors = ["first", "middle", "last"].map(find);
    const initial = [0, Math.floor((frames.length - 1) / 2), frames.length - 1];
    selectors.forEach((select, i) => {
      frames.forEach((frame, index) => select.add(new Option(label(frame), String(index))));
      select.value = String(initial[i]);
    });
    const stage = find("stage");
    const slider = find("position");
    const guide = find("guide");
    const middle = find("layer-middle");
    const last = find("layer-last");
    const chosen = () => selectors.map(s => frames[Number(s.value)]);
    const upload = find("upload-photo"), remove = find("remove-photo"), photoStatus = find("photo-status");
    let localURL = null, localFrame = null;
    function removeLocal() {
      if (localURL) URL.revokeObjectURL(localURL);
      localURL = null;
      if (localFrame) {
        const index = frames.indexOf(localFrame);
        if (index !== -1) frames.splice(index, 1);
        selectors.forEach(select => {
          select.querySelectorAll('[data-user-photo="true"]').forEach(option => option.remove());
          if (select.selectedIndex < 0 || !frames[Number(select.value)]) select.value = String(frames.length - 1);
        });
        localFrame = null;
      }
      remove.hidden = true;
      upload.value = "";
      photoStatus.textContent = "Снимок убран. Данные не отправлялись на сайт.";
      updateFrames();
    }
    remove.addEventListener("click", removeLocal);
    upload.addEventListener("change", () => {
      const file = upload.files && upload.files[0];
      if (!file) return;
      if (!file.type.startsWith("image/") || file.size > 20 * 1024 * 1024) {
        photoStatus.textContent = "Выберите изображение размером до 20 МБ.";
        upload.value = "";
        return;
      }
      if (localFrame) {
        if (localURL) URL.revokeObjectURL(localURL);
        const index = frames.indexOf(localFrame);
        if (index !== -1) frames.splice(index, 1);
        selectors.forEach(select => select.querySelectorAll('[data-user-photo="true"]').forEach(option => option.remove()));
      }
      localURL = URL.createObjectURL(file);
      localFrame = {
        file: localURL, year_label: "Моё фото · дата не указана",
        title: file.name, alt: "Снимок посетителя, выбранный на его устройстве",
        institution: "Личный снимок (не опубликован)", url: "", kind: "now",
      };
      frames.push(localFrame);
      selectors.forEach(select => {
        const opt = new Option(label(localFrame), String(frames.length - 1));
        opt.dataset.userPhoto = "true";
        select.add(opt);
      });
      selectors[2].value = String(frames.length - 1);
      remove.hidden = false;
      photoStatus.textContent = "Снимок добавлен только в этот просмотр. Выберите две другие эпохи и двигайте ползунок. Дата и совпадение ракурса не проверены.";
      updateFrames();
    });

    function updateFrames() {
      const three = chosen();
      ["first", "middle", "last"].forEach((role, i) => {
        const im = find("image-" + role);
        if (im.getAttribute("src") !== three[i].file) im.src = three[i].file;
        im.alt = label(three[i]) + ". " + (three[i].alt || "Архивное изображение");
      });
      const sources = find("sources");
      sources.replaceChildren();
      three.forEach((frame, index) => {
        const item = document.createElement("p");
        const prefix = document.createElement("strong");
        prefix.textContent = ["Ранний", "Промежуточный", "Поздний"][index] + ": ";
        item.append(prefix, document.createTextNode(label(frame) + " · " + (frame.institution || "источник уточняется") + " "));
        const url = safeURL(frame.url || frame.object_url);
        if (url) {
          const a = document.createElement("a");
          a.href = url;
          a.target = "_blank";
          a.rel = "noopener noreferrer";
          a.textContent = "Открыть первоисточник";
          item.append(a);
        }
        sources.append(item);
      });
      move();
    }

    function move() {
      const p = Math.max(0, Math.min(100, Number(slider.value) || 0));
      // Middle becomes fully visible at exactly 50%; last becomes fully visible at 100%.
      middle.style.clipPath = `inset(0 ${100 - Math.min(100, p * 2)}% 0 0)`;
      last.style.clipPath = `inset(0 ${100 - Math.max(0, (p - 50) * 2)}% 0 0)`;
      guide.style.left = p + "%";
      const framesNow = chosen();
      const left = p <= 50 ? framesNow[0] : framesNow[1];
      const right = p <= 50 ? framesNow[1] : framesNow[2];
      find("phase").textContent = `${p}% · ${left.year_label || "раньше"} → ${right.year_label || "позже"}`;
      slider.setAttribute("aria-valuetext", `${p} процентов, ${left.year_label || "раньше"} к ${right.year_label || "позже"}`);
    }

    const pointAt = (clientX) => {
      const rect = stage.getBoundingClientRect();
      slider.value = String(Math.round(100 * (clientX - rect.left) / rect.width));
      move();
    };
    let activePointer = null;
    stage.addEventListener("pointerdown", (e) => {
      activePointer = e.pointerId;
      stage.setPointerCapture(e.pointerId);
      pointAt(e.clientX);
    });
    stage.addEventListener("pointermove", (e) => {
      if (activePointer === e.pointerId) pointAt(e.clientX);
    });
    for (const kind of ["pointerup", "pointercancel", "lostpointercapture"])
      stage.addEventListener(kind, () => { activePointer = null; });
    slider.addEventListener("input", move);
    selectors.forEach(select => select.addEventListener("change", updateFrames));
    host.querySelectorAll("[data-go]").forEach(button => {
      button.addEventListener("click", () => {
        slider.value = button.dataset.go;
        move();
        slider.focus();
      });
    });
    updateFrames();
    return true;
  }
  window.CityOnPaperThreeEpochs = Object.freeze({ mount });
}());
