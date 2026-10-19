"use strict";
/* Atlas of historical first-round municipal results; no tracking or profiling. */
const $=id=>document.getElementById(id),NS="http://www.w3.org/2000/svg";
const nf=new Intl.NumberFormat("pt-BR");
const pct=v=>Number.isFinite(v)?v.toLocaleString("pt-BR",{minimumFractionDigits:2,maximumFractionDigits:2})+"%":"—";
const pp=v=>Number.isFinite(v)?(v>=0?"+":"")+v.toLocaleString("pt-BR",{minimumFractionDigits:2,maximumFractionDigits:2})+" pp":"—";
const normal=s=>String(s||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase().trim();
const UF={AC:"Acre",AL:"Alagoas",AP:"Amapá",AM:"Amazonas",BA:"Bahia",CE:"Ceará",DF:"Distrito Federal",ES:"Espírito Santo",GO:"Goiás",MA:"Maranhão",MT:"Mato Grosso",MS:"Mato Grosso do Sul",MG:"Minas Gerais",PA:"Pará",PB:"Paraíba",PR:"Paraná",PE:"Pernambuco",PI:"Piauí",RJ:"Rio de Janeiro",RN:"Rio Grande do Norte",RS:"Rio Grande do Sul",RO:"Rondônia",RR:"Roraima",SC:"Santa Catarina",SP:"São Paulo",SE:"Sergipe",TO:"Tocantins"};
const blues=["#eff6ff","#dbeafe","#bfdbfe","#93c5fd","#60a5fa","#2563eb","#1e40af"];
const divergent=["#7c3aed","#a78bfa","#ddd6fe","#f1f5f9","#99f6e4","#14b8a6","#0f766e"];
const A={rows:null,meta:null,geo:null,uf:"SP",year:"2022",metric:"turnout",candidate:"",selected:null,token:0};
window.atlasState=A;
const show=(s,error=false)=>{$("status").textContent=s;$("status").classList.toggle("error",error);};
async function json(url){let r=await fetch(url,{cache:"no-cache"});if(!r.ok)throw Error(r.status+" "+url);return r.json();}
function title(){if(A.metric==="delta_candidate")return "Variação histórica da participação: "+(A.meta.candidate_options["2026"][A.candidate]||"Candidatura");return A.metric==="candidate"?(A.meta.candidate_options[A.year][A.candidate]||"Candidatura")+" (nº "+A.candidate+")":({turnout:"Comparecimento",blank:"Votos brancos",null:"Votos nulos",delta_turnout:"Variação de comparecimento"}[A.metric]);}
function val(row){
 if(!row)return null;
 const y=row[A.year];
 if(A.metric==="candidate")return y.valid?100*(y.votes[A.candidate]||0)/y.valid:null;
 if(A.metric==="delta_candidate"){let pairs=A.meta.matched_candidate_labels||{};let match=Object.values(pairs).find(x=>x.code_2026===A.candidate);if(!match)return null;let a=row["2022"],b=row["2026"];return a.valid&&b.valid?100*((b.votes[match.code_2026]||0)/b.valid-(a.votes[match.code_2022]||0)/a.valid):null;}
 if(A.metric==="turnout")return 100*y.turnout;
 if(A.metric==="blank")return y.attended?100*y.blank/y.attended:null;
 if(A.metric==="null")return y.attended?100*y.null/y.attended:null;
 return 100*(row["2026"].turnout-row["2022"].turnout);
}
const display=v=>A.metric==="delta_turnout"||A.metric==="delta_candidate"?pp(v):pct(v);
function bins(){return (A.metric==="delta_turnout"||A.metric==="delta_candidate")?[-10,-5,-2,0,2,5,10]:A.metric==="candidate"?[0,10,20,35,50,65,80]:A.metric==="turnout"?[0,50,60,70,80,90,100]:[0,1,2,4,6,10,20];}
function color(v){if(!Number.isFinite(v))return"#e2e8f0";let t=bins(),colors=(A.metric==="delta_turnout"||A.metric==="delta_candidate")?divergent:blues;for(let i=0;i<t.length-1;i++)if(v<t[i+1])return colors[i];return colors[6];}
function chooseCandidate(){
 const options=A.meta.candidate_options[A.year],entries=Object.entries(options).sort((a,b)=>+a[0]-+b[0]);
 $("candidate").replaceChildren();
 for(const [code,name] of entries){let e=document.createElement("option");e.value=code;e.textContent=name+" (nº "+code+")";$("candidate").appendChild(e);}
 if(!Object.prototype.hasOwnProperty.call(options,A.candidate))A.candidate=entries[0]?.[0]||"";
 $("candidate").value=A.candidate;if(A.metric==="delta_candidate"){
   const matches=Object.values(A.meta.matched_candidate_labels||{});let allowed=new Set(matches.map(m=>m.code_2026));
   for(const opt of [...$("candidate").options])if(!allowed.has(opt.value))opt.remove();
   if(!allowed.has(A.candidate))A.candidate=$("candidate").options[0]?.value||"";
   $("candidate").value=A.candidate;
 }
 $("candidate-wrap").hidden=!(A.metric==="candidate"||A.metric==="delta_candidate");
}
function regionRows(){return Object.entries(A.rows).filter(([,r])=>r.uf===A.uf).map(([id,r])=>({id,r}));}
function stats(){
 const rows=regionRows(),year=A.year,sum=(field,y=year)=>rows.reduce((s,x)=>s+x.r[y][field],0);
 const eligible=sum("eligible"),attended=sum("attended"),valid=sum("valid");
 $("n-mun").textContent=nf.format(rows.length);$("n-valid").textContent=nf.format(valid);
 $("n-turnout").textContent=eligible?pct(100*attended/eligible):"—";$("focus-title").textContent=title();
 let f=null;
 if(A.metric==="delta_candidate"){
  let match=Object.values(A.meta.matched_candidate_labels||{}).find(m=>m.code_2026===A.candidate);
  let a=sum("valid","2022"),b=sum("valid","2026");
  let va=match?rows.reduce((s,x)=>s+(x.r["2022"].votes[match.code_2022]||0),0):0;
  let vb=match?rows.reduce((s,x)=>s+(x.r["2026"].votes[match.code_2026]||0),0):0;
  f=match&&a&&b?100*(vb/b-va/a):null;
 }
 else if(A.metric==="candidate")f=valid?100*rows.reduce((s,x)=>s+(x.r[year].votes[A.candidate]||0),0)/valid:null;
 else if(A.metric==="turnout")f=eligible?100*attended/eligible:null;
 else if(A.metric==="blank"||A.metric==="null")f=attended?100*sum(A.metric)/attended:null;
 else {let e22=sum("eligible","2022"),e26=sum("eligible","2026");f=e22&&e26?100*(sum("attended","2026")/e26-sum("attended","2022")/e22):null;}
 $("n-focus").textContent=display(f);
 $("focus-desc").textContent="Taxa agregada da UF; não é média de municípios";
}
function legend(){
 const node=$("legend");node.replaceChildren();
 let heading=document.createElement("strong");heading.textContent="Legenda · "+title();node.appendChild(heading);
 let band=document.createElement("div");band.className="legend-colors";
 for(let c of A.metric==="delta_turnout"?divergent:blues){let s=document.createElement("span");s.style.backgroundColor=c;band.appendChild(s);}
 node.appendChild(band);let labels=document.createElement("div");labels.className="legend-values";
 let t=bins(),unit=(A.metric==="delta_turnout"||A.metric==="delta_candidate")?" pp":"%";
 for(let v of ["≤ "+t[0]+unit,"≥ "+t[t.length-1]+unit]){let s=document.createElement("span");s.textContent=v;labels.appendChild(s);}
 node.appendChild(labels);let note=document.createElement("small");note.textContent="Faixas fixas por indicador · Cinza: indisponível";node.appendChild(note);
}
function polygons(geom){return geom.type==="Polygon"?[geom.coordinates]:geom.coordinates;}
function project(features){
 let minX=Infinity,maxX=-Infinity,minY=Infinity,maxY=-Infinity;
 for(let f of features)for(let poly of polygons(f.geometry))for(let ring of poly)for(let [x,y] of ring){minX=Math.min(minX,x);maxX=Math.max(maxX,x);minY=Math.min(minY,y);maxY=Math.max(maxY,y);}
 const dx=Math.max(.01,maxX-minX),dy=Math.max(.01,maxY-minY),s=Math.min(870/dx,565/dy),ox=30+(870-dx*s)/2,oy=25+(565-dy*s)/2;
 return ([x,y])=>[(ox+(x-minX)*s).toFixed(1),(oy+(maxY-y)*s).toFixed(1)].join(",");
}
function svgPath(g,p){return polygons(g).flatMap(poly=>poly.filter(r=>r.length>2).map(r=>"M"+r.map(p).join("L")+"Z")).join("");}
function select(id){A.selected=id;$("map").querySelectorAll("path").forEach(p=>p.classList.toggle("selected",p.dataset.ibge===id));detail();}
function detail(){
 let parent=$("detail");parent.replaceChildren();
 if(!A.selected){let p=document.createElement("p");p.className="empty-message";p.textContent="Selecione um município no mapa para consultar os resultados registrados.";parent.appendChild(p);return;}
 const row=A.rows[A.selected],year=row[A.year],feature=A.geo.features.find(f=>f.properties.ibge===A.selected);
 let h=document.createElement("h3");h.textContent=feature?.properties.name||A.selected;parent.appendChild(h);
 let subtitle=document.createElement("p");subtitle.className="detail-secondary";subtitle.textContent=UF[row.uf]+" · IBGE "+A.selected+" · "+A.year;parent.appendChild(subtitle);
 let dl=document.createElement("dl");dl.className="detail-metrics";
 for(let [name,v] of [["Comparecimento",pct(year.turnout*100)],["Aptos (seções regulares)",nf.format(year.eligible)],["Compareceram",nf.format(year.attended)],["Válidos",nf.format(year.valid)],["Brancos",nf.format(year.blank)],["Nulos",nf.format(year.null)]]){
   let d=document.createElement("div"),dt=document.createElement("dt"),dd=document.createElement("dd");dt.textContent=name;dd.textContent=v;d.append(dt,dd);dl.appendChild(d);
 }
 parent.appendChild(dl);
 if(row.turnout_denominator_caveat){let p=document.createElement("p");p.className="caveat";p.textContent="Ressalva: denominador de 2022 pode excluir 84 eleitores aptos de seção excepcional.";parent.appendChild(p);}
 let title=document.createElement("h4");title.textContent="Candidaturas registradas · "+A.year;parent.appendChild(title);
 let table=document.createElement("table");table.className="candidate-table",head=document.createElement("thead"),tr=document.createElement("tr");
 for(let t of ["Candidatura","Votos","% válidos"]){let th=document.createElement("th");th.textContent=t;tr.appendChild(th);}head.appendChild(tr);table.appendChild(head);
 let body=document.createElement("tbody");
 for(let [number,name] of Object.entries(A.meta.candidate_options[A.year]).sort((a,b)=>+a[0]-+b[0])){
   let votes=year.votes[number]||0,values=[name+" ("+number+")",nf.format(votes),year.valid?pct(100*votes/year.valid):"—"];
   let tr=document.createElement("tr");for(let text of values){let td=document.createElement("td");td.textContent=text;tr.appendChild(td);}body.appendChild(tr);
 }
 table.appendChild(body);parent.appendChild(table);
 let note=document.createElement("p");note.className="micro";note.textContent="Votos registrados no município, não atribuídos à residência dos eleitores.";parent.appendChild(note);
}
function draw(){
 let svg=$("map");svg.replaceChildren();
 if(!A.geo)return;
 let features=A.geo.features,p=project(features),fragment=document.createDocumentFragment();
 for(let f of features){
   let id=f.properties.ibge, v=val(A.rows[id]),shape=document.createElementNS(NS,"path");
   shape.setAttribute("d",svgPath(f.geometry,p));shape.setAttribute("fill",color(v));shape.setAttribute("fill-rule","evenodd");
   shape.setAttribute("tabindex","0");shape.setAttribute("role","button");shape.setAttribute("aria-label",f.properties.name+": "+display(v));
   shape.classList.add("municipality");if(id===A.selected)shape.classList.add("selected");shape.dataset.ibge=id;
   let tip=document.createElementNS(NS,"title");tip.textContent=f.properties.name+": "+display(v);shape.appendChild(tip);
   shape.addEventListener("click",()=>select(id));shape.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();select(id);}});
   fragment.appendChild(shape);
 }
 svg.appendChild(fragment);$("map-loading").hidden=true;
 $("map-subtitle").textContent=UF[A.uf]+" · "+nf.format(features.length)+" municípios · "+title();
}
function render(){if(!A.meta)return;stats();legend();draw();detail();document.dispatchEvent(new CustomEvent("atlas:render"));}
async function state(uf){
 A.uf=uf;A.geo=null;A.selected=null;const token=++A.token;
 $("map-loading").hidden=false;$("map-loading").textContent="Carregando malha de "+UF[uf]+"…";$("map").replaceChildren();
 try{let data=await json("./data/states/"+uf+".geojson");
   if(token!==A.token)return;
   if(data.type!=="FeatureCollection"||data.features.length!==A.meta.municipalities_by_uf[uf])throw Error("Geometria não coincide com a fonte oficial.");
   A.geo=data;render();show(nf.format(A.meta.municipalities)+" municípios disponíveis · Fonte TSE–IBGE.");
 }catch(e){if(token===A.token){show("Falha no mapa de "+uf+": "+e.message,true);$("map-loading").textContent="Não foi possível carregar a malha.";}}
}
function locate(){
 let q=normal($("city").value);if(q.length<2||!A.geo)return;
 let matches=A.geo.features.filter(f=>normal(f.properties.name).includes(q)),match=matches.find(f=>normal(f.properties.name)===q);
 if(match||matches.length===1){let f=match||matches[0];select(f.properties.ibge);show("Município localizado: "+f.properties.name+".");}
 else show(nf.format(matches.length)+" municípios correspondentes. Digite mais letras para localizar sem classificar municípios.");
}
async function init(){
 try{
   let [meta,rows,manifest]=await Promise.all([json("./data/metadata.json"),json("./data/municipalities.json"),json("./data/manifest.json")]);
   if(meta.municipalities!==5570||Object.keys(rows).length!==5570||manifest.municipalities!==5570)throw Error("Amostra municipal incompatível.");
   A.rows=rows;A.meta=meta;
   let select=$("uf");select.replaceChildren();
   for(let uf of Object.keys(meta.municipalities_by_uf).sort((a,b)=>UF[a].localeCompare(UF[b],"pt-BR"))){
      let option=document.createElement("option");option.value=uf;option.textContent=UF[uf]+" ("+uf+")";select.appendChild(option);
   }
   select.value=A.uf;
   $("provenance").textContent=JSON.stringify({panel_sha256:meta.electoral_panel_sha256,geometry_sha256:manifest.geometry_zip_sha256,display_simplification_degrees:manifest.map_presentation_simplification_degrees,municipalities:meta.municipalities,notes:meta.notes},null,2);
   chooseCandidate();
   select.addEventListener("change",()=>{void state(select.value);});
   $("year").addEventListener("change",()=>{A.year=$("year").value;chooseCandidate();render();});
   $("metric").addEventListener("change",()=>{A.metric=$("metric").value;chooseCandidate();render();});
   $("candidate").addEventListener("change",()=>{A.candidate=$("candidate").value;render();});
   $("city").addEventListener("change",locate);
   $("city").addEventListener("keydown",e=>{if(e.key==="Enter")locate();});
   $("reset").addEventListener("click",()=>{A.selected=null;$("city").value="";render();});
   await state(A.uf);
 }catch(e){show("Falha ao iniciar o atlas: "+e.message,true);$("map-loading").textContent="Dados ainda indisponíveis.";}
}
void init();
