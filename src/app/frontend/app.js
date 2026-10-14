"use strict";
// El SVG conserva la geometría original; los controles HTML aportan interacción.
let design, backend = {datos: [], resultado: null, aviso: null};
let page = 'inicio', format = 'instagram', category = 'Todas las plantillas', search = '', sort = 'recomendadas';
let busy = false, query = '', faqSearch = '', rawJson = '', jsonOpen = false, dataSearch = '', dataChannel = 'Todos';
let objective='Informar y generar interés', tone='Claro y cercano';
const selectionByResult=new Map();
const downloadsHandled=new Set();
let ready=false, sentHeight=-1;
let downloadFile=null;
const stage = document.getElementById('stage'), feedback = document.getElementById('feedback'), extras = document.getElementById('extras');
const nav = {'Inicio':'inicio','Plantillas':'plantillas','Agente en vivo':'agente','Analíticas':'analiticas','Ayuda':'ayuda'};
const cards = [
  {id:'cml-00117',format:'instagram',name:'Post para Instagram',category:'Contenido para redes'},
  {id:'cml-00126',format:'linkedin',name:'Publicación para LinkedIn',category:'Contenido para redes'},
  {id:'cml-00135',format:'x',name:'Publicación para X',category:'Contenido para redes'},
  {id:'cml-00144',format:'sentimiento',name:'Sentimiento de comunidad',category:'Analíticas'},
  {id:'cml-00153',format:'temas',name:'Temas y tendencias',category:'Analíticas'},
  {id:'cml-00162',format:'preguntas',name:'Preguntas de la comunidad',category:'Preguntas frecuentes'}
];
const postExample = '¿Qué nos está diciendo la comunidad?\n\nEscuchar las conversaciones permite encontrar ideas que conectan mejor con las personas.\n\nEsta semana encontramos preguntas recurrentes, interés por soluciones prácticas y oportunidades para explicar mejor nuestros servicios.\n\nComparte tu experiencia en los comentarios.\n\n#Comunidad #Insights #Marketing';
const faqs = [
  ['¿Qué hace CommunityLab?','Convierte conversaciones en análisis y activos de marketing reutilizables.'],
  ['¿Qué diferencia hay entre una plantilla y el agente en vivo?','La plantilla ejecuta una tarea definida; el agente recibe instrucciones abiertas. En esta demo, la IA está pendiente de conexión.'],
  ['¿Puedo publicar directamente en Instagram, LinkedIn o X?','No en el MVP. Puedes revisar y copiar el contenido y abrir la red social.'],
  ['¿Cuáles son las fuentes admitidas en la demostración?','Se inicia con archivos JSON procesados por el pipeline existente. La revisión actual se realiza localmente.']
];
let view;
const message = (type, fields) => window.parent.postMessage({isStreamlitMessage:true,type,...fields}, '*');
function height(){if(!ready)return;const h=Math.max(1,Math.ceil(document.body.getBoundingClientRect().height));if(h!==sentHeight){sentHeight=h;message('streamlit:setFrameHeight',{height:h});}}
function notify(text,type='info'){feedback.textContent=text;feedback.dataset.type=type;height();}
function syncPending(){
  document.querySelectorAll('[data-server-action]').forEach(node=>node.disabled=busy||node.dataset.unavailable==='true');
  extras.setAttribute('aria-busy',String(busy));
}
const requests=CommunityLabInteraction.requestGate({
  post:value=>message('streamlit:setComponentValue',{value,dataType:'json'}),
  changed:pending=>{busy=pending;syncPending();},
  timedOut:()=>notify('No se recibió respuesta del servidor. Puedes volver a pulsar el botón; si continúa, recarga la página.','error')
});
function send(accion, fields={}){
  if(!requests.send(accion,fields))return notify('Espera a que termine la acción en curso.');
  notify('Preparando la revisión local…');
}
function go(next){page=next;search='';category='Todas las plantillas';render();}
function rect(id){return typeof id==='string'?view.elementos[id]:id;}
function at(node,b){
  node.style.left=`${100*b.x/view.width}%`;node.style.top=`${100*b.y/view.height}%`;
  node.style.width=`${100*b.w/view.width}%`;node.style.height=`${100*b.h/view.height}%`;
  stage.append(node);return node;
}
function find(text,minY=-Infinity){return Object.entries(view.elementos).find(([,e])=>e.texto===text&&e.y>=minY)?.[0];}
function group(id){return stage.querySelector(`[data-id="${id}"]`);}
function hide(id){if(group(id))group(id).style.display='none';}
function replace(text,newText){const id=find(text);if(!id)return;let nodes=group(id).querySelectorAll('text');nodes.forEach((n,i)=>n.textContent=i===0?newText:'');}
function hot(id,label,handler,disabled=false){
  const source=rect(id);if(!source)return;
  const b=CommunityLabInteraction.hitBox(source,view.elementos,view.width,view.height,window.innerWidth/view.width);
  const node=document.createElement('button');node.type='button';node.className='hot';node.setAttribute('aria-label',label);node.title=label;
  node.innerHTML='<span class="sr-only"></span>';node.firstChild.textContent=label;node.disabled=disabled;node.addEventListener('click',handler);return at(node,b);
}
function field(id,label,value,onChange,options){
  const b=rect(id);if(!b)return;
  hide(id);const node=document.createElement(options?'select':'input');node.className='field';node.setAttribute('aria-label',label);
  if(options)options.forEach(([val,name])=>{let opt=new Option(name,val);node.add(opt);});
  else {node.type='text';node.placeholder=b.texto||label;}
  node.value=value;node.addEventListener(options?'change':'input',()=>onChange(node.value));
  node.style.fontSize=`${(b.font||14)/view.width*100}vw`;
  const box=Object.values(view.elementos).filter(e=>e.tipo==='rectangle'&&e.w<=1000&&e.h<=80&&e.x<=b.x&&e.y<=b.y&&e.x+e.w>=b.x+b.w&&e.y+e.h>=b.y+b.h).sort((a,b)=>a.w*a.h-b.w*b.h)[0];
  const width=box?box.w-2*(b.x-box.x):b.w+(options?40:0);
  return at(node,{...b,w:width,h:Math.max(b.h,32),y:b.y-5});
}
function action(label,handler,parent=extras,secondary=false){
  const node=document.createElement('button');node.type='button';node.className='action'+(secondary?' secondary':'');node.textContent=label;node.onclick=handler;parent.append(node);return node;
}
function serverAction(label,accion,fields={},parent=extras,secondary=false,unavailable=false){
  const node=action(label,()=>send(accion,typeof fields==='function'?fields():fields),parent,secondary);
  node.dataset.serverAction=accion;node.dataset.unavailable=String(unavailable);node.disabled=busy||unavailable;return node;
}
function menu(){
  const items=document.getElementById('menu-items');items.replaceChildren();
  [...Object.entries(nav),['Importar JSON','datos'],['Mapa de experiencia','mapa'],['Estados de interfaz','estados']].forEach(([name,key])=>{
    const btn=document.createElement('button');btn.textContent=name;btn.onclick=()=>{document.getElementById('menu').close();go(key);};items.append(btn);
  });
  serverAction('Usar ejemplo del proyecto','ejemplo',{},items,true).addEventListener('click',()=>document.getElementById('menu').close());
  if(!document.getElementById('menu').open)document.getElementById('menu').showModal();
}
document.getElementById('close-menu').onclick=()=>document.getElementById('menu').close();
async function copy(text){try{await navigator.clipboard.writeText(text);notify('Contenido copiado. Borrador ilustrativo; revisa antes de publicar.');}catch{notify('El navegador no permitió copiar. Usa la descarga local.', 'error');}}
function svgView(key){
  view=design[key];stage.style.aspectRatio=`${view.width}/${view.height}`;stage.innerHTML=view.svg;
  stage.setAttribute('aria-label',`CommunityLab · ${page} · demostración local`);
  // Los textos SVG están disponibles para lectores de pantalla; los controles tienen etiquetas propias.
  stage.querySelector('svg').removeAttribute('aria-hidden');stage.querySelector('svg').setAttribute('role','img');
  stage.querySelector('svg').setAttribute('aria-label',Object.values(view.elementos).map(e=>e.texto).filter(Boolean).join('. '));
}
function common(){
  Object.entries(nav).forEach(([label,key])=>hot(find(label),label,()=>go(key)));
  hot(find('communitylab'),'CommunityLab · Inicio',()=>go('inicio'));
  hot(find('DEMO · SIN CUENTAS'),'Opciones de la demo',menu);
}
function render(){
  if(!design)return;
  extras.replaceChildren();feedback.textContent='';feedback.removeAttribute('data-type');
  const mobile=window.innerWidth<=600;
  stage.style.backgroundColor=mobile?'#FFFFFF':'#F7F9FC';
  stage.ondrop=null;stage.ondragover=null;
  if(mobile && ['inicio','resultado'].includes(page)){
    svgView(page==='inicio'?'movil_inicio':'movil_resultado');
    hot(find('≡'),'Abrir menú',menu);
    if(page==='inicio'){
      ['Plantillas','Agente en vivo','Analíticas','FAQ'].forEach(label=>hot(find(label),label,()=>go(label==='FAQ'?'ayuda':nav[label])));
    }else{
      hot('cml-00652','Copiar publicación',()=>copy(outputText()));
      social(find('Abrir red social ↗'));
      resultExtras();
    }
  }else if(mobile){mobilePage();}
  else{
    stage.style.height='';
    svgView(page);common();
    if(page==='inicio'){
      hot('cml-00033','Explorar plantillas',()=>go('plantillas'));
      hot('cml-00035','Hablar con agente',()=>go('agente'));
      hot('cml-00051','Explorar Plantillas',()=>go('plantillas'));
      hot('cml-00058','Explorar Agente en vivo',()=>go('agente'));
      hot('cml-00065','Explorar FAQ y ayuda',()=>go('ayuda'));
      hot('cml-00037','Importar conversaciones en JSON',()=>go('datos'));
    }else if(page==='plantillas')catalog();
    else if(page==='resultado')result();
    else if(page==='datos')dataPage();
    else if(page==='agente')agent();
    else if(page==='ayuda')help();
    else if(page==='analiticas')analytics();
  }
  if(busy)notify('Preparando la revisión local…');
  else if(backend.aviso){notify(backend.aviso.texto,backend.aviso.tipo);}
  else if(mobile || (page!=='inicio' && page!=='plantillas'))notify('Vista ilustrativa del boceto · simulación local. IA y OCI pendientes de integración.');
  syncPending();renderDownload();height();
}
function catalog(){
  field(find('Buscar plantillas...'),'Buscar plantillas',search,value=>{search=value;filterCards();});
  const categories=['Todas las plantillas','Contenido para redes','Analíticas','Preguntas frecuentes'];
  categories.forEach((name,index)=>{
    const id=find(name,380);hide(id);
    const btn=hot({x:59,y:389+index*52,w:243,h:43},name,()=>{category=name;catalogCategories();filterCards();});
    btn.classList.add('category');btn.style.color=name===category?'#6557E8':'#161C32';btn.style.fontSize='0.9722vw';btn.textContent=name;
  });
  // Original highlight is replaced by the active native category control.
  hide('cml-00100');catalogCategories();
  field(find('Ordenar: recomendadas  ▾'),'Ordenar plantillas',sort,value=>{sort=value;filterCards();},[['recomendadas','Ordenar: recomendadas'],['nombre','Ordenar: nombre A–Z']]);
  filterCards();
}
function catalogCategories(){stage.querySelectorAll('.category').forEach(n=>{n.classList.toggle('active',n.textContent===category);n.style.color=n.textContent===category?'#6557E8':'#161C32';});}
function filterCards(){
  stage.querySelectorAll('.card-hit').forEach(n=>n.remove());
  const visible=cards.filter(c=>(category==='Todas las plantillas'||c.category===category)&&c.name.toLocaleLowerCase('es').includes(search.toLocaleLowerCase('es')));
  if(sort==='nombre')visible.sort((a,b)=>a.name.localeCompare(b.name,'es'));
  cards.forEach(c=>{
    const box=rect(c.id), index=visible.indexOf(c),dx=index<0?0:345+(index%2)*531-box.x,dy=index<0?0:257+Math.floor(index/2)*171-box.y;
    Object.entries(view.elementos).forEach(([id,e])=>{
      if(e.x>=box.x && e.y>=box.y && e.x+e.w<=box.x+box.w+2 && e.y+e.h<=box.y+box.h+2){
        const node=group(id);if(!node)return;node.style.display=index<0?'none':'';
        const original=node.dataset.originalTransform??node.getAttribute('transform')??'';node.dataset.originalTransform=original;
        node.setAttribute('transform',`translate(${dx} ${dy}) ${original}`);
      }
    });
    if(index>=0){const btn=hot({...box,x:box.x+dx,y:box.y+dy},c.name,()=>{format=c.format;go(c.category==='Analíticas'?'analiticas':'resultado');});btn.classList.add('card-hit');}
  });
  replace('6 EJEMPLOS',`${visible.length} EJEMPLOS`);
  if(!visible.length)notify('No hay plantillas para estos filtros.');else if(!backend.aviso)feedback.textContent='';
  height();
}
function outputText(){return backend.resultado?.formato===format?(backend.resultado.borradores[0]?.contenido??postExample):postExample;}
function social(id){
  const networks={instagram:['https://www.instagram.com/','Instagram'],linkedin:['https://www.linkedin.com/','LinkedIn'],x:['https://x.com/','X']};
  const [url,name]=networks[format]??networks.instagram;
  const source=rect(id);if(!source)return;const b=CommunityLabInteraction.hitBox(source,view.elementos,view.width,view.height,window.innerWidth/view.width);const link=document.createElement('a');link.className='hot';link.href=url;link.target='_blank';link.rel='noopener noreferrer';link.setAttribute('aria-label',`Abrir ${name} (no publica automáticamente)`);link.title=`Abrir ${name}`;at(link,b);
}
function result(){
  const names={instagram:'Instagram',linkedin:'LinkedIn',x:'X',preguntas:'Preguntas de la comunidad'};
  if(format!=='instagram')replace('Plantillas  /  Instagram  /  Resultado',`Plantillas  /  ${names[format]}  /  Resultado`);
  hot(find('Plantillas  /  Instagram  /  Resultado')||find(`Plantillas  /  ${names[format]}  /  Resultado`),'Volver al catálogo',()=>go('plantillas'));
  field(find('interacciones_comunidad.json'),'Lote',backend.origen||'interacciones_comunidad.json',()=>{},[[backend.origen||'interacciones_comunidad.json',backend.origen||'interacciones_comunidad.json']]);
  field(find('Instagram · post'),'Formato de salida',format,value=>{format=value;render();},[['instagram','Instagram · post'],['linkedin','LinkedIn · post'],['x','X · post'],['preguntas','Preguntas de la comunidad']]);
  field(find('Informar y generar interés'),'Objetivo de comunicación',objective,value=>objective=value);
  field(find('Claro y cercano'),'Tono',tone,value=>tone=value,[['Claro y cercano','Claro y cercano'],['Profesional','Profesional'],['Informativo','Informativo']]);
  hot(find('Copiar contenido'),'Copiar contenido',()=>copy(outputText()));
  social(find('Abrir Instagram ↗\n(el logo de ig)'));
  if(backend.resultado && backend.resultado.formato===format){
    const contenido=backend.resultado.borradores[0];
    if(contenido){
      ['¿Qué nos está diciendo la comunidad?','Escuchar las conversaciones permite encontrar\nideas que conectan mejor con las personas.\n\nEsta semana encontramos preguntas recurrentes,\ninterés por soluciones prácticas y oportunidades\npara explicar mejor nuestros servicios.','Comparte tu experiencia en los comentarios.','#Comunidad  #Insights  #Marketing'].forEach(t=>hide(find(t)));
      const node=document.createElement('div');node.className='dynamic';node.style.fontSize='1.11vw';node.textContent=contenido.contenido;at(node,{x:374,y:314,w:512,h:310});
      replace('Incluye: titular · cuerpo · CTA · hashtags','BORRADOR SIMULADO · requiere revisión');
    }else notify('Datos insuficientes: no hay mensajes del tipo requerido para esta plantilla.');
  }
  resultExtras();
}
function resultExtras(){
  const row=document.createElement('div');row.className='actions';extras.append(row);
  serverAction('Usar ejemplo del proyecto','ejemplo',{},row,true);
  serverAction('Generar borrador simulado','simular',()=>({formato:format}),row,false,!backend.datos.length);
  action('Importar JSON',()=>go('datos'),row,true);
  if(backend.resultado){
    const drafts=backend.resultado.borradores;
    const key=JSON.stringify(backend.resultado);
    const selected=selectionByResult.get(key)??new Set(drafts.map((_,i)=>i));selectionByResult.set(key,selected);
    let downloadButton;
    const legend=document.createElement('p');legend.textContent='Borradores simulados · no generados por IA ni guardados en OCI.';extras.append(legend);
    drafts.forEach((draft,index)=>{
      const details=document.createElement('details'),summary=document.createElement('summary'),checkbox=document.createElement('input'),body=document.createElement('pre');
      checkbox.type='checkbox';checkbox.checked=selected.has(index);checkbox.setAttribute('aria-label',`Seleccionar ${draft.titulo}`);checkbox.onchange=()=>{checkbox.checked?selected.add(index):selected.delete(index);if(downloadButton){downloadButton.dataset.unavailable=String(!selected.size);syncPending();}};
      summary.append(checkbox,document.createTextNode(' '+draft.titulo));body.textContent=draft.contenido+'\n\nMensajes fuente: '+draft.fuentes.join(', ');details.append(summary,body);extras.append(details);
    });
    downloadButton=serverAction('Descargar selección simulada','descargar',()=>({indices:[...selected].sort((a,b)=>a-b)}),extras,false,!selected.size);
  }
}
document.getElementById('file').onchange=async event=>{
  const file=event.target.files[0];if(!file)return;
  if(file.size>5*1024*1024){notify('El archivo supera 5 MB.','error');return;}
  try{
    const contenido=new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer());send('cargar',{contenido,nombre:file.name});
  }catch{notify('El archivo debe estar codificado en UTF-8.','error');}
  event.target.value='';
};
function dataPage(){
  const label='Arrastra un archivo JSON o selecciónalo';
  hot({x:54,y:204,w:820,h:240},label,()=>document.getElementById('file').click());
  stage.ondragover=e=>e.preventDefault();stage.ondrop=async e=>{e.preventDefault();const file=e.dataTransfer.files[0];if(!file)return;if(file.size>5*1024*1024)return notify('El archivo supera 5 MB.','error');try{send('cargar',{contenido:new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer()),nombre:file.name});}catch{notify('El archivo debe estar codificado en UTF-8.','error');}};
  hot(find('Procesar con IA  →'),'Procesar con IA · integración pendiente',()=>{},true);
  if(backend.datos.length){
    replace('Validar estructura JSON','Lote validado');replace('Evaluar relevancia','Revisión local disponible');replace('Procesar con IA','IA pendiente de integración');
    const rows=backend.datos.slice(0,3);
    ['M-001','M-002','M-003'].forEach((id,i)=>{if(rows[i])replace(id,rows[i].id);});
    const cellIds=Object.entries(view.elementos).filter(([,e])=>e.tipo==='text'&&[585,634,683].includes(Math.round(e.y))&&e.x===415).map(([id])=>id);
    cellIds.forEach((id,i)=>{if(rows[i])group(id).querySelector('text').textContent=rows[i].texto.slice(0,78);});
    const channelIds=Object.entries(view.elementos).filter(([,e])=>e.tipo==='text'&&[585,634,683].includes(Math.round(e.y))&&e.x===183).map(([id])=>id);
    channelIds.forEach((id,i)=>{if(rows[i])group(id).querySelector('text').textContent=rows[i].canal.slice(0,26);});
    Object.entries(view.elementos).filter(([,e])=>e.texto==='Validable').forEach(([id])=>group(id).querySelector('text').textContent='Validado');
  }
  dataExtras();
}
function dataExtras(){
  const row=document.createElement('div');row.className='actions';extras.append(row);
  action('Seleccionar archivo JSON',()=>document.getElementById('file').click(),row);
  serverAction('Usar ejemplo del proyecto','ejemplo',{},row,true);
  serverAction('Vaciar sesión','vaciar',{},row,true);
  const details=document.createElement('details'),summary=document.createElement('summary');details.open=jsonOpen;details.ontoggle=()=>jsonOpen=details.open;summary.textContent='Pegar JSON manualmente';details.append(summary);
  const form=document.createElement('form');form.className='extra-form';const textarea=document.createElement('textarea');textarea.rows=7;textarea.value=rawJson;textarea.oninput=()=>rawJson=textarea.value;textarea.setAttribute('aria-label','Contenido JSON');form.append(textarea);
  serverAction('Validar JSON pegado','cargar',()=>({contenido:textarea.value,nombre:'JSON pegado'}),form);details.append(form);extras.append(details);
  if(backend.datos.length){
    const title=document.createElement('h2');title.textContent=`${backend.datos.length} mensajes validados`;extras.append(title);
    const filters=document.createElement('div');filters.className='extra-form';const input=document.createElement('input'),select=document.createElement('select');input.placeholder='Buscar por autor o mensaje';input.value=dataSearch;input.setAttribute('aria-label','Buscar por autor o mensaje');select.setAttribute('aria-label','Canal');
    const channels=['Todos',...new Set(backend.datos.map(m=>m.canal))];if(!channels.includes(dataChannel))dataChannel='Todos';channels.forEach(c=>select.add(new Option(c,c)));select.value=dataChannel;filters.append(input,select);extras.append(filters);
    const tableContainer=document.createElement('div');tableContainer.className='scroll-table';extras.append(tableContainer);
    const update=()=>{tableContainer.replaceChildren();const rows=backend.datos.filter(m=>(select.value==='Todos'||m.canal===select.value)&&(m.autor+' '+m.texto).toLocaleLowerCase('es').includes(input.value.toLocaleLowerCase('es')));const count=document.createElement('p');count.textContent=`${rows.length} de ${backend.datos.length} mensajes`;tableContainer.append(count);
      const table=document.createElement('table');table.className='data-table';const header=table.createTHead().insertRow();['ID','Autor','Canal','Tipo','Mensaje completo'].forEach(name=>{let th=document.createElement('th');th.textContent=name;header.append(th);});
      rows.forEach(m=>{let tr=table.insertRow();[m.id,m.autor,m.canal,m.tipo,m.texto].forEach(value=>tr.insertCell().textContent=value);});tableContainer.append(table);height();};
    input.oninput=()=>{dataSearch=input.value;update();};select.onchange=()=>{dataChannel=select.value;update();};update();action('Elegir plantilla →',()=>go('plantillas'));
  }
}
function agent(){
  hot(find('+ Nueva consulta'),'Nueva consulta',()=>{query='';render();});
  ['Post para LinkedIn','Resumen de opiniones','Temas frecuentes'].forEach(label=>hot(find(label),label,()=>{query=label;const input=stage.querySelector('[aria-label="Consulta al agente"]');input.value=query;input.focus();notify('Consulta de ejemplo seleccionada. El agente real sigue pendiente de integración.');}));
  field(find('Escribe una instrucción sobre los datos que ya están disponibles...'),'Consulta al agente',query,value=>query=value);
  hot(find('Enviar  →'),'Enviar consulta de demostración',()=>notify('Respuesta no disponible: el agente en vivo está pendiente de integración. No se realizó ninguna llamada a IA.','error'));
  hot(find('Copiar post'),'Copiar post de ejemplo',()=>copy('Las mejores decisiones comienzan escuchando…\nConvirtamos las preguntas recurrentes en mejoras concretas.'));
  hot(find('Ver resultado ↗'),'Ver resultado de ejemplo',()=>{format='linkedin';go('resultado');});
  ['Crear contenido','Analizar sentimientos','Resumir hallazgos','Consultar temas'].forEach((label,i)=>hot(find(label),label,()=>go(i===0?'plantillas':'analiticas')));
}
function help(){
  field(find('⌕  Buscar una pregunta o una función...'),'Buscar una pregunta o una función',faqSearch,value=>{faqSearch=value;filterFaq();});
  faqs.forEach(([question,answer],i)=>hot({x:59,y:306+i*108,w:861,h:91},question,()=>notify(answer)));
  hot(find('Importa tus conversaciones en JSON'),'Importar JSON',()=>go('datos'));
  hot(find('Escoge una plantilla'),'Escoger una plantilla',()=>go('plantillas'));
  hot(find('¿Necesitas contactar al equipo?'),'Información de contacto',()=>notify('El formulario de contacto está propuesto en el boceto; todavía no está conectado.'));
}
function filterFaq(){
  const term=faqSearch.toLocaleLowerCase('es');let matches=0;
  faqs.forEach(([q,a],i)=>{let visible=(q+' '+a).toLocaleLowerCase('es').includes(term);if(visible)matches++;Object.entries(view.elementos).forEach(([id,e])=>{if(e.x>=58&&e.x<930&&e.y>=306+i*108&&e.y<407+i*108){const n=group(id);if(n)n.style.opacity=visible?'1':'.15';}});});
  notify(`${matches} ${matches===1?'pregunta coincide':'preguntas coinciden'} con la búsqueda.`);
}
function analytics(){
  const title=document.createElement('h2');title.textContent='Datos del lote validado';extras.append(title);
  const info=document.createElement('p');info.textContent='Los gráficos del boceto son ilustrativos: no son un análisis de IA de tu archivo. Los siguientes conteos sí proceden de los mensajes cargados.';extras.append(info);
  if(backend.datos.length){const actual=document.createElement('p');actual.textContent=`${backend.datos.length} mensajes · ${new Set(backend.datos.map(m=>m.canal)).size} canales · ${backend.datos.filter(m=>m.tipo==='testimonio').length} testimonios declarados · ${backend.datos.filter(m=>m.tipo.startsWith('pregunta_')).length} preguntas declaradas`;extras.append(actual);serverAction('Descargar mensajes validados','descargar_datos');}
  else action('Importar conversaciones',()=>go('datos'));
}
function mobilePage(){
  view={width:390,height:750,elementos:{}};stage.style.aspectRatio='auto';stage.style.height='auto';stage.innerHTML='';
  stage.setAttribute('aria-label',`CommunityLab · ${page} · demostración local`);
  const box=document.createElement('div');box.className='mobile-page';const header=document.createElement('header');header.textContent='communitylab';const hamburger=document.createElement('button');hamburger.textContent='≡';hamburger.setAttribute('aria-label','Abrir menú');hamburger.onclick=menu;header.append(hamburger);box.append(header);
  const heading=document.createElement('h1');heading.textContent={plantillas:'Elige el resultado que necesitas',agente:'Agente CommunityLab',analiticas:'Entiende las conversaciones de tu comunidad',ayuda:'¿En qué podemos ayudarte?',datos:'Prepara los datos antes de generar resultados',mapa:'Una base de datos, distintas salidas útiles',estados:'Estados de interfaz'}[page];box.append(heading);stage.append(box);
  if(page==='plantillas'){
    const input=document.createElement('input');input.className='field';input.style.position='static';input.style.width='100%';input.placeholder='Buscar plantillas';input.setAttribute('aria-label','Buscar plantillas');const grid=document.createElement('div');grid.className='mobile-grid';box.append(input,grid);
    const update=()=>{grid.replaceChildren();cards.filter(c=>c.name.toLocaleLowerCase('es').includes(input.value.toLocaleLowerCase('es'))).forEach(c=>{const card=document.createElement('button');card.className='mobile-card';card.textContent=c.name;card.onclick=()=>{format=c.format;go(c.category==='Analíticas'?'analiticas':'resultado');};grid.append(card);});height();};input.oninput=update;update();
  }else if(page==='datos')dataExtras();
  else if(page==='analiticas')analytics();
  else if(page==='ayuda')faqs.forEach(([q,a])=>{let details=document.createElement('details'),summary=document.createElement('summary'),text=document.createElement('p');summary.textContent=q;text.textContent=a;details.append(summary,text);box.append(details);});
  else if(page==='agente'){const p=document.createElement('p');p.textContent='Respuesta de ejemplo · agente real pendiente de integración.';box.append(p);action('Ver resultado de ejemplo',()=>{format='linkedin';go('resultado');},box);}
  else{const p=document.createElement('p');p.textContent='Datos procesados → LangGraph + modelos → plantillas o agente. Sin cuentas ni publicación automática. Integraciones pendientes.';box.append(p);}
}
function renderDownload(){
  if(!downloadFile)return;
  const url=new URL(downloadFile.url,window.location.origin);
  if(url.origin!==window.location.origin||!url.pathname.includes('/media/'))return;
  const link=document.createElement('a');link.href=url.href;link.download=downloadFile.nombre;link.textContent='Descargar archivo preparado';link.className='action';extras.append(link);
  if(!downloadsHandled.has(downloadFile.id)){downloadsHandled.add(downloadFile.id);link.click();}
}
window.addEventListener('message',event=>{
  if(event.source!==window.parent||event.data.type!=='streamlit:render')return;
  const next=event.data.args.estado??backend;
  const acknowledged=requests.acknowledge(next.ultimo_evento);
  const changed=JSON.stringify(next)!==JSON.stringify(backend);
  downloadFile=event.data.args.descarga??null;
  backend=next;if(!backend.resultado)selectionByResult.clear();
  // Streamlit también envía renders sin cambios; conservar los nodos evita perder clics y foco.
  if(changed||acknowledged)render();
});
let lastWidth=window.innerWidth;
window.addEventListener('resize',()=>{if(window.innerWidth!==lastWidth){lastWidth=window.innerWidth;render();}});
new ResizeObserver(height).observe(document.body);
fetch('./design.json').then(r=>r.json()).then(value=>{design=value;message('streamlit:componentReady',{apiVersion:1});ready=true;render();}).catch(()=>notify('No se pudo cargar la referencia visual local.','error'));
