'use strict';
const M=MarketDemo,KEY='projekt3-marketplace-demo-v02';
let state=M.initial(),tab='shop',activeSeller='firma',search='',category='',kindFilter='',sort='default',toastTimer;
let lastStored=null,storageOK=true,writeEnabled=true,loadWarning='',editId=null;
const drafts={},messageDrafts={};
try{lastStored=localStorage.getItem(KEY);if(lastStored){if(lastStored.length>2000000)throw Error('Prevelika kopija.');const saved=JSON.parse(lastStored);M.validateState(saved);state=saved;}}
catch(e){loadWarning=e.name==='SecurityError'?'Preglednik ovdje ne dopušta automatsko čuvanje. Demo radi u memoriji; napredak sačuvaj kroz Podaci / pomoć.':'Sačuvani zapis nije učitan jer ne prolazi provjeru formata. Nije obrisan. Demo radi u memoriji; otvori Podaci / pomoć.';storageOK=false;writeEnabled=false;}
const root=document.getElementById('content');
const stageText={CEKA_UPLATU:'Čeka demo uplatu',UPLACENO:'Plaćeno · demo',POSLANO:'Poslano · demo',DOSTAVLJENO:'Dostavljeno · demo',OTKAZANO:'Otkazano prije uplate',ISTEKLO:'Istekla rezervacija'};
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function add(p,...nodes){nodes.forEach(n=>p.append(n));return p;}
function button(text,fn,cls=''){const b=el('button',text,cls);b.type='button';b.onclick=fn;return b;}
function note(t,warning=false){return el('div',t,warning?'note alert':'note');}
function hero(title,desc,eyebrow='PROJEKT 3 / LOKALNI TEST 0.2'){
 const section=el('section',undefined,'hero');add(section,add(el('div'),el('div',eyebrow,'eyebrow'),el('h1',title),el('p',desc,'muted')));return section;
}
function panel(title){const p=el('section',undefined,'panel');if(title)p.append(el('h2',title));return p;}
function empty(t){return el('div',t,'empty');}
function field(label,id,value,type='text',extra={}){const f=el('label',undefined,'field'),i=el('input');i.id=id;i.type=type;i.value=value;Object.assign(i,extra);add(f,el('span',label),i);return f;}
function area(label,id,value,max=1000){const f=el('label',undefined,'field full'),i=el('textarea');i.id=id;i.value=value;i.rows=3;i.maxLength=max;add(f,el('span',label),i);return f;}
function selectField(label,id,options,value){const f=el('label',undefined,'field'),s=el('select');s.id=id;options.forEach(o=>{const opt=el('option',typeof o==='string'?o:o.label);opt.value=typeof o==='string'?o:o.value;s.append(opt);});s.value=value;return add(f,el('span',label),s);}
function val(id){return document.getElementById(id).value;}
function kv(p,label,value,cls=''){add(p,el('span',label),el('strong',value,cls));}
function table(headers,rows){const w=el('div',undefined,'tablewrap'),t=el('table'),h=el('tr');headers.forEach(x=>h.append(el('th',x)));t.append(add(el('thead'),h));const body=el('tbody');rows.forEach(row=>{const tr=el('tr');row.forEach(cell=>{const td=el('td');td.append(cell instanceof Node?cell:document.createTextNode(String(cell)));tr.append(td);});body.append(tr);});t.append(body);w.append(t);return w;}
function notify(t){const n=document.getElementById('toast');n.textContent=t;n.hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>n.hidden=true,7000);}
function storageLabel(){document.getElementById('storage').textContent=storageOK&&writeEnabled?'Lokalno čuvanje aktivno':'Samo memorija — sačuvaj kopiju';document.getElementById('storage').className=storageOK&&writeEnabled?'badge':'badge caution';}
function run(fn,ok='Promjena sačuvana u lokalnom demou.'){
 try{
  if(storageOK&&writeEnabled){const latest=localStorage.getItem(KEY);if(latest!==lastStored)throw Error('Podaci su izmijenjeni u drugom prozoru. U Podaci / pomoć izaberi „Učitaj novije lokalne podatke“.');}
  const next=M.clone(state);const result=fn(next);next.revision=state.revision+1;M.validateState(next);
  const raw=JSON.stringify(next);if(raw.length>1000000)throw Error('Demo je dostigao lokalni limit. Izvezi kopiju pa resetuj.');
  let saved=true;
  if(storageOK&&writeEnabled){try{localStorage.setItem(KEY,raw);lastStored=raw;}catch(e){storageOK=false;saved=false;}}
  else saved=false;
  state=next;render();notify(saved?ok:ok+' Podaci su samo u memoriji — izvezi kopiju.');return {ok:true,result};
 }catch(e){notify(e.message);return {ok:false};}
}
function go(t){tab=t;render();window.scrollTo(0,0);}
function modal(title,build){
 const d=document.getElementById('dialog');if(d.open)d.close();d.replaceChildren();
 const head=el('div',undefined,'row wrap');add(head,el('h2',title),button('Zatvori',()=>d.close()));d.append(head);build(d);d.showModal();
}
function askAmount(title,max,fn,warning=''){
 modal(title,d=>{if(warning)d.append(note(warning,true));const f=el('form');add(f,field('Iznos (€), najviše '+M.money(max),'amount',(max/100).toFixed(2),'text',{required:true,inputMode:'decimal'}),el('p','Sve je lokalna simulacija. Nema bankovne transakcije.','small muted'));
 const b=el('button','Potvrdi simulaciju','primary');b.type='submit';f.append(b);f.onsubmit=e=>{e.preventDefault();let n;try{n=M.cents(val('amount'));}catch(error){notify(error.message);return;}const r=run(s=>fn(s,n));if(r.ok)d.close();};d.append(f);});
}
function render(){
 if(!state.sellers.some(s=>s.id===activeSeller)){activeSeller=state.sellers[0].id;editId=null;}
 if(editId&&!state.products.some(p=>p.id===editId&&p.sellerId===activeSeller))editId=null;
 document.querySelectorAll('[data-tab]').forEach(b=>{b.classList.toggle('active',b.dataset.tab===tab);b.setAttribute('aria-current',b.dataset.tab===tab?'page':'false');});
 document.getElementById('cartcount').textContent=state.cart.reduce((a,l)=>a+l.qty,0);root.replaceChildren();storageLabel();
 ({shop,cart,orders,seller:sellerPage,admin,calc:calculator,data:dataPage})[tab]();
}
function sellerNotice(kind){return kind==='Firma'?'Firma: kod online kupovine potrošača u EU u pravilu postoji 14 dana za odustanak, uz izuzetke. Ovo je informativni demo, ne kompletan pravni tekst.':'Privatna osoba: EU pravo na 14-dnevni odustanak ne primjenjuje se kao kod kupovine od trgovca. To ne znači da je isključena svaka odgovornost. Prijava problema ostaje dostupna u demou.';}
function detail(id){const p=M.item(state,id),s=M.seller(state,p.sellerId);modal('Detalji demo artikla',d=>{
 add(d,el('div',p.icon,'detail-art'),el('div',p.category,'eyebrow'),el('h3',p.title),el('p',p.description,'prewrap'),el('p',s.name+' · '+s.kind),el('p',M.money(p.price)+' + '+M.money(p.shipping)+' dostava','big'),el('p','Slobodno: '+M.available(state,p.id)+' · Rezervisano: '+M.reserved(state,p.id),'small muted'),note(sellerNotice(s.kind)));
 const b=button('Dodaj u demo korpu',()=>{const r=run(x=>M.addCart(x,p.id),'Artikl je dodan.');if(r.ok)d.close();},'primary');b.disabled=!p.approved||p.paused||!s.ready||M.available(state,id)===0;d.append(b);
 });}
