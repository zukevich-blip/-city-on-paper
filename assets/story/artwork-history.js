/* City on Paper — evidence-led individual artwork stories.
 * Curatorial prose is never invented for items whose holder record has not been researched.
 * Three distinct layers: record (per artwork); historical place (sourced); unknowns.
 */
"use strict";
window.CityArtworkHistory = (() => {
  const h = x => String(x ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const s = x => String(x ?? "").trim();
  const link = x => /^https:\/\/[^ <>"']+$/.test(s(x)) ? s(x) : "";
  const related = [
    {
      match: a => /(?:\/item\/2016652452\/?|pga-14315)/i.test(a.url+" "+a.id) ||
        (/paris\. la madeleine/i.test(a.title) && /benoist/i.test(a.author)),
      badge:"Проверено по первоисточнику",
      text:[
        "На листе различимы портик и боковая коринфская колоннада церкви Мадлен, а перед зданием — конный экипаж и прохожие. Это не постановочная фотография города: Библиотека Конгресса описывает его как раскрашенную вручную литографию.",
        "Надпись «Ph. Benoist del.» фиксирует автора рисунка, а «Imp. Lemercier» называет печатное предприятие. Имя заказчика этого конкретного выпуска и точный год изготовления листа не установлены."
      ],
      context:"Мадлен завершили в 1842 году после многократных изменений назначения при монархии, Революции и Наполеоне. Вокруг здания стоят 52 коринфские колонны. Таким образом, работа Бенуа показывает уже достроенный храм.",
      sources:[
        ["Библиотека Конгресса: эстамп","https://www.loc.gov/item/2016652452/"],
        ["Париж: история и колоннада","https://www.paris.fr/pages/debut-des-travaux-pour-l-eglise-de-la-madeleine-18409"]
      ]
    },
    {
      match: a => /320289563|\/paris-boulevart-des-italiens(?:\/|$)/i.test(a.url+" "+a.id),
      badge:"Проверено по музейному инвентарю",
      text:[
        "Этот цветной литографированный лист с видом бульвара Итальянцев музей Карнавале датирует примерно 1855 годом. В музейной записи Филипп Бенуа назван рисовальщиком-литографом, Lemercier — печатником, а Daziaro — издателем.",
        "Это важное различие: художник, типография и издатель не обязательно были одним лицом. По записи музея лист имеет размеры 43,3 × 60 см и смонтирован на картонной основе."
      ],
      context:"Музей связывает изображение с южной стороной бульвара и окрестностями улиц Rue de la Paix, Rue Daunou, а также будущей Avenue de l’Opéra. Эта индексная связь не доказывает точное положение художника.",
      sources:[["Paris Musées / Carnavalet","https://parismuseescollections.paris.fr/fr/musee-carnavalet/oeuvres/paris-boulevart-des-italiens"]]
    },
    {
      match: a => /320289583|vues-de-paris-11-views-of-paris-le-boulevart-des/i.test(a.url+" "+a.id),
      badge:"Проверено по музейному инвентарю",
      text:[
        "Работа относится к серии «Vues de Paris» и обозначена номером 11. Каталог музея Карнавале отдельно называет Филиппа Бенуа и Адольфа Байо, а для печати — мастерскую Gihaut Frères.",
        "Это другой лист о бульваре Итальянцев, не совпадающий автоматически с литографией, напечатанной Lemercier и изданной Daziaro около 1855 года. Дату именно этого листа музей в доступном описании не приводит."
      ],
      context:"Размер изображения по инвентарю: 37,5 × 48,5 см; на музейном монтаже 50,2 × 65,2 см. Сравнивать варианты следует по подписи, композиции и номеру серии, не только по месту.",
      sources:[["Paris Musées / Carnavalet","https://parismuseescollections.paris.fr/fr/musee-carnavalet/oeuvres/vues-de-paris-11-views-of-paris-le-boulevart-des-italiens-the-boulevart-des"]]
    },
    {
      match: a => /le vieux paris du 15me au 16me|tour de nesle/i.test(a.title),
      badge:"Ретроспективный исторический вид",
      text:[
        "Франсуа Александр Перно создал этот офорт приблизительно в 1835–1836 годах, изображая воображаемую реконструкцию Парижа XV–XVI веков. Даты в названии указывают эпоху сюжета, а не время печати.",
        "Сама Нельская башня возникла около 1200 года и была уничтожена в 1663 году. На карте Парижа 1878 года здесь можно отмечать только историческое местоположение исчезнувшего сооружения."
      ],
      context:"В инвентаре Maison de Victor Hugo значится офорт Перно, а не лист Филиппа Бенуа. Это различие важно для правильной атрибуции в общем городском каталоге.",
      sources:[
        ["Paris Musées: офорт Перно","https://parismuseescollections.paris.fr/fr/maison-de-victor-hugo/oeuvres/le-vieux-paris-du-15me-au-16me-siecle-vu-pres-de-la-tour-de-nesle"],
        ["Город Париж: история башни","https://www.paris.fr/pages/ces-lieux-disparus-qui-font-aussi-l-histoire-de-paris-17263"]
      ]
    },
    {
      match: a => /le vieux paris du 14me au 15me/i.test(a.title),
      badge:"Ретроспективный исторический вид",
      text:[
        "Офорт Франсуа Александра Перно с видом средневекового Парижа со стороны башен Нотр-Дама выполнен около 1835–1836 годов. XIV–XV века обозначают изображаемую историческую эпоху, но не дату создания произведения.",
        "Лист хранится в коллекции Maisons de Victor Hugo; это не современная фотография и не свидетельство очевидца Средневековья. Как реконструкция он требует особой осторожности при геопривязке."
      ],
      context:"Музей указывает автором модели Перно, технику «офорт» и инвентарный номер 2017.0.2677.1.",
      sources:[["Paris Musées: Перно, Нотр-Дам","https://www.parismuseescollections.paris.fr/fr/maison-de-victor-hugo/oeuvres/le-vieux-paris-du-14me-au-15me-siecle-vu-des-tours-notre-dame"]]
    }
  ];
  const limit = (t,n=240) => s(t).slice(0,n);
  const normal = w => ({
    id:s(w.id||w.source_id||w.wid),title:s(w.title||w.name||w.title_original||"Без заглавия"),
    original:s(w.title_original),author:s(w.artist||w.maker||w.author||(w.creators||[]).map(c=>c.name).join(", ")),
    date:s(w.date||w.year_label||w.year),place:s(w.place||w.city||w.site_name||w.site_ru),
    medium:s(w.medium||w.style||w.kind),institution:s(w.institution||w.source||""),
    url:link(w.url||w.object_url||w.source_url),album:s(w.album||w.series||""),
    note:s(w.note||w.description),identity:s(w.identity_certainty),creatorField:s(w.creator_field),roles:Array.isArray(w.creator_roles)?w.creator_roles:[],
    confidence:s(w.confidence)
  });
  function story(work){
    const a=normal(work), deep=related.find(r=>r.match(a)), hasDate=Boolean(a.date);
    const data=[];
    if(a.author)data.push("В каталоге автор указан как "+limit(a.author,180)+".");
    else data.push("Авторство в доступной записи пока не подтверждено.");
    if(hasDate)data.push("Датировка экземпляра или произведения: "+limit(a.date,90)+".");
    else data.push("Надёжная дата создания этого листа пока не установлена.");
    if(a.medium)data.push("Техника или тип в каталоге: "+limit(a.medium,85)+".");
    if(a.place)data.push("В записи произведение связано с местом: "+limit(a.place,110)+". Эта запись сама по себе не доказывает точку наблюдателя.");
    if(a.album)data.push("Указанная в источнике серия или альбом: "+limit(a.album,140)+".");
    if(a.roles.length)data.push("Участники изготовления по музейной записи: "+a.roles.slice(0,4).map(r=>limit(r.name||"",70)+(r.role?" ("+limit(r.role,50)+")":"")).join("; ")+".");
    if(a.creatorField)data.push("Поля атрибуции исходного каталога: "+limit(a.creatorField,260)+". Запись не всегда разделяет художника рисунка, литографа и издателя.");
    if(a.identity&&/probable|album-level|unresolved|uncertain|initial|question|not confirmed|неопредел/i.test(a.identity))data.push("Авторская атрибуция предварительна: "+limit(a.identity,120)+".");
    const source=[];
    if(a.url)source.push(["Карточка произведения у хранителя",a.url]);
    if(deep)for(const [name,url] of deep.sources)if(!source.some(x=>x[1]===url))source.push([name,url]);
    const missing=[];
    if(!hasDate)missing.push("точная датировка");
    if(!a.author)missing.push("личность автора");
    if(!a.place)missing.push("идентификация изображённого места");
    missing.push("подтверждённая точка наблюдения");
    if(!deep)missing.push("события, связанные именно с созданием этого листа");
    return {a,deep,source,data,missing};
  }
  function markup(w,{open=false,compact=false}={}){
    const x=story(w),{a,deep}=x,heading=deep?deep.badge:"Индивидуальный паспорт · история уточняется";
    const origins=x.data.map(t=>"<p>"+h(t)+"</p>").join("");
    const editorial=a.note&&!deep?'<div class="art-history-editorial"><h5>Описание в каталоге проекта</h5><p>'+h(limit(a.note,450))+'</p><small>Редакционная помета, не независимое подтверждение исторического события.</small></div>':"";
    const deepHtml=deep?'<div class="art-history-context"><h5>Что происходило с местом и листом</h5>'+
      deep.text.map(t=>"<p>"+h(t)+"</p>").join("")+
      (deep.context?"<p>"+h(deep.context)+"</p>":"")+"</div>":
      '<p class="art-history-pending">Подробная история создания пока не подтверждена источниками. '+
      'Здесь приведены установленные сведения именно об этом листе, а не выдуманный рассказ.</p>';
    const refs=x.source.length?'<div class="art-history-sources"><b>Первоисточники</b>'+
      x.source.map(([n,u])=>'<a target="_blank" rel="noopener noreferrer" href="'+h(u)+'">'+h(n)+' ↗</a>').join("")+
      '</div>':'<p class="art-history-pending">Ссылка на музейный оригинал пока не указана.</p>';
    return '<details class="art-history'+(compact?" art-history-compact":"")+'"'+(open?" open":"")+'> '+
      '<summary><span>История произведения</span><small>'+h(heading)+'</small></summary>'+
      '<div class="art-history-body"><h4>'+h(a.title)+'</h4><section><h5>Паспорт и происхождение</h5>'+origins+'</section>'+
      deepHtml+editorial+
      '<p class="art-history-unknown"><b>Что пока неизвестно:</b> '+h(x.missing.join("; "))+'.</p>'+refs+
      '</div></details>';
  }
  return {story,markup};
})();
