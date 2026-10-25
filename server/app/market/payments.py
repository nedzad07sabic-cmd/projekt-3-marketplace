"""Stripe adapter. Remote calls only when explicit private settings are configured.
No fallback marks real payments as successful. Snapshot webhooks, Accounts v1
controller configuration; API version pinned and must be integration-tested.
"""
from datetime import timedelta
from urllib.parse import urlparse
import stripe
from stripe._http_client import RequestsClient
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from .models import Order,Seller,SellerOrder,Refund,PaymentEvent
from .services import CommerceError,payments_ready,mark_paid,release_stock,audit,mail


def plain(obj):
    """Normalize Stripe v16 resources before dictionary access."""
    return obj if isinstance(obj, dict) else obj.to_dict()

def gateway():
    mode=settings.PAYMENTS_MODE
    if mode not in ('test','live') or not settings.STRIPE_SECRET_KEY.startswith('sk_'+mode+'_'):
        raise CommerceError('Procesor plaćanja nije konfigurisan.')
    stripe.api_key=settings.STRIPE_SECRET_KEY
    stripe.api_version=settings.STRIPE_API_VERSION
    stripe.max_network_retries=2
    stripe.default_http_client=RequestsClient(timeout=12)
    return stripe

def safe_provider_url(url,allowed):
    p=urlparse(url)
    if p.scheme!='https' or p.hostname not in allowed: raise CommerceError('Unexpected payment provider URL')
    return url

@transaction.atomic
def prepare_checkout(order,user):
    payments_ready()
    o=Order.objects.select_for_update().get(pk=order.pk)
    if o.buyer_id!=user.pk: raise PermissionDenied()
    if o.status!='pending' or o.expires_at<=timezone.now(): raise CommerceError('Ova narudžba više nije otvorena za plaćanje.')
    if not o.checkout_started_at:
        # Commit before the network call: an ambiguous timeout must not release stock.
        o.checkout_started_at=timezone.now()
        o.expires_at=max(o.expires_at,timezone.now()+timedelta(minutes=35))
        o.save(update_fields=['checkout_started_at','expires_at'])
    return o

def start_checkout(order,user):
    prepare_checkout(order,user)
    with transaction.atomic():
        o=Order.objects.select_for_update().get(pk=order.pk)
        if o.status!='pending': raise CommerceError('Naplata se provjerava. Osvježi narudžbu.')
        api=gateway()
        if o.stripe_session_id:
            session=api.checkout.Session.retrieve(o.stripe_session_id)
            if session.status!='open': raise CommerceError('Naplata se provjerava. Osvježi narudžbu.')
            return safe_provider_url(session.url,{'checkout.stripe.com'})
        if timezone.now()-o.checkout_started_at>timedelta(hours=23):
            raise CommerceError('Nerazriješena naplata zahtijeva ručnu provjeru procesora.')
        session=api.checkout.Session.create(
            mode='payment',payment_method_types=['card'],customer_email=o.buyer.email,
            client_reference_id=str(o.pk),metadata={'order_id':str(o.pk)},
            line_items=[{'price_data':{'currency':o.currency,'unit_amount':o.total_cents,'product_data':{'name':settings.SITE_NAME+' · narudžba '+str(o.pk)[:8]}},'quantity':1}],
            payment_intent_data={'metadata':{'order_id':str(o.pk)},'transfer_group':'ORDER_'+str(o.pk)},
            success_url=settings.SITE_URL+o.get_absolute_url()+'?payment=processing',
            cancel_url=settings.SITE_URL+o.get_absolute_url(),
            expires_at=int(o.expires_at.timestamp()),
            idempotency_key='checkout-'+str(o.pk))
        o.stripe_session_id=session.id;o.save(update_fields=['stripe_session_id'])
        return safe_provider_url(session.url,{'checkout.stripe.com'})

