/* Optional Paris research tools. Keep the regular atlas usable if an archive is unavailable. */
"use strict";
window.AtlasPilot = (() => {
  const ids = ["320292326", "320292157", "320293177"];
  const source = "https://www.loc.gov/item/2012586603/";
  let osd;

  function add(parent, tag, text) {
    const element = document.createElement(tag);
    if (text) element.textContent = text;
    parent.append(element);
    return element;
  }

  function link(parent, url, label) {
    const anchor = add(parent, "a", label);
    anchor.href = url;
    return anchor;
  }

  function loadViewer() {
    return osd ||= new Promise((resolve, reject) => {
      const script = add(document.head, "script");
      script.src = "vendor/openseadragon-6.1.1/openseadragon.min.js";
      script.onload = () => resolve(window.OpenSeadragon);
      script.onerror = reject;
    }).catch(error => { osd = null; throw error; });
  }

  async function works(host, city) {
    if (city.id !== "paris") return;
    host.hidden = false;
    add(host, "h2", "Три листа Бенуа крупным планом");
    const route = add(host, "p");
    link(route, "../poc/compare/?journey=1#madeleine-benoist-carnavalet", "Продолжить по Парижу: Мадлен тогда и сейчас");
    const grid = add(host, "div");
    grid.className = "pilot-grid";
    try {
      const response = await fetch("../data/curation/benoist-paris-musees-v1.json");
      if (!response.ok) throw new Error("catalogue");
      const {items} = await response.json();
      if (!host.isConnected) return;
      for (const id of ids) {
        const item = items.find(row => row.source_id === id && row.rights === "cc0");
        if (!item) continue;
        const card = add(grid, "article");
        card.id = "pilot-" + id;
        add(card, "h3", item.name);
        const preview = add(card, "img");
        preview.src = item.image;
        preview.alt = item.name;
        preview.loading = "lazy";
        const button = add(card, "button", "Увеличить");
        button.type = "button";
        button.setAttribute("aria-label", "Увеличить: " + item.name);
        const info = add(card, "details");
        add(info, "summary", "Карточка произведения");
        const fields = [
          ["Название в каталоге", item.title_original],
          ["Создание", item.date],
          ["Изображённая эпоха", "Точный год не установлен"],
          ["Изображённое место", item.name + ", Париж"],
          ["Точка художника", "Не подтверждена"],
          ["Техника", item.medium],
          ["Хранитель", item.source],
          ["Инвентарный номер", item.inventory_no || "См. музейную запись"],
          ["Права", item.license_label]
        ];
        const list = add(info, "dl");
        for (const [label, value] of [...fields, ...item.creator_roles.map(a => [a.role, a.name])]) {
          add(list, "dt", label);
          add(list, "dd", value);
        }
        link(info, item.url, "Музейная запись");
        link(info, item.manifest_url, "Цифровой манифест");
        link(info, item.license_url, "Условия CC0");
        button.onclick = () => openWork(item, button);
      }
    } catch {
      grid.textContent = "Коллекция сейчас недоступна.";
    }
  }

  async function openWork(item, opener) {
    const dialog = add(document.body, "dialog");
    dialog.className = "pilot-dialog";
    dialog.setAttribute("aria-label", item.name);
    add(dialog, "h2", item.name);
    const bar = add(dialog, "div");
    bar.className = "pilot-controls";
    const close = add(bar, "button", "Закрыть");
    const plus = add(bar, "button", "+");
    plus.setAttribute("aria-label", "Увеличить");
    const minus = add(bar, "button", "−");
    minus.setAttribute("aria-label", "Уменьшить");
    const reset = add(bar, "button", "Вписать");
    for (const control of [plus, minus, reset]) control.disabled = true;
    link(bar, item.image_large, "Полный размер у музея");
    const stage = add(dialog, "div");
    stage.className = "pilot-zoom";
    const image = add(stage, "img");
    image.src = item.image;
    image.alt = item.name;
    const status = add(dialog, "p");
    status.setAttribute("role", "status");
    let viewer;
    dialog.onclose = () => {
      viewer?.destroy();
      dialog.remove();
      opener.focus();
    };
    close.onclick = () => dialog.close();
    dialog.showModal();
    try {
      const OpenSeadragon = await loadViewer();
      if (!dialog.open) return;
      viewer = OpenSeadragon({
        element: stage, showNavigationControl: false, drawer: "canvas",
        placeholderFillStyle: "#eae3d1", visibilityRatio: 1,
        tileSources: {type: "image", url: item.image}
      });
      viewer.addHandler("open", () => {
        image.hidden = true;
        for (const control of [plus, minus, reset]) control.disabled = false;
        plus.onclick = () => viewer.viewport.zoomBy(1.4).applyConstraints();
        minus.onclick = () => viewer.viewport.zoomBy(1 / 1.4).applyConstraints();
        reset.onclick = () => viewer.viewport.goHome();
      });
      viewer.addHandler("open-failed", () => {
        image.hidden = false;
        status.textContent = "Просмотр увеличения недоступен. Можно открыть полную копию у музея.";
      });
    } catch {
      status.textContent = "Просмотр увеличения недоступен. Можно открыть полную копию у музея.";
    }
  }

  function localPlan(data) {
    return new (L.Layer.extend({
      onAdd(map) {
        this.image = document.createElement("img");
        this.image.src = "img/loc-2012586603-paris-1878.jpg";
        this.image.alt = "";
        this.image.className = "pilot-map-image";
        this.image.style.clipPath = `polygon(${data.clip})`;
        const update = () => {
          const [tl, tr, , bl] = data.corners.map(coords => map.latLngToLayerPoint(coords));
          const a = (tr.x - tl.x) / 2000, b = (tr.y - tl.y) / 2000;
          const c = (bl.x - tl.x) / 1448, d = (bl.y - tl.y) / 1448;
          this.image.style.transform = `matrix(${a},${b},${c},${d},${tl.x},${tl.y})`;
        };
        this.update = update;
        map.getPane("overlayPane").append(this.image);
        map.on("move zoom viewreset", update);
        update();
      },
      onRemove(map) {
        this.image.remove();
        map.off("move zoom viewreset", this.update);
      }
    }))();
  }

  function mapControls(host, map, city) {
    if (city.id !== "paris") return;
    host.hidden = false;
    const group = add(host, "div");
    group.className = "pilot-controls pilot-map-controls";
    const toggle = add(group, "button", "Наложить план 1878 года");
    toggle.type = "button";
    toggle.setAttribute("aria-pressed", "false");
    link(group, source, "Исторический план в архиве");
    const status = add(host, "p");
    status.className = "mapnote";
    status.setAttribute("role", "status");
    const details = add(host, "details");
    details.hidden = true;
    add(details, "summary", "Опорные точки и погрешность");
    let layer, markers, data, backup;
    let wanted = false, tilesReady = false;
    toggle.onclick = async () => {
      if (wanted) {
        wanted = false;
        if (layer) map.removeLayer(layer);
        if (backup) map.removeLayer(backup);
        map.removeLayer(markers);
        toggle.setAttribute("aria-pressed", "false");
        status.textContent = "Показана современная карта.";
        return;
      }
      toggle.disabled = true;
      status.textContent = "Загружаем исторический план…";
      try {
        if (!data) {
          const response = await fetch("data/paris-1878-overlay.json");
          if (!response.ok || !host.isConnected) throw new Error("overlay");
          data = await response.json();
          markers = L.layerGroup(data.points.map(point => L.circleMarker(point.location, {
            radius: 5, color: point.confidence === "low" ? "#96351c" : "#294c5a", fillOpacity: 0.85
          }).bindTooltip(Object.assign(document.createElement("span"), {textContent: point.name}))));
          add(details, "p", "Исследовательская привязка. Независимая проверка точек ещё не проведена. Среднеквадратический остаток на опорных точках: " + data.rms + " м.");
          const list = add(details, "ul");
          for (const point of data.points) {
            add(list, "li", point.name + " · " + point.error + " м без этой точки" +
              (point.confidence === "low" ? " · низкая уверенность" : ""));
          }
          details.hidden = false;
        }
        if (!host.isConnected) return;
        backup ||= localPlan(data);
        if (!tilesReady) backup.addTo(map);
        markers.addTo(map);
        wanted = true;
        toggle.setAttribute("aria-pressed", "true");
        status.textContent = "Показана приблизительная привязка в пределах опорных точек.";
        if (layer) layer.addTo(map);
        else import("./vendor/allmaps-leaflet-beta55/layer.js").then(({WarpedMapLayer}) => {
          if (!wanted || !host.isConnected || layer) return;
          const candidate = new WarpedMapLayer(undefined, {opacity: 0.75, zIndex: 300});
          const results = candidate.addGeoreferenceAnnotation(data.annotation);
          if (!results.length || results.every(result => result instanceof Error)) return;
          layer = candidate;
          map.once("tilefetched", () => {
            tilesReady = true;
            if (wanted) map.removeLayer(backup);
          });
          layer.addTo(map);
        }).catch(() => { /* The local scan stays visible without WebGL or archive tiles. */ });
      } catch {
        status.textContent = "Наложение сейчас недоступно. Отдельный исторический план можно открыть во вкладке выше.";
      } finally {
        toggle.disabled = false;
      }
    };
  }
  return {works, mapControls};
})();
