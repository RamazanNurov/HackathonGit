'use strict';
const account = JSON.parse(document.getElementById('account-data').textContent);
const databaseNews = JSON.parse(document.getElementById('news-data').textContent);
const storagePrefix = `context-user-${account.id}-news-`;
const defaults = {name:account.name,company:'Северстальмаш',loan:500,spread:3,metal:20,imports:10,equipment:80,floating:'yes'};
const numericFields = ['loan','spread','metal','imports','equipment'];
function load(key, fallback) { try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; } }
function validProfile(value) {return value && typeof value.name==='string' && value.name.trim() && typeof value.company==='string' && value.company.trim() && ['yes','no'].includes(value.floating) && numericFields.every(key=>Number.isFinite(value[key]) && value[key]>=0 && value[key]<=(key==='spread'?50:1000000));}
const storedProfile = load(storagePrefix+'profile',defaults);
let profile = validProfile(storedProfile) ? {...storedProfile, name:account.name} : {...defaults};
const storedSaved = load(storagePrefix+'saved',[]);
let saved = new Set(Array.isArray(storedSaved) ? storedSaved.filter(id=>Number.isInteger(id)&&id>=1) : []);
let filter = 'all', view = 'all', query = '';
const expanded = new Set();
const news = databaseNews.map(item => ({
 ...item, type:['risk','opportunity','neutral'].includes(item.kind)?item.kind:'neutral',
 analysis:()=> 'Персональный разбор этой новости ещё не подготовлен.',
}));
saved = new Set([...saved].filter(id=>news.some(item=>item.id===id)));
function sourceLink(url, label) {
 try {const parsed = new URL(url); if(!['http:','https:'].includes(parsed.protocol)) return '';}
 catch {return '';}
 return `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)} ↗</a>`;
}
function articleDetails(n) {
 return `<p><strong>Первоисточник.</strong> ${sourceLink(n.source_url,n.source_name)}</p>
 ${n.bank_analysis?`<p><strong>Позиция банка (из указанного материала).</strong> ${escapeHtml(n.bank_analysis)}</p><p>${sourceLink(n.bank_source_url,'Источник позиции банка')}</p>`:''}
 <details><summary>Текст источника / анонс RSS</summary><p class="article-content">${escapeHtml(n.content)}</p></details>`;
}
function escapeHtml(value) {return String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
let toastTimer;
function toast(message) {const el=document.querySelector('#toast');el.textContent=message;el.style.display='block';clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.style.display='none',3500);}
function persist(key,value) {try{localStorage.setItem(key,JSON.stringify(value));}catch{toast('Хранилище браузера недоступно. Изменения сохранятся только до перезагрузки.');}}
function render(animate = true) {
 document.querySelector('#company-name').textContent=profile.company;
 document.querySelector('.nav-count').textContent=news.length;
 document.querySelector('[data-filter="all"] span').textContent=news.length;
 document.querySelector('#total-count').textContent=news.length;
 document.querySelector('#risk-count').textContent=news.filter(n=>n.type==='risk').length;
 document.querySelector('#opportunity-count').textContent=news.filter(n=>n.type==='opportunity').length;
 document.querySelector('#user-name').textContent=account.name;
 document.querySelector('#greeting').textContent=account.name;
 document.querySelector('#saved-count').textContent=saved.size;
 document.querySelector('#view-title').textContent=view==='saved'?'Сохранённое':'Моя лента';
 const visible=news.filter(n=>(view!=='saved'||saved.has(n.id))&&(filter==='all'||n.type===filter)&&(`${n.title} ${n.summary} ${n.category}`.toLowerCase().includes(query.toLowerCase())));
 document.querySelector('#results-label').textContent=`${view==='saved'?'СОХРАНЁННОЕ':'ВАЖНОЕ ДЛЯ ВАС'} · ${visible.length}`;
 document.querySelector('#feed').innerHTML=visible.map(n=>`<article class="news-card${animate ? ' entering' : ''}"><div class="news-top"><div class="meta"><span class="source">${escapeHtml(n.source_name)}</span><span>·</span><span>${escapeHtml(new Date(n.published_at).toLocaleDateString('ru-RU'))}</span><span class="badge ${n.type}">${{risk:'Требует внимания',opportunity:'Возможность',neutral:'К сведению'}[n.type]}</span></div><button class="save" data-save="${n.id}" aria-label="${saved.has(n.id)?'Удалить из сохранённого':'Сохранить новость'}" aria-pressed="${saved.has(n.id)}">${saved.has(n.id)?'★':'☆'}</button></div><h2>${escapeHtml(n.title)}</h2><p class="summary">${escapeHtml(n.summary)}</p><div class="analysis"><span class="analysis-label">✦ ЧТО ЭТО ЗНАЧИТ ДЛЯ ВАШЕГО БИЗНЕСА</span><p>${n.analysis(profile)}</p></div><div class="card-bottom"><span class="category">${escapeHtml(n.category)}</span><button class="detail-button" data-detail="${n.id}" aria-expanded="${expanded.has(n.id)}" aria-controls="detail-${n.id}">${expanded.has(n.id)?'Свернуть ↑':'Подробнее и источники ↗'}</button></div><div class="details" id="detail-${n.id}" ${expanded.has(n.id)?'':'hidden'}>${articleDetails(n)}</div></article>`).join('') || `<div class="empty">${news.length ? 'Нет подходящих новостей. Измените фильтр или сохраните новости из основной ленты.' : 'Пока нет опубликованных новостей. Загрузите их командой import_news или добавьте через админку.'}</div>`;
}
document.querySelector('#feed').addEventListener('click',event=>{const save=event.target.closest('[data-save]');const detail=event.target.closest('[data-detail]');if(save){const id=Number(save.dataset.save);saved.has(id)?saved.delete(id):saved.add(id);persist(storagePrefix+'saved',[...saved]);render(false);document.querySelector(`[data-save="${id}"]`)?.focus();}if(detail){const id=Number(detail.dataset.detail);expanded.has(id)?expanded.delete(id):expanded.add(id);render(false);document.querySelector(`[data-detail="${id}"]`)?.focus();}});
document.querySelectorAll('[data-filter]').forEach(button=>button.addEventListener('click',()=>{filter=button.dataset.filter;document.querySelectorAll('[data-filter]').forEach(el=>el.classList.toggle('selected',el===button));render();}));
document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>{view=button.dataset.view;document.querySelectorAll('[data-view]').forEach(el=>el.classList.toggle('active',el===button));render();}));
document.querySelector('#search').addEventListener('input',event=>{query=event.target.value;render();});
const dialog=document.querySelector('#profile-dialog');
const form=document.querySelector('#profile-form');
function openProfile(){Object.entries(profile).forEach(([key,value])=>{if(form.elements.namedItem(key))form.elements.namedItem(key).value=value;});dialog.showModal();}
['company-button','profile-button','edit-profile'].forEach(id=>document.getElementById(id).addEventListener('click',openProfile));
document.querySelector('#close-dialog').addEventListener('click',()=>dialog.close());
form.addEventListener('submit',event=>{event.preventDefault();const data=new FormData(form);const next={name:account.name,company:String(data.get('company')).trim(),floating:data.get('floating')};numericFields.forEach(key=>next[key]=Number(data.get(key)));if(!validProfile(next)){toast('Проверьте имя, компанию и числовые значения.');return;}profile=next;persist(storagePrefix+'profile',profile);render();dialog.close();toast('Профиль бизнеса сохранён.');});
render();
