"use strict";

const kinds = {guidebook: "Путеводитель", "view-series": "Альбом или серия видов"};
const filters = ["query", "city", "kind"].map(id => document.getElementById(id));
const [query, city, kind] = filters;
const books = document.getElementById("books");
const status = document.getElementById("status");
const params = new URLSearchParams(location.search);
const matchText = value => String(value || "").toLocaleLowerCase("ru").replaceAll("ё", "е").trim();

function node(tag, value, className) {
  const element = document.createElement(tag);
  if (value) element.textContent = value;
  if (className) element.className = className;
  return element;
}

function link(value, title, className, local = false) {
  if (!value) return null;
  const root = new URL("../", location.href);
  const url = new URL(value, local ? root : location.href);
  if (local ? url.origin !== root.origin || !url.pathname.startsWith(root.pathname) : url.protocol !== "https:") return null;
  const anchor = node("a", title, className);
  anchor.href = url.href;
  return anchor;
}

function card(book) {
  const article = node("article", "", "book");
  article.id = book.id;
  article.append(
    node("p", [kinds[book.kind], book.city, book.yearLabel || book.year].filter(Boolean).join(" · "), "meta"),
    node("h3", book.title)
  );
  if (book.originalTitle) article.append(node("p", book.originalTitle, "original"));
  if (book.authors) article.append(node("p", [].concat(book.authors).join(", "), "meta"));
  if (book.image) {
    const picture = link(book.image, "", "", true);
    if (picture) {
      const img = node("img");
      img.src = picture.href;
      img.alt = book.imageAlt || "";
      img.loading = "lazy";
      const figure = node("figure");
      figure.append(img);
      if (book.imageCredit) {
        const caption = node("figcaption");
        caption.append(link(book.imageSourceUrl, book.imageCredit) || book.imageCredit);
        figure.append(caption);
      }
      article.append(figure);
    }
  }
  article.append(node("p", book.summary, "summary"));
  const provenance = node("p", book.institution, "provenance");
  if (book.rights) {
    provenance.append(" · ");
    provenance.append(link(book.rightsUrl, book.rights) || book.rights);
  }
  article.append(provenance);
  const actions = node("div", "", "actions");
  const related = book.related || {};
  actions.append(...[
    link(book.readUrl || book.sourceUrl, book.kind === "guidebook" ? "Листать в архиве" : "Открыть в архиве", "button primary"),
    book.readUrl && book.readUrl !== book.sourceUrl ? link(book.sourceUrl, "Запись об издании", "button") : null,
    link(related.compare, "Сравнить с фото", "button", true),
    link(related.map, "Открыть карту", "button", true),
    link(related.salon, "Городские листы", "button", true)
  ].filter(Boolean));
  article.append(actions);
  if (book.volumes?.length) {
    const details = node("details", "", "volume-list");
    details.append(node("summary", "Открыть отдельные тома"));
    const list = node("ul");
    for (const volume of book.volumes) {
      const anchor = link(volume.url, volume.label);
      if (anchor) {
        const item = node("li");
        item.append(anchor);
        list.append(item);
      }
    }
    details.append(list);
    article.append(details);
  }
  return article;
}

function render(items) {
  const text = matchText(query.value);
  const listed = items.filter(book =>
    (!city.value || book.city === city.value) && (!kind.value || book.kind === kind.value) &&
    [book.title, book.originalTitle, book.authors, book.city, book.year, book.yearLabel].some(value => matchText(value).includes(text))
  );
  books.replaceChildren(...listed.map(card));
  status.textContent = listed.length ? `Найдено изданий: ${listed.length}` : "По этим условиям изданий пока нет. Попробуйте другой запрос или уберите фильтр.";
}

async function start() {
  const response = await fetch("../data/curation/historical-guidebooks-v1.json");
  if (!response.ok) throw new Error(String(response.status));
  const {items} = await response.json();
  const cities = [...new Set(items.map(book => book.city))].sort((a,b) => a.localeCompare(b,"ru"));
  city.append(...cities.map(name => new Option(name, name)));
  for (const filter of filters) {
    const initial = params.get(filter.id);
    if (initial) filter.value = initial;
    filter.addEventListener(filter === query ? "input" : "change", () => {
      const url = new URL(location.href);
      for (const input of filters) {
        if (input.value) url.searchParams.set(input.id, input.value);
        else url.searchParams.delete(input.id);
      }
      url.hash = "";
      history.replaceState(null, "", url);
      render(items);
    });
  }
  document.querySelectorAll(".chips [data-city]").forEach(chip => {
    const name = chip.dataset.city;
    if (![...city.options].some(option => option.value === name)) { chip.hidden = true; return; }
    chip.addEventListener("click", () => { city.value = name; city.dispatchEvent(new Event("change")); });
  });
  render(items);
  const target = document.getElementById(location.hash.slice(1));
  if (target?.classList.contains("book")) target.scrollIntoView();
}

start().catch(() => {
  status.textContent = "Каталог пока недоступен. Можно открыть путеводитель Вази напрямую.";
  status.append(" ", link("https://dlib.biblhertz.it/dg4503631", "Открыть книгу"));
});
