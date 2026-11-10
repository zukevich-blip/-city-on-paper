/* Город на бумаге — единая навигация по всем залам музея (одна строка сверху на каждой странице).
 * Подключение: <script src="<путь>/assets/nav/museum-nav.js" defer></script>. Ссылки строятся от адреса самого скрипта. */
(() => {
  "use strict";
  const me = document.currentScript || [...document.scripts].find((s) => /assets\/nav\/museum-nav\.js/.test(s.src));
  if (!me || document.getElementById("museumBar")) return;
  const base = me.src.replace(/assets\/nav\/museum-nav\.js.*$/, "");
  const HALLS = [
    ["Главный вход", [["", "Живой музей", "Истории, коллекция, мастерская и все разделы"], ["stories/", "Истории", "Документированные рассказы по произведениям и городам"], ["atlas/", "Атлас времени", "Исследование мест, эпох и музейных первоисточников"], ["experience/", "Книга городов", "Необязательное путешествие с раскрывающейся книгой"], ["eras/", "Архивный атлас эпох", "Карты Европы, планы городов, тогда и сейчас"]]],
    ["Смотреть", [["salon/", "Салон открытий", "Литографии и картины из открытых музеев"], ["closeup/", "Кабинет деталей", "Рассматривать лист в подробностях"],
      ["exhibitions/city-as-evidence/", "Город как свидетельство", "Выставка: что рассказывает гравюра"], ["exhibitions/lost-florence/", "Исчезнувшая Флоренция", "Выставка о старом центре"],
      ["photography/", "Современный город", "Фотографии тех же мест сегодня"]]],
    ["Путешествовать", [["journeys/", "Путешествие по векам", "Города по векам"], ["cities/", "Все города мира", "Географический каталог с источниками и степенью проверки"], ["world/", "Мировая галерея", "Отобранные открытые произведения за пределами Европы"],
      ["poc/compare/", "Тогда / сейчас", "Сравнить литографию и фотографию"], ["atlas-prototype/", "Исторический атлас (прототип)", "Первый вариант карты"]]],
    ["Расследовать", [["discover/", "Первое расследование", "Начать знакомство"], ["detective/", "Дело № 01 · Мадлен", "Литография под лупой"],
      ["fieldwork/", "Городская фотоохота", "Найти ракурс художника самому"], ["studio/", "Кабинет коллекционера", "Происхождение листов, блокнот"]]],
    ["Как это сделано", [["printlab/", "Камень и бумага", "Как печатали литографию"], ["atelier/bargue/", "Школа рисунка", "Учиться рисовать по-старому"],
      ["ornaments/", "Мастерская орнамента", "Узоры и декор"], ["ideas/", "Лаборатория идей", "Куда растёт музей"]]],
  ];
  const here = location.pathname.replace(/index\.html$/, "");
  // The curated homepage owns its primary navigation. Keep the global bar in inner rooms.
  if (here === new URL(base).pathname) return;
  const isHere = (p) => here.endsWith("/" + p) || (p === "" && new URL(base).pathname === here);
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const css = `#museumBar{background:#29463D;color:#f4efe5;font:13px/1.3 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;position:relative;z-index:1000}
#museumBar .mb{max-width:1500px;margin:0 auto;display:flex;align-items:center;gap:6px 14px;padding:4px clamp(12px,3vw,40px);flex-wrap:wrap}
#museumBar a{color:#eadfc9;text-decoration:none}#museumBar .mbh{font:15px "Iowan Old Style",Georgia,serif;letter-spacing:.02em;margin-right:auto;display:inline-flex;align-items:center;min-height:44px}
#museumBar .mbq{display:flex;gap:2px;flex-wrap:wrap}#museumBar .mbq a{display:inline-flex;align-items:center;min-height:44px;padding:0 8px;border-radius:2px}#museumBar .mbq a:hover,#museumBar .mbq a[aria-current]{background:#ffffff1a}
#museumBar button{min-height:44px;border:1px solid #dcb88c;background:none;color:#f1e3c4;padding:4px 12px;border-radius:2px;font:inherit;cursor:pointer}
#museumBar .mbp{max-width:1500px;margin:0 auto;padding:6px clamp(12px,3vw,40px) 18px;display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px 22px}
#museumBar .mbp .mbt{font:600 11px system-ui;letter-spacing:.16em;text-transform:uppercase;color:#c9a96e;margin:8px 0 4px}
#museumBar .mbp a{display:block;min-height:44px;padding:7px 0;border-bottom:1px solid #ffffff14}#museumBar .mbp a b{font:400 16px Georgia,serif;display:block}#museumBar .mbp a small{color:#b8ad98}
#museumBar .mbp a[aria-current] b{color:#f0c987}
@media(max-width:700px){#museumBar .mbq{display:none}}`;
  const st = document.createElement("style"); st.textContent = css; document.head.appendChild(st);
  const quick = [["stories/", "Истории"], ["atlas/", "Атлас времени"], ["salon/", "Коллекция"], ["studio/", "Кабинет"], ["cities/", "Города"]];
  const bar = document.createElement("div");
  bar.id = "museumBar";
  bar.innerHTML = `<div class="mb"><a class="mbh" href="${esc(base)}">Город на бумаге</a>
    <nav class="mbq" aria-label="Залы музея">${quick.map(([p, t]) => `<a href="${esc(base + p)}"${isHere(p) ? ' aria-current="page"' : ""}>${esc(t)}</a>`).join("")}</nav>
    <button type="button" aria-expanded="false" aria-controls="museumPanel">Все залы ▾</button></div>
    <nav class="mbp" id="museumPanel" aria-label="Все залы музея" hidden>${HALLS.map(([h, items]) => `<div><p class="mbt">${esc(h)}</p>${items.map(([p, t, d]) =>
      `<a href="${esc(base + p)}"${isHere(p) ? ' aria-current="page"' : ""}><b>${esc(t)}</b><small>${esc(d)}</small></a>`).join("")}</div>`).join("")}</nav>`;
  document.body.insertBefore(bar, document.body.firstChild);
  const btn = bar.querySelector("button"), panel = bar.querySelector("#museumPanel");
  btn.addEventListener("click", () => { const open = panel.hidden; panel.hidden = !open; btn.setAttribute("aria-expanded", String(open)); btn.textContent = open ? "Закрыть ▴" : "Все залы ▾"; });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !panel.hidden) btn.click(); });
  window.MuseumHalls = HALLS;
})();
