"""Browser acceptance against an isolated CI database only; never run on production."""
import os,sys,json,re
from pathlib import Path
BASE_DIR=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE_DIR/'app'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
# Playwright's sync loop and the ORM are used only in this isolated test harness.
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE']='true'
import django;django.setup()
from django.conf import settings
assert settings.DEBUG and settings.TESTING, 'This harness is only for isolated testing.'
assert settings.DATABASES['default']['NAME'].endswith('_ci'), 'Use a disposable *_ci database.'
from market.models import User,Seller,Product,Outbox,Category
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright
BASE='http://127.0.0.1:8000';PASSWORD='Browser-local-only-847!Strong'
OUT=BASE_DIR/'engineering/browser';OUT.mkdir(exist_ok=True)
report={'checks':[],'errors':[],'scope':'Local browser + PostgreSQL; no external payment or SMTP calls.'}
def checked(name,ok=True):
    if not ok: raise AssertionError(name)
    report['checks'].append(name)
def login(page,username):
    page.goto(BASE+'/account/login/');page.locator('#id_username').fill(username);page.locator('#id_password').fill(PASSWORD);page.get_by_role('button',name='Prijavi se',exact=True).click();page.wait_for_url('**/account/')
def signup(page,name):
    page.goto(BASE+'/account/signup/');page.locator('#id_username').fill(name);page.locator('#id_email').fill(name+'@example.invalid');page.locator('#id_password1').fill(PASSWORD);page.locator('#id_password2').fill(PASSWORD);page.locator('#id_accept').check();page.get_by_role('button',name='Napravi račun',exact=True).click();page.wait_for_url('**/account/')
    checked('HTTP signup saved to database: '+name,User.objects.filter(username=name).exists())
    msg=Outbox.objects.filter(recipient=name+'@example.invalid',key__startswith='verify-').latest('created_at')
    page.goto(re.search(r'http://\S+',msg.body).group());page.locator('main form button').click();page.wait_for_url('**/account/')
    checked('Signed email verification: '+name,User.objects.get(username=name).email_verified)
