import uuid
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.urls import reverse

class User(AbstractUser):
    email = models.EmailField(unique=True)
    email_verified = models.BooleanField(default=False)
    class Meta:
        constraints=[models.UniqueConstraint(Lower('email'),name='unique_email_casefold')]

class Category(models.Model):
    name=models.CharField(max_length=80)
    slug=models.SlugField(unique=True)
    symbol=models.CharField(max_length=8,default='◇')
    enabled=models.BooleanField(default=True)
    commission_bps=models.PositiveIntegerField(default=1000,validators=[MaxValueValidator(3000)])
    class Meta:
        ordering=['name']
        constraints=[models.CheckConstraint(condition=models.Q(commission_bps__lte=3000),name='category_fee_limit')]
    def __str__(self): return self.name

class Seller(models.Model):
    KINDS=[('business','Firma'),('private','Privatna osoba')]
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='seller')
    kind=models.CharField(max_length=12,choices=KINDS)
    display_name=models.CharField(max_length=100)
    description=models.TextField(max_length=3000,blank=True)
    # Business legal disclosure is public; private contact details are not copied here.
    legal_notice=models.TextField(max_length=5000,blank=True)
    return_policy=models.TextField(max_length=5000,blank=True)
    accepted_terms_version=models.CharField(max_length=50)
    status=models.CharField(max_length=12,default='pending',choices=[('pending','Na provjeri'),('approved','Odobren'),('suspended','Blokiran')])
    stripe_account_id=models.CharField(max_length=100,blank=True,unique=True,null=True)
    stripe_ready=models.BooleanField(default=False)
    stripe_mode=models.CharField(max_length=10,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.display_name
    def get_absolute_url(self): return reverse('seller_profile',args=[self.pk])

class Product(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    seller=models.ForeignKey(Seller,on_delete=models.PROTECT,related_name='products')
    category=models.ForeignKey(Category,on_delete=models.PROTECT)
    title=models.CharField(max_length=160)
    description=models.TextField(max_length=12000)
    brand=models.CharField(max_length=100,blank=True)
    condition=models.CharField(max_length=10,choices=[('new','Novo'),('used','Polovno')])
    price_cents=models.PositiveIntegerField(validators=[MinValueValidator(50),MaxValueValidator(1000000)])
    shipping_cents=models.PositiveIntegerField(default=0,validators=[MaxValueValidator(50000)])
    stock=models.PositiveIntegerField(default=1,validators=[MaxValueValidator(100000)])
    revision=models.PositiveIntegerField(default=1)
    status=models.CharField(max_length=12,default='pending',choices=[('pending','Na provjeri'),('active','Aktivan'),('paused','Pauziran'),('rejected','Odbijen')])
    safety_info=models.TextField(max_length=5000,blank=True,help_text='Applicable manufacturer/responsible-person, traceability and safety information. Must be reviewed before publication.')
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=['-created_at']
        indexes=[models.Index(fields=['status','category','created_at'])]
        constraints=[models.CheckConstraint(condition=models.Q(price_cents__gte=50,price_cents__lte=1000000),name='product_price_range'),models.CheckConstraint(condition=models.Q(shipping_cents__lte=50000),name='shipping_limit')]
    def __str__(self): return self.title
    def get_absolute_url(self): return reverse('product',args=[self.pk])
    @property
    def price(self): return Decimal(self.price_cents)/100
    @property
    def cover(self): return self.images.first()


def image_path(instance, filename): return f'products/{instance.product_id}/{uuid.uuid4().hex}.jpg'
class ProductImage(models.Model):
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='images')
    image=models.ImageField(upload_to=image_path)
    alt=models.CharField(max_length=160,blank=True)

class Wishlist(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    product=models.ForeignKey(Product,on_delete=models.CASCADE)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['user','product'],name='unique_saved_product')]

