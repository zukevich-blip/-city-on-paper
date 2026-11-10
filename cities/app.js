/* World City Journal: display actual coverage stages, never invented catalog counts. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const state = {records:[],query:"",region:"all",status:"all",type:"all",take:36,source:""};
  const known = new Map([
    ["париж","paris"],["флоренция","florence"],["неаполь","naples"]
  ]);
  const statusLabels = {
    detailed:"Подробный атлас",
    candidate:"Есть находки",
    seed_only:"Материалы ищутся"
  };
  const typeLabels = {city:"Город",place:"Памятник или место",unclassified:"Тип не уточнён"};

  const compact = (x) => String(x||"").normalize("NFKC").trim().toLocaleLowerCase("ru-RU").replace(/\s+/g," ");
  function el(tag,className,text){
    const x=document.createElement(tag);
    if(className)x.className=className;
    if(text!==undefined)x.textContent=String(text);
    return x;
  }
  const goodUrl = (raw) => {
    try {const u=new URL(String(raw));return u.protocol==="https:"?u.href:"";}
    catch {return "";}
  };
  function navigate(){
    const url=new URL(location.href);
    const fields=[["query",state.query],["region",state.region],["status",state.status],["type",state.type]];
    fields.forEach(([key,value]) => {
      if(value && value!=="all")url.searchParams.set(key,value);
      else url.searchParams.delete(key);
    });
    history.replaceState({},"",url.pathname+url.search+url.hash);
  }
  function fromSeed(data){
    if(!data || !Array.isArray(data.cities))throw Error("Invalid city seed file");
    return data.cities.map(city=>{
      const id=known.get(compact(city.name));
      return {
        name:city.name,country:city.country||"",region:city.region||"",type:"city",
        status:id?"detailed":"seed_only",detail_images:0,atlas_works:0,
        commons_candidates:0,museum_candidates:0,modern_candidates:0,
        candidate_records:0,source_examples:[],seed:true,atlas:false
      };
    });
  }
  function validateRegistry(data){
    if(!data || !Array.isArray(data.entries) || !data.summary || !Number.isInteger(data.summary.combined_names))throw Error("Invalid city coverage registry");
    const names=new Set();
    for(const x of data.entries){
      if(!x || !x.name || !["detailed","candidate","seed_only"].includes(x.status))throw Error("Invalid city entry");
      const key=compact(x.name);
      if(names.has(key))throw Error("Duplicate city entry: "+x.name);
      names.add(key);
    }
    if(names.size!==data.summary.combined_names)throw Error("Registry count mismatch");
    return data.entries;
  }
  function renderStats(){
    const records=state.records;
    const detailed=records.filter(x=>x.status==="detailed").length;
    const candidates=records.filter(x=>x.status==="candidate").length;
    const blank=records.filter(x=>x.status==="seed_only").length;
    const area=$("coverageStats");
    area.replaceChildren();
    const arr=[
      [records.length,state.source==="registry"?"Географических названий в сводном указателе":"Городов в стартовом списке"],
      [detailed,"С подробными материалами"],
      [candidates,"С исследовательскими кандидатами"],
      [blank,"Ожидают наполнения"]
    ];
    for(const [number,label] of arr){
      const stat=el("div","stat");
      stat.append(el("strong",null,number),el("small",null,label));
      area.append(stat);
    }
    $("sourceNote").textContent = state.source==="registry" ?
      "Сводный указатель включает отдельные памятники и местности, не только города. Слияние названий сейчас предварительное, совпадающие имена в разных странах необходимо проверять отдельно. Кандидат — ещё не подтверждённая музейная работа." :
      "Показан исходный список из 150 географических направлений. Полный исследовательский реестр из собранной версии недоступен, поэтому неподтверждённые находки здесь не показаны. Для полного охвата откройте проверяемую сборку музея.";
  }
  function renderRegions(){
    const region=$("region");
    const old=state.region;
    region.replaceChildren(new Option("Все регионы","all"));
    const regions=[...new Set(state.records.map(x=>x.region||"Регион не указан"))].sort((a,b)=>a.localeCompare(b,"ru"));
    for(const name of regions)region.add(new Option(name,name));
    region.value=regions.includes(old)?old:"all";
    state.region=region.value;
  }
  function filtered(){
    const q=compact(state.query);
    return state.records.filter(row=>
      (!q||compact([row.name,row.country,row.region].join(" ")).includes(q)) &&
      (state.region==="all"||(row.region||"Регион не указан")===state.region) &&
      (state.status==="all"||row.status===state.status) &&
      (state.type==="all"||row.type===state.type)
    ).sort((a,b)=>{
      const order={detailed:0,candidate:1,seed_only:2};
      return order[a.status]-order[b.status] || a.name.localeCompare(b.name,"ru");
    });
  }
  function card(row){
    const item=el("article","city-card");
    const top=el("div","city-card-top");
    top.append(el("span","region",row.region||"География уточняется"));
    const badge=el("span","status is-"+row.status,statusLabels[row.status]||"Сверка");
    top.append(badge);
    item.append(top,el("h3",null,row.name));
    const place=(row.country||"Страна не уточнена")+(row.type==="place"?" · "+typeLabels.place:row.type==="unclassified"?" · "+typeLabels.unclassified:"");
    item.append(el("p","place-meta",place));
    const details=row.detail_images||0,candidates=row.candidate_records||0;
    let hint=row.status==="detailed" ?
      (details?details+" изображений с источниками в детальном атласе":"Есть подробная музейная история") :
      row.status==="candidate" ? 
      (candidates+" ссылок и находок для исследовательской проверки") :
      "Пока нет предметных карточек в исследовательском реестре";
    item.append(el("p","info",hint));
    const city=known.get(compact(row.name));
    if(row.status==="detailed" && city){
      const a=el("a","action","Открыть исторический атлас →");
      a.href="../atlas/?city="+encodeURIComponent(city);
      item.append(a);
    } else if(row.status==="candidate"){
      const sources=Array.isArray(row.source_examples)?row.source_examples.filter(x=>goodUrl(x.url)).slice(0,3):[];
      if(sources.length){
        const box=el("details");
        box.append(el("summary",null,"Открыть архивные записи ("+sources.length+")"));
        for(const source of sources){
          const a=el("a",null,source.title||"Перейти к архивной записи");
          a.href=goodUrl(source.url);
          a.target="_blank";
          a.rel="noopener noreferrer";
          box.append(a);
        }
        item.append(box);
      } else item.append(el("span","status-note","Результаты поиска требуют каталогизации"));
    } else {
      item.append(el("span","status-note","Редакционная страница ещё не подготовлена"));
    }
    if(row.country_conflict)item.append(el("small","status-note","Название или страна требуют проверки при объединении"));
    return item;
  }
  function render(){
    const list=filtered();
    $("resultCount").textContent="Показано "+Math.min(list.length,state.take)+" из "+list.length+" найденных объектов";
    const grid=$("cityGrid");
    grid.replaceChildren();
    if(!list.length)grid.append(el("div","empty","По этим условиям ничего не найдено. Попробуйте другое название или регион."));
    else for(const row of list.slice(0,state.take))grid.append(card(row));
    $("showMore").hidden=list.length<=state.take;
    $("showMore").textContent="Показать ещё "+Math.min(36,list.length-state.take)+" объектов";
  }
  function choose(){
    state.query=$("query").value;
    state.region=$("region").value;
    state.status=$("status").value;
    state.type=$("type").value;
    state.take=36;
    navigate();render();
  }
  for(const id of ["query","region","status","type"])
    $(id).addEventListener(id==="query"?"input":"change",choose);
  $("reset").addEventListener("click",()=>{
    state.query="";state.region="all";state.status="all";state.type="all";state.take=36;
    $("query").value="";
    for(const id of ["region","status","type"])$(id).value="all";
    navigate();render();
  });
  $("showMore").addEventListener("click",()=>{state.take+=36;render();});
  const qs=new URLSearchParams(location.search);
  state.query=qs.get("query")||"";
  state.region=qs.get("region")||"all";
  state.status=["all","detailed","candidate","seed_only"].includes(qs.get("status"))?qs.get("status")||"all":"all";
  state.type=["all","city","place","unclassified"].includes(qs.get("type"))?qs.get("type")||"all":"all";
  $("query").value=state.query;
  $("status").value=state.status;
  $("type").value=state.type;

  async function load(){
    let rows,via="seed";
    try {
      const response=await fetch("../data/coverage/world-coverage-20261110.json");
      if(response.ok){
        rows=validateRegistry(await response.json());
        via="registry";
      }
    } catch { /* Static source checkout has no generated registry: use the seed safely. */ }
    if(!rows){
      const response=await fetch("../data/curation/world-cities-v1.json");
      if(!response.ok)throw Error("City seed file unavailable");
      rows=fromSeed(await response.json());
    }
    state.records=rows;
    state.source=via;
    renderRegions();renderStats();render();
  }
  load().catch(err=>{
    $("coverageStats").textContent="Не удалось загрузить каталог";
    $("resultCount").textContent="Ошибка загрузки данных";
    $("cityGrid").replaceChildren(el("div","empty",
      "Каталог недоступен: "+err.message+". Откройте музей через локальный HTTP-сервер или защищённый сайт."));
  });
})();