assert not User.objects.filter(username__startswith='qa_').exists(), 'The test needs a clean database.'
User.objects.create_user('qa_operator','qa_operator@example.invalid',PASSWORD,is_staff=True,email_verified=True)
img=Image.new('RGB',(720,540),'#e9e4f5');d=ImageDraw.Draw(img);d.rounded_rectangle((100,140,620,360),30,fill='#313147');d.text((210,405),'QA TEST IMAGE - NOT A LIVE OFFER',fill='#313147');img.save('/tmp/marketplace-test-upload.png')
try:
    with sync_playwright() as pw:
        b=pw.chromium.launch(headless=True,args=['--disable-dev-shm-usage'])
        context=b.new_context(viewport={'width':1440,'height':1000});buyer=context.new_page();buyer.on('pageerror',lambda e:report['errors'].append(str(e)))
        response=buyer.goto(BASE);checked('Server catalog HTTP 200',response.status==200);checked('Original catalog hero',buyer.locator('h1').inner_text().startswith('Pronađi'))
        buyer.screenshot(path=str(OUT/'home.png'),full_page=True)
        checked('Desktop fits viewport',buyer.evaluate('document.documentElement.scrollWidth<=innerWidth'))
        signup(buyer,'qa_buyer')
        seller_ctx=b.new_context(viewport={'width':1440,'height':1000});seller=seller_ctx.new_page();signup(seller,'qa_seller')
        seller.goto(BASE+'/sell/apply/');seller.locator('#id_kind').select_option('private');seller.locator('#id_display_name').fill('QA test prodavnica');seller.locator('#id_description').fill('Testni zapis isključivo u izolovanoj bazi.');seller.locator('#id_return_policy').fill('QA test uslovi, nisu javna ponuda.');seller.locator('#id_accept').check();seller.get_by_role('button',name='Pošalji prijavu').click();seller.wait_for_url('**/sell/')
        checked('Private seller awaits moderation',Seller.objects.get(user__username='qa_seller').status=='pending')
        ops_ctx=b.new_context(viewport={'width':1440,'height':1000});ops=ops_ctx.new_page();login(ops,'qa_operator');ops.goto(BASE+'/ops/');ops.get_by_role('button',name='Odobri prodavački profil').click()
        checked('Staff approval persisted',Seller.objects.get(user__username='qa_seller').status=='approved')
        seller.goto(BASE+'/sell/product/add/');seller.locator('#id_title').fill('QA tastatura — testna ponuda');seller.locator('#id_category').select_option(str(Category.objects.filter(enabled=True).first().pk));seller.locator('#id_description').fill('Artikl za automatsku provjeru stvarnog serverskog toka.');seller.locator('#id_brand').fill('QA');seller.locator('#id_condition').select_option('new');seller.locator('#id_stock').fill('3');seller.locator('#id_safety_info').fill('Testni zapis, nije roba za stvarnu prodaju.');seller.locator('#id_price').fill('75.00');seller.locator('#id_shipping').fill('5.00');seller.locator('#id_image').set_input_files('/tmp/marketplace-test-upload.png');seller.get_by_role('button',name='Sačuvaj i pošalji na provjeru').click();seller.wait_for_url('**/sell/')
        product=Product.objects.get(title='QA tastatura — testna ponuda');checked('Product and photo persisted, pending moderation',product.status=='pending' and product.images.count()==1)
        checked('Unapproved product is hidden',buyer.goto(BASE+product.get_absolute_url()).status==404)
        ops.goto(BASE+'/ops/');ops.locator('input[name=reviewed]').check();ops.get_by_role('button',name='Odobri oglas').click();product.refresh_from_db();checked('Staff activates reviewed listing',product.status=='active')
        checked('Independent buyer sees shared listing',buyer.goto(BASE+product.get_absolute_url()).status==200)
        buyer.get_by_role('button',name='Dodaj u korpu').click();buyer.wait_for_url('**/cart/');checked('Server calculated total','80.00' in buyer.inner_text('main') or '80,00' in buyer.inner_text('main'))
        buyer.get_by_role('link',name='Dodaj adresu dostave').click();buyer.locator('#id_recipient').fill('QA buyer');buyer.locator('#id_line1').fill('QA example street 1');buyer.locator('#id_postcode').fill('10115');buyer.locator('#id_city').fill('Berlin');buyer.locator('main button').click();buyer.goto(BASE+'/cart/')
        checked('Address persisted',buyer.locator('#id_address option').count()==2)
        checked('Unconfigured payment remains blocked',buyer.get_by_role('button',name='Naruči i nastavi na plaćanje').is_disabled())
        buyer.screenshot(path=str(OUT/'cart.png'),full_page=True)
        buyer.goto(BASE+product.get_absolute_url());buyer.get_by_role('button',name='♡ Sačuvaj artikl').click();buyer.wait_for_url('**/saved/');checked('Wishlist persisted',buyer.get_by_text(product.title,exact=True).count()>0)
        checked('Buyer cannot enter administration',buyer.goto(BASE+'/ops/').status==403)
        seller.goto(BASE+'/sell/');seller.screenshot(path=str(OUT/'seller.png'),full_page=True)
        buyer.goto(BASE+'/?q=QA');checked('Search uses shared database',buyer.locator('main').get_by_text(product.title,exact=True).count()>0)
        buyer.goto(BASE+'/?q=DoesNotExist');checked('No fabricated search results',buyer.get_by_role('heading',name='Nema artikala za ovu pretragu').count()==1)
        ops.goto(BASE+'/ops/');ops.screenshot(path=str(OUT/'operations.png'),full_page=True)
        mobile_ctx=b.new_context(viewport={'width':390,'height':844},is_mobile=True,device_scale_factor=1);mobile=mobile_ctx.new_page();mobile.goto(BASE);mobile.screenshot(path=str(OUT/'mobile.png'),full_page=True)
        checked('Mobile fits viewport',mobile.evaluate('document.documentElement.scrollWidth<=innerWidth'))
        checked('No browser script errors',not report['errors']);report['browser']=b.version;report['status']='passed';b.close()
except Exception as exc:
    report['status']='failed';report['failure']=str(exc);raise
finally:
    report['count']=len(report['checks']);(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
