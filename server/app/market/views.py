import json,uuid,logging,hashlib
from functools import wraps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import PermissionDenied,ValidationError
from django.db import transaction,IntegrityError
from django.db.models import Q,Avg,Sum
from django.http import HttpResponse,JsonResponse,Http404
from django.shortcuts import render,redirect,get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST,require_GET
import stripe
from .models import *
from .forms import *
from .services import *
from . import payments
logger=logging.getLogger(__name__)

def page(request,template,**kwargs): return render(request,'market/'+template,kwargs)
def friendly_error(request,exc):
    logger.warning('Marketplace operation failed: %s',type(exc).__name__)
    messages.error(request,str(exc) if isinstance(exc,(CommerceError,ValidationError)) else 'Usluga trenutno nije dostupna. Novac nije označen kao naplaćen. Pokušaj ponovo ili kontaktiraj podršku.')

def staff_only(view):
    @wraps(view)
    @login_required
    def wrapper(request,*a,**kw):
        if not request.user.is_staff: raise PermissionDenied()
        if settings.ADMIN_OTP_REQUIRED and not request.user.is_verified(): return redirect('/manage/login/?next='+request.path)
        return view(request,*a,**kw)
    return wrapper

def verified(view):
    @wraps(view)
    @login_required
    def wrapper(request,*a,**kw):
        if not request.user.email_verified:
            messages.warning(request,'Prvo potvrdi svoju e-mail adresu.');return redirect('account')
        return view(request,*a,**kw)
    return wrapper

@require_GET
def home(request):
    products=visible_products()
    query=request.GET.get('q','').strip()[:150]
    if query: products=products.filter(Q(title__icontains=query)|Q(brand__icontains=query)|Q(description__icontains=query))
    cat=request.GET.get('category','')[:100]
    if cat: products=products.filter(category__slug=cat)
    kind=request.GET.get('seller','')
    if kind in ('private','business'): products=products.filter(seller__kind=kind)
    condition=request.GET.get('condition','')
    if condition in ('new','used'): products=products.filter(condition=condition)
    for key,lookup in [('min','price_cents__gte'),('max','price_cents__lte')]:
        val=request.GET.get(key,'')
        if val:
            try: products=products.filter(**{lookup:cents(val,True)})
            except ValidationError: pass
    sort=request.GET.get('sort','new')
    products=products.order_by({'price':'price_cents','price-desc':'-price_cents','new':'-created_at'}.get(sort,'-created_at'))
    from django.core.paginator import Paginator
    pagination=Paginator(products,24).get_page(request.GET.get('page',1))
    params=request.GET.copy();params.pop('page',None)
    return page(request,'catalog.html',products=pagination,query=query,selected_category=cat,selected_kind=kind,selected_condition=condition,sort=sort,filter_query=params.urlencode())

@require_GET
def product(request,pk):
    p=get_object_or_404(visible_products(),pk=pk)
    reviews=p.reviews.filter(visible=True).select_related('author')
    return page(request,'product.html',product=p,reviews=reviews[:20],rating=reviews.aggregate(n=Avg('rating'))['n'],related=visible_products().filter(category=p.category).exclude(pk=pk)[:4])

@require_GET
def seller_profile(request,pk):
    seller=get_object_or_404(Seller,status='approved',pk=pk)
    return page(request,'seller_profile.html',seller=seller,products=visible_products().filter(seller=seller)[:100])

def signup(request):
    if not settings.REGISTRATION_OPEN: return page(request,'notice.html',title='Registracije još nisu otvorene',text='Platforma se priprema za pokretanje. Ne prikupljamo javne prijave dok uslovi i postavke nisu završeni.')
    form=SignupForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        try:
            with transaction.atomic():
                user=form.save();queue_verification(user);audit(user,'account.created',user)
        except IntegrityError:
            form.add_error(None,'Korisničko ime ili e-mail nisu dostupni.')
        else:
            login(request,user);messages.success(request,'Račun je napravljen. Potvrda adrese je stavljena u red za slanje e-maila.');return redirect('account')
    return page(request,'form.html',title='Napravi svoj račun',subtitle='Jedan račun za kupovinu i prijavu za prodaju.',form=form,button='Napravi račun')