function shop(){
 add(root,hero('Mjesto za firme i privatne prodavače.','Isprobaj prodaju od oglasa do povrata. Svi artikli i prodavači su izmišljeni; nijedan proizvod nije stvarna ponuda.'),note('Bez stvarnih uplata · Radna provizija '+state.rateBps/100+'% · Jedan prodavač po narudžbi.'));
 const tools=el('div',undefined,'toolbar');const q=el('input');q.type='search';q.placeholder='Pretraži demo artikle';q.value=search;q.setAttribute('aria-label','Pretraži demo artikle');
 const c=selectField('Kategorija','filter-cat',[{value:'',label:'Sve kategorije'},...M.CATS.map(x=>({value:x,label:x}))],category);
 const k=selectField('Prodavač','filter-kind',[{value:'',label:'Svi prodavači'},...M.KINDS.map(x=>({value:x,label:x}))],kindFilter);
 const so=selectField('Poredak','filter-sort',[{value:'default',label:'Preporučeni demo poredak'},{value:'low',label:'Cijena: niža prvo'},{value:'high',label:'Cijena: viša prvo'}],sort);
 add(tools,add(el('label',undefined,'field search-field'),el('span','Pretraga'),q),c,k,so);root.append(tools);
 const grid=el('div',undefined,'grid');root.append(grid);
 function list(){
  grid.replaceChildren();let ps=state.products.filter(p=>p.approved&&!p.paused&&M.seller(state,p.sellerId).ready&&p.title.toLocaleLowerCase().includes(search.toLocaleLowerCase())&&(!category||p.category===category)&&(!kindFilter||M.seller(state,p.sellerId).kind===kindFilter));
  if(sort!=='default')ps.sort((a,b)=>sort==='low'?a.price-b.price:b.price-a.price);
  ps.forEach(p=>{const s=M.seller(state,p.sellerId),n=M.available(state,p.id),card=el('article',undefined,'card'),art=el('div',p.icon,'product-art');art.setAttribute('aria-hidden','true');art.append(el('span',p.condition,'badge'));
   const body=el('div',undefined,'card-content');add(body,el('div',p.category,'eyebrow'),el('h3',p.title),el('div',s.kind+' · '+s.name,'small muted'),el('div',M.money(p.price),'price'),el('p','Dostava '+M.money(p.shipping)+' · Slobodno '+n,'small muted'));
   const actions=el('div',undefined,'product-actions'),b=button(n?'Dodaj u korpu':'Nema slobodnih',()=>run(x=>M.addCart(x,p.id),'Dodano u demo korpu.'),'primary');b.disabled=!n;add(actions,b,button('Detalji',()=>detail(p.id)));body.append(actions);add(card,art,body);grid.append(card);
  });if(!ps.length)grid.append(empty('Nema aktivnih demo artikala za ovaj izbor.'));
 }
 q.oninput=()=>{search=q.value;list();};c.querySelector('select').onchange=e=>{category=e.target.value;list();};k.querySelector('select').onchange=e=>{kindFilter=e.target.value;list();};so.querySelector('select').onchange=e=>{sort=e.target.value;list();};list();
}
function cart(){
 root.append(hero('Demo korpa','Dodavanje u korpu ne rezerviše robu. Rezervacija od 15 minuta nastaje tek kreiranjem demo narudžbe.'));
 if(!state.cart.length){add(root,empty('Korpa je prazna.'),button('Pregledaj artikle',()=>go('shop'),'primary'));return;}
 const se=M.seller(state,M.item(state,state.cart[0].productId).sellerId),p=panel(se.name);p.append(note(sellerNotice(se.kind)));
 p.append(table(['Artikl','Količina','Ukupno',''],state.cart.map(l=>{const it=M.item(state,l.productId),buttons=el('div',undefined,'actions');add(buttons,button('−',()=>run(s=>M.changeQty(s,it.id,l.qty-1))),el('span',String(l.qty),'qty'),button('+',()=>run(s=>M.changeQty(s,it.id,l.qty+1))));return [it.title,buttons,M.money(it.price*l.qty),button('Ukloni',()=>run(s=>M.removeCart(s,it.id)),'danger')];})));
 const t=M.cartTotal(state),tot=el('div',undefined,'totals');kv(tot,'Artikli',M.money(t.goods));kv(tot,'Dostava (najviša pojedinačna, demo pravilo)',M.money(t.shipping));kv(tot,'Ukupno za simulaciju',M.money(t.gross),'big');p.append(tot);
 add(p,note('Ne unosi karticu, adresu ili lične dokumente. Nema stvarnog ugovora ni naplate.'),button('Kreiraj demo narudžbu',()=>{const r=run(s=>M.checkout(s),'Demo narudžba kreirana i roba rezervisana.');if(r.ok)go('orders');},'primary'),document.createTextNode(' '),button('Isprazni korpu',()=>run(s=>{s.cart=[];})));root.append(p);
}
function openIssue(id){modal('Otvori lokalni predmet',d=>{const f=el('form');add(f,selectField('Razlog','issue-reason',M.REASONS,M.REASONS[0]),area('Izmišljeni opis problema','issue-detail','',1000),note('Ne šalje se e-mail. Predmet je vidljiv samo u ovom demou.'));const b=el('button','Otvori demo predmet','primary');b.type='submit';f.append(b);f.onsubmit=e=>{e.preventDefault();const reason=val('issue-reason'),desc=val('issue-detail');const r=run(s=>M.dispute(s,id,reason,desc));if(r.ok)d.close();};d.append(f);});}
function shippingDialog(id){modal('Simuliraj slanje',d=>{const f=el('form');add(f,field('Izmišljena oznaka pošiljke','tracking','DEMO-PAKET-001','text',{minLength:3,maxLength:80,required:true}),note('Oznaka nije povezana s kurirom.'));const b=el('button','Evidentiraj demo slanje','primary');b.type='submit';f.append(b);f.onsubmit=e=>{e.preventDefault();const tracking=val('tracking');const r=run(s=>M.ship(s,id,tracking));if(r.ok)d.close();};d.append(f);});}
function closeIssue(id){modal('Zatvori lokalni predmet',d=>{const f=el('form');f.append(area('Razlog zatvaranja','resolution','Demo pregled je završen.',500));const b=el('button','Potvrdi zatvaranje','primary');b.type='submit';f.append(b);f.onsubmit=e=>{e.preventDefault();const value=val('resolution');const r=run(s=>M.resolve(s,id,value));if(r.ok)d.close();};d.append(f);});}
function historyMessages(o,role){
 const de=el('details'),su=el('summary','Poruke unutar narudžbe ('+o.messages.length+') — lokalno');de.append(su);
 o.messages.forEach(m=>add(de,add(el('div',undefined,'message'),el('strong',m.role),el('span',' · '+new Date(m.at).toLocaleString('bs-BA'),'small muted'),el('p',m.text,'prewrap'))));
 const f=el('form'),id='msg-'+role+'-'+o.id,a=area('Demo poruka — bez stvarnih podataka',id,messageDrafts[id]||'');a.querySelector('textarea').required=true;a.querySelector('textarea').oninput=e=>{messageDrafts[id]=e.target.value;};f.append(a);const b=el('button','Dodaj lokalnu poruku');b.type='submit';f.append(b);f.onsubmit=e=>{e.preventDefault();const msg=val(id);const r=run(s=>M.message(s,o.id,role,msg),'Poruka je sačuvana samo lokalno, nije poslana.');if(r.ok){delete messageDrafts[id];render();}};add(de,note('Promjena demo uloge nije prijava. Sve poruke su dostupne u ovoj datoteci.'),f);return de;
}
function orderCard(o,role){
 const p=el('article',undefined,'order'),head=el('div',undefined,'row wrap'),badges=el('div',undefined,'actions');badges.append(el('span',stageText[o.status],'pill'));
 if(o.payoutAt!==null)badges.append(el('span','Isplaćeno · demo','badge'));if(o.refunded)badges.append(el('span',o.refunded===o.gross?'Puni povrat · demo':'Djelimični povrat · demo','badge caution'));if(o.issue&&o.issue.open)badges.append(el('span','Otvoren predmet','badge caution'));
 add(head,el('h3',o.id),badges);add(p,head,el('p',o.lines.map(l=>l.title+' × '+l.qty).join(' · '),'small'),el('p',o.sellerName+' · '+o.sellerKind,'small muted'));
 const f=M.financials(o),tot=el('div',undefined,'totals');kv(tot,o.paidAt===null?'Planirani iznos':'Prvobitno naplaćeno (demo)',M.money(o.gross));kv(tot,'Vraćeno kupcu (demo)',M.money(o.refunded));
 if(role!=='buyer'&&o.paidAt!==null){kv(tot,'Preostala bruto naknada platforme',M.money(f.commission));kv(tot,'Pripada prodavaču nakon povrata',M.money(f.entitlement));kv(tot,'Već isplaćeno prodavaču',M.money(o.payout));kv(tot,'Vraćeno od prodavača (simulirano)',M.money(o.recovered));}
 p.append(tot);
 if(o.tracking)p.append(el('p','Demo oznaka pošiljke: '+o.tracking,'small'));
 if(o.status==='CEKA_UPLATU')p.append(el('p','Rezervacija do '+new Date(o.expiresAt).toLocaleTimeString('bs-BA')+' — 15 minuta. Nema automatskog brisanja narudžbe.','small muted'));
 if(o.issue){const d=el('details');d.open=o.issue.open;add(d,el('summary',(o.issue.open?'Otvoreno: ':'Zatvoreno: ')+o.issue.reason),el('p',o.issue.detail,'prewrap'));if(o.issue.resolution)d.append(el('p','Rješenje: '+o.issue.resolution,'prewrap'));p.append(d);}
 if(role==='admin'&&o.paidAt!==null){const info=el('div',undefined,'ledger');add(info,el('strong','Finansijski test — nije bankovni saldo'),el('p','Simulirana sredstva preostala platformi: '+M.money(f.cash),'big '+(f.cash<0?'negative':'positive')),el('p','Za naplatiti od prodavača (demo potraživanje): '+M.money(f.receivable),'small'));p.append(info);if(f.receivable>0)p.append(note('Povrat kupcu je evidentiran, ali ovaj iznos još nije vraćen od prodavača. Naplativost nije garantovana. Obračun ne uključuje troškove procesora ni poreze.',true));}
 const actions=el('div',undefined,'actions');
 if(role==='buyer'&&o.status==='CEKA_UPLATU'){
  actions.append(button('Simuliraj uspješnu uplatu',()=>run(s=>M.pay(s,o.id,M.uid('pay'))),'primary'));
  actions.append(button('Simuliraj odbijenu uplatu',()=>run(s=>M.pay(s,o.id,M.uid('fail'),false),'Odbijena demo uplata.')));
  actions.append(button('Otkaži bez uplate',()=>run(s=>M.cancel(s,o.id)),'danger'));
  actions.append(button('Simuliraj istek rezervacije',()=>run(s=>M.expire(s,o.id,o.expiresAt),'Simuliran istek; roba je ponovo slobodna.')));
 }
 if(role==='seller'&&o.status==='UPLACENO'&&o.refunded<o.gross){const b=button('Simuliraj slanje',()=>shippingDialog(o.id),'primary');b.disabled=!!(o.issue&&o.issue.open);actions.append(b);}
 if(role==='buyer'&&o.status==='POSLANO')actions.append(button('Simuliraj dostavu',()=>run(s=>M.deliver(s,o.id)),'primary'));
 if(role==='buyer'&&o.paidAt!==null&&o.refunded<o.gross&&!(o.issue&&o.issue.open))actions.append(button('Prijavi problem / zatraži povrat',()=>openIssue(o.id)));
 if(role==='admin'){
  const payEvent=state.events.find(e=>e.orderId===o.id&&e.type==='PAY');if(payEvent)actions.append(button('Ponovi isti događaj uplate',()=>run(s=>M.pay(s,o.id,payEvent.id),'Duplikat prepoznat; nema druge naplate ni promjene zalihe.')));
  if(o.paidAt!==null&&o.refunded<o.gross)actions.append(button('Simuliraj povrat kupcu',()=>askAmount('Povrat kupcu — simulacija',o.gross-o.refunded,(s,n)=>M.refund(s,o.id,n,M.uid('refund')),o.payoutAt!==null?'Prodavaču je novac već isplaćen. Ovaj korak ne vraća automatski novac od prodavača; nastaje zasebno demo potraživanje.':'Naknada i pripadajući iznos prodavača bit će proporcionalno umanjeni u ovom demo modelu.'),'danger'));
  if(f.receivable>0)actions.append(button('Simuliraj povrat od prodavača',()=>askAmount('Naplata od prodavača — simulacija',f.receivable,(s,n)=>M.recover(s,o.id,n,M.uid('recover')),'Nema bankovne naplate. Ovim samo potvrđuješ zamišljeni povrat sredstava u lokalnom modelu.')));
  if(o.issue&&o.issue.open)actions.append(button('Zatvori demo predmet',()=>closeIssue(o.id)));
  if(o.paidAt!==null&&o.payoutAt===null){const b=button('Simuliraj isplatu prodavaču',()=>run(s=>M.payout(s,o.id,M.uid('payout'))),'primary');b.disabled=o.status!=='DOSTAVLJENO'||!!(o.issue&&o.issue.open)||f.due<=0||!M.seller(state,o.sellerId).ready;actions.append(b);}
  if(o.refunded===o.gross&&o.shippedAt!==null&&!o.stockRestored)actions.append(button('Potvrdi prijem vraćene robe',()=>{if(confirm('Simulirati da su SVI artikli vraćeni i pregledani te ih vratiti na zalihu?'))run(s=>M.restockReturn(s,o.id));}));
 }
 p.append(actions);if(o.refunded===o.gross)p.append(el('p',o.stockRestored?'Zaliha je vraćena jednom u demo modelu.':'Roba NIJE automatski vraćena na zalihu; potreban je prijem i pregled.','small muted'));
 p.append(historyMessages(o,role==='buyer'?'Kupac':role==='seller'?'Prodavač':'Administracija'));return p;
}
function orders(){add(root,hero('Narudžbe i pisana podrška','Prati demo uplatu, dostavu i povrat — i nakon isplate. Prodavač šalje robu; platforma vodi lokalni testni zapis.'));if(!state.orders.length)root.append(empty('Još nema narudžbi. Počni u katalogu.'));state.orders.forEach(o=>root.append(orderCard(o,'buyer')));}
function defaultDraft(){return {title:'',description:'',category:M.CATS[0],condition:'Novo',price:'30.00',shipping:'5.00',stock:'1'};}
function sellerPage(){
 add(root,hero('Prodavačev radni prostor','Dodaj ili uredi artikle i obradi demo narudžbe. Ovaj izbor uloge nije stvarna prijava ni zaštita pristupa.'));
 const se=M.seller(state,activeSeller),switcher=selectField('Demo prodavač','active-seller',state.sellers.map(s=>({value:s.id,label:s.name+' · '+s.kind})),activeSeller);root.append(switcher);switcher.querySelector('select').onchange=e=>{activeSeller=e.target.value;editId=null;render();};
 root.append(note(se.ready?'Demo prodavač je označen kao spreman. To nije stvarna verifikacija identiteta.':'Novi demo prodavač: u Administraciji prvo simuliraj provjeru.',!se.ready));
 const draftKey=editId||('new-'+activeSeller);if(!drafts[draftKey])drafts[draftKey]=defaultDraft();const d=drafts[draftKey];
 const p=panel(editId?'Uredi demo artikl':'Dodaj demo artikl'),form=el('form'),fs=el('div',undefined,'fields');add(fs,field('Naziv','product-title',d.title,'text',{required:true,minLength:3,maxLength:100}),selectField('Kategorija','product-category',M.CATS,d.category),field('Cijena (€)','product-price',d.price,'text',{required:true,inputMode:'decimal'}),field('Dostava (€)','product-shipping',d.shipping,'text',{required:true,inputMode:'decimal'}),field('Zaliha','product-stock',d.stock,'number',{required:true,min:0,max:1000,step:1}),selectField('Stanje','product-condition',['Novo','Polovno'],d.condition),area('Izmišljeni opis artikla','product-description',d.description,2000));
 function readDraft(){const x={};for(const k of ['title','category','price','shipping','stock','condition','description'])x[k]=val('product-'+k);drafts[draftKey]=x;return x;}
 fs.addEventListener('input',readDraft);fs.addEventListener('change',readDraft);form.append(fs);form.append(note('Svaka izmjena oglasa traži novo demo odobrenje. Ranije narudžbe zadržavaju stare cijene. Bez stvarnih imena, adresa, brendova ili dokumenata.'));
 const b=el('button',editId?'Sačuvaj izmjene za pregled':'Pošalji demo oglas na pregled','primary');b.type='submit';form.append(b);
 if(editId){form.append(document.createTextNode(' '));form.append(button('Odustani od uređivanja',()=>{editId=null;render();}));}
 form.onsubmit=e=>{e.preventDefault();const data={...readDraft(),sellerId:activeSeller},editing=editId;const r=run(s=>editing?M.editProduct(s,editing,activeSeller,data):M.addProduct(s,data));if(r.ok){delete drafts[draftKey];editId=null;render();}};p.append(form);root.append(p);
 const ps=panel('Tvoji demo artikli');ps.append(table(['Artikl','Slobodno / rezervisano','Status','Radnje'],state.products.filter(p=>p.sellerId===activeSeller).map(p=>{const actions=el('div',undefined,'actions');add(actions,button('Uredi',()=>{editId=p.id;drafts[p.id]={title:p.title,description:p.description,category:p.category,condition:p.condition,price:(p.price/100).toFixed(2),shipping:(p.shipping/100).toFixed(2),stock:String(p.stock)};render();window.scrollTo(0,0);}),button(p.paused?'Nastavi oglas':'Pauziraj',()=>run(s=>M.pause(s,p.id))));return [p.title,M.available(state,p.id)+' / '+M.reserved(state,p.id),p.paused?'Pauziran':p.approved?'Demo odobren':'Čeka pregled',actions];})));root.append(ps);
 const reg=el('details');reg.append(el('summary','Dodaj novog izmišljenog prodavača'));const f=el('form');add(f,field('Samo izmišljeni naziv','seller-name','','text',{minLength:3,maxLength:80,required:true}),selectField('Vrsta prodavača','seller-kind',M.KINDS,M.KINDS[0]));const sb=el('button','Kreiraj demo prodavača');sb.type='submit';f.append(sb);f.onsubmit=e=>{e.preventDefault();const name=val('seller-name'),kind=val('seller-kind');const r=run(s=>M.addSeller(s,name,kind));if(r.ok){activeSeller=r.result.id;editId=null;render();}};reg.append(f);root.append(reg);
 root.append(el('h2','Narudžbe ovog prodavača'));const os=state.orders.filter(o=>o.sellerId===activeSeller);if(!os.length)root.append(empty('Nema narudžbi.'));os.forEach(o=>root.append(orderCard(o,'seller')));
}
function admin(){
 add(root,hero('Kontrola prodaje i finansijskog rizika','Naplata, isplata, povrat kupcu i povrat sredstava od prodavača odvojeni su događaji. Nijedan ne predstavlja stvarni novac.'));
 const paid=state.orders.filter(o=>o.paidAt!==null),stats=el('div',undefined,'stats');[['Simulirano naplaćeno',paid.reduce((a,o)=>a+o.gross,0)],['Simulirano vraćeno kupcima',paid.reduce((a,o)=>a+o.refunded,0)],['Za naplatiti od prodavača (demo)',paid.reduce((a,o)=>a+M.financials(o).receivable,0)]].forEach(([t,n])=>stats.append(add(el('div',undefined,'stat'),el('div',t,'small muted'),el('strong',M.money(n)))));root.append(stats);
 const f=panel('Probna provizija, bez usvojenog cjenovnika'),row=el('div',undefined,'row wrap');add(row,field('Za nove narudžbe (%)','rate',state.rateBps/100,'text',{inputMode:'decimal'}),button('Primijeni',()=>{const value=val('rate');run(s=>{s.rateBps=M.basisPoints(value);M.log(s,'Nova probna stopa',value+'%');});}));add(f,row,el('p','Stopa važi za obje vrste demo prodavača. Ne mijenja stare narudžbe. Bruto naknada nije čista zarada.','small muted'));root.append(f);
 const se=panel('Provjera prodavača — simulacija');state.sellers.forEach(s=>{const r=el('div',undefined,'row wrap itemrow');add(r,el('p',s.name+' · '+s.kind),button(s.ready?'Blokiraj demo prodavača':'Simuliraj provjeru prodavača',()=>run(x=>M.setReady(x,s.id,!s.ready)),s.ready?'':'primary'));se.append(r);});se.append(note('Ova sklopka nije zamjena za KYC/KYB, pravnu provjeru ili odobrenje pružaoca plaćanja.'));root.append(se);
 const pp=panel('Oglasi koji čekaju pregled');const pending=state.products.filter(p=>!p.approved);if(!pending.length)pp.append(el('p','Nema oglasa na čekanju.','muted'));pending.forEach(p=>{const r=el('div',undefined,'row wrap itemrow');const b=button('Odobri demo oglas',()=>run(s=>M.approve(s,p.id)),'primary');b.disabled=!M.seller(state,p.sellerId).ready;add(r,el('p',p.title+' · '+M.money(p.price)),b);pp.append(r);});root.append(pp);
 root.append(el('h2','Narudžbe, povrati i potraživanja'));if(!state.orders.length)root.append(empty('Nema demo narudžbi.'));state.orders.forEach(o=>root.append(orderCard(o,'admin')));
 const audit=el('details');audit.append(el('summary','Evidencija lokalnih promjena ('+state.audit.length+')'));const list=el('div',undefined,'audit');state.audit.forEach(a=>list.append(el('p',new Date(a.at).toLocaleString('bs-BA')+' · '+a.action+' · '+a.detail)));audit.append(list);root.append(audit);
}
const calcSpec=[['gross','Iznos narudžbe (€)'],['rate','Naknada platforme (%)'],['feeVat','Pretpostavljeni PDV u našoj naknadi (%)'],['processingRate','Obrada plaćanja (%)'],['processingFixed','Obrada — fiksno (€)'],['activeFee','Aktivan prodavač / mjesec (€)'],['ordersPerSeller','Narudžbi po aktivnom prodavaču'],['payoutRate','Isplata (%)'],['payoutFixed','Isplata — fiksno (€)'],['payoutsPerOrder','Broj isplata po narudžbi'],['routingRate','Raspodjela sredstava (%)'],['adCost','Oglasi po narudžbi (€)'],['supportCost','Rad/podrška po narudžbi (€)'],['lossReserve','Rezerva za gubitke po narudžbi (€)'],['monthlyOrders','Narudžbi mjesečno'],['monthlyFixed','Ostali mjesečni troškovi (€)']];
let calcState={gross:100,rate:10,feeVat:19,processingRate:1.5,processingFixed:.25,activeFee:2,ordersPerSeller:10,payoutRate:.25,payoutFixed:.1,payoutsPerOrder:1,routingRate:.25,adCost:3,supportCost:1,lossReserve:1,monthlyOrders:100,monthlyFixed:100};
function calculator(){
 add(root,hero('Promet nije isto što i dobit.','Radna računica je odvojena od demo narudžbi. Mijenjaj pretpostavke i posmatraj trošak svake prodaje.'),note('Brojke nisu ponuda pružaoca plaćanja niti prognoza. Oglasi, podrška i rezerva su sada uključeni kao izmišljene pretpostavke. Poreski status i konačni troškovi nisu potvrđeni.'));
 const split=el('div',undefined,'two'),left=panel('Podesive pretpostavke'),right=panel('Rezultat'),fs=el('div',undefined,'fields');calcSpec.forEach(([k,l])=>fs.append(field(l,'calc-'+k,calcState[k],'number',{min:0,step:'any'})));left.append(fs);add(split,left,right);root.append(split);
 function update(){right.replaceChildren(el('h2','Rezultat simulacije'));try{const x={};for(const [k]of calcSpec){const t=val('calc-'+k).trim();if(!t)throw Error('Popuni sva polja računice.');x[k]=Number(t);}const r=M.estimate(x);calcState=x;const t=el('div',undefined,'totals');for(const [l,n]of [['Bruto naknada',r.grossFee],['Naknada bez pretpostavljenog PDV-a',r.netFee],['Obrada plaćanja',r.processing],['Dio mjesečnog troška prodavača',r.active],['Isplata i raspodjela',r.payoutFees+r.routing],['Oglasi + rad + rezerva',x.adCost+x.supportCost+x.lossReserve]])kv(t,l,M.money(Math.round(n*100)));right.append(t);add(right,el('p','Ostaje po narudžbi prije ostalih fiksnih troškova','small muted'),el('div',M.money(Math.round(r.contribution*100)),'big '+(r.contribution>=0?'positive':'negative')),el('p','Mjesečno nakon unesenih fiksnih troškova, prije poreza na dohodak/dobit','small muted'),el('div',M.money(Math.round(r.monthly*100)),'big '+(r.monthly>=0?'positive':'negative')),note(r.breakEven===null?'Ovaj scenario gubi novac po narudžbi ili ne daje doprinos fiksnim troškovima. Više takvih narudžbi ne rješava problem.':'Za pokriće unesenih mjesečnih fiksnih troškova: najmanje '+r.breakEven+' narudžbi uz iste pretpostavke. To nije predviđanje prodaje.'));right.append(el('p','Nisu automatski uključeni svi porezi na troškove, druge kartice, konverzije, dodatne provjere, savjetnici i nepredviđeni gubici.','small muted'));}catch(e){right.append(note(e.message,true));}}
 fs.addEventListener('input',update);update();
}
function download(name,content,type='application/json'){const blob=new Blob([content],{type}),url=URL.createObjectURL(blob),a=el('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),5000);}
function loadLatest(){try{const raw=localStorage.getItem(KEY);if(!raw)throw Error('Nema sačuvanih podataka.');const s=JSON.parse(raw);M.validateState(s);state=s;lastStored=raw;storageOK=true;writeEnabled=true;loadWarning='';if(!s.sellers.some(x=>x.id===activeSeller))activeSeller=s.sellers[0].id;editId=null;render();notify('Noviji podaci su učitani.');}catch(e){notify(e.message);}}
function dataPage(){
 add(root,hero('Sačuvaj napredak. Provjeri ograničenja.','HTML ostaje samostalan lokalni demo. Kopija podataka je JSON datoteka i nije produkcijska baza.'),note('Radi u jednom prozoru. Upozorenje na promjenu u drugom prozoru nije zamjena za serversku bazu i istovremene transakcije.',true));if(loadWarning)root.append(note(loadWarning,true));
 const p=panel('Izvoz i učitavanje testnih podataka');add(p,el('p','Automatsko čuvanje zavisi od preglednika i putanje lokalne datoteke. Kopiju izvezi prije premještanja datoteke, resetovanja ili zatvaranja privatnog prozora.'),button('Izvezi demo kopiju (.json)',()=>{try{download('Projekt_3_DEMO_kopija_v02.json',M.backup(state));notify('Kopija je pripremljena za preuzimanje.');}catch(e){notify(e.message);}},'primary'),document.createTextNode(' '),button('Učitaj novije lokalne podatke',loadLatest));
 const upload=field('Učitaj kopiju samo iz ove verzije 0.2','backup-file','','file',{accept:'.json,application/json'});upload.querySelector('input').onchange=async e=>{const file=e.target.files[0];if(!file)return;try{if(file.size>2000000)throw Error('Kopija smije imati najviše 2 MB.');const restored=M.restore(await file.text());if(!confirm('Zamijeniti sadašnje DEMO podatke ovom kopijom? Prethodno izvezi kopiju ako ih želiš sačuvati.'))return;const r=run(s=>{Object.keys(s).forEach(k=>delete s[k]);Object.assign(s,restored);});if(r.ok){activeSeller=state.sellers[0].id;editId=null;render();}}catch(error){notify('Kopija nije učitana: '+error.message);}};p.append(upload);p.append(note('Kopija nije šifrovana ni potpisana. Provjera formata ne dokazuje autentičnost; ne unosi stvarne podatke. Verzija 0.1 ostaje netaknuta i ne uvozi se automatski.'));root.append(p);
 const flow=panel('Kratak test novog toka');[
 '1. Katalog → tastatura → Korpa → kreiraj narudžbu → simuliraj uplatu.',
 '2. Prodavač → simuliraj slanje; Narudžbe → simuliraj dostavu.',
 '3. Administracija → simuliraj isplatu prodavaču.',
 '4. Narudžbe → prijavi problem; Administracija → vrati kupcu 20 €.',
 '5. Pogledaj odvojeno demo potraživanje i sredstva preostala platformi.',
 '6. Tek zasebnom simulacijom povrata od prodavača smanjuješ potraživanje.',
 '7. Podaci / pomoć → izvezi kopiju. Resetuj pa uvezi tu kopiju za provjeru.'
 ].forEach(t=>flow.append(el('p',t)));root.append(flow);
 const scope=panel('Šta NIJE urađeno');[
 'Nema stvarnih računa, autentifikacije, serverskih ovlaštenja, sigurne baze ili izolacije korisnika.',
 'Nema WordPress/WooCommerce/Dokan instalacije ni veze s postojećim TimeIQ hostingom.',
 'Nema API poziva, identifikacije prodavača, uplata, isplata, transfera, webhookova ili bankovnih povrata.',
 'Nema kurirske provjere, e-mailova, automatskih obavijesti ili stvarnog sistema podrške.',
 'Spor u demou nije kartični chargeback. Potraživanje nije garantovana naplata od prodavača.',
 'Finansijski model srazmjerno umanjuje platformsku naknadu pri povratu; to je testno pravilo, ne ugovor.',
 'Povrat robe na zalihu nakon slanja podržan je samo za potvrđen puni povrat svih artikala.',
 'Pisana prihvatljivost privatnih prodavača, cijene, pravila platforme, porezi i produkcijska sigurnost ostaju otvoreni.'
 ].forEach(t=>scope.append(el('p',t)));root.append(scope);
 const projects=panel('Tri odvojena projekta');add(projects,el('p','1 — TimeIQ.eu: postojeći projekt, bez izmjena.'),el('p','2 — B2B posredovanje: odvojena saradnja i provizije.'),el('p','3 — Ovaj marketplace: firme i privatne osobe, više kategorija, radni naziv.'));root.append(projects);
}
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>go(b.dataset.tab));
document.getElementById('reset').onclick=()=>{if(!confirm('Obrisati samo podatke demoa 0.2 u ovom pregledniku? Verzija 0.1 i TimeIQ ostaju netaknuti.'))return;try{lastStored=localStorage.getItem(KEY);storageOK=true;writeEnabled=true;}catch(e){storageOK=false;}activeSeller='firma';editId=null;tab='shop';search='';category='';kindFilter='';Object.keys(drafts).forEach(k=>delete drafts[k]);Object.keys(messageDrafts).forEach(k=>delete messageDrafts[k]);loadWarning='';run(s=>{Object.keys(s).forEach(k=>delete s[k]);Object.assign(s,M.initial());},'Resetovan samo demo 0.2.');};
window.addEventListener('storage',e=>{if(e.key===KEY&&e.newValue!==lastStored)notify('Demo je promijenjen u drugom prozoru. Učitaj novije podatke prije rada.');});
render();if(loadWarning)notify(loadWarning);
