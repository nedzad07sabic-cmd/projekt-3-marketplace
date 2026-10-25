from django.contrib import admin
from django.conf import settings
from django.contrib.auth.admin import UserAdmin
from .models import *
from .services import audit

@admin.register(User)
class MarketUserAdmin(UserAdmin):
    fieldsets=UserAdmin.fieldsets+(("Marketplace",{'fields':('email_verified',)}),)
    readonly_fields=('email_verified',)

class AuditedAdmin(admin.ModelAdmin):
    def save_model(self,request,obj,form,change):
        super().save_model(request,obj,form,change)
        audit(request.user,'admin.changed',obj,model=obj._meta.label,fields=list(form.changed_data))

@admin.register(Category)
class CategoryAdmin(AuditedAdmin): list_display=('name','enabled','commission_bps')

@admin.register(LegalPage)
class LegalAdmin(AuditedAdmin): list_display=('slug','version','approved','updated_at')

@admin.register(Seller)
class SellerAdmin(AuditedAdmin):
    list_display=('display_name','kind','status','stripe_ready')
    readonly_fields=('user','stripe_account_id','stripe_ready','stripe_mode','accepted_terms_version','created_at')
    def has_add_permission(self,request): return False
    def has_delete_permission(self,request,obj=None): return False

@admin.register(Product)
class ProductAdmin(AuditedAdmin):
    list_display=('title','seller','status','stock')
    readonly_fields=('seller','category','title','description','brand','condition','price_cents','shipping_cents','stock','revision','safety_info','created_at','updated_at')
    def has_add_permission(self,request): return False
    def has_delete_permission(self,request,obj=None): return False

class ReadOnlyAdmin(admin.ModelAdmin):
    def get_readonly_fields(self,request,obj=None): return [f.name for f in self.model._meta.fields]
    def has_add_permission(self,request): return False
    def has_delete_permission(self,request,obj=None): return False

for model in [Order,SellerOrder,OrderLine,Refund,PaymentEvent,AuditEvent,SupportCase,CaseMessage,Outbox,ProductImage]: admin.site.register(model,ReadOnlyAdmin)
@admin.register(Review)
class ReviewAdmin(AuditedAdmin):
    readonly_fields=('line','author','product','rating','body','created_at')
    def has_add_permission(self,request): return False
    def has_delete_permission(self,request,obj=None): return False
@admin.register(ListingReport)
class ReportAdmin(AuditedAdmin):
    readonly_fields=('product','reporter','body','created_at')
    def has_add_permission(self,request): return False
    def has_delete_permission(self,request,obj=None): return False
admin.site.site_header=f'{settings.SITE_NAME} · Upravljanje'
admin.site.site_title=settings.SITE_NAME
admin.site.index_title='Upravljanje marketplaceom'
