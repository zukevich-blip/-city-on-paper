/* Editorial museum trail, connecting archival context to the next action.
 * The atlas is a hash router: scroll buttons MUST NOT mutate location.hash.
 */
"use strict";
window.MuseumJourney = (() => {
  const describe = (title, detail, anchor, route) => ({ title, detail, anchor, route });
  const stop = (city) => city ? [
    describe("Карта", "Место и ориентиры", "cmapH"),
    describe("Старинные планы", "Оригиналы карт", "historicCartography"),
    describe("Произведения", "Рисунки и фотографии", "cityLab"),
    city.epochs?.length
      ? describe("Сравнить эпохи", "Тогда и сейчас", "epH")
      : describe("Сравнить эпохи", "Другие города", null, "#/epochs"),
    describe("Архивы", "Проверить источники", "archiveSearch"),
  ] : [
    describe("Карта Европы", "Начать с мест", "maphost"),
    describe("Города и страны", "Выбрать направление", "countryIndex"),
    describe("Мировая коллекция", "Работы шести регионов", null, "../world/"),
    describe("Салон открытий", "Оригиналы и художники", null, "../salon/"),
  ];
  function mount(host, city = null) {
    if (!host) return;
    const nav = document.createElement("nav");
    nav.className = "museum-journey";
    nav.setAttribute("aria-label", city ? "Маршрут исследования города" : "Как исследовать атлас");
    const heading = document.createElement("span");
    heading.className = "museum-journey-heading";
    heading.textContent = city ? "Маршрут исследования: " + city.name
      : "Как устроен атлас";
    nav.appendChild(heading);
    const track = document.createElement("div");
    track.className = "museum-journey-track";
    stop(city).forEach((item, index) => {
      const el = document.createElement(item.route ? "a" : "button");
      if (item.route) el.href = item.route;
      else {
        el.type = "button";
        el.addEventListener("click", () => {
          const target = document.getElementById(item.anchor);
          if (!target) return;
          const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
          target.scrollIntoView({ behavior: reduce ? "instant" : "smooth", block: "start" });
        });
      }
      el.className = "museum-journey-step";
      const number = document.createElement("span");
      number.className = "museum-journey-number";
      number.textContent = String(index + 1).padStart(2, "0");
      const title = document.createElement("span");
      title.className = "museum-journey-caption";
      const strong = document.createElement("strong");
      strong.textContent = item.title;
      const note = document.createElement("small");
      note.textContent = item.detail;
      title.append(strong, note);
      el.append(number, title);
      track.appendChild(el);
    });
    nav.append(track);
    host.replaceChildren(nav);
  }
  return { mount };
})();
