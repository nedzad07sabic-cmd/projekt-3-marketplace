"""Server-side commerce rules. No client-side payment or role simulation."""
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal, InvalidOperation
import hashlib, json, uuid
from django.conf import settings
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from .models import (User, Seller, Product, CartLine, Address, Order, SellerOrder,
 OrderLine, SupportCase, CaseMessage, AuditEvent, Outbox, LegalPage, Refund, Review)

class CommerceError(Exception): pass

def cents(value, allow_zero=False):
    try:
        n=Decimal(str(value).replace(',','.'))
        if not n.is_finite() or n.as_tuple().exponent < -2: raise ValueError()
        result=int(n*100)
    except (InvalidOperation, ValueError, OverflowError):
        raise ValidationError('Unesi iznos s najviše dvije decimale.')
    if result < (0 if allow_zero else 50) or result > 1000000:
        raise ValidationError('Iznos nije u dopuštenom rasponu.')
    return result

def money(n): return f'{Decimal(n)/100:.2f} €'
def fee(n,bps): return (n*bps+5000)//10000

def audit(actor,action,obj,**detail):
    return AuditEvent.objects.create(actor=actor if getattr(actor,'pk',None) else None,action=action,object_id=str(obj.pk if hasattr(obj,'pk') else obj),detail=detail)

def mail(key,to,subject,body):
    Outbox.objects.get_or_create(key=key,defaults={'recipient':to,'subject':subject,'body':body})

def required_legal(): return ['impressum','privacy','terms','seller-terms','returns']
def legal_ready(): return all(LegalPage.objects.filter(slug=s,approved=True).exclude(body='').exists() for s in required_legal())
def payments_ready():
    mode=settings.PAYMENTS_MODE
    if mode=='disabled': raise CommerceError('Naplata još nije uključena. Narudžba nije naplaćena.')
    if not settings.STRIPE_SECRET_KEY.startswith('sk_'+mode+'_') or not settings.STRIPE_WEBHOOK_SECRET:
        raise CommerceError('Naplata nije potpuno podešena.')
    if mode=='live' and not (settings.LIVE_APPROVED and settings.PROVIDER_APPROVED and legal_ready() and not settings.DEBUG):
        raise CommerceError('Stvarna prodaja čeka provjeru prije pokretanja.')

def visible_products():
    return Product.objects.filter(status='active',seller__status='approved',category__enabled=True).select_related('seller','category').prefetch_related('images')

def cart_quote(user, products=None):
    lines=list(CartLine.objects.filter(user=user).select_related('product__seller','product__category').order_by('product_id'))
    if not lines: raise CommerceError('Korpa je prazna.')
    if len(lines)>30: raise CommerceError('Najviše 30 različitih artikala u narudžbi.')
    groups={}; snapshot=[]
    for line in lines:
        p=products.get(line.product_id) if products is not None else line.product
        if not p or p.status!='active' or p.seller.status!='approved' or not p.category.enabled:
            raise CommerceError('Jedan artikl više nije dostupan.')
        if p.seller.user_id==user.pk: raise CommerceError('Vlastite artikle nije moguće kupovati.')
        if not (1<=line.quantity<=min(100,p.stock)): raise CommerceError('Nema dovoljno zalihe za '+p.title)
        g=groups.setdefault(p.seller_id,{'seller':p.seller,'lines':[],'goods':0,'shipping':0,'commission':0,'shipping_bps':0})
        gross=p.price_cents*line.quantity
        g['lines'].append({'product':p,'qty':line.quantity,'total':gross})
        g['goods']+=gross;g['shipping']=max(g['shipping'],p.shipping_cents)
        g['commission']+=fee(gross,p.category.commission_bps)
        g['shipping_bps']=max(g['shipping_bps'],p.category.commission_bps)
        snapshot.append([str(p.pk),p.revision,line.quantity,p.price_cents,p.shipping_cents,p.category.commission_bps,str(p.seller_id)])
    for g in groups.values():
        g['total']=g['goods']+g['shipping'];g['commission']+=fee(g['shipping'],g['shipping_bps'])
    total=sum(g['total'] for g in groups.values())
    if total>10000000: raise CommerceError('Narudžba je iznad početnog limita.')
    fingerprint=hashlib.sha256(json.dumps(snapshot,separators=(',',':')).encode()).hexdigest()
    return {'groups':list(groups.values()),'total':total,'fingerprint':fingerprint}

def quote_token(user,quote):
    return signing.dumps({'user':user.pk,'hash':quote['fingerprint']},salt='checkout-quote')

