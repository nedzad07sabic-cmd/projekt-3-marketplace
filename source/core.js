/* Project 3 v0.2 — LOCAL SIMULATION ONLY. No real authentication, payments or legal accounting.
   Amounts are integer cents. UI commits clone/validate state; functions never call a network.
   Post-payout recovery is an explicitly simulated receivable, NOT an automatic bank reversal. */
(function(root){
'use strict';
const VERSION=2, LIMIT=100000000, MAX_ITEMS=200, MAX_ORDERS=300;
const CATS=['Elektronika i gaming','Dom i bašta','Moda','Sport i hobi','Knjige i mediji','Ostalo'];
const KINDS=['Firma','Privatna osoba'];
const STAGES=['CEKA_UPLATU','UPLACENO','POSLANO','DOSTAVLJENO','OTKAZANO','ISTEKLO'];
const REASONS=['Paket nije stigao','Artikl je oštećen','Pogrešan artikl','Zahtjev za povrat','Drugi problem'];
function check(ok,msg){if(!ok)throw Error(msg);}
function integer(x,min=0,max=LIMIT){return Number.isSafeInteger(x)&&x>=min&&x<=max;}
function text(v,min=0,max=100){return typeof v==='string'&&v.trim().length>=min&&v.length<=max;}
function cents(v,allowZero=false){
 const t=String(v).trim().replace(',','.');check(/^\d{1,7}(\.\d{1,2})?$/.test(t),'Iznos: najviše dvije decimale, bez minusa.');
 const [a,b='']=t.split('.'), n=Number(a)*100+Number(b.padEnd(2,'0'));
 check(integer(n,allowZero?0:1),'Iznos je izvan demo raspona.');return n;
}
function basisPoints(v){const t=String(v).trim().replace(',','.');check(/^\d{1,2}(\.\d{1,2})?$/.test(t),'Provizija: 0–30%, najviše dvije decimale.');const n=Math.round(Number(t)*100);check(integer(n,0,3000),'Provizija: 0–30%.');return n;}
function money(c){return new Intl.NumberFormat('de-DE',{style:'currency',currency:'EUR'}).format(c/100);}
function fee(amount,bps){check(integer(amount)&&integer(bps,0,3000),'Nevažeći obračun.');return Math.round(amount*bps/10000);}
function uid(prefix){return prefix+'-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,10);}
function clone(x){return JSON.parse(JSON.stringify(x));}
function now(){return Date.now();}
function log(s,action,detail){s.audit.unshift({at:now(),action:String(action).slice(0,100),detail:String(detail).slice(0,500)});s.audit=s.audit.slice(0,300);}
function seller(s,id){const x=s.sellers.find(x=>x.id===id);check(x,'Prodavač nije pronađen.');return x;}
function item(s,id){const x=s.products.find(x=>x.id===id);check(x,'Artikl nije pronađen.');return x;}
function order(s,id){const x=s.orders.find(x=>x.id===id);check(x,'Narudžba nije pronađena.');return x;}
function initial(){
 const products=[
 ['p1','Mehanička tastatura — demo','firma',CATS[0],'Novo',7500,5,'⌨'],
 ['p2','Stolni organizator — demo','firma',CATS[1],'Novo',2500,4,'▦'],
 ['p3','Sportska torba — demo','firma',CATS[3],'Novo',3500,3,'◇'],
 ['p4','Kolekcija knjiga — demo','privatno',CATS[4],'Polovno',2000,1,'▤'],
 ['p5','Jakna — demo','privatno',CATS[2],'Polovno',4500,1,'♧'],
 ['p6','Stolna dekoracija — demo','privatno',CATS[5],'Polovno',1500,1,'◈']
 ].map(([id,title,sellerId,category,condition,price,stock,icon])=>({id,title,sellerId,category,condition,price,stock,icon,shipping:500,description:'Izmišljeni artikl za testiranje prodaje. Nije stvarna ponuda i ne može se naručiti za novac.',approved:true,paused:false}));
 return {schema:VERSION,revision:0,sellers:[{id:'firma',name:'Demo trgovina — izmišljena firma',kind:KINDS[0],ready:true},{id:'privatno',name:'Demo privatni prodavač',kind:KINDS[1],ready:true}],products,cart:[],orders:[],events:[],audit:[],rateBps:1000};
}
function reserved(s,id,t=now()){
 return s.orders.filter(o=>o.status==='CEKA_UPLATU'&&o.expiresAt>t).reduce((sum,o)=>sum+o.lines.filter(l=>l.productId===id).reduce((a,l)=>a+l.qty,0),0);
}
function available(s,id,t=now()){return Math.max(0,item(s,id).stock-reserved(s,id,t));}
function addCart(s,id,t=now()){
 const p=item(s,id);check(p.approved&&!p.paused,'Oglas nije aktivan.');check(seller(s,p.sellerId).ready,'Prodavač nije spreman za demo prodaju.');
 if(s.cart.length)check(item(s,s.cart[0].productId).sellerId===p.sellerId,'Jedna korpa = jedan prodavač. Završi ili isprazni trenutnu korpu.');
 const line=s.cart.find(l=>l.productId===id);check(available(s,id,t)>(line?line.qty:0),'Nema slobodnih komada; neki mogu biti rezervisani.');
 if(line)line.qty++;else s.cart.push({productId:id,qty:1});
}
function removeCart(s,id){s.cart=s.cart.filter(l=>l.productId!==id);}
function changeQty(s,id,qty,t=now()){
 check(integer(qty,0,1000),'Količina mora biti cijeli broj.');const l=s.cart.find(l=>l.productId===id);check(l,'Nema artikla u korpi.');
 if(qty===0){removeCart(s,id);return;}check(qty<=available(s,id,t),'Nema dovoljno slobodne zalihe.');l.qty=qty;
}
function cartTotal(s){let goods=0,shipping=0;for(const l of s.cart){const p=item(s,l.productId);goods+=p.price*l.qty;shipping=Math.max(shipping,p.shipping);}check(integer(goods+shipping),'Prevelika demo narudžba.');return {goods,shipping,gross:goods+shipping};}
function checkout(s,t=now()){
 check(s.orders.length<MAX_ORDERS,'Demo podržava najviše 300 narudžbi. Sačuvaj kopiju pa resetuj.');check(s.cart.length,'Korpa je prazna.');
 const sid=item(s,s.cart[0].productId).sellerId,se=seller(s,sid);check(se.ready,'Prodavač nije spreman.');
 const lines=s.cart.map(l=>{const p=item(s,l.productId);check(p.sellerId===sid&&p.approved&&!p.paused,'Oglas nije dostupan.');check(integer(l.qty,1,1000)&&l.qty<=available(s,p.id,t),'Nema slobodne zalihe.');return {productId:p.id,title:p.title,unit:p.price,qty:l.qty};});
 const total=cartTotal(s);const o={id:uid('DEMO'),sellerId:sid,sellerName:se.name,sellerKind:se.kind,lines,...total,rateBps:s.rateBps,status:'CEKA_UPLATU',createdAt:t,expiresAt:t+15*60*1000,paidAt:null,shippedAt:null,deliveredAt:null,payoutAt:null,payout:0,refunded:0,recovered:0,stockRestored:false,tracking:'',issue:null,messages:[]};
 s.orders.unshift(o);s.cart=[];log(s,'Rezervisano 15 minuta — bez naplate',o.id);return o;
}
function cancel(s,id){const o=order(s,id);check(o.status==='CEKA_UPLATU','Otkazivanje bez povrata moguće je samo prije uplate.');o.status='OTKAZANO';log(s,'Otkazana neplaćena narudžba',id);}
function expire(s,id,t=now()){const o=order(s,id);check(o.status==='CEKA_UPLATU'&&t>=o.expiresAt,'Rezervacija još nije istekla.');o.status='ISTEKLO';log(s,'Istek rezervacije',id);}
function eventSeen(s,id,type,orderId,amount){
 check(text(id,1,100),'Nedostaje oznaka događaja.');const old=s.events.find(e=>e.id===id);
 if(!old)return false;
 check(old.type===type&&old.orderId===orderId&&old.amount===amount,'Oznaka događaja je već korištena za drugu radnju ili iznos.');return true;
}
function record(s,id,type,orderId,amount){check(s.events.length<3000,'Dostignut demo limit događaja.');s.events.push({id,type,orderId,amount});}
function pay(s,id,eventId,success=true,t=now()){
 const o=order(s,id),type=success?'PAY':'FAIL';if(eventSeen(s,eventId,type,id,o.gross))return false;
 check(o.status==='CEKA_UPLATU'&&!o.paidAt,'Narudžba više ne čeka uplatu.');check(t<o.expiresAt,'Rezervacija je istekla. Kreiraj novu narudžbu.');
 if(!success){record(s,eventId,type,id,o.gross);log(s,'Odbijena demo uplata',id);return false;}
 check(seller(s,o.sellerId).ready,'Prodavač nije spreman.');
 for(const l of o.lines){const p=item(s,l.productId);check(p.approved&&!p.paused&&p.stock>=l.qty,'Artikl nije dostupan. Nije simulirana uplata.');}
 check(s.events.length<3000,'Dostignut demo limit događaja.');
 for(const l of o.lines)item(s,l.productId).stock-=l.qty;
 o.status='UPLACENO';o.paidAt=t;record(s,eventId,type,id,o.gross);log(s,'Uplata SIMULIRANA',id);return true;
}
function ship(s,id,tracking='DEMO-POSILJKA',t=now()){
 const o=order(s,id);check(o.status==='UPLACENO'&&o.refunded<o.gross,'Nema plaćene narudžbe za slanje.');check(!o.issue||!o.issue.open,'Otvoren problem: prvo riješi predmet.');check(text(tracking,3,80),'Unesi demo oznaku pošiljke (3–80 znakova).');o.tracking=tracking.trim();o.status='POSLANO';o.shippedAt=t;log(s,'Slanje SIMULIRANO',id);
}
function deliver(s,id,t=now()){const o=order(s,id);check(o.status==='POSLANO','Prvo evidentiraj slanje.');o.status='DOSTAVLJENO';o.deliveredAt=t;log(s,'Dostava SIMULIRANA',id);}
function dispute(s,id,reason='Drugi problem',detail='Demo zahtjev'){
 const o=order(s,id);check(o.paidAt!==null&&o.refunded<o.gross,'Problem otvori nakon uplate, prije punog povrata.');check(!o.issue||!o.issue.open,'Predmet je već otvoren.');check(REASONS.includes(reason)&&text(detail,3,1000),'Odaberi razlog i unesi 3–1000 znakova.');
 o.issue={open:true,reason,detail:detail.trim(),openedAt:now(),closedAt:null,resolution:''};log(s,'Otvoren lokalni predmet',id);
}
function resolve(s,id,resolution='Predmet pregledan u demonstraciji.'){
 const o=order(s,id);check(o.issue&&o.issue.open,'Nema otvorenog predmeta.');check(text(resolution,3,500),'Unesi razlog zatvaranja.');o.issue.open=false;o.issue.closedAt=now();o.issue.resolution=resolution.trim();log(s,'Zatvoren lokalni predmet',id);
}
function financials(o){
 const paid=o.paidAt!==null,remaining=paid?o.gross-o.refunded:0;
 const commission=fee(remaining,o.rateBps),entitlement=remaining-commission,netToSeller=o.payout-o.recovered;
 const receivable=Math.max(0,netToSeller-entitlement),due=Math.max(0,entitlement-netToSeller);
 const cash=(paid?o.gross:0)-o.refunded-o.payout+o.recovered;
 return {remaining,commission,entitlement,netToSeller,receivable,due,cash,sellerAmount:entitlement};
}
function payout(s,id,eventId=uid('payout'),t=now()){
 const o=order(s,id);if(eventSeen(s,eventId,'PAYOUT',id,o.payoutAt===null?financials(o).due:o.payout))return false;
 check(o.status==='DOSTAVLJENO'&&o.paidAt!==null,'Demo isplata tek nakon dostave.');check(o.payoutAt===null,'Isplata je već evidentirana.');check(!o.issue||!o.issue.open,'Otvoren predmet blokira isplatu.');check(seller(s,o.sellerId).ready,'Prodavač nije spreman za isplatu.');const amount=financials(o).due;check(amount>0,'Nema iznosa za isplatu.');check(s.events.length<3000,'Dostignut demo limit događaja.');
 o.payout=amount;o.payoutAt=t;record(s,eventId,'PAYOUT',id,amount);log(s,'Isplata SIMULIRANA',id+' / '+money(amount));return amount;
}
function restoreStock(s,o){for(const l of o.lines)check(item(s,l.productId).stock+l.qty<=100000,'Prevelika demo zaliha.');for(const l of o.lines)item(s,l.productId).stock+=l.qty;o.stockRestored=true;}
function refund(s,id,amount,eventId){
 const o=order(s,id);if(eventSeen(s,eventId,'REFUND',id,amount))return false;
 check(o.paidAt!==null,'Nema uplate za povrat.');check(integer(amount,1)&&amount<=o.gross-o.refunded,'Povrat je veći od preostale uplate ili nevažeći.');check(s.events.length<3000,'Dostignut demo limit događaja.');
 if(o.refunded+amount===o.gross&&!o.shippedAt&&!o.stockRestored)restoreStock(s,o);
 o.refunded+=amount;record(s,eventId,'REFUND',id,amount);log(s,o.payoutAt!==null?'Povrat POSLIJE isplate — simulacija':'Povrat PRIJE isplate — simulacija',id+' / '+money(amount));return true;
}
function recover(s,id,amount,eventId){
 const o=order(s,id);if(eventSeen(s,eventId,'RECOVERY',id,amount))return false;
 check(o.payoutAt!==null&&integer(amount,1)&&amount<=financials(o).receivable,'Iznos prelazi demo potraživanje od prodavača.');check(s.events.length<3000,'Dostignut demo limit događaja.');
 o.recovered+=amount;record(s,eventId,'RECOVERY',id,amount);log(s,'Povrat sredstava od prodavača SIMULIRAN',id+' / '+money(amount));return true;
}
function restockReturn(s,id){const o=order(s,id);check(o.shippedAt!==null&&o.refunded===o.gross&&!o.stockRestored,'Potvrda zalihe samo nakon punog povrata, jednom za primljenu robu.');restoreStock(s,o);log(s,'Prijem svih vraćenih artikala SIMULIRAN',id);}
function message(s,id,role,value){const o=order(s,id);check(['Kupac','Prodavač','Administracija'].includes(role),'Nepoznata demo uloga.');check(text(value,1,1000),'Poruka: 1–1000 znakova.');check(o.messages.length<100,'Demo limit: 100 poruka po narudžbi.');o.messages.push({id:uid('msg'),role,text:value.trim(),at:now()});log(s,'Lokalna poruka — nije poslana',id+' / '+role);}
function addSeller(s,name,kind){check(s.sellers.length<50,'Demo limit: 50 prodavača.');check(text(name,3,80)&&KINDS.includes(kind),'Unesi demo naziv i vrstu prodavača.');const se={id:uid('seller'),name:name.trim(),kind,ready:false};s.sellers.push(se);log(s,'Novi demo prodavač čeka provjeru',se.name);return se;}
function setReady(s,id,ready){check(typeof ready==='boolean','Nevažeći status.');seller(s,id).ready=ready;log(s,'Simulirana provjera prodavača',id+' / '+ready);}
function productData(data){
 check(text(data.title,3,100)&&text(data.description,0,2000),'Naziv: 3–100; opis: do 2000 znakova.');check(CATS.includes(data.category)&&['Novo','Polovno'].includes(data.condition),'Odaberi kategoriju i stanje.');const stock=Number(data.stock);check(integer(stock,0,1000),'Zaliha: 0–1000 komada.');
 return {title:data.title.trim(),description:data.description.trim(),category:data.category,condition:data.condition,price:cents(data.price),shipping:cents(data.shipping,true),stock};
}
function addProduct(s,data){seller(s,data.sellerId);check(s.products.length<MAX_ITEMS,'Demo limit: 200 artikala.');const p={id:uid('product'),sellerId:data.sellerId,...productData(data),approved:false,paused:false,icon:'□'};s.products.push(p);log(s,'Novi oglas čeka odobrenje',p.title);return p;}
function editProduct(s,id,sellerId,data,t=now()){
 const p=item(s,id);check(p.sellerId===sellerId,'Artikl pripada drugom demo prodavaču.');const d=productData(data);check(d.stock>=reserved(s,id,t),'Zaliha ne može biti manja od rezervisanih komada.');Object.assign(p,d);p.approved=false;log(s,'Izmijenjen oglas čeka novo odobrenje',p.title);
}
function approve(s,id){const p=item(s,id);check(seller(s,p.sellerId).ready,'Prvo simuliraj provjeru prodavača.');p.approved=true;log(s,'Oglas odobren u demou',p.title);}
function pause(s,id){const p=item(s,id);p.paused=!p.paused;log(s,p.paused?'Oglas pauziran':'Oglas vraćen iz pauze',p.title);}
function estimate(x){
 const fields=['gross','rate','feeVat','processingRate','processingFixed','activeFee','ordersPerSeller','payoutRate','payoutFixed','payoutsPerOrder','routingRate','adCost','supportCost','lossReserve','monthlyOrders','monthlyFixed'];
 for(const k of fields)check(Number.isFinite(x[k])&&x[k]>=0&&x[k]<=10000000,'Provjeri unos računice.');check(x.gross>0&&x.ordersPerSeller>0&&x.monthlyOrders>0&&x.rate<=30,'Pozitivni iznosi i broj narudžbi; provizija do 30%.');
 const grossFee=x.gross*x.rate/100,netFee=grossFee/(1+x.feeVat/100),feeVat=grossFee-netFee,sellerNet=x.gross-grossFee;
 const processing=x.gross*x.processingRate/100+x.processingFixed,active=x.activeFee/x.ordersPerSeller,payoutFees=sellerNet*x.payoutRate/100+x.payoutFixed*x.payoutsPerOrder,routing=sellerNet*x.routingRate/100;
 const contribution=netFee-processing-active-payoutFees-routing-x.adCost-x.supportCost-x.lossReserve;
 return {grossFee,netFee,feeVat,sellerNet,processing,active,payoutFees,routing,contribution,monthly:contribution*x.monthlyOrders-x.monthlyFixed,breakEven:contribution>0?Math.ceil(x.monthlyFixed/contribution):null};
}
// Strict import boundary. Reject unknown keys, prototype-like keys, dangling refs, invalid ledgers.
function keys(o,required){check(o&&typeof o==='object'&&!Array.isArray(o),'Očekivan je zapis.');check(Object.keys(o).length===required.length&&required.every(k=>Object.hasOwn(o,k)),'Nepoznat ili nepotpun format zapisa.');}
function array(a,max){check(Array.isArray(a)&&a.length<=max,'Prevelika ili nevažeća lista.');}
function id(v){check(typeof v==='string'&&/^[a-zA-Z0-9_-]{1,100}$/.test(v),'Nevažeća demo oznaka.');}
function unique(a,field='id'){check(new Set(a.map(x=>x[field])).size===a.length,'Duplirana oznaka.');}
function timestamp(v,nullable=false){check((nullable&&v===null)||integer(v,1,8640000000000000),'Nevažeće vrijeme.');}
function validateState(s){
 keys(s,['schema','revision','sellers','products','cart','orders','events','audit','rateBps']);check(s.schema===2,'Podržana je samo demo kopija verzije 0.2.');check(integer(s.revision)&&integer(s.rateBps,0,3000),'Nevažeće postavke.');
 array(s.sellers,50);array(s.products,MAX_ITEMS);array(s.cart,MAX_ITEMS);array(s.orders,MAX_ORDERS);array(s.events,3000);array(s.audit,300);
 check(s.sellers.length>=1,'Nedostaje demo prodavač.');unique(s.sellers);unique(s.products);unique(s.orders);unique(s.cart,'productId');unique(s.events);
 for(const se of s.sellers){keys(se,['id','name','kind','ready']);id(se.id);check(text(se.name,3,80)&&KINDS.includes(se.kind)&&typeof se.ready==='boolean','Nevažeći prodavač.');}
 for(const p of s.products){keys(p,['id','title','sellerId','category','condition','price','stock','icon','shipping','description','approved','paused']);id(p.id);seller(s,p.sellerId);check(text(p.title,3,100)&&text(p.description,0,2000)&&text(p.icon,1,4),'Nevažeći opis artikla.');check(CATS.includes(p.category)&&['Novo','Polovno'].includes(p.condition),'Nevažeća kategorija.');check(integer(p.price,1)&&integer(p.shipping)&&integer(p.stock,0,100000)&&typeof p.approved==='boolean'&&typeof p.paused==='boolean','Nevažeći artikl.');}
 let sid=null;for(const l of s.cart){keys(l,['productId','qty']);const p=item(s,l.productId);check(integer(l.qty,1,1000),'Nevažeća količina.');if(sid)check(p.sellerId===sid,'Mješovita korpa.');sid=p.sellerId;}
 for(const o of s.orders){
  keys(o,['id','sellerId','sellerName','sellerKind','lines','goods','shipping','gross','rateBps','status','createdAt','expiresAt','paidAt','shippedAt','deliveredAt','payoutAt','payout','refunded','recovered','stockRestored','tracking','issue','messages']);id(o.id);seller(s,o.sellerId);
  check(text(o.sellerName,3,80)&&KINDS.includes(o.sellerKind)&&STAGES.includes(o.status),'Nevažeća narudžba.');
  array(o.lines,MAX_ITEMS);check(o.lines.length>0,'Narudžba je prazna.');unique(o.lines,'productId');let goods=0;
  for(const l of o.lines){keys(l,['productId','title','unit','qty']);check(item(s,l.productId).sellerId===o.sellerId,'Artikl i prodavač nisu usklađeni.');check(text(l.title,3,100)&&integer(l.unit,1)&&integer(l.qty,1,1000),'Nevažeća stavka.');goods+=l.unit*l.qty;}
  for(const k of ['goods','shipping','gross','payout','refunded','recovered'])check(integer(o[k]),'Nevažeći iznos.');check(o.goods===goods&&o.gross===goods+o.shipping&&o.gross>0&&integer(o.rateBps,0,3000),'Neusklađen zbir.');
  check(o.refunded<=o.gross&&o.recovered<=o.payout&&o.payout<=o.gross-fee(o.gross,o.rateBps),'Neusklađen povrat ili isplata.');
  timestamp(o.createdAt);timestamp(o.expiresAt);check(o.expiresAt===o.createdAt+900000,'Nevažeća rezervacija.');for(const k of ['paidAt','shippedAt','deliveredAt','payoutAt'])timestamp(o[k],true);
  const isPaid=o.paidAt!==null;check(isPaid===['UPLACENO','POSLANO','DOSTAVLJENO'].includes(o.status),'Status i uplata se ne podudaraju.');
  if(!isPaid)check(!o.payout&&!o.refunded&&!o.recovered&&o.payoutAt===null&&o.shippedAt===null&&o.deliveredAt===null&&!o.stockRestored&&o.issue===null,'Neplaćena narudžba ima finansijske promjene.');
  if(isPaid)check(o.paidAt>=o.createdAt&&o.paidAt<o.expiresAt,'Uplata izvan rezervacije.');
  check((o.shippedAt!==null)===['POSLANO','DOSTAVLJENO'].includes(o.status),'Status slanja nije usklađen.');check((o.deliveredAt!==null)===(o.status==='DOSTAVLJENO'),'Status dostave nije usklađen.');
  if(o.shippedAt!==null)check(o.shippedAt>=o.paidAt,'Nevažeći slijed slanja.');if(o.deliveredAt!==null)check(o.deliveredAt>=o.shippedAt,'Nevažeći slijed dostave.');
  if(o.payoutAt!==null)check(o.status==='DOSTAVLJENO'&&o.payout>0&&o.payoutAt>=o.deliveredAt,'Nevažeća isplata.');else check(o.payout===0&&o.recovered===0,'Isplata bez vremena.');
  check(typeof o.stockRestored==='boolean'&&(!o.stockRestored||o.refunded===o.gross)&&text(o.tracking,0,80),'Nevažeći povrat robe.');
  const f=financials(o);check(f.netToSeller>=0&&o.recovered<=Math.max(0,o.payout-f.entitlement),'Povrat prodavača prelazi obavezu u demo modelu.');
  if(o.issue!==null){keys(o.issue,['open','reason','detail','openedAt','closedAt','resolution']);check(typeof o.issue.open==='boolean'&&REASONS.includes(o.issue.reason)&&text(o.issue.detail,3,1000)&&text(o.issue.resolution,0,500),'Nevažeći predmet.');timestamp(o.issue.openedAt);timestamp(o.issue.closedAt,true);check(o.issue.open?(o.issue.closedAt===null):(o.issue.closedAt!==null),'Nevažeći status predmeta.');}
  array(o.messages,100);unique(o.messages);for(const m of o.messages){keys(m,['id','role','text','at']);id(m.id);check(['Kupac','Prodavač','Administracija'].includes(m.role)&&text(m.text,1,1000),'Nevažeća poruka.');timestamp(m.at);}
 }
 for(const e of s.events){keys(e,['id','type','orderId','amount']);id(e.id);order(s,e.orderId);check(['PAY','FAIL','REFUND','PAYOUT','RECOVERY'].includes(e.type)&&integer(e.amount,1),'Nevažeći događaj.');}
 for(const o of s.orders){const es=s.events.filter(e=>e.orderId===o.id),sum=t=>es.filter(e=>e.type===t).reduce((a,e)=>a+e.amount,0),n=t=>es.filter(e=>e.type===t).length;
  check(n('PAY')===(o.paidAt===null?0:1)&&sum('PAY')===(o.paidAt===null?0:o.gross)&&sum('REFUND')===o.refunded&&sum('PAYOUT')===o.payout&&n('PAYOUT')===(o.payoutAt===null?0:1)&&sum('RECOVERY')===o.recovered,'Evidencija se ne podudara s finansijama.');}
 for(const a of s.audit){keys(a,['at','action','detail']);timestamp(a.at);check(text(a.action,0,100)&&text(a.detail,0,500),'Nevažeći zapis historije.');}
 return true;
}
function backup(s){validateState(s);return JSON.stringify({format:'projekt3-local-demo',version:2,exportedAt:new Date().toISOString(),state:s},null,2);}
function restore(raw){check(typeof raw==='string'&&raw.length<=2000000,'Kopija je prevelika (najviše 2 MB teksta).');const x=JSON.parse(raw);keys(x,['format','version','exportedAt','state']);check(x.format==='projekt3-local-demo'&&x.version===2&&text(x.exportedAt,1,50),'Ovo nije demo kopija verzije 0.2.');validateState(x.state);return clone(x.state);}
const api={VERSION,CATS,KINDS,REASONS,STAGES,cents,basisPoints,money,fee,uid,clone,initial,log,seller,item,order,reserved,available,addCart,changeQty,removeCart,cartTotal,checkout,cancel,expire,pay,ship,deliver,dispute,resolve,financials,payout,refund,recover,restockReturn,message,addSeller,setReady,addProduct,editProduct,approve,pause,estimate,validateState,backup,restore};
if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.MarketDemo=api;
})(typeof globalThis!=='undefined'?globalThis:this);
