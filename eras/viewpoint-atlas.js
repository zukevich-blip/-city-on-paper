/* City on Paper | Viewpoint Atlas. Curated evidence and local visitor photos.
 * A depicted-place coordinate is NEVER treated as an artist camera position.
 * Historical image pixels are ONLY used with their exact named detail sheet.
 */
"use strict";
window.CityOnPaperViewpoints = (() => {
  const esc = s => String(s ?? "").replace(/[&<>"']/g, x => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[x]));
  const https = u => typeof u === "string" && /^https:\/\//.test(u) ? u : "";
  const finite = (n,a,b) => Number.isFinite(+n) && +n >= a && +n <= b;
  const localFile = p => typeof p === "string" && /^img\/[a-zA-Z0-9_.-]+\.jpg$/.test(p) ? p : "";
  const dist = (a,b) => {
    const dy=(a.lat-b.lat)*111195, dx=(a.lon-b.lon)*111195*Math.cos(a.lat*Math.PI/180);
    return Math.hypot(dx,dy);
  };
  const azdiff = (a,b) => Math.abs(((a-b+540)%360)-180);
  const target = (cam, angle, length) => {
    const rad=angle*Math.PI/180;
    return [cam.lat + (length/111195)*Math.cos(rad),
      cam.lon + (length/(111195*Math.cos(cam.lat*Math.PI/180)))*Math.sin(rad)];
  };
  let archivePromise;
  const archive = () => archivePromise || (archivePromise=fetch("data/eras.json")
    .then(r=>{if(!r.ok)throw Error("HTTP "+r.status);return r.json();}).catch(()=>({cities:[]})));
  const localDb = (() => {
    let promise;
    const db = () => promise || (promise=new Promise((resolve,reject)=>{
      if(!window.indexedDB)return reject(Error("IndexedDB unavailable"));
      const r=indexedDB.open("city-on-paper-mine",1);
      r.onupgradeneeded=()=>{if(!r.result.objectStoreNames.contains("photos"))r.result.createObjectStore("photos",{keyPath:"id"});};
      r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);
    }));
    const tx = (mode,cb) => db().then(d=>new Promise((resolve,reject)=>{
      const t=d.transaction("photos",mode),req=cb(t.objectStore("photos"));
      t.oncomplete=()=>resolve(req && "result" in req ? req.result : null);
      t.onerror=()=>reject(t.error||Error("storage error"));
    }));
    return {
      all:()=>tx("readonly",s=>s.getAll()).catch(()=>[]),
      put:v=>tx("readwrite",s=>s.put(v)),
      del:id=>tx("readwrite",s=>s.delete(id))
    };
  })();
  const photos = new Map();
  const ownURL = r => {
    if(!photos.has(r.id))photos.set(r.id,URL.createObjectURL(r.blob));
    return photos.get(r.id);
  };
  const creator = img => (img.creators||[]).map(x=>x.name).filter(Boolean).join(", ") || "Автор в источнике не установлен";
  function curated(cityId, data) {
    const c=(data.cities||[]).find(x=>x.id===cityId);
    if(!c)return {city:null,rows:[]};
    const rows=[];
    for(const place of c.places||[]) {
      const modern=(place.images||[]).filter(x=>x.era==="today" && localFile(x.file));
      for(const image of place.images||[]) {
        if(!localFile(image.file))continue;
        const cam=image.camera && finite(image.camera.lat,-90,90) && finite(image.camera.lon,-180,180)
          ? {lat:+image.camera.lat,lon:+image.camera.lon,az:+image.camera.azimuth_deg||0,
            radius:+image.camera.radius_m||null,px:+image.camera.px,py:+image.camera.py,
            confidence:image.camera.confidence||"",basis:image.camera.basis||""} : null;
        const candidate= image.era==="today" ? null : modern.slice().sort((a,b)=>{
          const d=x=>cam && x.camera ? dist(cam,x.camera)+azdiff(cam.az,+x.camera.azimuth_deg)*3 : 10000;
          return d(a)-d(b);
        })[0]||null;
        let match="missing";
        if(candidate) {
          if(cam && candidate.camera) {
            const distance=dist(cam,candidate.camera);
            const angle=azdiff(cam.az,+candidate.camera.azimuth_deg);
            match=distance<=45 && angle<=15 ? "near" : "different";
          } else match="site";
        }
        rows.push({id:image.id,kind:image.era,placeId:place.id,place:place.title||place.short||"",
          title:image.title,year:image.year_label||image.date||"Дата уточняется",
          author:creator(image),image:localFile(image.file),source:https(image.object_url),
          rights:image.rights_short||image.rights||"Права уточняются",cam,modern:candidate,
          match,plan:place.plan_detail||null,target:place.plan_xy||null});
      }
    }
    return {city:c,rows};
  }
  function status(row) {
    if(row.kind==="today")return "Современный снимок · геоданные: "+(row.cam?"есть":"нет");
    if(!row.modern)return "Современная фотография того же объекта не подобрана";
    if(row.match==="near")return "Близкий ракурс по оценке координат и направления, совпадение не доказано";
    if(row.match==="different")return "Тот же объект, другой ракурс";
    return "Тот же объект, точка съёмки не установлена";
  }
  function mount(host, city) {
    if(!host||!city)return;
    host.innerHTML='<div class="vpa-shell"><p class="note">Загружаем подтверждённые ракурсы и личные снимки…</p></div>';
    Promise.all([archive(),localDb.all()]).then(([data,personal])=>{
      if(!host.isConnected)return;
      let list=curated(city.id,data);
      const own=personal.filter(x=>x.city===city.id && x.workType==="modern" && x.blob &&
        finite(x.lat,-90,90)&&finite(x.lon,-180,180));
      const selected={row:null,overlay:false};
      const gallery=list.rows.filter(x=>x.kind!=="today");
      const works=gallery.length?gallery:(city.sites||[]).slice(0,120).map((s,i)=>({
        id:String(s.wid||("site-"+i)),place:String(s.site_ru||s.site_name||city.name),
        title:String(s.title||s.site_ru||"Вид города"),year:String(s.date||"Дата уточняется"),
        author:(city.works||[]).find(w=>w.url===s.url)?.artist||"Автор в каталоге",
        image:"",source:https(s.url),rights:"Смотреть права у хранителя",kind:"print",
        cam:null,modern:null,match:"missing",target:null,placeId:null,object:{lat:+s.lat,lon:+s.lon}
      }));
      const years=works.length, located=gallery.filter(x=>x.cam).length,
        analogues=gallery.filter(x=>x.modern).length;
      const historic=list.city && (list.city.places||[]).find(p=>p.plan_detail && (p.images||[]).some(x=>x.camera&&finite(x.camera.px,0,1e6)));
      const oldSheet=historic?historic.plan_detail:null;
      const oldMapHtml=oldSheet?'<div class="vpa-map-col"><h3>Исторический план · '+esc(oldSheet.title)+
        '</h3><div id="vpaOld" class="vpa-map" role="region" aria-label="Лист исторической карты с исследовательскими точками ракурсов"></div>'+
        '<p class="vpa-note">Положение на листе установлено приблизительно по опорным точкам. Это фрагмент именно '+esc(oldSheet.title)+
        ', не любая историческая карта.</p></div>':'';
      host.innerHTML='<div class="vpa-shell"><div class="vpa-intro"><span class="eyebrow">Карта ракурсов · музейная лаборатория</span>'+
        '<h2 id="vpaTitle">Откуда смотрел автор. Как выглядит сегодня</h2>'+
        '<p>Одна работа, один изображённый объект, отдельная точка наблюдения и современная фотография. Отсутствующий ракурс не заменяем выдуманным.</p>'+
        '<div class="vpa-counts" role="status"><span>Работ: <b>'+years+'</b></span><span>Исследованных точек: <b>'+located+
        '</b></span><span>Современных аналогов объекта: <b>'+analogues+
        '</b></span><span>Мои снимки: <b id="vpaOwnCount">'+own.length+'</b></span></div></div>'+
        '<div class="vpa-map-grid">'+oldMapHtml+
        '<div class="vpa-map-col"><h3>Город сегодня · точки камеры и объекты</h3>'+
        '<div id="vpaNow" class="vpa-map" role="region" aria-label="Современная карта с ракурсами авторов и посетителя"></div>'+
        '<p class="vpa-note">◉ Камера с направлением; ● изображённый объект. Приблизительные позиции исторических авторов отмечены как гипотезы.</p></div></div>'+
        '<div class="vpa-film"><div class="vpa-film-head"><h3 id="vpaSelected">Выберите изображение для сравнения</h3>'+
        '<span id="vpaStatus"></span></div><div id="vpaCompare" class="vpa-compare" role="region" aria-label="Сравнение старого и нового ракурса"></div>'+
        '<div class="vpa-mode"><button id="vpaSide" type="button" aria-pressed="true">Рядом</button>'+
        '<button id="vpaWipe" type="button" aria-pressed="false">Шторка</button>'+
        '<label id="vpaWipeWrap" hidden>Положение шторки <input id="vpaWipeRange" type="range" min="0" max="100" value="50"></label></div>'+
        '<p class="vpa-note" id="vpaCompareTruth">Пара не выбрана. При разных ракурсах геометрическое наложение не подтверждено.</p></div>'+
        '<h3 class="vpa-list-title">Произведения и паспорт точки</h3>'+
        '<div id="vpaGallery" class="vpa-gallery"></div>'+
        '<details class="vpa-contribute" id="vpaContribution"><summary>Добавить современное фото и точку съёмки на карту</summary>'+
        '<p>Ваш снимок останется в этом браузере. Выберите произведение, нажмите на современную карту в месте съёмки, укажите направление взгляда. На карте появится ваш маркер.</p>'+
        '<form id="vpaForm"><label>Файл JPG/PNG/WebP (до 15 МБ)<input id="vpaFile" type="file" accept="image/jpeg,image/png,image/webp" required></label>'+
        '<label>К какому произведению снимок<input id="vpaLink" list="vpaWorks" placeholder="Выберите произведение" required></label>'+
        '<datalist id="vpaWorks">'+works.map(r=>'<option value="'+esc(r.id)+'">'+esc(r.title)+'</option>').join("")+'</datalist>'+
        '<div class="vpa-geofields"><label>Широта<input id="vpaLat" type="number" min="-90" max="90" step="any" required></label>'+
        '<label>Долгота<input id="vpaLon" type="number" min="-180" max="180" step="any" required></label>'+
        '<label>Направление взгляда, °<input id="vpaAz" type="number" min="0" max="359" value="0" required></label></div>'+
        '<div class="vpa-form-actions"><button type="button" id="vpaPick">Указать точку на карте</button>'+
        '<button type="submit" id="vpaSave">Сохранить локально</button></div>'+
        '<p id="vpaFeedback" role="status" aria-live="polite"></p></form></details></div>';
      const $=s=>host.querySelector(s);
      const galleryHost=$("#vpaGallery"), feedback=$("#vpaFeedback");
      const nowNode=$("#vpaNow");
      let current=null, old=null, ownLayer=null, camLayer=null, historicLayer=null, temp=null, pickMode=false;
      let mode="side";
      const hasLeaflet=!!window.L;
      const placeObject=new Map();
      (city.sites||[]).forEach(s=>{
        if(finite(s.lat,-90,90)&&finite(s.lon,-180,180))
          placeObject.set(s.site_ru||s.site_name,[+s.lat,+s.lon]);
      });
      function modernFor(r){
        const p=own.find(x=>x.workLink===r.id);
        if(p)return {file:ownURL(p),year:p.date||"Мой снимок",author:p.author||"Посетитель",cam:{lat:p.lat,lon:p.lon,az:p.az||0},source:"",local:true};
        if(r.modern&&localFile(r.modern.file))return {file:r.modern.file,
          year:r.modern.year_label||r.modern.date||"Сегодня",
          author:creator(r.modern),cam:r.modern.camera,source:https(r.modern.object_url)};
        return null;
      }
      function compare(r){
        selected.row=r;$("#vpaSelected").textContent=r.title;
        const analog=modernFor(r), box=$("#vpaCompare"), info=$("#vpaCompareTruth");
        $("#vpaStatus").textContent=(r.cam?"Камера: "+r.cam.lat.toFixed(5)+", "+r.cam.lon.toFixed(5)+
          " · азимут "+r.cam.az+"° · точность "+(r.cam.confidence||"не задана"):"Точка автора не установлена");
        const left=r.image?'<figure><img loading="lazy" src="'+esc(r.image)+'" alt="'+esc(r.title)+'"><figcaption>'+
          esc(r.year)+" · "+esc(r.author)+'</figcaption></figure>':
          '<div class="vpa-empty">Источник изображения находится у хранителя. Откройте архивную карточку.</div>';
        const right=analog?'<figure><img loading="lazy" src="'+esc(analog.file)+'" alt="Современный аналог объекта"><figcaption>'+
          esc(analog.year)+" · "+esc(analog.author)+'</figcaption></figure>':
          '<div class="vpa-empty">Современный снимок пока не найден. Можно добавить свой.</div>';
        box.className="vpa-compare "+(mode==="wipe"&&r.image&&analog?"is-wipe":"");
        box.innerHTML=left+right;
        if(box.classList.contains("is-wipe"))box.style.setProperty("--wipe",$("#vpaWipeRange").value+"%");
        $("#vpaWipeWrap").hidden=!(r.image&&analog&&mode==="wipe");
        $("#vpaWipe").disabled=!(r.image&&analog);
        const mat=analog && r.cam && analog.cam && finite(analog.cam.lat,-90,90) &&
          finite(analog.cam.lon,-180,180) ?
          "Разница точек ≈"+Math.round(dist(r.cam,analog.cam))+" м, направления ≈"+
            Math.round(azdiff(r.cam.az,+analog.cam.azimuth_deg||analog.cam.az||0))+"°. " : "";
        info.textContent=(analog?"Один изображённый объект. "+mat+
          "Сравнение исследовательское: точное совпадение перспективы не подтверждено.":
          "Для этой работы нет подобранного современного кадра. Сохраните снимок с новой точки на карте.")+
          (r.cam&&r.cam.basis?" Основание оценки: "+r.cam.basis:"");
        galleryHost.querySelectorAll("[data-vpa-id]").forEach(b=>
          b.setAttribute("aria-pressed",String(b.dataset.vpaId===r.id)));
        if(current && r.cam) {
          current.setView([r.cam.lat,r.cam.lon],Math.max(current.getZoom(),16));
          highlight(r);
        }
        if(old&&r.cam&&finite(r.cam.px,0,oldSheet.width)&&finite(r.cam.py,0,oldSheet.height)) {
          old.setView([-r.cam.py,r.cam.px],old.getZoom(),{animate:false});
        }
      }
      function highlight(r){
        if(!current||!window.L)return;
        if(temp){current.removeLayer(temp);temp=null;}
        if(r.cam) {
          const anchor=[r.cam.lat,r.cam.lon],endpoint=target(r.cam,r.cam.az,60);
          temp=L.layerGroup().addTo(current);
          L.circle(anchor,{radius:Math.max(7,Math.min(120,r.cam.radius||15)),weight:1,
            color:"#9d4a32",fillOpacity:.06}).addTo(temp);
          L.polyline([anchor,endpoint],{color:"#9d4a32",weight:3,dashArray:"8 5"}).addTo(temp);
        }
      }
      function drawGallery(){
        const all=works.slice(0,90);
        galleryHost.innerHTML=all.length?all.map(r=>{
          const analog=modernFor(r), a=r.source?
            '<a href="'+esc(r.source)+'" target="_blank" rel="noopener noreferrer">Архивный источник</a>':'';
          return '<article class="vpa-art"><button type="button" data-vpa-id="'+esc(r.id)+
            '" aria-pressed="false">'+(r.image?'<img src="'+esc(r.image)+
            '" alt="" loading="lazy">':'<span class="vpa-placeholder">Архивный источник</span>')+
            '<span class="vpa-art-text"><b>'+esc(r.title)+'</b><small>'+esc(r.year)+" · "+esc(r.author)+
            '</small><small>'+esc(r.place)+'</small><em>'+esc(analog?"Современный аналог объекта: найден":
            "Современный аналог требуется")+'</em></span></button>'+
            '<div class="vpa-art-foot"><small>'+esc(r.cam?
              "Ракурс: "+(r.cam.confidence||"оценка")+" · ±"+(r.cam.radius||"?")+" м":
              "Точка автора не установлена")+'</small>'+a+'</div></article>';
        }).join(""):'<p class="vpa-note">Для этого города ещё нет работ с индивидуальной географической карточкой. Городской каталог доступен выше; карта не выдаёт центр города за точку художника.</p>';
        galleryHost.querySelectorAll("button[data-vpa-id]").forEach(b=>
          b.onclick=()=>{const r=works.find(x=>x.id===b.dataset.vpaId);
            if(r){compare(r);$(".vpa-film").scrollIntoView({behavior:"smooth",block:"start"});}});
      }
      $("#vpaSide").onclick=()=>{mode="side";$("#vpaSide").setAttribute("aria-pressed","true");
        $("#vpaWipe").setAttribute("aria-pressed","false");if(selected.row)compare(selected.row);};
      $("#vpaWipe").onclick=()=>{mode="wipe";$("#vpaSide").setAttribute("aria-pressed","false");
        $("#vpaWipe").setAttribute("aria-pressed","true");if(selected.row)compare(selected.row);};
      $("#vpaWipeRange").oninput=e=>$("#vpaCompare").style.setProperty("--wipe",e.target.value+"%");
      function drawNow(){
        if(!hasLeaflet)return;
        current=L.map(nowNode,{zoomControl:false}).setView(
          [Number(city.lat)||48,Number(city.lon)||2],14);
        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",{
          maxZoom:19,attribution:'© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>'
        }).addTo(current);
        L.control.zoom({position:"topright"}).addTo(current);
        camLayer=L.layerGroup().addTo(current);
        ownLayer=L.layerGroup().addTo(current);
        const rows=list.rows.filter(r=>r.cam);
        for(const r of rows){
          const isModern=r.kind==="today";
          const point=[r.cam.lat,r.cam.lon];
          const marker=L.circleMarker(point,{radius:isModern?5:7,color:isModern?"#345d69":"#9e472c",
            fillColor:isModern?"#345d69":"#9e472c",fillOpacity:.8,weight:2}).addTo(camLayer);
          marker.bindTooltip(r.title+" · "+r.year);
          marker.on("click",()=>{compare(r);$(".vpa-film").scrollIntoView({behavior:"smooth",block:"start"});});
        }
        for(const s of (city.sites||[]).slice(0,140)) {
          if(!finite(s.lat,-90,90)||!finite(s.lon,-180,180))continue;
          const mark=L.circleMarker([+s.lat,+s.lon],{radius:4,color:"#4c6654",weight:1,
            fillOpacity:.2}).addTo(camLayer);
          mark.bindPopup("<b>"+esc(s.site_ru||s.site_name||"Место")+"</b><p>Изображённый объект. "+
            "Точка художника по этому маркеру не установлена.</p>");
        }
        refreshOwn();
        current.on("click",e=>{
          if(!pickMode)return;
          pickMode=false;
          $("#vpaLat").value=e.latlng.lat.toFixed(6);
          $("#vpaLon").value=e.latlng.lng.toFixed(6);
          feedback.textContent="Точка съёмки выбрана. Проверьте направление камеры и сохраните.";
          current.getContainer().classList.remove("vpa-picking");
          $("#vpaContribution").open=true;
          $("#vpaContribution").scrollIntoView({behavior:"smooth",block:"nearest"});
        });
      }
      function refreshOwn(){
        if(!ownLayer)return;
        ownLayer.clearLayers();
        for(const p of own){
          const m=L.circleMarker([p.lat,p.lon],{radius:8,color:"#154f78",
            fillColor:"#e6bf69",fillOpacity:1,weight:2}).addTo(ownLayer);
          const linked=works.find(x=>x.id===p.workLink);
          m.bindPopup("<b>Мой снимок</b><p>"+esc(linked?linked.title:"Своя фотография")+
            "</p><small>Точка введена посетителем, совпадение с историческим ракурсом не проверено.</small>");
          m.on("click",()=>{if(linked)compare(linked);});
        }
      }
      function drawOld(){
        if(!oldSheet||!hasLeaflet)return;
        const node=$("#vpaOld");
        const bounds=[[-oldSheet.height,0],[0,oldSheet.width]];
        old=L.map(node,{crs:L.CRS.Simple,zoomControl:false,zoomSnap:.25,maxBoundsViscosity:.8});
        L.imageOverlay(oldSheet.image,bounds,{interactive:false,alt:oldSheet.title}).addTo(old);
        old.fitBounds(bounds,{animate:false});
        old.setMinZoom(old.getZoom()-.3);
        L.control.zoom({position:"topright"}).addTo(old);
        for(const r of list.rows.filter(x=>x.plan && x.plan.image===oldSheet.image &&
          x.cam && finite(x.cam.px,0,oldSheet.width)&&finite(x.cam.py,0,oldSheet.height))){
          const m=L.circleMarker([-r.cam.py,r.cam.px],{radius:7,color:r.kind==="today"?"#345d69":"#9e472c",
            fillColor:"#fff2d5",fillOpacity:.9,weight:2}).addTo(old);
          m.bindTooltip(r.year+" · "+r.title);
          m.on("click",()=>{compare(r);$(".vpa-film").scrollIntoView({behavior:"smooth",block:"start"});});
        }
        requestAnimationFrame(()=>old.invalidateSize());
      }
      $("#vpaPick").onclick=()=>{
        if(!current){feedback.textContent="Карта недоступна; координаты можно ввести вручную.";return;}
        pickMode=true;
        current.getContainer().classList.add("vpa-picking");
        feedback.textContent="Нажмите на современной карте, где вы стояли, когда снимали фото.";
        nowNode.scrollIntoView({behavior:"smooth",block:"center"});
      };
      $("#vpaForm").onsubmit=async e=>{
        e.preventDefault();
        const f=$("#vpaFile").files[0],id=$("#vpaLink").value.trim();
        const r=works.find(x=>x.id===id);
        const lat=+$("#vpaLat").value,lon=+$("#vpaLon").value,az=+$("#vpaAz").value;
        if(!f||!["image/jpeg","image/png","image/webp"].includes(f.type)||f.size>15*1024*1024){
          feedback.textContent="Нужен JPG, PNG или WebP до 15 МБ.";return;
        }
        if(!r){feedback.textContent="Выберите произведение из списка. Для него будет создан современный аналог.";return;}
        if(!finite(lat,-90,90)||!finite(lon,-180,180)||!finite(az,0,359)){
          feedback.textContent="Проверьте широту, долготу и направление (0–359°).";return;
        }
        const save=$("#vpaSave");save.disabled=true;
        try {
          const p={id:"vpa-"+Date.now()+"-"+Math.random().toString(36).slice(2,8),
            city:city.id,cityName:city.name,place:city.id+"|visitor",
            name:f.name.slice(0,90),blob:f,workType:"modern",workLink:r.id,
            date:new Date(f.lastModified||Date.now()).toISOString().slice(0,10),
            author:"Посетитель",lat,lon,az,fov:60,created:Date.now(),
            rights:"Личный материал, не опубликован",point_basis:"visitor_confirmed_manually"};
          await localDb.put(p);own.push(p);
          $("#vpaOwnCount").textContent=String(own.length);
          $("#vpaFile").value="";
          refreshOwn();drawGallery();compare(r);
          feedback.textContent="Снимок сохранён только в этом браузере. Его точка появилась на карте.";
          window.dispatchEvent(new CustomEvent("city-on-paper-photo-saved",{detail:{city:city.id}}));
        }catch(err){feedback.textContent="Не удалось сохранить фото на устройстве. Проверьте доступное место и разрешения браузера.";}
        finally{save.disabled=false;}
      };
      drawGallery();drawNow();drawOld();
      if(works.length)compare(works[0]);
      if(!hasLeaflet)nowNode.innerHTML="<p class='vpa-note'>Карта недоступна. Координаты можно ввести вручную.</p>";
      if(!works.length)$("#vpaLink").disabled=true;
    }).catch(()=>{
      if(host.isConnected)host.innerHTML='<p class="note">Не удалось загрузить карту ракурсов. Каталог города и исторические карты выше остаются доступны.</p>';
    });
  }
  return {mount,curated,status};
})();