@transaction.atomic
def cancel_pending(order,user=None,expire=False):
    o=Order.objects.select_for_update().get(pk=order.pk)
    if user and o.buyer_id!=user.pk: raise PermissionDenied()
    if o.status!='pending': raise CommerceError('Plaćenu narudžbu rješavamo kroz povrat, ne brisanje.')
    if o.stripe_session_id:
        api=gateway();session=api.checkout.Session.retrieve(o.stripe_session_id)
        if session.status=='complete':
            mark_paid(plain(session));return False
        if session.status=='open': session=api.checkout.Session.expire(o.stripe_session_id,idempotency_key='expire-'+str(o.pk))
        if session.status!='expired': raise CommerceError('Naplata nije potvrđeno istekla; zaliha ostaje rezervisana.')
    elif o.checkout_started_at:
        raise CommerceError('Ishod pokretanja naplate nije poznat. Rezervacija ostaje do potvrde procesora; ne naplaćuj ponovo.')
    return release_stock(o,'expired' if expire else 'cancelled')

@transaction.atomic
def onboarding_url(user):
    payments_ready()
    s=Seller.objects.select_for_update().get(user=user)
    if not user.email_verified or s.status!='approved': raise CommerceError('Najprije potvrda e-maila i odobrenje prodavača.')
    if settings.PAYMENTS_MODE=='live' and s.kind=='private' and not settings.PRIVATE_SELLERS_APPROVED:
        raise CommerceError('Privatni prodavači čekaju odobrenje pružaoca plaćanja.')
    api=gateway()
    if s.stripe_account_id and s.stripe_mode!=settings.PAYMENTS_MODE:
        raise CommerceError('Testni račun se ne smije koristiti za stvarne isplate. Potrebna je kontrolisana migracija.')
    if not s.stripe_account_id:
        # Self-declared seller kind is not automatically mapped to a legal business type.
        # Stripe-hosted onboarding collects and verifies the actual business/individual data.
        account=api.Account.create(country='DE',email=user.email,
            controller={'stripe_dashboard':{'type':'express'},'fees':{'payer':'application'},'losses':{'payments':'application'},'requirement_collection':'stripe'},
            capabilities={'transfers':{'requested':True}},
            metadata={'seller_id':str(s.pk)},idempotency_key='account-'+settings.PAYMENTS_MODE+'-'+str(s.pk))
        s.stripe_account_id=account.id;s.stripe_mode=settings.PAYMENTS_MODE;s.save(update_fields=['stripe_account_id','stripe_mode'])
    link=api.AccountLink.create(account=s.stripe_account_id,type='account_onboarding',refresh_url=settings.SITE_URL+'/sell/',return_url=settings.SITE_URL+'/sell/')
    return safe_provider_url(link.url,{'connect.stripe.com'})

@transaction.atomic
def refresh_seller(user):
    s=Seller.objects.select_for_update().get(user=user)
    if not s.stripe_account_id: raise CommerceError('Poveži račun za isplate.')
    account=gateway().Account.retrieve(s.stripe_account_id)
    s.stripe_ready=bool(account.details_submitted and account.payouts_enabled and plain(account.capabilities).get('transfers')=='active')
    s.save(update_fields=['stripe_ready']);return s.stripe_ready

@transaction.atomic
def prepare_transfer(part_id,actor):
    if not actor.is_staff: raise PermissionDenied()
    parent=SellerOrder.objects.get(pk=part_id).order_id
    o=Order.objects.select_for_update().get(pk=parent)
    p=SellerOrder.objects.select_for_update().select_related('seller').get(pk=part_id)
    if p.transfer_state in ('done','requested','unknown'): return p
    if o.status!='paid' or o.payment_hold or p.status!='delivered': raise CommerceError('Isplata nije dopuštena.')
    if not p.delivered_at or timezone.now()<p.delivered_at+timedelta(days=settings.PAYOUT_HOLD_DAYS): raise CommerceError('Operativni rok za pregled još traje.')
    if p.cases.filter(status='open').exists() or p.refunds.filter(status__in=['requested','pending']).exists(): raise CommerceError('Otvoren predmet ili nedovršen povrat blokira isplatu.')
    if not p.seller.stripe_ready or p.seller.status!='approved': raise CommerceError('Prodavač nije spreman.')
    if p.payable_cents<=0: raise CommerceError('Nema iznosa za isplatu.')
    p.transfer_requested_cents=p.payable_cents;p.transfer_state='requested';p.transfer_requested_at=timezone.now()
    p.save(update_fields=['transfer_requested_cents','transfer_state','transfer_requested_at'])
    audit(actor,'transfer.requested',p,amount_cents=p.transfer_requested_cents)
    return p