class CartLine(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='cart_lines')
    product=models.ForeignKey(Product,on_delete=models.CASCADE)
    quantity=models.PositiveIntegerField(validators=[MinValueValidator(1),MaxValueValidator(100)])
    class Meta:
        constraints=[models.UniqueConstraint(fields=['user','product'],name='unique_cart_product'),models.CheckConstraint(condition=models.Q(quantity__gte=1,quantity__lte=100),name='cart_qty_range')]

class Address(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    recipient=models.CharField(max_length=100)
    line1=models.CharField(max_length=150)
    line2=models.CharField(max_length=150,blank=True)
    postcode=models.CharField(max_length=12)
    city=models.CharField(max_length=100)
    country=models.CharField(max_length=2,default='DE')
    def __str__(self): return f'{self.recipient} · {self.city}'
    def snapshot(self): return {f:getattr(self,f) for f in ['recipient','line1','line2','postcode','city','country']}

class Order(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    buyer=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='orders')
    checkout_token=models.UUIDField(unique=True)
    status=models.CharField(max_length=18,default='pending',choices=[('pending','Čeka uplatu'),('paid','Plaćeno'),('cancelled','Otkazano'),('expired','Isteklo'),('payment_review','Provjera naplate')])
    total_cents=models.PositiveIntegerField()
    currency=models.CharField(max_length=3,default='eur')
    address=models.JSONField()
    terms_version=models.CharField(max_length=50)
    checkout_started_at=models.DateTimeField(null=True,blank=True)
    stripe_session_id=models.CharField(max_length=120,blank=True,unique=True,null=True)
    stripe_payment_intent=models.CharField(max_length=120,blank=True)
    stripe_charge_id=models.CharField(max_length=120,blank=True)
    payment_mode=models.CharField(max_length=10)
    payment_hold=models.BooleanField(default=False)
    stock_released=models.BooleanField(default=False)
    expires_at=models.DateTimeField()
    created_at=models.DateTimeField(auto_now_add=True)
    paid_at=models.DateTimeField(null=True,blank=True)
    class Meta: ordering=['-created_at']
    def __str__(self): return str(self.pk)[:8]
    def get_absolute_url(self): return reverse('order_detail',args=[self.pk])

class SellerOrder(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    order=models.ForeignKey(Order,on_delete=models.PROTECT,related_name='parts')
    seller=models.ForeignKey(Seller,on_delete=models.PROTECT,related_name='sales')
    # Immutable identity snapshots survive subsequent seller edits.
    seller_name=models.CharField(max_length=100)
    seller_kind=models.CharField(max_length=12)
    seller_legal_notice=models.TextField(blank=True)
    seller_return_policy=models.TextField(blank=True)
    goods_cents=models.PositiveIntegerField()
    shipping_cents=models.PositiveIntegerField()
    commission_cents=models.PositiveIntegerField()
    refunded_cents=models.PositiveIntegerField(default=0)
    commission_refunded_cents=models.PositiveIntegerField(default=0)
    transferred_cents=models.PositiveIntegerField(default=0)
    recovered_cents=models.PositiveIntegerField(default=0)
    transfer_id=models.CharField(max_length=120,blank=True)
    transfer_requested_cents=models.PositiveIntegerField(default=0)
    transfer_requested_at=models.DateTimeField(null=True,blank=True)
    transfer_state=models.CharField(max_length=12,default='none')
    status=models.CharField(max_length=12,default='new',choices=[('new','Za obradu'),('shipped','Poslano'),('delivered','Primljeno')])
    carrier=models.CharField(max_length=60,blank=True)
    tracking_number=models.CharField(max_length=100,blank=True)
    shipped_at=models.DateTimeField(null=True,blank=True)
    delivered_at=models.DateTimeField(null=True,blank=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['order','seller'],name='one_seller_per_order')]
    @property
    def total_cents(self): return self.goods_cents+self.shipping_cents
    @property
    def remaining_cents(self): return self.total_cents-self.refunded_cents
    @property
    def payable_cents(self): return self.total_cents-self.commission_cents-self.refunded_cents+self.commission_refunded_cents
    @property
    def recovery_due_cents(self): return max(0,self.transferred_cents-self.recovered_cents-self.payable_cents)
    def __str__(self): return f'{str(self.pk)[:8]} · {self.seller_name}'

class OrderLine(models.Model):
    part=models.ForeignKey(SellerOrder,on_delete=models.PROTECT,related_name='lines')
    product=models.ForeignKey(Product,on_delete=models.PROTECT)
    title=models.CharField(max_length=160)
    quantity=models.PositiveIntegerField()
    unit_cents=models.PositiveIntegerField()
    commission_bps=models.PositiveIntegerField()
    @property
    def total_cents(self): return self.unit_cents*self.quantity

class SupportCase(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    part=models.ForeignKey(SellerOrder,on_delete=models.PROTECT,related_name='cases')
    buyer=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    reason=models.CharField(max_length=50,choices=[('delivery','Pošiljka nije stigla'),('damaged','Oštećen artikl'),('return','Zahtjev za povrat'),('other','Drugi problem')])
    status=models.CharField(max_length=12,default='open',choices=[('open','Otvoreno'),('closed','Zatvoreno')])
    created_at=models.DateTimeField(auto_now_add=True)
    def get_absolute_url(self): return reverse('case_detail',args=[self.pk])

class CaseMessage(models.Model):
    case=models.ForeignKey(SupportCase,on_delete=models.PROTECT,related_name='messages')
    author=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    body=models.TextField(max_length=5000)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['created_at']

class Refund(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    part=models.ForeignKey(SellerOrder,on_delete=models.PROTECT,related_name='refunds')
    requested_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    amount_cents=models.PositiveIntegerField()
    status=models.CharField(max_length=14,default='requested')
    stripe_id=models.CharField(max_length=120,blank=True,unique=True,null=True)
    recovery_cents=models.PositiveIntegerField(default=0)
    recovery_id=models.CharField(max_length=120,blank=True)
    recovery_requested_at=models.DateTimeField(null=True,blank=True)
    failure_code=models.CharField(max_length=80,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)

class Review(models.Model):
    line=models.OneToOneField(OrderLine,on_delete=models.PROTECT)
    author=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    product=models.ForeignKey(Product,on_delete=models.PROTECT,related_name='reviews')
    rating=models.PositiveSmallIntegerField(validators=[MinValueValidator(1),MaxValueValidator(5)])
    body=models.TextField(max_length=2000)
    created_at=models.DateTimeField(auto_now_add=True)
    visible=models.BooleanField(default=True)
    class Meta:
        constraints=[models.CheckConstraint(condition=models.Q(rating__gte=1,rating__lte=5),name='review_rating_range')]

class ListingReport(models.Model):
    product=models.ForeignKey(Product,on_delete=models.PROTECT)
    reporter=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    body=models.TextField(max_length=3000)
    status=models.CharField(max_length=10,default='open')
    created_at=models.DateTimeField(auto_now_add=True)

class LegalPage(models.Model):
    slug=models.SlugField(unique=True)
    title=models.CharField(max_length=160)
    body=models.TextField()
    version=models.CharField(max_length=50)
    approved=models.BooleanField(default=False)
    updated_at=models.DateTimeField(auto_now=True)
    def __str__(self): return self.title

class AuditEvent(models.Model):
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True)
    action=models.CharField(max_length=100)
    object_id=models.CharField(max_length=120)
    detail=models.JSONField(default=dict)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['-created_at']

class PaymentEvent(models.Model):
    event_id=models.CharField(max_length=120,unique=True)
    event_type=models.CharField(max_length=120)
    processed_at=models.DateTimeField(auto_now_add=True)

class Outbox(models.Model):
    key=models.CharField(max_length=150,unique=True)
    recipient=models.EmailField()
    subject=models.CharField(max_length=200)
    body=models.TextField()
    attempts=models.PositiveIntegerField(default=0)
    sent_at=models.DateTimeField(null=True,blank=True)
    retry_at=models.DateTimeField(null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)

class RateBucket(models.Model):
    key=models.CharField(max_length=64,unique=True)
    count=models.PositiveIntegerField(default=0)
    expires_at=models.DateTimeField()
