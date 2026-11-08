/* City on Paper · source-linked art-history reading desk.
 * Authoritative sources, explicit certainty, and no invented historical characters.
 */
"use strict";
(() => {
  const WORKS = {
    "paris-la_madeleine": {
      title: "Мадлен: как читать фасад и сам лист",
      preface: "Этот лист создан после превращения долгостроя в церковь и показывает повседневное движение у монументального неоклассического фасада. Дата листа дана хранителем интервалом, а не одним годом.",
      terms: [
        ["Коринфский ордер", "Капители колонн с характерной лиственной декорацией. На Мадлен 52 коринфские колонны; ищите их повторяющийся ритм на фасаде и боковой колоннаде.", "https://www.paris.fr/pages/la-madeleine-n-a-ni-croix-ni-clocher-25919"],
        ["Фронтон", "Треугольное завершение главного фасада; у Мадлен фронтон несёт рельеф Страшного суда. Не путать фронтон с расположенным ниже антаблементом.", "https://www.paris.fr/pages/la-madeleine-n-a-ni-croix-ni-clocher-25919"],
        ["Стилобат", "Массивное ступенчатое основание, поднимающее храмовую колоннаду над уровнем улицы.", "https://www.paris.fr/pages/debut-des-travaux-pour-l-eglise-de-la-madeleine-18409"]
      ],
      timeline: [
        ["1764", "Людовик XV заложил первый камень Мадлен. Исходный замысел существенно отличался от дошедшего до нас сооружения.", "https://www.paris.fr/pages/la-madeleine-n-a-ni-croix-ni-clocher-25919"],
        ["1806", "Наполеон предполагал создать на этом месте храм славы Великой армии; дальнейшие политические перемены снова изменили назначение здания.", "https://www.paris.fr/pages/la-madeleine-n-a-ni-croix-ni-clocher-25919"],
        ["1842", "Здание окончательно освящено как церковь. Лист Бенуа датируется 1845–1860 годами: это уже действующий храм.", "https://www.loc.gov/item/2016652452/"],
        ["1845–1860", "Библиотека Конгресса называет Филиппа Бенуа автором рисунка, а Lemercier печатником. Экипаж и пешеходы изображены; их личности и маршруты неизвестны.", "https://www.loc.gov/item/2016652452/"]
      ],
      question: "Как изображённые экипаж и пешеходы помогают передать масштаб здания? Что художник мог усилить композиционно и чего мы не можем знать из одного листа?"
    },
    "paris-palais_royal": {
      title: "Пале-Рояль: сад, перспектива, направление взгляда",
      preface: "На разных исторических изображениях Пале-Рояль может выглядеть словно другим местом: художники и фотографы смотрели на ансамбль с разных сторон. На текущем сравнении противоположные направления нужно показывать явно.",
      terms: [
        ["Ритм колоннад", "Повторение опор и пролётов задаёт перспективу и помогает определить, с какой стороны художник смотрел на сад.", "https://www.loc.gov/item/2016652451/"],
        ["Линия схода", "Воображаемая точка, к которой сходятся параллельные линии рисунка в линейной перспективе. Это помогает оценивать ракурс, но не заменяет координат съёмки.", "https://www.loc.gov/item/2016652451/"]
      ],
      timeline: [
        ["XIX век", "Исторический лист и современный снимок показывают ансамбль с разных сторон. Не выдаём их за геометрически совмещённую фотографию.", "https://www.loc.gov/item/2016652451/"]
      ],
      question: "Найдите границы сада и направляющие линии перспективы. Какие два ориентира позволят отличить разные направления взгляда?"
    },
    "florence-duomo": {
      title: "Флорентийский собор: как устроен купол Брунеллески",
      preface: "Здесь особенно интересно сравнивать исторический вид города с современным силуэтом: купол служит устойчивым ориентиром, а плотность застройки и линии взгляда меняются.",
      terms: [
        ["Двойная оболочка купола", "Купол состоит из внутренней и наружной конструкций; между ними находится проход к фонарю. Это инженерный принцип, а не два самостоятельных купола.", "https://duomo.firenze.it/en/discover/dome"],
        ["Восьмигранный барабан", "Основание купола имеет восемь сторон. В конструкции купола восемь крупных сегментов и система рёбер.", "https://duomo.firenze.it/en/discover/dome"],
        ["Фонарь", "Верхнее завершение над сводом. Его проектировал Брунеллески; окончание строительства произошло после его смерти.", "https://duomo.firenze.it/en/about-us/history/art"]
      ],
      timeline: [
        ["1420", "Начато возведение купола по проекту Филиппо Брунеллески.", "https://duomo.firenze.it/en/discover/dome"],
        ["1436", "Основные работы по куполу завершены. Строительство велось без традиционного деревянного центрирования такого размера.", "https://duomo.firenze.it/en/discover/dome"]
      ],
      question: "Сравните очертания купола и его отношение к окружающим домам. Какие изменения вызваны новой застройкой, а какие — разницей положения художника?"
    },
    "florence-ponte_vecchio": {
      title: "Понте-Веккьо: мост, лавки и коридор Вазари",
      preface: "Над торговыми помещениями проходит отдельная крытая галерея Медичи. На рисунках важно различать сам мост, встроенные лавки и расположенный выше коридор.",
      terms: [
        ["Коридор Вазари", "Переход, проложенный в 1565 году по заказу Козимо I Медичи. Он проходит над Понте-Веккьо и связывает административные и жилые дворцы.", "https://www.uffizi.it/en/corridoio-vasariano/history"],
        ["Арка моста", "Несущее криволинейное перекрытие пролёта. Ритм пролётов помогает сравнивать исторический рисунок и снимки.", "https://www.uffizi.it/en/corridoio-vasariano"]
      ],
      timeline: [
        ["1565", "По приказу Козимо I Медичи Джорджо Вазари создал закрытый проход, связавший Палаццо Веккьо и Палаццо Питти через комплекс Уффици и мост.", "https://www.uffizi.it/en/corridoio-vasariano/history"]
      ],
      question: "На какой высоте проходит коридор относительно лавок? Можно ли по рисунку отделить реальную архитектуру от условной перспективы?"
    }
  };
  const DEFAULT = {
    title: "Как исследовать старую литографию",
    preface: "Начните с надписей, печатника, источника и ракурса. Город и изображённый памятник должны быть установлены раньше, чем мы предполагаем, где находился художник.",
    terms: [
      ["Рисовальщик, литограф, печатник", "Одно изображение могли создавать разные люди. Надписи del. (рисовал), lith. (литографировал), imp. (печатал) нельзя сводить к одному автору.", "https://www.loc.gov/item/2016652452/"],
      ["Литография", "Плоская печать на камне или металлической пластине. Жирный рисунок притягивает печатную краску, а смоченные водой незапечатанные участки её отталкивают.", "https://www.vam.ac.uk/articles/what-is-print"]
    ],
    timeline: [],
    question: "Найдите дату, подпись художника, литографа и издателя. Есть ли у источника инвентарный номер и явная отметка о правах?"
  };
  const BOOKS = [
    ["Алоиз Зенефельдер. Полный курс литографии (1819)", "Первоначальные технические инструкции изобретателя процесса; Wellcome Collection, Public Domain Mark.", "https://wellcomecollection.org/works/sbgf3bwk"],
    ["Джозеф и Элизабет Пеннелл. Lithography & Lithographers (1898)", "История литографской техники, художников и печатных мастерских; Библиотека Конгресса.", "https://www.loc.gov/item/09034362/"],
    ["Оуэн Джонс. The Grammar of Ornament (1856)", "Сто исторических таблиц орнамента; Smithsonian Libraries, CC0.", "https://library.si.edu/digital-library/book/grammarornament00jone"],
    ["V&A. What is print?", "Музейное объяснение различных способов печати и литографии.", "https://www.vam.ac.uk/articles/what-is-print"]
  ];
  function mount(host, id) {
    if (!host) return false;
    const d = WORKS[id] || DEFAULT;
    host.replaceChildren();
    const head = document.createElement("div");
    head.className = "cd-title";
    const kicker = document.createElement("span"); kicker.className = "eyebrow";
    kicker.textContent = "Кабинет исследователя · проверенные источники";
    const h = document.createElement("h2"); h.textContent = d.title;
    const intro = document.createElement("p"); intro.textContent = d.preface;
    head.append(kicker, h, intro);
    host.append(head);
    function section(name, entries, type) {
      if (!entries.length) return;
      const wrap = document.createElement("section"); wrap.className = "cd-section";
      const h3 = document.createElement("h3"); h3.textContent = name; wrap.append(h3);
      const grid = document.createElement("div"); grid.className = "cd-grid";
      for (const [label,desc,url] of entries) {
        const item = document.createElement("article"); item.className = "cd-item";
        const strong = document.createElement("strong"); strong.textContent = label;
        const p = document.createElement("p"); p.textContent = desc;
        const link = document.createElement("a"); link.href = url; link.target="_blank"; link.rel="noopener noreferrer";
        link.textContent = type === "book" ? "Открыть книгу / статью у хранителя" : "Проверить в источнике";
        item.append(strong,p,link);grid.append(item);
      }
      wrap.append(grid);host.append(wrap);
    }
    section("Архитектура и детали, которые стоит найти на листе", d.terms);
    section("Что происходило в разные годы", d.timeline);
    const prompt = document.createElement("p"); prompt.className="cd-question";
    prompt.textContent = "Вопрос для наблюдения: " + d.question;
    host.append(prompt);
    section("Полка исследователя: книги и техника", BOOKS, "book");
    const more = document.createElement("p"); more.className="cd-standards";
    more.textContent = "Важное различие: факты и датировки ссылаются на музейные документы. Вопросы для наблюдения предполагают самостоятельный анализ, а не утверждение о мотивах исторических персонажей. Исторические подписи могут быть уточнены.";
    host.append(more);
    return true;
  }
  window.CityOnPaperCuratorialDesk = Object.freeze({mount});
})();