def transfer_part(part_id,actor):
    prepared=prepare_transfer(part_id,actor)
    if prepared.transfer_state=='done': return prepared.transfer_id
    # The request amount is committed BEFORE the network call. A timeout cannot
    # permit an intervening refund or change the amount on an idempotent retry.
    try:
        with transaction.atomic():
            o=Order.objects.select_for_update().get(pk=prepared.order_id)
            p=SellerOrder.objects.select_for_update().select_related('seller').get(pk=part_id)
            if p.transfer_state=='done': return p.transfer_id
            if not p.transfer_requested_at or timezone.now()-p.transfer_requested_at>timedelta(hours=23):
                raise CommerceError('Nerazriješena isplata zahtijeva ručnu provjeru kod procesora prije ponovnog pokušaja.')
            if o.payment_hold or p.cases.filter(status='open').exists():
                raise CommerceError('Nova prijava ili procesorski spor blokira nastavak isplate; potrebna je provjera.')
            api=gateway()
            account=api.Account.retrieve(p.seller.stripe_account_id)
            if not account.payouts_enabled or plain(account.capabilities).get('transfers')!='active': raise CommerceError('Procesor nije odobrio isplate ovom prodavaču.')
            pi=api.PaymentIntent.retrieve(o.stripe_payment_intent)
            if pi.status!='succeeded' or pi.currency!=o.currency or pi.amount_received!=o.total_cents or not pi.latest_charge: raise CommerceError('Izvor naplate nije potvrđen.')
            amount=p.transfer_requested_cents
            transfer=api.Transfer.create(amount=amount,currency=o.currency,destination=p.seller.stripe_account_id,source_transaction=pi.latest_charge,transfer_group='ORDER_'+str(o.pk),metadata={'seller_order':str(p.pk)},idempotency_key='transfer-'+str(p.pk))
            p.transfer_id=transfer.id;p.transferred_cents=amount;p.transfer_state='done'
            p.save(update_fields=['transfer_id','transferred_cents','transfer_state'])
            o.stripe_charge_id=pi.latest_charge;o.save(update_fields=['stripe_charge_id'])
            audit(actor,'transfer.confirmed_by_provider',p,transfer_id=transfer.id,amount_cents=amount)
            return transfer.id
    except Exception:
        SellerOrder.objects.filter(pk=part_id,transfer_state='requested').update(transfer_state='unknown')
        raise

@transaction.atomic
def request_refund(part_id,actor,amount):
    if not actor.is_staff: raise PermissionDenied()
    parent=SellerOrder.objects.get(pk=part_id).order_id
    o=Order.objects.select_for_update().get(pk=parent)
    p=SellerOrder.objects.select_for_update().get(pk=part_id)
    if o.status!='paid' or o.payment_hold: raise CommerceError('Povrat čeka ručnu provjeru statusa naplate/spora.')
    if p.transfer_state in ('requested','unknown'): raise CommerceError('Prvo provjeri nerazriješenu isplatu.')
    reserved=p.refunds.filter(status__in=['requested','pending']).aggregate(n=Sum('amount_cents'))['n'] or 0
    if not isinstance(amount,int) or amount<=0 or amount>p.remaining_cents-reserved:
        raise CommerceError('Povrat je izvan preostalog naplaćenog iznosa.')
    refund=Refund.objects.create(part=p,requested_by=actor,amount_cents=amount)
    audit(actor,'refund.requested',refund,amount_cents=amount)
    return refund