def queue_verification(user):
    token=signing.dumps({'id':user.pk,'email':user.email,'password':hashlib.sha256(user.password.encode()).hexdigest()},salt='verify-email')
    url=settings.SITE_URL+reverse('verify_email',args=[token])
    mail('verify-'+str(user.pk)+'-'+uuid.uuid4().hex,user.email,'Potvrdi svoju e-mail adresu','Potvrdi adresu u naredna 24 sata: '+url)

@login_required
def account(request):
    return page(request,'account.html',addresses=Address.objects.filter(user=request.user),recent=request.user.orders.all()[:8])

@login_required
@require_POST
def resend_verification(request):
    if not request.user.email_verified:
        if not Outbox.objects.filter(recipient=request.user.email,key__startswith='verify-',created_at__gte=timezone.now()-__import__('datetime').timedelta(minutes=5)).exists(): queue_verification(request.user)
    messages.info(request,'Ako je potvrda potrebna, poruka je u redu za slanje.');return redirect('account')

def verify_email(request,token):
    try:
        data=signing.loads(token,salt='verify-email',max_age=86400)
        user=User.objects.get(pk=data['id'],email=data['email'])
        if data.get('password')!=hashlib.sha256(user.password.encode()).hexdigest(): raise signing.BadSignature()
    except (signing.BadSignature,User.DoesNotExist,KeyError,ValueError):
        return page(request,'notice.html',title='Veza nije važeća',text='Zatraži novu potvrdu u svom računu.')
    if request.method=='POST':
        user.email_verified=True;user.save(update_fields=['email_verified']);audit(user,'email.verified',user)
        messages.success(request,'E-mail adresa je potvrđena.');return redirect('account')
    return page(request,'verify.html')

@login_required
def address_add(request):
    form=AddressForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        address=form.save(commit=False);address.user=request.user;address.country='DE';address.save()
        messages.success(request,'Adresa je sačuvana.');return redirect('cart')
    return page(request,'form.html',title='Adresa dostave',subtitle='Početno tržište: Njemačka.',form=form,button='Sačuvaj adresu')

@login_required
@require_POST
def address_delete(request,pk):
    get_object_or_404(Address,user=request.user,pk=pk).delete();return redirect('account')

@login_required
def wishlist(request):
    ids=Wishlist.objects.filter(user=request.user).values_list('product_id',flat=True)
    return page(request,'wishlist.html',products=visible_products().filter(pk__in=ids))

@login_required
@require_POST
def wishlist_toggle(request,pk):
    p=get_object_or_404(visible_products(),pk=pk)
    obj,created=Wishlist.objects.get_or_create(user=request.user,product=p)
    if not created: obj.delete()
    return redirect('wishlist')

@login_required
def cart(request):
    try: quote=cart_quote(request.user)
    except CommerceError as exc:
        return page(request,'cart.html',quote=None,error=str(exc),lines=request.user.cart_lines.select_related('product'))
    token=request.session.setdefault('checkout_token',str(uuid.uuid4()))
    form=CheckoutForm(user=request.user,initial={'token':token,'quote':quote_token(request.user,quote)})
    return page(request,'cart.html',quote=quote,form=form,lines=request.user.cart_lines.select_related('product'))

@login_required
@require_POST
def cart_update(request,pk):
    try: update_cart(request.user,pk,int(request.POST.get('quantity','1')),request.POST.get('action')=='add')
    except (CommerceError,ValueError) as exc: friendly_error(request,CommerceError(str(exc)))
    request.session['checkout_token']=str(uuid.uuid4());return redirect('cart')

@login_required
@require_POST
def cart_remove(request,pk):
    # Allow removal even if the product is no longer public.
    with transaction.atomic():
        User.objects.select_for_update().get(pk=request.user.pk)
        CartLine.objects.filter(user=request.user,product_id=pk).delete()
    request.session['checkout_token']=str(uuid.uuid4());return redirect('cart')

