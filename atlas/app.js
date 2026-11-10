/* City on Paper / Time Atlas.
   The museum dataset supplies every title, attribution, file, date and rights record.
   This viewer does NOT use GCP coordinates or claim a precise historical viewpoint. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const state = {city:"paris",era:"all",items:[],selected:null,ready:false};
  const names = {paris:"Париж",florence:"Флоренция",naples:"Неаполь"};
  const eraNames = {print:"Печатная графика",photo:"Фотография / фотохром",today:"Современный снимок"};
  const sourceBase = new URL("../eras/",location.href);

  const cityParams = new URLSearchParams(location.search);
  const initCity = cityParams.get("city");
  const initEra = cityParams.get("era");
  if (Object.hasOwn(names,initCity)) state.city=initCity;
  if (["all","print","photo","today"].includes(initEra)) state.era=initEra;

  function itemUrl(img){
    if (typeof img.file!=="string" || !/^img\/[a-zA-Z0-9_./-]+\.(?:jpg|jpeg|png|webp)$/.test(img.file) || img.file.includes(".."))return "";
    return new URL(img.file,sourceBase).href;
  }
  function safeSource(img){
    try {
      const u=new URL(img.object_url);
      return u.protocol==="https:" ? u.href : "";
    } catch{return "";}
  }
  function yearText(img){return String(img.year_label||img.date||"Дата не установлена")}
  function readableCreator(img){
    const people=Array.isArray(img.creators)?img.creators.filter(x=>x && x.name).map(x=>x.name):[];
    return people.length?people.join("; "):"Автор не указан в источнике";
  }
  function typeOf(img){
    if(["print","photo","today"].includes(img.era))return img.era;
    if(img.kind==="photochrom" || img.kind==="photo")return "photo";
    return img.kind==="today"?"today":"print";
  }
  function selectedCity(){
    return (state.items||[]).find(x=>x.id===state.city);
  }
  function available(){
    const city=selectedCity();
    if(!city || !Array.isArray(city.places))return [];
    return city.places.flatMap(place=>
      (place.images||[]).filter(img=>img.rights_class==="open"&&itemUrl(img)&&safeSource(img)).map(img=>({place,img})))
      .filter(x=>state.era==="all"||typeOf(x.img)===state.era);
  }
  function create(tag,cls,value){
    const n=document.createElement(tag);
    if(cls)n.className=cls;
    if(value!==undefined)n.textContent=value;
    return n;
  }
  function updateButtons(){
    document.querySelectorAll("#cityFilters button").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.city===state.city)));
    document.querySelectorAll("#eraFilters button").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.era===state.era)));
  }
  function shareCurrent(){
    const url=new URL(location.href);
    url.searchParams.set("city",state.city);
    if(state.era!=="all")url.searchParams.set("era",state.era);
    else url.searchParams.delete("era");
    history.replaceState(null,"",url.pathname+url.search+url.hash);
  }
  function selectImage(item,scroll=true){
    const img=item.img;
    state.selected=item;
    $("selection").hidden=false;
    $("selectPrompt").hidden=true;
    $("selectedImage").src=itemUrl(img);
    $("selectedImage").alt=img.alt||img.title||"Архивное изображение";
    $("selectedCaption").textContent=(img.title||item.place.title)+" · "+(img.institution||"Музейная коллекция");
    $("selectedKind").textContent=eraNames[typeOf(img)]||"Исторический вид";
    $("selectedTitle").textContent=img.title||"Без названия";
    $("selectedAttribution").replaceChildren(create("strong",null,"Автор: "),document.createTextNode(readableCreator(img)));
    $("selectedDate").replaceChildren(create("strong",null,"Дата: "),document.createTextNode(yearText(img)));
    $("selectedInstitution").replaceChildren(create("strong",null,"Хранитель: "),document.createTextNode(img.institution||"Не указан"));
    $("selectedRights").replaceChildren(create("strong",null,"Право: "),document.createTextNode(img.rights_short||img.rights||"Проверка прав требуется"));
    const source=$("selectedSource");
    source.href=safeSource(img);
    source.textContent="Открыть музейный оригинал ↗";
    const story=$("selectedStory");
    if(state.city==="paris"){story.href="../stories/paris-on-paper/";story.textContent="Читать историю Парижа";}
    else{story.href="../experience/?city="+encodeURIComponent(state.city)+"&chapter=1";story.textContent="Читать главу "+names[state.city];}
    document.querySelectorAll(".result-item").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.item===img.id)));
    if(scroll)$("selectedArea").scrollIntoView({behavior:matchMedia("(prefers-reduced-motion: reduce)").matches?"auto":"smooth",block:"start"});
  }
  function render(){
    updateButtons();
    if(!state.ready)return;
    const city=selectedCity();
    if(!city)return;
    $("currentCity").textContent=names[state.city]+" · Исторические изображения";
    $("cityDescription").textContent=city.places.map(p=>p.title).join(" · ")+". Выберите лист для просмотра архивной карточки.";
    const items=available();
    $("resultCount").textContent=items.length+" изображений с открытым статусом прав";
    const container=$("atlasResults");
    container.replaceChildren();
    if(!items.length){
      container.append(create("div","empty","Нет подтверждённых изображений для этого периода. Можно выбрать другую эпоху; недостающие записи не заполняются выдумкой."));
      $("selection").hidden=true;
      $("selectPrompt").hidden=false;
      return;
    }
    items.forEach(item=>{
      const b=create("button","result-item");
      b.type="button";
      b.dataset.item=item.img.id;
      b.setAttribute("aria-pressed",String(state.selected?.img.id===item.img.id));
      b.setAttribute("aria-label",(item.img.title||item.place.title)+", "+yearText(item.img)+", показать архивные сведения");
      const pic=create("img");
      pic.src=itemUrl(item.img);
      pic.alt=item.img.alt||item.img.title||"Архивное изображение";
      pic.loading="lazy";
      const label=create("div","record-mini");
      label.append(create("span",null,yearText(item.img)+" · "+(eraNames[typeOf(item.img)]||"Исторический вид")));
      label.append(create("strong",null,item.img.title||item.place.title));
      label.append(create("small",null,item.img.institution||"Историческая коллекция"));
      b.append(pic,label);
      b.addEventListener("click",()=>selectImage(item));
      container.append(b);
    });
    selectImage(items[0],false);
  }
  document.querySelectorAll("#cityFilters button").forEach(b=>b.addEventListener("click",()=>{
    state.city=b.dataset.city;
    state.selected=null;shareCurrent();render();
  }));
  document.querySelectorAll("#eraFilters button").forEach(b=>b.addEventListener("click",()=>{
    state.era=b.dataset.era;
    state.selected=null;shareCurrent();render();
  }));
  updateButtons();
  fetch(new URL("../eras/data/eras.json",location.href))
    .then(response=>{
      if(!response.ok)throw Error("HTTP "+response.status);
      return response.json();
    })
    .then(data=>{
      if(!data || !Array.isArray(data.cities))throw Error("Invalid museum atlas");
      state.items=data.cities.filter(city=>Object.hasOwn(names,city.id));
      state.ready=true;
      render();
    })
    .catch(err=>{
      $("resultCount").textContent="Каталог временно недоступен";
      $("atlasResults").replaceChildren(create("div","empty","Не удалось загрузить список изображений ("+err.message+"). Попробуйте открыть исходный атлас эпох по ссылке слева."));
      $("selection").hidden=true;
      $("selectPrompt").hidden=false;
    });
})();