@transaction.atomic
def create_order(user,address,token,signed_quote):
    payments_ready()
    User.objects.select_for_update().get(pk=user.pk)
    previous=Order.objects.filter(checkout_token=token).first()
    if previous:
        if previous.buyer_id!=user.pk: raise PermissionDenied()
        return previous
    if not user.email_verified: raise CommerceError('Prvo potvrdi svoju e-mail adresu.')
    if address.user_id!=user.pk or address.country!='DE': raise CommerceError('Početna dostava dostupna je samo u Njemačkoj.')
    try: q=signing.loads(signed_quote,salt='checkout-quote',max_age=1800)
    except signing.BadSignature: raise CommerceError('Pregled narudžbe je istekao. Ponovo otvori korpu.')
    ids=list(CartLine.objects.filter(user=user).values_list('product_id',flat=True))
    locked=list(Product.objects.select_for_update().filter(pk__in=ids).order_by('pk'))
    products={p.pk:p for p in locked}
    current=cart_quote(user,products)
    if q!={'user':user.pk,'hash':current['fingerprint']}:
        raise CommerceError('Korpa ili cijena je promijenjena. Provjeri novi ukupni iznos.')
    for g in current['groups']:
        seller=g['seller']
        if not seller.stripe_account_id or not seller.stripe_ready or seller.stripe_mode!=settings.PAYMENTS_MODE:
            raise CommerceError('Prodavač još nije spreman za primanje uplata.')
        if settings.PAYMENTS_MODE=='live' and seller.kind=='private' and not settings.PRIVATE_SELLERS_APPROVED:
            raise CommerceError('Prodaja privatnih osoba čeka odobrenje pružaoca plaćanja.')
    terms=LegalPage.objects.filter(slug='terms',approved=True).first()
    order=Order.objects.create(buyer=user,checkout_token=token,total_cents=current['total'],address=address.snapshot(),terms_version=terms.version if terms else 'test-unapproved',payment_mode=settings.PAYMENTS_MODE,expires_at=timezone.now()+timedelta(minutes=35))
    for g in current['groups']:
        s=g['seller']
        part=SellerOrder.objects.create(order=order,seller=s,seller_name=s.display_name,seller_kind=s.kind,seller_legal_notice=s.legal_notice,seller_return_policy=s.return_policy,goods_cents=g['goods'],shipping_cents=g['shipping'],commission_cents=g['commission'])
        for l in g['lines']:
            p=l['product'];p.stock-=l['qty'];p.save(update_fields=['stock'])
            OrderLine.objects.create(part=part,product=p,title=p.title,quantity=l['qty'],unit_cents=p.price_cents,commission_bps=p.category.commission_bps)
    CartLine.objects.filter(user=user).delete()
    audit(user,'order.reserved',order,total_cents=order.total_cents)
    return order

@transaction.atomic
def update_cart(user,product_id,qty,add=False):
    User.objects.select_for_update().get(pk=user.pk)
    p=visible_products().filter(pk=product_id).first()
    if not p: raise CommerceError('Artikl nije dostupan.')
    if p.seller.user_id==user.pk: raise CommerceError('Ne možeš kupiti vlastiti artikl.')
    line=CartLine.objects.filter(user=user,product=p).first()
    if add: qty=(line.quantity if line else 0)+qty
    if qty==0:
        CartLine.objects.filter(user=user,product=p).delete();return
    if not 1<=qty<=min(100,p.stock): raise CommerceError('Odabrana količina nije dostupna.')
    CartLine.objects.update_or_create(user=user,product=p,defaults={'quantity':qty})

@transaction.atomic
def release_stock(order,status):
    # Call only after a confirmed provider expiration or before a session is created.
    o=Order.objects.select_for_update().get(pk=order.pk)
    if o.status!='pending' or o.stock_released: return False
    quantities=defaultdict(int)
    for l in OrderLine.objects.filter(part__order=o): quantities[l.product_id]+=l.quantity
    for p in Product.objects.select_for_update().filter(pk__in=quantities).order_by('pk'):
        p.stock+=quantities[p.pk];p.save(update_fields=['stock'])
    o.status=status;o.stock_released=True;o.save(update_fields=['status','stock_released'])
    audit(None,'order.stock_released',o,reason=status)
    return True