@verified
@require_POST
def checkout(request):
    form=CheckoutForm(request.POST,user=request.user)
    if not form.is_valid():
        messages.error(request,'Odaberi svoju adresu i prihvati uslove.');return redirect('cart')
    o=None
    try:
        o=create_order(request.user,form.cleaned_data['address'],form.cleaned_data['token'],form.cleaned_data['quote'])
        request.session['checkout_token']=str(uuid.uuid4())
        return redirect(payments.start_checkout(o,request.user))
    except (CommerceError,stripe.StripeError,ValidationError) as exc:
        friendly_error(request,exc)
        return redirect(o.get_absolute_url() if o else 'cart')

@login_required
def order_list(request): return page(request,'orders.html',orders=request.user.orders.all()[:100])

@login_required
def order_detail(request,pk):
    o=get_object_or_404(Order.objects.prefetch_related('parts__lines__product','parts__cases'),buyer=request.user,pk=pk)
    return page(request,'order.html',order=o)

@login_required
@require_POST
def retry_payment(request,pk):
    o=get_object_or_404(Order,buyer=request.user,pk=pk)
    try: return redirect(payments.start_checkout(o,request.user))
    except (CommerceError,stripe.StripeError) as exc: friendly_error(request,exc)
    return redirect(o)

@login_required
@require_POST
def cancel_order(request,pk):
    o=get_object_or_404(Order,buyer=request.user,pk=pk)
    try: payments.cancel_pending(o,request.user);messages.info(request,'Status narudžbe je ažuriran.')
    except (CommerceError,stripe.StripeError) as exc: friendly_error(request,exc)
    return redirect(o)

@login_required
@require_POST
def receive(request,pk):
    p=get_object_or_404(SellerOrder,pk=pk,order__buyer=request.user)
    try: receive_part(request.user,p.pk)
    except CommerceError as exc: friendly_error(request,exc)
    return redirect(p.order)

@verified
def seller_apply(request):
    if Seller.objects.filter(user=request.user).exists(): return redirect('seller_dashboard')
    form=SellerForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        s=form.save(commit=False);s.user=request.user
        terms=LegalPage.objects.filter(slug='seller-terms',approved=True).first()
        if settings.PAYMENTS_MODE=='live' and not terms:
            form.add_error(None,'Uslovi za prodavače još nisu odobreni.')
        else:
            s.accepted_terms_version=terms.version if terms else 'prelaunch-unapproved';s.save();audit(request.user,'seller.applied',s)
            messages.success(request,'Prijava je sačuvana. Administracija provjerava podatke.');return redirect('seller_dashboard')
    return page(request,'form.html',title='Otvori svoju prodavnicu',subtitle='Za firme i privatne prodavače. Prijava ne znači automatsko odobrenje prodaje ili isplata.',form=form,button='Pošalji prijavu')

@login_required
def seller_dashboard(request):
    s=Seller.objects.filter(user=request.user).first()
    if not s: return redirect('seller_apply')
    return page(request,'seller_dashboard.html',seller=s,products=s.products.all().prefetch_related('images'),sales=s.sales.filter(order__status='paid').select_related('order').order_by('-order__created_at')[:100])

@verified
def product_edit(request,pk=None):
    s=get_object_or_404(Seller,user=request.user)
    if s.status!='approved':
        messages.error(request,'Objavljivanje je dostupno nakon odobrenja prodavača.');return redirect('seller_dashboard')
    p=get_object_or_404(Product,seller=s,pk=pk) if pk else None
    form=ProductForm(request.POST or None,request.FILES or None,instance=p)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            if p:
                p=Product.objects.select_for_update().get(pk=p.pk,seller=s)
                try:
                    snapshot=signing.loads(form.cleaned_data.get('edit_token',''),salt='product-edit',max_age=7200)
                except signing.BadSignature: snapshot=None
                if snapshot!={'id':str(p.pk),'revision':p.revision,'stock':p.stock}:
                    messages.error(request,'Artikl ili zaliha su se promijenili. Ponovo otvori uređivanje i provjeri dostupne komade.')
                    return redirect('product_edit',pk=p.pk)
                # Form exposed no seller/status/payment fields.
                for f in ProductForm.Meta.fields: setattr(p,f,form.cleaned_data[f])
            else: p=form.save(commit=False);p.seller=s
            p.price_cents=form.cleaned_data['price'];p.shipping_cents=form.cleaned_data['shipping'];p.status='pending';p.revision+=1;p.save()
            if form.cleaned_data.get('image') and p.images.count()<5:
                ProductImage.objects.create(product=p,image=form.cleaned_data['image'],alt=p.title)
            audit(request.user,'product.submitted',p)
        messages.success(request,'Artikl je sačuvan i čeka provjeru.');return redirect('seller_dashboard')
    return page(request,'form.html',title='Uredi artikl' if p else 'Dodaj novi artikl',subtitle='Promjene se provjeravaju prije javne objave. Unosi samo artikle koje smiješ prodavati.',form=form,button='Sačuvaj i pošalji na provjeru',multipart=True)

