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
      .catch(() => ({ items: [], load_error: true }));
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
    const sourceChain = (item) => {
      const stages = [
        ["Архив", item.status === "catalogue_source_checked"
          ? "Страница найдена" : "Проверить"],
        ["Изображение крупным планом", item.image_api_status === "working_IIIF_Image_API_for_this_item"
          ? "Можно увеличить" : "Доступность уточнить"],
        ["Положение на карте", item.georeferencing_status ===
          "research_affine_not_independently_verified"
          ? "Отмечено примерно" : "Пока не определили"],
        ["Проверка", "Нужна ещё одна проверка"],
      ];
      return '<ol class="map-source-chain" aria-label="Этапы проверки архивной карты">' +
        stages.map(([name, status], index) =>
          '<li><span class="map-chain-index">' + String(index + 1).padStart(2, "0") +
          '</span><b>' + esc(name) + '</b><small>' + esc(status) + '</small></li>'
        ).join("") + '</ol>';
    };
    const cards = rows.slice(0, 8).map(item => {
      const verified = item.status === "catalogue_source_checked";
      return '<li class="historic-map-source"><strong>' + esc(item.title) + '</strong>' +
        (item.date_as_reported ? ' <span>' + esc(item.date_as_reported) + '</span>' : '') +
        '<small>' + (verified ? "Старый план найден. Его положение на современной карте ещё проверяем." :
          "Находку ещё проверяем") + '</small>' +
        sourceChain(item) +
        '<a href="' + esc(link(item.object_url)) +
        '" target="_blank" rel="noopener">Смотреть в Библиотеке Конгресса США</a></li>';
    }).join("");
    host.innerHTML = '<h3>Старые карты города</h3>' +
      (data.load_error ?
        '<p class="note" role="status">Старые карты не загрузились. ' +
        'Попробуйте обновить страницу.</p>'
        : cards ? '<ul class="historic-map-list">' + cards + '</ul>' :
        '<p class="note">Проверенных исторических планов в этом каталоге пока нет. ' +
        'Город остаётся доступен на современной карте.</p>') +
      '<p class="historic-map-search"><a href="' + esc(officialSearch) +
      '" target="_blank" rel="noopener">Найти карты города в Библиотеке Конгресса США</a></p>' +
      '<p class="historic-map-caution">Положение старого плана уточняем по знакомым местам. ' +
      'Условия использования указаны на странице в архиве.</p>';
  }
  return { mount };
})();