@transaction.atomic
def mark_paid(session):
    oid=session.get('metadata',{}).get('order_id')
    try: o=Order.objects.select_for_update().get(pk=oid)
    except (Order.DoesNotExist,ValidationError,ValueError): raise CommerceError('Unknown payment order')
    if session.get('payment_status')!='paid': return False
    if (session.get('amount_total')!=o.total_cents or session.get('currency')!=o.currency
        or bool(session.get('livemode'))!=(o.payment_mode=='live')
        or (o.stripe_session_id and o.stripe_session_id!=session.get('id'))):
        raise CommerceError('Payment does not match the immutable order')
    if o.status=='paid': return False
    if o.status!='pending' or o.stock_released:
        o.status='payment_review';o.payment_hold=True;o.save(update_fields=['status','payment_hold'])
        audit(None,'payment.late_manual_review',o)
        return False
    pi=session.get('payment_intent')
    if not isinstance(pi,str) or not pi.startswith('pi_'): raise CommerceError('Missing payment intent')
    o.stripe_session_id=session['id'];o.stripe_payment_intent=pi;o.status='paid';o.paid_at=timezone.now()
    o.save(update_fields=['stripe_session_id','stripe_payment_intent','status','paid_at'])
    mail('paid-buyer-'+str(o.pk),o.buyer.email,'Plaćanje narudžbe je potvrđeno',f'Narudžba {o.pk} je plaćena. Pregled: {settings.SITE_URL}{o.get_absolute_url()}')
    for part in o.parts.select_related('seller__user'):
        mail('paid-seller-'+str(part.pk),part.seller.user.email,'Nova plaćena narudžba',f'Nova narudžba {part.pk}. Prijavi se u prodavački panel: {settings.SITE_URL}/sell/')
    audit(None,'payment.confirmed',o,session_id=session['id'])
    return True

@transaction.atomic
def ship_part(user,part_id,carrier,tracking):
    part=SellerOrder.objects.select_for_update().select_related('order','seller').get(pk=part_id)
    if part.seller.user_id!=user.pk: raise PermissionDenied()
    if part.order.status!='paid' or part.order.payment_hold or part.status!='new' or part.refunded_cents:
        raise CommerceError('Narudžba nije spremna za slanje.')
    if not carrier.strip() or not tracking.strip(): raise CommerceError('Unesi dostavnu službu i broj pošiljke.')
    if part.cases.filter(status='open').exists() or part.refunds.filter(status__in=['requested','pending']).exists(): raise CommerceError('Prvo riješi otvoreni predmet ili zahtjev za povrat.')
    part.status='shipped';part.carrier=carrier[:60];part.tracking_number=tracking[:100];part.shipped_at=timezone.now()
    part.save(update_fields=['status','carrier','tracking_number','shipped_at'])
    mail('shipped-'+str(part.pk),part.order.buyer.email,'Narudžba je poslana',f'Narudžba {part.order_id}. Dostavna služba: {part.carrier}. Broj pošiljke: {part.tracking_number}.')
    audit(user,'shipment.created',part)

@transaction.atomic
def receive_part(user,part_id):
    p=SellerOrder.objects.select_for_update().select_related('order').get(pk=part_id)
    if p.order.buyer_id!=user.pk: raise PermissionDenied()
    if p.status!='shipped' or p.order.status!='paid': raise CommerceError('Pošiljka još nije označena kao poslana.')
    p.status='delivered';p.delivered_at=timezone.now();p.save(update_fields=['status','delivered_at'])
    audit(user,'shipment.buyer_confirmed_receipt',p)

@transaction.atomic
def open_case(user,part_id,reason,body):
    p=SellerOrder.objects.select_for_update().select_related('order').get(pk=part_id)
    if p.order.buyer_id!=user.pk: raise PermissionDenied()
    if p.order.status!='paid': raise CommerceError('Predmet se otvara za plaćenu narudžbu.')
    existing=p.cases.filter(status='open').first()
    if existing: return existing
    case=SupportCase.objects.create(part=p,buyer=user,reason=reason)
    CaseMessage.objects.create(case=case,author=user,body=body)
    mail('case-'+str(case.pk),p.seller.user.email,'Otvoren predmet uz narudžbu',f'Pregledaj predmet nakon prijave: {settings.SITE_URL}{case.get_absolute_url()}')
    audit(user,'case.opened',case)
    return case

def can_case(user,case):
    return user.is_authenticated and (user.is_staff or case.buyer_id==user.pk or case.part.seller.user_id==user.pk)

def make_review(user,line,rating,body):
    if line.part.order.buyer_id!=user.pk: raise PermissionDenied()
    if line.part.status!='delivered' or line.part.order.status!='paid' or line.part.remaining_cents<=0:
        raise CommerceError('Ocjena je dostupna nakon potvrđene kupovine i prijema.')
    r,created=Review.objects.get_or_create(line=line,defaults={'author':user,'product':line.product,'rating':rating,'body':body})
    if not created: raise CommerceError('Ova kupovina je već ocijenjena.')
    audit(user,'review.created',r)
    return r