@login_required
@require_POST
@transaction.atomic
def product_pause(request,pk):
    p=get_object_or_404(Product.objects.select_for_update(),pk=pk,seller__user=request.user)
    p.status='paused';p.revision+=1;p.save(update_fields=['status','revision']);audit(request.user,'product.paused',p)
    return redirect('seller_dashboard')

@verified
@require_POST
def seller_connect(request):
    try: return redirect(payments.onboarding_url(request.user))
    except (CommerceError,stripe.StripeError,Seller.DoesNotExist) as exc: friendly_error(request,exc)
    return redirect('seller_dashboard')

@verified
@require_POST
def seller_refresh(request):
    try: payments.refresh_seller(request.user);messages.info(request,'Status računa je provjeren kod procesora.')
    except (CommerceError,stripe.StripeError,Seller.DoesNotExist) as exc: friendly_error(request,exc)
    return redirect('seller_dashboard')

@login_required
def seller_order(request,pk):
    p=get_object_or_404(SellerOrder.objects.select_related('order','seller').prefetch_related('lines'),pk=pk,seller__user=request.user,order__status='paid')
    form=ShipForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        try: ship_part(request.user,p.pk,form.cleaned_data['carrier'],form.cleaned_data['tracking']);return redirect('seller_order',pk=pk)
        except CommerceError as exc: friendly_error(request,exc)
    return page(request,'seller_order.html',part=p,form=form)

@login_required
def case_open(request,pk):
    p=get_object_or_404(SellerOrder,pk=pk,order__buyer=request.user)
    form=CaseForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        try: return redirect(open_case(request.user,p.pk,form.cleaned_data['reason'],form.cleaned_data['body']))
        except CommerceError as exc: friendly_error(request,exc)
    return page(request,'form.html',title='Pomoć uz narudžbu',subtitle='Poruke i zahtjev vidljivi su samo kupcu, ovom prodavaču i podršci.',form=form,button='Pošalji zahtjev')

@login_required
def case_detail(request,pk):
    case=get_object_or_404(SupportCase.objects.select_related('part__seller'),pk=pk)
    if not can_case(request.user,case): raise Http404()
    if request.user.is_staff and settings.ADMIN_OTP_REQUIRED and not request.user.is_verified(): return redirect('/manage/login/?next='+request.path)
    form=MessageForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        if case.status!='open': messages.error(request,'Predmet je zatvoren.')
        else:
            CaseMessage.objects.create(case=case,author=request.user,body=form.cleaned_data['body']);audit(request.user,'case.message',case)
            return redirect(case)
    return page(request,'case.html',case=case,form=form,history=case.messages.select_related('author'))

@login_required
def review(request,pk):
    line=get_object_or_404(OrderLine.objects.select_related('part__order','product'),pk=pk,part__order__buyer=request.user)
    form=ReviewForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        try: make_review(request.user,line,form.cleaned_data['rating'],form.cleaned_data['body']);return redirect(line.product)
        except CommerceError as exc: friendly_error(request,exc)
    return page(request,'form.html',title='Ocijeni kupljeni artikl',subtitle=line.title,form=form,button='Objavi ocjenu')

@login_required
def report(request,pk):
    p=get_object_or_404(visible_products(),pk=pk)
    form=MessageForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        ListingReport.objects.create(product=p,reporter=request.user,body=form.cleaned_data['body']);audit(request.user,'listing.reported',p)
        messages.success(request,'Prijava je sačuvana za pregled podrške.');return redirect(p)
    return page(request,'form.html',title='Prijavi oglas',subtitle='Navedi konkretan problem ili razlog prijave.',form=form,button='Pošalji prijavu')