@transaction.atomic
def execute_refund(refund_id):
    parent=Refund.objects.select_related('part').get(pk=refund_id).part.order_id
    o=Order.objects.select_for_update().get(pk=parent)
    r=Refund.objects.select_for_update().select_related('part').get(pk=refund_id)
    if r.status in ['succeeded','failed','cancelled']: return r
    if not r.stripe_id and timezone.now()-r.created_at>timedelta(hours=23):
        raise CommerceError('Nerazriješen zahtjev je stariji od sigurnog roka ponavljanja. Potrebna je ručna provjera procesora; ne šaljemo novi povrat.')
    if r.stripe_id: response=gateway().Refund.retrieve(r.stripe_id)
    else:
        response=gateway().Refund.create(payment_intent=o.stripe_payment_intent,amount=r.amount_cents,metadata={'local_refund':str(r.pk),'seller_order':str(r.part_id)},idempotency_key='refund-'+str(r.pk))
    r.stripe_id=response.id;r.status='pending';r.save(update_fields=['stripe_id','status'])
    apply_refund(plain(response))
    r.refresh_from_db();return r

@transaction.atomic
def apply_refund(obj):
    rid=obj.get('metadata',{}).get('local_refund')
    r=Refund.objects.select_related('part').filter(pk=rid).first() if rid else Refund.objects.select_related('part').filter(stripe_id=obj.get('id')).first()
    if not r: return False
    o=Order.objects.select_for_update().get(pk=r.part.order_id)
    p=SellerOrder.objects.select_for_update().get(pk=r.part_id)
    r=Refund.objects.select_for_update().get(pk=r.pk)
    if obj.get('amount')!=r.amount_cents or obj.get('currency')!=o.currency or obj.get('payment_intent')!=o.stripe_payment_intent:
        raise CommerceError('Refund does not match immutable request')
    if r.stripe_id and r.stripe_id!=obj.get('id'): raise CommerceError('Refund ID mismatch')
    if r.status=='succeeded': return False
    status=obj.get('status')
    r.stripe_id=obj['id']
    if status=='succeeded':
        if p.refunded_cents+r.amount_cents>p.total_cents: raise CommerceError('Refund exceeds total')
        p.refunded_cents+=r.amount_cents
        p.commission_refunded_cents=(p.commission_cents*p.refunded_cents+p.total_cents//2)//p.total_cents
        p.save(update_fields=['refunded_cents','commission_refunded_cents'])
        r.status='succeeded'
        audit(None,'refund.confirmed_by_provider',r,amount_cents=r.amount_cents)
        mail('refunded-'+str(r.pk),o.buyer.email,'Povrat je obrađen',f'Za narudžbu {o.pk} obrađen je povrat od {r.amount_cents/100:.2f} EUR. Prikaz na računu zavisi od banke.')
    elif status in ['failed','canceled']:
        r.status='failed';r.failure_code=str(obj.get('failure_reason','provider_failed'))[:80]
        audit(None,'refund.failed',r)
    else: r.status='pending'
    r.save(update_fields=['stripe_id','status','failure_code'])
    return True

@transaction.atomic
def prepare_recovery(refund_id):
    parent=Refund.objects.select_related('part').get(pk=refund_id).part.order_id
    Order.objects.select_for_update().get(pk=parent)
    r=Refund.objects.select_for_update().get(pk=refund_id)
    p=SellerOrder.objects.select_for_update().get(pk=r.part_id)
    if r.recovery_id or r.status!='succeeded' or not p.transfer_id: return None
    if r.recovery_cents: return r
    if p.refunds.exclude(pk=r.pk).filter(recovery_cents__gt=0,recovery_id='').exists(): return None
    amount=p.recovery_due_cents
    if amount<=0: return None
    r.recovery_cents=amount;r.recovery_requested_at=timezone.now();r.save(update_fields=['recovery_cents','recovery_requested_at'])
    return r

def recover_refund(refund_id):
    r=prepare_recovery(refund_id)
    if not r: return False
    with transaction.atomic():
        parent=Refund.objects.select_related('part').get(pk=refund_id).part.order_id
        Order.objects.select_for_update().get(pk=parent)
        r=Refund.objects.select_for_update().get(pk=refund_id)
        p=SellerOrder.objects.select_for_update().get(pk=r.part_id)
        if r.recovery_id: return False
        if not r.recovery_requested_at or timezone.now()-r.recovery_requested_at>timedelta(hours=23):
            raise CommerceError('Potraživanje zahtijeva ručnu provjeru kod procesora prije ponovnog pokušaja.')
        rev=gateway().Transfer.create_reversal(p.transfer_id,amount=r.recovery_cents,metadata={'local_refund':str(r.pk)},idempotency_key='recovery-'+str(r.pk))
        r.recovery_id=rev.id;r.save(update_fields=['recovery_id'])
        p.recovered_cents+=r.recovery_cents;p.save(update_fields=['recovered_cents'])
        audit(None,'transfer.recovery_confirmed',r,amount_cents=r.recovery_cents)
        return True

@transaction.atomic
def process_event(event,connected=False):
    event=plain(event)
    if bool(event.get('livemode'))!=(settings.PAYMENTS_MODE=='live'): raise CommerceError('Webhook mode mismatch')
    if PaymentEvent.objects.filter(event_id=event['id']).exists(): return False
    kind=event['type'];obj=event['data']['object']
    # Connected-account events must never be accepted as platform payments.
    if kind=='account.updated':
        if not connected: return False
        Seller.objects.filter(stripe_account_id=obj['id'],stripe_mode=settings.PAYMENTS_MODE).update(stripe_ready=bool(obj.get('details_submitted') and obj.get('payouts_enabled') and obj.get('capabilities',{}).get('transfers')=='active'))
    elif connected or event.get('account'):
        raise CommerceError('Unexpected connected-account payment event')
    elif kind=='checkout.session.completed': mark_paid(obj)
    elif kind=='checkout.session.expired':
        o=Order.objects.filter(stripe_session_id=obj['id'],status='pending').first()
        if not o:
            oid=obj.get('metadata',{}).get('order_id')
            if oid:
                o=Order.objects.select_for_update().filter(pk=oid,status='pending',stripe_session_id__isnull=True).first()
                if o:
                    if obj.get('amount_total')!=o.total_cents or obj.get('currency')!=o.currency:
                        raise CommerceError('Expired checkout does not match order')
                    o.stripe_session_id=obj['id'];o.save(update_fields=['stripe_session_id'])
        if o: release_stock(o,'expired')
    elif kind in ['refund.created','refund.updated','refund.failed']: apply_refund(obj)
    elif kind in ['charge.dispute.created','charge.dispute.closed']:
        for o in Order.objects.select_for_update().filter(stripe_payment_intent=obj.get('payment_intent')):
            o.payment_hold=True;o.save(update_fields=['payment_hold'])
            audit(None,'processor.dispute_manual_review',o,event_type=kind,status=obj.get('status',''))
    elif kind=='charge.refunded':
        for o in Order.objects.select_for_update().filter(stripe_payment_intent=obj.get('payment_intent')):
            known=Refund.objects.filter(part__order=o).exclude(status__in=['failed','cancelled']).aggregate(n=Sum('amount_cents'))['n'] or 0
            if obj.get('amount_refunded',0)>known:
                o.payment_hold=True;o.save(update_fields=['payment_hold'])
                audit(None,'processor.external_refund_review',o)
    PaymentEvent.objects.create(event_id=event['id'],event_type=kind)
    return True
