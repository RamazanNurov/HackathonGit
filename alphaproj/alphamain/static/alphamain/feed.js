'use strict';
const account = JSON.parse(document.getElementById('account-data').textContent);
const databaseNews = JSON.parse(document.getElementById('news-data').textContent);
const storagePrefix = `context-user-${account.id}-${databaseNews.length ? 'news' : 'demo'}-`;
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
const money = value => new Intl.NumberFormat('ru-RU',{maximumFractionDigits:2}).format(value);
const demoNews = [
{id:1,type:'risk',category:'Финансы · Кредитная нагрузка',title:'ЦБ сохранил ключевую ставку на уровне 14%',summary:'В учебном сценарии стоимость денег остаётся высокой, а снижение ставок по кредитам откладывается.',analysis:p=>p.loan===0?'В профиле нет кредита. Прямой процентной нагрузки нет; при планировании нового займа учитывайте стоимость финансирования.':p.floating==='yes'?`При кредите ${money(p.loan)} млн ₽ и ставке «ключевая + ${money(p.spread)} п. п.» расходы на проценты составят около <strong>${money(p.loan*(14+p.spread)/100)} млн ₽ в год</strong>. Снижение ключевой ставки на 1 п. п. сэкономило бы ${money(p.loan/100)} млн ₽ в год, но в этом сценарии экономии нет. Проверьте, хватает ли бюджета на оборудование.`:'У вас кредит с фиксированной ставкой. Это решение ЦБ само по себе не меняет текущие платежи. Проверьте условия рефинансирования и стоимость новых займов.',action:'Пересмотрите денежный поток на квартал и сравните предложения по рефинансированию.',formula:p=>`Кредит × (14% + надбавка): ${money(p.loan)} × ${money(14+p.spread)}% в год. Расчёт предполагает неизменный остаток долга; погашение тела, комиссии и график платежей не учтены.`},
{id:2,type:'risk',category:'Производство · Сырьё',title:'Поставщики металла объявили о повышении цен на 8%',summary:'Сценарий: новые прайс-листы распространяются на следующие закупки металлопроката.',analysis:p=>p.metal>0?`При закупках на ${money(p.metal)} млн ₽ в месяц ваши расходы могут вырасти на <strong>${money(p.metal*.08)} млн ₽ в месяц</strong>, или на ${money(p.metal*.08*3)} млн ₽ за квартал. Пересмотрите себестоимость и сроки фиксации цен с поставщиками.`:'Закупки металла в профиле равны нулю. Прямого влияния на указанную статью расходов нет. Проверьте зависимость от металла у поставщиков оборудования.',action:'Запросите фиксацию цены и оцените запас сырья до следующего пересмотра прайса.',formula:p=>`${money(p.metal)} млн ₽ × 8%. Объём закупок принят неизменным, вся закупаемая номенклатура дорожает одинаково.`},
{id:3,type:'opportunity',category:'Господдержка · Оборудование',title:'Открыт приём заявок на льготное финансирование производства',summary:'Учебный сценарий: программа предлагает финансирование оборудования по ставке 5% годовых.',analysis:p=>p.equipment>0?`На оборудование запланировано ${money(p.equipment)} млн ₽. При полном финансировании под 5% вместо условных ${money(14+p.spread)}% разница в процентах составит <strong>${money(p.equipment*(14+p.spread-5)/100)} млн ₽ в год</strong>. Это повод проверить доступные программы и требования к участникам.`:'У вас не указан бюджет на оборудование. Если модернизация появится в планах, проверьте возможность льготного финансирования.',action:'Проверьте действующие программы, требования к проекту и перечень документов. Условия этой карточки вымышлены.',formula:p=>`${money(p.equipment)} × (${money(14+p.spread)}% − 5%). Полное финансирование, одинаковый остаток и срок; комиссии, лимиты, залог и соответствие условиям не учтены.`},
{id:4,type:'risk',category:'Внешняя торговля · Логистика',title:'Стоимость доставки импортных комплектующих выросла',summary:'Сценарий: логистические изменения увеличивают полную стоимость импортных поставок на 6%.',analysis:p=>p.imports>0?`Импорт на ${money(p.imports)} млн ₽ в месяц может потребовать дополнительно <strong>${money(p.imports*.06)} млн ₽ в месяц</strong>. За квартал это ${money(p.imports*.06*3)} млн ₽. Уточните сроки доставки критичных комплектующих и резерв бюджета.`:'Импортные закупки в профиле не указаны. Прямых дополнительных расходов по этому сценарию нет; проверьте импортные компоненты у ваших поставщиков.',action:'Сравните альтернативные маршруты и локальных поставщиков, уточните стоимость ближайших поставок.',formula:p=>`${money(p.imports)} млн ₽ × 6%. Допущение: на 6% дорожает полная стоимость импорта, а не только транспортная составляющая.`},
{id:5,type:'opportunity',category:'Продажи · Новые рынки',title:'Крупные заказчики ищут российских производителей оборудования',summary:'Учебный сценарий: расширяется спрос на локальные промышленные решения.',analysis:()=> 'Для производственной компании это повод проверить новые каналы продаж. <strong>Оцените соответствие продукции требованиям заказчиков</strong>, свободные мощности и маржинальность. Без данных о заказах и мощностях денежный эффект посчитать нельзя.',action:'Подготовьте список целевых заказчиков и проверьте закупочные площадки по вашей номенклатуре.',formula:()=> 'Качественный сценарий. Прогноз выручки отсутствует: нет данных о спросе, конверсии и производственных мощностях.'},
{id:6,type:'neutral',category:'Управление · Планирование',title:'Компании пересматривают инвестиционные планы на следующий год',summary:'Сценарий для обсуждения: бизнес повышает требования к окупаемости новых проектов.',analysis:p=>`Ваш бюджет на оборудование — <strong>${money(p.equipment)} млн ₽</strong>. Сравните базовый и стрессовый сценарии: дорогой кредит, рост закупочных цен и задержки поставок. Решение о переносе инвестиций требует расчёта отдачи проекта.`,action:'Обновите инвестиционную модель и определите минимальный резерв ликвидности.',formula:()=> 'Качественная оценка. Для NPV и срока окупаемости нужны прогноз денежных потоков, ставка дисконтирования и график инвестиций.'}
];
const news = databaseNews.length ? databaseNews.map(item => ({
 ...item, type:['risk','opportunity','neutral'].includes(item.kind)?item.kind:'neutral', demo:false,
 analysis:()=> 'Персональный разбор этой новости ещё не подготовлен. Для оценки влияния нужны данные компании и анализ события.',
 action:'Ознакомьтесь с первоисточником. Персональные рекомендации для этой публикации пока не сформированы.',
 formula:()=> 'Персональная модель и расчёты к этой публикации пока не применялись.'
})) : demoNews.map(item=>({...item,demo:true}));
saved = new Set([...saved].filter(id=>news.some(item=>item.id===id)));
function sourceLink(url, label) {
 try {const parsed = new URL(url); if(!['http:','https:'].includes(parsed.protocol)) return '';}
 catch {return '';}
 return `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)} ↗</a>`;
}
function articleDetails(n) {
 if(n.demo) return '<p>Событие вымышленное. Разбор рассчитан правилами, без языковой модели.</p>';
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
 const visible=news.filter(n=>(view!=='saved'||saved.has(n.id))&&(filter==='all'||n.type===filter)&&(`${escapeHtml(n.title)} ${escapeHtml(n.summary)} ${escapeHtml(n.category)}`.toLowerCase().includes(query.toLowerCase())));
 document.querySelector('#results-label').textContent=`${view==='saved'?'СОХРАНЁННОЕ':'ВАЖНОЕ ДЛЯ ВАС'} · ${visible.length}`;
 document.querySelector('#feed').innerHTML=visible.map(n=>`<article class="news-card${animate ? ' entering' : ''}"><div class="news-top"><div class="meta"><span class="source">${n.demo ? `Сценарий ${String(n.id).padStart(2,'0')}` : escapeHtml(n.source_name)}</span><span>·</span><span>${n.demo ? 'Демо-новость' : escapeHtml(new Date(n.published_at).toLocaleDateString('ru-RU'))}</span><span class="badge ${n.type}">${{risk:'Требует внимания',opportunity:'Возможность',neutral:'К сведению'}[n.type]}</span></div><button class="save" data-save="${n.id}" aria-label="${saved.has(n.id)?'Удалить из сохранённого':'Сохранить новость'}" aria-pressed="${saved.has(n.id)}">${saved.has(n.id)?'★':'☆'}</button></div><h2>${escapeHtml(n.title)}</h2><p class="summary">${escapeHtml(n.summary)}</p><div class="analysis"><span class="analysis-label">✦ ЧТО ЭТО ЗНАЧИТ ДЛЯ ВАШЕГО БИЗНЕСА</span><p>${n.analysis(profile)}</p></div><div class="card-bottom"><span class="category">${escapeHtml(n.category)}</span><button class="detail-button" data-detail="${n.id}" aria-expanded="${expanded.has(n.id)}" aria-controls="detail-${n.id}">${expanded.has(n.id)?'Свернуть ↑':(n.demo?'Рекомендации и расчёт ↗':'Подробнее и источники ↗')}</button></div><div class="details" id="detail-${n.id}" ${expanded.has(n.id)?'':'hidden'}><p><strong>Следующий шаг.</strong> ${escapeHtml(n.action)}</p><p><strong>Допущения.</strong> ${n.formula(profile)}</p>${articleDetails(n)}</div></article>`).join('') || '<div class="empty">Нет подходящих новостей. Измените фильтр или сохраните новости из основной ленты.</div>';
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
form.addEventListener('submit',event=>{event.preventDefault();const data=new FormData(form);const next={name:account.name,company:String(data.get('company')).trim(),floating:data.get('floating')};numericFields.forEach(key=>next[key]=Number(data.get(key)));if(!validProfile(next)){toast('Проверьте имя, компанию и числовые значения.');return;}profile=next;persist(storagePrefix+'profile',profile);render();dialog.close();toast('Профиль сохранён. Последствия новостей пересчитаны.');});
render();