@staff_only
def operations(request):
    return page(request,'ops.html',sellers=Seller.objects.filter(status='pending'),pending=Product.objects.filter(status='pending').select_related('seller','category'),parts=SellerOrder.objects.filter(order__status='paid').select_related('order','seller').order_by('-order__created_at')[:100],cases=SupportCase.objects.filter(status='open').select_related('part'),reports=ListingReport.objects.filter(status='open').select_related('product'),refunds=Refund.objects.exclude(status='failed').select_related('part')[:100])

@staff_only
@require_POST
def approve_seller(request,pk):
    s=get_object_or_404(Seller,pk=pk)
    if not s.user.email_verified: messages.error(request,'E-mail prodavača nije potvrđen.')
    elif s.kind=='business' and not s.legal_notice.strip(): messages.error(request,'Nedostaju podaci firme.')
    else: s.status='approved';s.save(update_fields=['status']);audit(request.user,'seller.approved',s)
    return redirect('operations')

@staff_only
@require_POST
@transaction.atomic
def approve_product(request,pk):
    p=get_object_or_404(Product.objects.select_for_update(),pk=pk)
    if request.POST.get('revision')!=str(p.revision):
        messages.error(request,'Oglas je promijenjen. Pregledaj novu verziju prije odobravanja.');return redirect('operations')
    if p.seller.status!='approved' or not p.images.exists(): messages.error(request,'Potrebni su odobren prodavač i fotografija artikla.')
    elif request.POST.get('reviewed')!='yes': messages.error(request,'Potvrdi provjeru prava prodaje i sigurnosnih podataka.')
    else: p.status='active';p.save(update_fields=['status']);audit(request.user,'product.approved',p)
    return redirect('operations')

@staff_only
@require_POST
def close_case(request,pk):
    c=get_object_or_404(SupportCase,pk=pk);c.status='closed';c.save(update_fields=['status']);audit(request.user,'case.closed',c)
    return redirect('operations')

@staff_only
def refund_part(request,pk):
    p=get_object_or_404(SellerOrder,pk=pk)
    form=RefundForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        try:
            r=payments.request_refund(p.pk,request.user,form.cleaned_data['amount'])
            payments.execute_refund(r.pk)
            messages.info(request,'Zahtjev za povrat je obrađen. Konačni status dolazi od procesora.')
            return redirect('operations')
        except (CommerceError,stripe.StripeError) as exc: friendly_error(request,exc)
    return page(request,'form.html',title='Povrat kupcu',subtitle='Dio narudžbe '+str(p.pk)+' · preostalo '+money(p.remaining_cents),form=form,button='Zatraži povrat kod procesora')

@staff_only
@require_POST
def transfer_part(request,pk):
    try: payments.transfer_part(pk,request.user);messages.success(request,'Procesor je potvrdio transfer. Transfer na povezani račun nije potvrda bankovne isplate.')
    except (CommerceError,stripe.StripeError) as exc: friendly_error(request,exc)
    return redirect('operations')

@require_GET
def legal(request,slug):
    doc=get_object_or_404(LegalPage,slug=slug,approved=True)
    return page(request,'legal.html',doc=doc)

@require_GET
def health(request):
    from django.db import connection
    try:
        with connection.cursor() as cursor: cursor.execute('SELECT 1');cursor.fetchone()
        return JsonResponse({'status':'ok'})
    except Exception: return JsonResponse({'status':'unavailable'},status=503)

@csrf_exempt
@require_POST
def webhook(request,connected=False):
    if len(request.body)>1024*1024: return HttpResponse(status=413)
    secret=settings.STRIPE_CONNECT_WEBHOOK_SECRET if connected else settings.STRIPE_WEBHOOK_SECRET
    if not secret or settings.PAYMENTS_MODE=='disabled': return HttpResponse(status=503)
    try:
        event=stripe.Webhook.construct_event(request.body,request.headers.get('Stripe-Signature',''),secret,tolerance=300)
        payments.process_event(event,connected=connected)
    except (ValueError,stripe.SignatureVerificationError,KeyError,CommerceError,ValidationError): return HttpResponse(status=400)
    except Exception:
        logger.exception('Webhook processing failed');return HttpResponse(status=500)
    return HttpResponse(status=200)
