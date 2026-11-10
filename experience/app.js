/* Город на бумаге: book-like entry built on reviewed catalogue records.
   These objects deliberately carry sources and image rights, not guessed geolocation. */
"use strict";
(() => {
  const root = document;
  const $ = (id) => root.getElementById(id);
  const cities = {
    paris: {
      name: "Париж", label: "FRANCE · 1845–1900",
      intro: "Литограф Филипп Бенуа, торжественная Мадлен и сад Пале-Рояль. Один город, разные художественные взгляды.",
      heading: ["Париж", "на бумаге"],
      chapters: [
        {
          short: "Мадлен",
          date: "Париж · 1845–1860",
          title: "Церковь, которая заняла весь лист",
          lead: "Представьте знакомую улицу без автомобиля. На первом плане прохожие, за ними — портик, почти древнегреческий храм.",
          paragraphs: [
            "Филипп Бенуа выбрал для Мадлен угловой вид. Отсюда хорошо читаются фронтон, ряды колонн и лестница, но пространство не превращается в архитектурный чертёж: люди и движение на улице задают жизнь всей композиции.",
            "Библиотека Конгресса США датирует этот раскрашенный вручную лист 1845–1860 годами. Подпись Ph. Benoist del. обозначает рисовальщика; Imp. Lemercier, Paris — печатную мастерскую. Это разные роли.",
            "На этом месте можно задавать вопросы: почему автор приблизил фасад? Какие мелкие фигуры он счёл необходимым оставить? Насколько реальные пропорции здания совпадали с впечатлением художника?"
          ],
          interpretation: "Наблюдение, а не доказанный замысел: крупный портик и маленькие фигуры создают ощущение торжественного городского пространства.",
          src: "../poc/compare/pairs/madeleine-historic-loc-pga14315v.jpg",
          alt: "Раскрашенная литография Филиппа Бенуа: церковь Мадлен, колоннада и прохожие Парижа XIX века",
          caption: "Филипп Бенуа (рисунок), Lemercier (типография). Paris. La Madeleine. Plate 8, 1845–1860. Library of Congress, LC-DIG-pga-14315.",
          url: "https://www.loc.gov/item/2016652452/",
          sourceText: "Library of Congress · Paris. La Madeleine",
          rights: "LoC: No known restrictions on publication. Ручная раскраска конкретного экземпляра.",
        },
        {
          short: "Пале-Рояль",
          date: "Париж · 1845–1860",
          title: "Сад как место для прогулки",
          lead: "От величественного храма мы переходим в сад. Архитектура здесь задаёт направление взгляда, а не подавляет человека.",
          paragraphs: [
            "На другом листе Филиппа Бенуа вдоль аллей Пале-Рояль появляются деревья, галереи и городская публика. Это не просто узнаваемое место: сцена устроена так, что зритель мысленно идёт по саду.",
            "Библиотека Конгресса указывает то же широкое время, 1845–1860 годы, и обозначает лист как plate 6. Автор рисунка — Филипп Бенуа, типография — Lemercier. Нумерация сама по себе ещё не доказывает единое конкретное издание с Мадлен.",
            "Сравнивать этот лист с сегодняшней фотографией нужно осторожно. Имеющийся современный снимок сделан с противоположной стороны сада. Поэтому здесь нельзя правдоподобно наложить один вид на другой с помощью шторки."
          ],
          interpretation: "Кураторское прочтение: аллеи, разнесённые группы людей и обрамляющие сад галереи превращают изображение в рассказ о повседневном движении.",
          src: "../poc/compare/pairs/palais-royal-historic-loc-pga14314v.jpg",
          alt: "Филипп Бенуа, исторический вид аллей сада Пале-Рояль с посетителями и галереями",
          caption: "Филипп Бенуа. Paris. Jardin du Palais Royal. Plate 6, 1845–1860. Library of Congress, LC-DIG-pga-14314.",
          url: "https://www.loc.gov/item/2016652451/",
          sourceText: "Library of Congress · Jardin du Palais Royal",
          rights: "LoC: No known restrictions on publication. Современный ракурс исследуется отдельно."
        },
        {
          short: "Другой век",
          date: "Париж · около 1890–1900",
          title: "Мадлен смотрит на новую улицу",
          lead: "Проходит несколько десятилетий. Памятник узнаваем, а графическая техника и впечатление от улицы уже другие.",
          paragraphs: [
            "Фотохром конца XIX века позволяет увидеть Мадлен с улицы Руаяль. Технология фотохрома придаёт печатному изображению цвет, но это не обычная цветная фотография и не тот же процесс, что ручная раскраска ранней литографии Бенуа.",
            "Поменялось и положение наблюдателя: теперь церковь становится завершением прямого уличного коридора. Сравнение листов помогает заметить, насколько сильно один и тот же город зависит от выбранной точки зрения.",
            "Это даёт материал для исторического исследования, но не доказывает, что конкретная деталь улицы изменилась. Для такого вывода нужны даты, планы, фотографии с сопоставимым ракурсом и дополнительные источники."
          ],
          interpretation: "Обращайте внимание на точку взгляда: художественное различие не всегда означает архитектурное изменение.",
          src: "../eras/img/paris_madeleine_c1890-1900_photochrom_rue-royale_loc-ppmsc-05184.jpg",
          alt: "Фотохром конца XIX века: улица Руаяль ведёт к церкви Мадлен в Париже",
          caption: "The Madeleine, and rue Royale, Paris. Фотохром, около 1890–1900. Library of Congress, LC-DIG-ppmsc-05184.",
          url: "https://www.loc.gov/item/2001698526/",
          sourceText: "Library of Congress · The Madeleine and rue Royale",
          rights: "LoC: No known restrictions on reproduction. Автор снимка в карточке не установлен."
        }
      ]
    },
    florence: {
      name: "Флоренция", label: "ITALIA · 1859–1900",
      heading: ["Флоренция", "во времени"],
      intro: "Старый мост, рисунок офортиста и кафедральный собор. Как фотография и печатная графика рассказывают об одном городе.",
      chapters: [
        {
          short: "Понте-Веккьо",
          date: "Флоренция · 1859–1866",
          title: "Мост, на котором живёт город",
          lead: "Во Флоренции мост похож на улицу. Дома и лавки образуют силуэт, который трудно спутать с другим.",
          paragraphs: [
            "Фотографы Джорджо Зоммер и Эдмон Белес оставили стереоскопический вид Понте-Веккьо со стороны Уффици. По карточке Библиотеки Конгресса снимок относится к периоду 1859–1866 годов.",
            "Стереоскопическое изображение задумывалось как пара снимков для объёмного просмотра. Сегодня оно позволяет рассмотреть повседневную архитектуру моста и плотность застройки на реке.",
            "Историческая фотография даёт больше геометрических подсказок, чем художественный вид, но и она зависит от положения камеры, оптики и обработки отпечатка."
          ],
          interpretation: "На фотографии архитектура и движение города буквально сливаются: мост становится одновременно переправой и улицей.",
          src: "../eras/img/florence_pontevecchio_1859-66_sommer-behles_stereo_loc-1s53703.jpg",
          alt: "Старинный стереоскопический вид Понте-Веккьо во Флоренции, 1859–1866",
          caption: "Giorgio Sommer и Edmond Behles. Ponte vechio dagli Uffizi (Firenze), 1859–1866. Library of Congress.",
          url: "https://www.loc.gov/item/2024722637/",
          sourceText: "Library of Congress · Ponte vechio dagli Uffizi",
          rights: "LoC: No known restrictions on publication."
        },
        {
          short: "Глаз художника",
          date: "Флоренция · 1883",
          title: "Когда мост становится офортом",
          lead: "В фотографии и офорте можно узнать одно место. Но художественный штрих меняет сам способ его увидеть.",
          paragraphs: [
            "В 1883 году художник Джозеф Пеннелл создал офорт Ponte Vecchio, Florence. Лист хранится в Художественном институте Чикаго.",
            "В офорте важны линия, плотность штриха и выбранные акценты. Сравнение с фотографией позволяет наблюдать два подхода к одному историческому пространству: фиксацию светом и рисунок, предназначенный для печатного оттиска.",
            "Эти изображения нельзя использовать как доказательство точного изменения геометрии моста без дополнительного сопоставления."
          ],
          interpretation: "Это два взгляда, а не две взаимозаменяемые фиксации реальности. Художник может усилить контраст и ритм силуэтов.",
          src: "../eras/img/florence_pontevecchio_1883_pennell_etching_aic-194443.jpg",
          alt: "Офорт Джозефа Пеннелла 1883 года: мост Понте-Веккьо во Флоренции",
          caption: "Joseph Pennell. Ponte Vecchio, Florence, 1883. Art Institute of Chicago.",
          url: "https://www.artic.edu/artworks/194443",
          sourceText: "Art Institute of Chicago · Ponte Vecchio, Florence",
          rights: "AIC: произведение в общественном достоянии."
        },
        {
          short: "Собор",
          date: "Флоренция · около 1890–1900",
          title: "Купол над крышами",
          lead: "Печатный цвет возвращает нам Флоренцию глазами туриста рубежа веков.",
          paragraphs: [
            "На фотохроме из собрания Библиотеки Конгресса рядом показаны собор Санта-Мария-дель-Фьоре и колокольня. Архивная датировка — примерно 1890–1900 годы.",
            "Перед нами не карта и не техническая съёмка. Фотохром помогал распространять цветные образы путешествий в эпоху, когда массовая цветная фотография ещё не была привычной.",
            "Можно продолжить изучение города через другие источники и музейные записи, не выдавая художественную цветопередачу за точный цвет зданий того времени."
          ],
          interpretation: "Город остаётся узнаваемым за счёт силуэта, а цвет и ракурс работают как часть культурного образа путешествия.",
          src: "../eras/img/florence_duomo_c1890-1900_photochrom_loc-ppmsc-06455.jpg",
          alt: "Исторический фотохром: купол и колокольня кафедрального собора во Флоренции около 1890–1900 годов",
          caption: "The Cathedral and campanile, Florence, Italy. Фотохром, около 1890–1900. Library of Congress.",
          url: "https://www.loc.gov/item/2001700795/",
          sourceText: "Library of Congress · Cathedral and campanile",
          rights: "LoC: No known restrictions on publication."
        }
      ]
    },
    naples: {
      name: "Неаполь",label: "ITALIA · 1846–1900",
      heading: ["Неаполь", "у моря"],
      intro: "Санта-Лючия, морской променад, дворцовая площадь. Как южный город появился в ранней фотографии и цветной печати.",
      chapters: [
        {
          short: "Санта-Лючия",
          date: "Неаполь · 1846",
          title: "Побережье на рассвете фотографии",
          lead: "Море, набережная и город, который ещё не знал массовой туристической открытки.",
          paragraphs: [
            "Английский фотограф Калверт Ричард Джонс снял вид St. Lucia, Naples в 1846 году. Работа хранится в Художественном институте Чикаго.",
            "Этот ранний вид южного города появился до расцвета открыток и массовой цветной печати. Можно рассмотреть, как морской берег и архитектура делят кадр.",
            "Снимок помогает поставить вопрос о жизни города у воды. Но атмосфера и время суток, которые мы чувствуем в изображении, ещё не доказаны его каталогом."
          ],
          interpretation: "Море придаёт сцене не только географию, но и настроение. Это впечатление зрителя, а не зафиксированная эмоция фотографа.",
          src: "../eras/img/naples_santalucia_1846_calvert-jones_aic-27086.jpg",
          alt: "Ранняя фотография Санта-Лючии, Неаполь, 1846 год",
          caption: "Calvert Richard Jones. St. Lucia, Naples, 1846. Art Institute of Chicago.",
          url: "https://www.artic.edu/artworks/27086",
          sourceText: "Art Institute of Chicago · St. Lucia, Naples",
          rights: "AIC: произведение в общественном достоянии."
        },
        {
          short: "Королевский дворец",
          date: "Неаполь · до 1852",
          title: "Площадь и власть",
          lead: "Камера перемещается от морского берега к пространству дворца.",
          paragraphs: [
            "Преподобный Джордж Уилсон Бриджес создал фотографию The King's Palace, Naples до 1852 года. Экземпляр находится в Кливлендском музее искусств.",
            "Её интересно рассмотреть рядом с архитектурой площади: дворец и открытое пространство работают как две части одной композиции.",
            "Здесь особенно важно различать видимое место и рассказ о власти. Кому принадлежал дворец, какие события происходили на площади и кто был зрителем фотографии — отдельные исторические вопросы."
          ],
          interpretation: "Фотография даёт повод исследовать социальную историю пространства, но не отвечает на все вопросы о его политической роли.",
          src: "../eras/img/naples_palazzoreale_pre1852_bridges_cma-1997.13.jpg",
          alt: "Ранняя фотография королевского дворца в Неаполе, созданная до 1852 года",
          caption: "George Wilson Bridges. The King's Palace, Naples, до 1852. Cleveland Museum of Art, 1997.13.",
          url: "https://clevelandart.org/art/1997.13",
          sourceText: "Cleveland Museum of Art · The King's Palace",
          rights: "Cleveland Museum of Art: CC0."
        },
        {
          short: "Неаполь в цвете",
          date: "Неаполь · около 1890–1900",
          title: "Площадь, превращённая в открытку",
          lead: "Печатные цвета создают другой образ города — торжественный и рассчитанный на путешественника.",
          paragraphs: [
            "На фотохроме конца XIX века показаны площадь и церковь Сан-Франческо-ди-Паола. Библиотека Конгресса хранит этот лист в своей коллекции фотохромов.",
            "Как и при взгляде на цветные виды Флоренции, важно помнить о технологии: фотохром не совпадает по способу производства с ранней ручной раскраской литографий.",
            "Два неаполитанских вида позволяют проследить изменение не только объектов, но и самой привычки изображать путешествие."
          ],
          interpretation: "Большая площадь и насыщенные краски формируют впечатление открытки. Это интерпретация композиции, а не вывод об исходном виде камня или штукатурки.",
          src: "../eras/img/naples_plebiscito_c1890-1900_photochrom_loc-ppmsc-06576.jpg",
          alt: "Цветной фотохром площади и церкви Сан-Франческо-ди-Паола в Неаполе около 1890–1900 годов",
          caption: "Plaza and church of San Francesco di Paola, Naples, Italy. Фотохром, около 1890–1900. Library of Congress.",
          url: "https://www.loc.gov/item/2001700916/",
          sourceText: "Library of Congress · Piazza San Francesco di Paola",
          rights: "LoC: No known restrictions on publication. Создатель в карточке не указан."
        }
      ]
    }
  };

  let selected = "paris";
  let chapter = 0;
  let opened = false;
  let quiet = false;

  function readPreference() {
    try { return localStorage.getItem("city-on-paper:quiet-mode") === "true"; }
    catch { return false; }
  }
  function savePreference(value) {
    try { localStorage.setItem("city-on-paper:quiet-mode", value ? "true" : "false"); }
    catch { /* Browser privacy settings may disable storage. */ }
  }
  function setQuiet(value) {
    quiet = Boolean(value);
    document.body.classList.toggle("quiet-mode", quiet);
    $("quietToggle").setAttribute("aria-pressed", String(quiet));
    $("quietToggle").textContent = quiet ? "Включить анимацию" : "Спокойный режим";
    if (quiet && !opened) openBook();
    savePreference(quiet);
  }
  function openBook() {
    if (opened) return;
    opened = true;
    $("atlasBook").dataset.open = "true";
    $("openBook").setAttribute("aria-expanded", "true");
    $("openBook").textContent = "Книга открыта";
    $("openBook").disabled = true;
    $("closeBook").hidden = false;
    $("bookStatus").textContent = "Том открыт. Выберите главу или разверните карту.";
    $(".spread").inert = false;
  }
  function closeBook() {
    if (!opened) return;
    opened = false;
    $("atlasBook").dataset.open = "false";
    $("openBook").setAttribute("aria-expanded", "false");
    $("openBook").textContent = "Открыть атлас";
    $("openBook").disabled = false;
    $("closeBook").hidden = true;
    $("bookStatus").textContent = "Атлас закрыт. Откройте первую страницу.";
    $(".spread").inert = true;
  }
  function $(query) { return root.querySelector(query); } // Small CSS-selector helper.

  function setCity(id) {
    if (!Object.prototype.hasOwnProperty.call(cities, id)) return;
    selected = id;
    chapter = 0;
    openBook();
    const city = cities[id];
    $("pageCountry").textContent = city.label;
    $("cityHeading").replaceChildren();
    $("cityHeading").append(document.createTextNode(city.heading[0]),root.createElement("br"));
    const secondLine = root.createElement("em");
    secondLine.textContent = city.heading[1];
    $("cityHeading").append(secondLine);
    $("cityIntro").textContent = city.intro;
    const list = $("chapterList");
    list.replaceChildren();
    city.chapters.forEach((item, index) => {
      const button = root.createElement("button");
      button.type = "button";
      button.className = "chapter-link" + (index === 0 ? " current" : "");
      button.dataset.chapter = String(index);
      if (index === 0) button.setAttribute("aria-current", "step");
      const num = root.createElement("span");
      num.textContent = String(index + 1).padStart(2, "0");
      const title = root.createElement("strong");
      title.textContent = item.short;
      button.append(num, title);
      button.addEventListener("click", () => chooseChapter(index));
      list.append(button);
    });
    root.querySelectorAll("[data-city]").forEach(button => {
      const active = button.dataset.city === id;
      if (button.classList.contains("spine")) {
        button.classList.toggle("active", active);
        button.setAttribute("aria-pressed", String(active));
      }
    });
    if (!$("reading").hidden) renderChapter();
    $("bookStatus").textContent = "Том «" + city.name + "». Выберите главу.";
  }

  function chooseChapter(index) {
    if (!Number.isInteger(index) || index < 0 || index >= cities[selected].chapters.length) return;
    chapter = index;
    root.querySelectorAll(".chapter-link").forEach(button => {
      const active = Number(button.dataset.chapter) === chapter;
      button.classList.toggle("current", active);
      if (active) button.setAttribute("aria-current", "step");
      else button.removeAttribute("aria-current");
    });
    renderChapter();
    $("reading").hidden = false;
    $("reading").scrollIntoView({ behavior: quiet ? "auto" : "smooth", block: "start" });
  }

  function renderChapter() {
    const data = cities[selected];
    const story = data.chapters[chapter];
    $("readingCity").textContent = data.name;
    $("readingCounter").textContent = "Глава " + (chapter + 1) + " из " + data.chapters.length;
    $("progressFill").style.width = ((chapter + 1) / data.chapters.length * 100) + "%";
    $("chapterImage").src = story.src;
    $("chapterImage").alt = story.alt;
    $("chapterCaption").textContent = story.caption;
    $("chapterEra").textContent = story.date;
    $("reading-title").textContent = story.title;
    $("chapterLead").textContent = story.lead;
    $("chapterBody").replaceChildren();
    story.paragraphs.forEach(text => {
      const paragraph = root.createElement("p");
      paragraph.textContent = text;
      $("chapterBody").append(paragraph);
    });
    const interpretation = root.createElement("p");
    interpretation.className = "interpretation";
    interpretation.textContent = "Авторское прочтение: " + story.interpretation;
    $("chapterBody").append(interpretation);
    $("chapterSource").href = story.url;
    $("chapterSource").textContent = story.sourceText + " ↗";
    $("chapterRights").textContent = story.rights;
    $("prevChapter").disabled = chapter === 0;
    $("nextChapter").textContent = chapter + 1 === data.chapters.length ?
      "Вернуться к карте ↑" : "Следующая глава →";
    root.querySelectorAll(".chapter-link").forEach(button => {
      const active = Number(button.dataset.chapter) === chapter;
      button.classList.toggle("current", active);
      if (active) button.setAttribute("aria-current", "step");
      else button.removeAttribute("aria-current");
    });
  }

  function showDialog(dialog) {
    if (!dialog.open) {
      if (typeof dialog.showModal === "function") dialog.showModal();
      else dialog.setAttribute("open", "");
    }
  }
  function closeDialog(dialog) { if (dialog.open) dialog.close(); }

  $("atlasBook").querySelector(".spread").inert = true;
  $("openBook").addEventListener("click", openBook);
  $("closeBook").addEventListener("click", closeBook);
  $("quietToggle").addEventListener("click", () => setQuiet(!quiet));
  root.querySelectorAll(".spine[data-city]").forEach(button =>
    button.addEventListener("click", () => setCity(button.dataset.city))
  );
  $("topicsToggle").addEventListener("click", () => {
    const isOpen = $("topicsPanel").hidden;
    $("topicsPanel").hidden = !isOpen;
    $("topicsToggle").setAttribute("aria-expanded", String(isOpen));
  });
  $("topicsClose").addEventListener("click", () => {
    $("topicsPanel").hidden = true;
    $("topicsToggle").setAttribute("aria-expanded", "false");
    $("topicsToggle").focus();
  });
  $("startStory").addEventListener("click", () => chooseChapter(chapter));
  $("prevChapter").addEventListener("click", () => chooseChapter(chapter - 1));
  $("nextChapter").addEventListener("click", () => {
    if (chapter + 1 < cities[selected].chapters.length) chooseChapter(chapter + 1);
    else $("atlasBook").scrollIntoView({behavior: quiet ? "auto" : "smooth",block:"center"});
  });
  $("mapOpen").addEventListener("click", () => showDialog($("mapDialog")));
  $("mapClose").addEventListener("click", () => closeDialog($("mapDialog")));
  $("mapDialog").querySelectorAll("button[data-city]").forEach(button =>
    button.addEventListener("click", () => {
      closeDialog($("mapDialog"));
      setCity(button.dataset.city);
      $("atlasBook").scrollIntoView({behavior: quiet ? "auto" : "smooth",block:"center"});
    })
  );
  $("zoomPicture").addEventListener("click", () => {
    const item = cities[selected].chapters[chapter];
    $("largeImage").src = item.src;
    $("largeImage").alt = item.alt;
    $("imageCredit").textContent = item.caption + " · " + item.rights;
    $("zoomSlider").value = "100";
    $("zoomLabel").textContent = "100%";
    $("largeImage").style.width = "100%";
    showDialog($("imageDialog"));
  });
  $("imageClose").addEventListener("click", () => closeDialog($("imageDialog")));
  $("zoomSlider").addEventListener("input", () => {
    const value = Number($("zoomSlider").value);
    $("largeImage").style.width = value + "%";
    $("zoomLabel").textContent = value + "%";
  });
  root.querySelectorAll("dialog").forEach(dialog =>
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) closeDialog(dialog);
    })
  );
  root.addEventListener("keydown", event => {
    if ($("reading").hidden || event.altKey || event.ctrlKey || event.metaKey ||
        event.target.closest("input,textarea,select,dialog")) return;
    if (event.key === "ArrowRight" && chapter < cities[selected].chapters.length - 1) {
      chooseChapter(chapter + 1);
    } else if (event.key === "ArrowLeft" && chapter > 0) {
      chooseChapter(chapter - 1);
    }
  });

  if (readPreference() || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    setQuiet(true);
  }
  const deepLink = new URLSearchParams(location.search);
  if (["paris", "florence", "naples"].includes(deepLink.get("city"))) {
    setCity(deepLink.get("city"));
    const step = Number(deepLink.get("chapter"));
    if (Number.isInteger(step) && step >= 1 && step <= cities[selected].chapters.length) {
      chapter = step - 1;
      renderChapter();
      $("reading").hidden = false;
    }
  } else {
    setCity("paris");
    // First visit starts with the leather cover, unless calm/reduced-motion mode
    // was explicitly enabled. The scene is a UI illustration, not a historical asset.
    if (!quiet) closeBook();
  }
})();
