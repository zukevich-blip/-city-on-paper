/* City on Paper — small, dependency-free, truthful first-visit interaction.
 * Different camera angles: switching frames never claims pixel-perfect registration.
 */
"use strict";
(() => {
  const root=document.querySelector("#home .museum-wow");
  if(!root)return;
  const duet=root.querySelector(".wow-duet"), figures=Array.from(duet?.querySelectorAll("figure")||[]);
  const buttons=Array.from(root.querySelectorAll("[data-wow-view]"));
  const state=root.querySelector("#wowViewStatus");
  if(figures.length!==2||!duet||!state||buttons.length!==3)return;
  const labels={
    pair:"Два вида рядом. Это одно здание, но изображения сняты с разных точек.",
    past:"Литография Филиппа Бенуа, 1845–1860 годы. Посмотрите на боковую колоннаду.",
    now:"Фотография jerome92370, 2026 год. Сравните фасад и положение камеры."
  };
  const setMode=mode=>{
    if(!Object.prototype.hasOwnProperty.call(labels,mode))return;
    figures[0].hidden=mode==="now";
    figures[1].hidden=mode==="past";
    duet.classList.toggle("wow-single",mode!=="pair");
    buttons.forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.wowView===mode)));
    state.textContent=labels[mode];
  };
  buttons.forEach(b=>b.addEventListener("click",()=>setMode(b.dataset.wowView)));
  setMode("pair");

  const quiz=root.querySelector("#wowPrintQuiz"),result=root.querySelector("#wowPrintAnswer");
  if(!quiz||!result)return;
  const choices=Array.from(quiz.querySelectorAll("[data-wow-answer]"));
  choices.forEach(button=>button.addEventListener("click",()=>{
    const correct=button.dataset.wowAnswer==="printer";
    choices.forEach(b=>b.setAttribute("aria-pressed",String(b===button)));
    result.hidden=false;
    result.textContent=correct
      ?"Верно. «Ph. Benoist del.» указывает автора рисунка; «Imp. Lemercier» — мастерскую, напечатавшую литографию."
      :"Lemercier — типография, а не автор рисунка. На листе стоит «Ph. Benoist del.»: рисунок сделал Филипп Бенуа.";
    quiz.classList.toggle("answered",true);
  }));
})();