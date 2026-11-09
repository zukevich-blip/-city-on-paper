/* Worldwide city cartography source shelf; separate from georeferenced layers.
 * No automatic geo-warp, no unverified rights or 19th-century date assertions.
 * All cities have the same offline-backed research interface.
 */
"use strict";
window.CityHistoricCartography = (() => {
  let catalog;
  const esc = (x) => String(x == null ? "" : x).replace(/[&<>"']/g,
    c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const link = (url) => {
    try {
      const parsed = new URL(url);
      return parsed.protocol === "https:" && ["www.loc.gov", "loc.gov"].includes(parsed.hostname)
        ? parsed.href : null;
    } catch (_e) { return null; }
  };
  const load = () => {
    if (!catalog) catalog = fetch("data/map-evidence.json")
      .then(r => { if (!r.ok) throw new Error(String(r.status)); return r.json(); })
      .catch(() => ({ items: [] }));
    return catalog;
  };

  async function mount(host, city) {
    if (!host || !city || !city.id) return;
    host.innerHTML = '<p class="note">Проверяем доступные архивные планы города…</p>';
    const data = await load();
    if (!host.isConnected) return;
    const rows = (data.items || []).filter(x => x.city_id === city.id && link(x.object_url));
    const officialQuery = city.name_orig || city.name;
    const officialSearch = "https://www.loc.gov/maps/?q=" +
      encodeURIComponent(officialQuery + " city map");
    const cards = rows.slice(0, 8).map(item => {
      const verified = item.status === "catalogue_source_checked";
      return '<li class="historic-map-source"><strong>' + esc(item.title) + '</strong>' +
        (item.date_as_reported ? ' <span>' + esc(item.date_as_reported) + '</span>' : '') +
        '<small>' + (verified ? "Архивная карточка установлена, геопривязка ещё не проверена" :
          "Поисковая находка, требует проверки") + '</small>' +
        '<a href="' + esc(link(item.object_url)) +
        '" target="_blank" rel="noopener">Открыть в Library of Congress</a></li>';
    }).join("");
    host.innerHTML = '<h3>Историческая картография</h3>' +
      (cards ? '<ul class="historic-map-list">' + cards + '</ul>' :
        '<p class="note">Проверенных исторических планов в этом каталоге пока нет. ' +
        'Город остаётся доступен на современной карте.</p>') +
      '<p class="historic-map-search"><a href="' + esc(officialSearch) +
      '" target="_blank" rel="noopener">Искать карты города в Library of Congress</a></p>' +
      '<p class="historic-map-caution">Находка в архиве не означает точную геопривязку. ' +
      'Совмещение карт требует независимых опорных точек и проверки прав.</p>';
  }
  return { mount };
})();