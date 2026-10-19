"use strict";
(function () {
  const NS="http://www.w3.org/2000/svg";
  const get=id=>document.getElementById(id);
  const num=(x,d=3)=>Number(x).toLocaleString("pt-BR",{minimumFractionDigits:d,maximumFractionDigits:d});
  let census=null,science=null;
  function elt(name,attrs={},text=""){
    const n=document.createElementNS(NS,name);
    for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));
    if(text)n.textContent=text;
    return n;
  }
  function putText(svg,x,y,text,size=12,anchor="start",color="#334155"){
    svg.appendChild(elt("text",{x,y,"font-size":size,"font-family":"Arial","text-anchor":anchor,fill:color},text));
  }
  function clear(id){const root=get(id);root.replaceChildren();return root;}
  function scatter(){
    const state=window.atlasState;if(!state?.rows||!census)return;
    const svg=clear("census-scatter");
    const axis=get("scatter-x").value,records=[];
    for(const [id,row] of Object.entries(state.rows)){
      if(row.uf!==state.uf||row.turnout_denominator_caveat&&state.year==="2022")continue;
      const censusRow=census[id];
      const raw=censusRow?.[axis],turnout=row[state.year]?.turnout;
      if(Number.isFinite(raw)&&raw>=0&&Number.isFinite(turnout))records.push([Math.log10(1+raw),turnout*100]);
    }
    if(records.length<3){get("scatter-summary").textContent="Amostra municipal insuficiente.";return;}
    const mean=(arr,i)=>arr.reduce((s,a)=>s+a[i],0)/arr.length;
    const mx=mean(records,0),my=mean(records,1);
    const cross=records.reduce((s,p)=>s+(p[0]-mx)*(p[1]-my),0);
    const sx=records.reduce((s,p)=>s+(p[0]-mx)**2,0);
    const sy=records.reduce((s,p)=>s+(p[1]-my)**2,0);
    const corr=sx>0&&sy>0?cross/Math.sqrt(sx*sy):null;
    const xmin=Math.min(...records.map(p=>p[0])),xmax=Math.max(...records.map(p=>p[0]));
    const ymin=Math.min(...records.map(p=>p[1])),ymax=Math.max(...records.map(p=>p[1]));
    const scaleX=x=>70+(x-xmin)/Math.max(xmax-xmin,1e-9)*535;
    const scaleY=y=>300-(y-ymin)/Math.max(ymax-ymin,1e-9)*250;
    svg.appendChild(elt("line",{x1:70,y1:300,x2:610,y2:300,stroke:"#94a3b8"}));
    svg.appendChild(elt("line",{x1:70,y1:45,x2:70,y2:300,stroke:"#94a3b8"}));
    for(const [x,y] of records)svg.appendChild(elt("circle",{cx:scaleX(x),cy:scaleY(y),r:3,fill:"#0e7490",opacity:0.55}));
    putText(svg,339,343,"log₁₀(1 + indicador do Censo)",12,"middle");
    putText(svg,15,29,"Comparecimento (%)",12);
    putText(svg,70,321,num(xmin,1),11);putText(svg,605,321,num(xmax,1),11,"end");
    putText(svg,62,305,num(ymin,1),11,"end");putText(svg,62,53,num(ymax,1),11,"end");
    get("scatter-summary").textContent=records.length+" municípios; Pearson r = "+(corr===null?"indefinido":num(corr,3))+". Associação descritiva, sem inferência causal.";
    get("scatter-year").textContent=state.year;
  }
  function bars(){
    if(!science)return;
    const svg=clear("model-chart");
    const labels={persistence:"Persistência",ridge:"Ridge E006",ridge_regional:"Ridge regional E007",spatial_queen:"Espacial queen E010",spatial_rook:"Espacial rook E010"};
    const models=science.models;
    const max=Math.max(...models.map(m=>m.mae_pp))*1.16;
    models.forEach((model,i)=>{
      const y=38+i*58,barWidth=model.mae_pp/max*345;
      putText(svg,12,y+17,labels[model.method],13);
      svg.appendChild(elt("rect",{x:230,y,width:barWidth,height:25,rx:4,fill:model.method==="ridge_regional"?"#0d9488":"#64748b"}));
      putText(svg,Math.min(590,238+barWidth),y+17,num(model.mae_pp,4)+" pp",12);
    });
    putText(svg,12,339,"MAE (pontos percentuais) — 5.569 municípios avaliados",12);
    const best=models.reduce((a,b)=>a.mae_pp<b.mae_pp?a:b);
    get("model-summary").textContent="Menor MAE observado: "+labels[best.method]+" — "+num(best.mae_pp,4)+" pp. Os intervalos exploratórios estão documentados no relatório científico.";
  }
  function moran(){
    if(!science)return;
    const svg=clear("moran-chart");
    const labels={baseline:"Persistência",ridge:"Ridge",ridge_regional:"Ridge + região"};
    const modalities=[["global","Moran global E008"],["within_uf","Moran condicionado E009"]];
    const series=["baseline","ridge","ridge_regional"];
    modalities.forEach(([scope,title],j)=>{
      const startX=j?335:10;
      putText(svg,startX+6,28,title,14);
      series.forEach((method,i)=>{
        const y=62+i*75,v=science.moran[scope][method].queen.I;
        putText(svg,startX+5,y+9,labels[method],12);
        svg.appendChild(elt("rect",{x:startX+5,y:y+16,width:v/0.6*260,height:17,rx:3,fill:j?"#0d9488":"#64748b"}));
        putText(svg,startX+9,y+48,num(v,4),12);
      });
    });
    putText(svg,12,339,"Grafo queen, dados históricos; escalas comparáveis só dentro de cada teste",11);
    get("moran-summary").textContent="A autocorrelação residual positiva permanece dentro das UFs; a correção regional não elimina os contrastes espaciais municipais.";
  }
  async function init(){
    try{
      const responses=await Promise.all(["./data/census.json","./data/research.json"].map(x=>fetch(x,{cache:"no-cache"})));
      if(responses.some(x=>!x.ok))throw Error("Arquivos E012 ainda indisponíveis");
      [census,science]=await Promise.all(responses.map(x=>x.json()));
      get("scatter-x").addEventListener("change",scatter);
      document.addEventListener("atlas:render",scatter);
      scatter();bars();moran();
    }catch(error){
      for(const id of ["scatter-summary","model-summary","moran-summary"])get(id).textContent="Não foi possível carregar a pesquisa E012: "+error.message;
    }
  }
  void init();
})();
