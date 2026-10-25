from pathlib import Path
import os
from urllib.parse import urlparse
import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env', override=False)
def flag(name, default='0'): return os.getenv(name, default) == '1'
DEBUG = flag('DEBUG')
TESTING = flag('TESTING')
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '')
if len(SECRET_KEY) < 50:
    if DEBUG or TESTING: SECRET_KEY = 'local-development-only-' * 4
    else: raise ImproperlyConfigured('Set a private DJANGO_SECRET_KEY of at least 50 characters.')
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver' if (DEBUG or TESTING) else '').split(',') if h.strip()]
SITE_URL = os.getenv('SITE_URL', 'http://localhost:8000').rstrip('/')
if not DEBUG and not TESTING and (not SITE_URL.startswith('https://') or not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS):
    raise ImproperlyConfigured('Production needs SITE_URL=https://... and explicit ALLOWED_HOSTS.')
CSRF_TRUSTED_ORIGINS = [SITE_URL]
INSTALLED_APPS = ['django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','django_otp','django_otp.plugins.otp_totp','market']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware','whitenoise.middleware.WhiteNoiseMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.locale.LocaleMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django_otp.middleware.OTPMiddleware','market.middleware.RateLimitMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware','market.middleware.HeadersMiddleware']
ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
TEMPLATES = [{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages','market.context.site_context']}}]
DATABASES = {'default': dj_database_url.config(default='sqlite:///' + str(BASE_DIR/'development.sqlite3'), conn_max_age=60, conn_health_checks=True)}
if not (DEBUG or TESTING) and DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
    raise ImproperlyConfigured('PostgreSQL is required in production; SQLite is only for local tests.')
AUTH_USER_MODEL = 'market.User'
AUTH_PASSWORD_VALIDATORS = [
 {'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
 {'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator','OPTIONS':{'min_length':12}},
 {'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},
 {'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LOGIN_URL='/account/login/'
LOGIN_REDIRECT_URL='/account/'
LOGOUT_REDIRECT_URL='/'
LANGUAGE_CODE='bs'
LANGUAGES=[('bs','Bosanski'),('de','Deutsch'),('en','English')]
TIME_ZONE='Europe/Berlin'
USE_I18N=True
USE_TZ=True
STATIC_URL='/static/'
STATIC_ROOT=BASE_DIR/'staticfiles'
STATICFILES_DIRS=[BASE_DIR/'static']
MEDIA_URL='/media/'
MEDIA_ROOT=Path(os.getenv('MEDIA_ROOT', str(BASE_DIR/'media')))
STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'whitenoise.storage.CompressedManifestStaticFilesStorage'}}
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SECURE=not (DEBUG or TESTING)
CSRF_COOKIE_SECURE=not (DEBUG or TESTING)
SESSION_COOKIE_SAMESITE='Lax'
SESSION_COOKIE_AGE=86400
SECURE_SSL_REDIRECT=not (DEBUG or TESTING)
SECURE_HSTS_SECONDS=31536000 if not (DEBUG or TESTING) else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS=False
SECURE_HSTS_PRELOAD=False
SECURE_CONTENT_TYPE_NOSNIFF=True
X_FRAME_OPTIONS='DENY'
TRUST_PROXY=flag('TRUST_PROXY')
if TRUST_PROXY: SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https')
DATA_UPLOAD_MAX_MEMORY_SIZE=7*1024*1024
FILE_UPLOAD_MAX_MEMORY_SIZE=6*1024*1024
EMAIL_BACKEND=os.getenv('EMAIL_BACKEND','django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST=os.getenv('EMAIL_HOST','')
EMAIL_PORT=int(os.getenv('EMAIL_PORT','587'))
EMAIL_HOST_USER=os.getenv('EMAIL_HOST_USER','')
EMAIL_HOST_PASSWORD=os.getenv('EMAIL_HOST_PASSWORD','')
EMAIL_USE_TLS=flag('EMAIL_USE_TLS','1')
EMAIL_TIMEOUT=10
DEFAULT_FROM_EMAIL=os.getenv('DEFAULT_FROM_EMAIL','no-reply@localhost')
SUPPORT_EMAIL=os.getenv('SUPPORT_EMAIL','')
SITE_NAME=os.getenv('SITE_NAME','Zadenvo')
PAYMENTS_MODE=os.getenv('PAYMENTS_MODE','disabled')
if PAYMENTS_MODE not in ('disabled','test','live'): raise ImproperlyConfigured('Invalid PAYMENTS_MODE')
STRIPE_SECRET_KEY=os.getenv('STRIPE_SECRET_KEY','')
STRIPE_WEBHOOK_SECRET=os.getenv('STRIPE_WEBHOOK_SECRET','')
STRIPE_CONNECT_WEBHOOK_SECRET=os.getenv('STRIPE_CONNECT_WEBHOOK_SECRET','')
STRIPE_API_VERSION='2025-02-24.acacia'
PROVIDER_APPROVED=flag('PROVIDER_APPROVED')
PRIVATE_SELLERS_APPROVED=flag('PRIVATE_SELLERS_APPROVED')
LIVE_APPROVED=flag('LIVE_APPROVED')
REGISTRATION_OPEN=flag('REGISTRATION_OPEN','1' if (DEBUG or TESTING) else '0')
ADMIN_OTP_REQUIRED=not (DEBUG or TESTING)
PAYOUT_HOLD_DAYS=int(os.getenv('PAYOUT_HOLD_DAYS','7'))
# Only DE is launch-configured. Do not silently enable cross-border tax/currency handling.
MARKET_COUNTRY='DE'
MARKET_CURRENCY='eur'
RATE_LIMIT_ENABLED=not TESTING
LOGGING={'version':1,'disable_existing_loggers':False,'handlers':{'console':{'class':'logging.StreamHandler'}},'root':{'handlers':['console'],'level':'WARNING'}}
