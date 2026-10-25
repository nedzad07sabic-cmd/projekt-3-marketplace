from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth
from django.urls import path
from django_otp.admin import OTPAdminSite
from market import views as v
if settings.ADMIN_OTP_REQUIRED: admin.site.__class__=OTPAdminSite
urlpatterns=[
 path('',v.home,name='home'),path('product/<uuid:pk>/',v.product,name='product'),path('shops/<uuid:pk>/',v.seller_profile,name='seller_profile'),
 path('account/',v.account,name='account'),path('account/signup/',v.signup,name='signup'),
 path('account/login/',auth.LoginView.as_view(template_name='registration/login.html'),name='login'),path('account/logout/',auth.LogoutView.as_view(),name='logout'),
 path('account/verify/<str:token>/',v.verify_email,name='verify_email'),path('account/resend/',v.resend_verification,name='resend_verification'),
 path('account/reset/',auth.PasswordResetView.as_view(template_name='registration/password_reset_form.html',email_template_name='registration/password_reset_email.txt',subject_template_name='registration/password_reset_subject.txt'),name='password_reset'),
 path('account/reset/sent/',auth.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'),name='password_reset_done'),
 path('account/reset/<uidb64>/<token>/',auth.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'),name='password_reset_confirm'),
 path('account/reset/complete/',auth.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'),name='password_reset_complete'),
 path('account/address/add/',v.address_add,name='address_add'),path('account/address/<int:pk>/delete/',v.address_delete,name='address_delete'),
 path('saved/',v.wishlist,name='wishlist'),path('saved/<uuid:pk>/',v.wishlist_toggle,name='wishlist_toggle'),
 path('cart/',v.cart,name='cart'),path('cart/<uuid:pk>/update/',v.cart_update,name='cart_update'),path('cart/<uuid:pk>/remove/',v.cart_remove,name='cart_remove'),path('checkout/',v.checkout,name='checkout'),
 path('orders/',v.order_list,name='orders'),path('orders/<uuid:pk>/',v.order_detail,name='order_detail'),path('orders/<uuid:pk>/pay/',v.retry_payment,name='retry_payment'),path('orders/<uuid:pk>/cancel/',v.cancel_order,name='cancel_order'),path('received/<uuid:pk>/',v.receive,name='receive'),
 path('sell/',v.seller_dashboard,name='seller_dashboard'),path('sell/apply/',v.seller_apply,name='seller_apply'),path('sell/product/add/',v.product_edit,name='product_add'),path('sell/product/<uuid:pk>/',v.product_edit,name='product_edit'),path('sell/product/<uuid:pk>/pause/',v.product_pause,name='product_pause'),path('sell/connect/',v.seller_connect,name='seller_connect'),path('sell/connect/refresh/',v.seller_refresh,name='seller_refresh'),path('sell/order/<uuid:pk>/',v.seller_order,name='seller_order'),
 path('cases/open/<uuid:pk>/',v.case_open,name='case_open'),path('cases/<uuid:pk>/',v.case_detail,name='case_detail'),path('review/<int:pk>/',v.review,name='review'),path('report/<uuid:pk>/',v.report,name='report'),
 path('ops/',v.operations,name='operations'),path('ops/seller/<uuid:pk>/approve/',v.approve_seller,name='approve_seller'),path('ops/product/<uuid:pk>/approve/',v.approve_product,name='approve_product'),path('ops/case/<uuid:pk>/close/',v.close_case,name='close_case'),path('ops/refund/<uuid:pk>/',v.refund_part,name='refund_part'),path('ops/transfer/<uuid:pk>/',v.transfer_part,name='transfer_part'),
 path('legal/<slug:slug>/',v.legal,name='legal'),path('health/',v.health,name='health'),path('payments/webhook/',v.webhook,name='webhook'),path('payments/webhook/connect/',v.webhook,{'connected':True},name='connect_webhook'),path('manage/',admin.site.urls),
]
if settings.DEBUG: urlpatterns+=static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
