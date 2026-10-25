import hashlib,hmac,json,time,uuid
from datetime import timedelta
from io import BytesIO
from unittest.mock import patch,MagicMock
from django.conf import settings
from django.db import transaction
from django.contrib.auth.hashers import check_password
from django.core import signing
from django.core.exceptions import ValidationError,PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase,Client,override_settings,TransactionTestCase
from django.utils import timezone
from PIL import Image
from market.models import *
from market import services as s, payments as p
from market.images import clean_image

TEST_SETTINGS=dict(PAYMENTS_MODE='test',STRIPE_SECRET_KEY='sk_test_unit_test_only_not_a_credential',STRIPE_WEBHOOK_SECRET='whsec_unit_test_only_not_a_credential',STRIPE_CONNECT_WEBHOOK_SECRET='whsec_connected_unit_test_only',REGISTRATION_OPEN=True,PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],PAYOUT_HOLD_DAYS=0,EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',STORAGES={'default':{'BACKEND':'django.core.files.storage.InMemoryStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class Obj(dict):
    def __getattr__(self,key): return self[key]

@override_settings(**TEST_SETTINGS)
class CommerceTests(TestCase):
    def setUp(self):
        self.buyer=User.objects.create_user('buyer','buyer@example.invalid','Long-test-password-123',email_verified=True)
        self.other=User.objects.create_user('other','other@example.invalid','Long-test-password-123',email_verified=True)
        self.owner=User.objects.create_user('seller','seller@example.invalid','Long-test-password-123',email_verified=True)
        self.staff=User.objects.create_user('operator','operator@example.invalid','Long-test-password-123',is_staff=True)
        self.cat=Category.objects.create(name='Elektronika',slug='electronics',commission_bps=1000)
        self.seller=Seller.objects.create(user=self.owner,kind='business',display_name='Test seller',legal_notice='Test legal info',return_policy='Test policy',accepted_terms_version='unit',status='approved',stripe_account_id='acct_test_fixture',stripe_ready=True,stripe_mode='test')
        self.item=Product.objects.create(seller=self.seller,category=self.cat,title='Test keyboard',description='A product used only in automated tests',condition='new',price_cents=7500,shipping_cents=500,stock=5,status='active')
        self.address=Address.objects.create(user=self.buyer,recipient='Test buyer',line1='Example street 1',postcode='10115',city='Berlin')
        self.client.force_login(self.buyer)
    def reserve(self,token=None,qty=1):
        s.update_cart(self.buyer,self.item.pk,qty)
        q=s.cart_quote(self.buyer)
        return s.create_order(self.buyer,self.address,token or uuid.uuid4(),s.quote_token(self.buyer,q))
    def paid(self):
        o=self.reserve();s.mark_paid(self.session(o));o.refresh_from_db();return o
    def session(self,o,**overrides):
        obj={'id':'cs_test_'+o.pk.hex,'metadata':{'order_id':str(o.pk)},'payment_status':'paid','amount_total':o.total_cents,'currency':'eur','payment_intent':'pi_'+o.pk.hex,'livemode':False}
        obj.update(overrides);return obj
    def event(self,o,event_id='evt_test',**overrides):
        return {'id':event_id,'type':'checkout.session.completed','livemode':False,'data':{'object':self.session(o,**overrides)}}
    def sign(self,payload,secret=None):
        stamp=int(time.time());raw=json.dumps(payload).encode();sig=hmac.new((secret or settings.STRIPE_WEBHOOK_SECRET).encode(),str(stamp).encode()+b'.'+raw,hashlib.sha256).hexdigest()
        return raw,f't={stamp},v1={sig}'
    def test_money_decimal_and_limits(self):
        self.assertEqual(s.cents('12,34'),1234)
        for value in ['NaN','-1','0.001','Infinity','1000000000']:
            with self.subTest(value=value),self.assertRaises(ValidationError): s.cents(value)
    def test_reservation_is_in_database(self):
        o=self.reserve();self.item.refresh_from_db()
        self.assertEqual(self.item.stock,4);self.assertEqual(o.total_cents,8000)
        self.assertEqual(o.parts.get().commission_cents,800);self.assertFalse(CartLine.objects.filter(user=self.buyer).exists())
    def test_idempotent_checkout(self):
        token=uuid.uuid4();o=self.reserve(token)
        again=s.create_order(self.buyer,self.address,token,'irrelevant-after-safe-idempotency-hit')
        self.assertEqual(o.pk,again.pk);self.item.refresh_from_db();self.assertEqual(self.item.stock,4)
    def test_other_buyer_cannot_reuse_token(self):
        o=self.reserve()
        with self.assertRaises(PermissionDenied): s.create_order(self.other,self.address,o.checkout_token,'unused')
    def test_price_change_requires_new_quote(self):
        s.update_cart(self.buyer,self.item.pk,1);q=s.quote_token(self.buyer,s.cart_quote(self.buyer))
        self.item.price_cents=9000;self.item.save()
        with self.assertRaises(s.CommerceError): s.create_order(self.buyer,self.address,uuid.uuid4(),q)
        self.assertFalse(Order.objects.exists())
    def test_tampered_quote_rejected(self):
        s.update_cart(self.buyer,self.item.pk,1)
        with self.assertRaises(s.CommerceError): s.create_order(self.buyer,self.address,uuid.uuid4(),'forged')
    def test_inventory_exhaustion(self):
        self.item.stock=1;self.item.save();self.reserve()
        with self.assertRaises(s.CommerceError): s.update_cart(self.other,self.item.pk,1)
    def test_release_stock_exactly_once(self):
        o=self.reserve();self.assertTrue(p.cancel_pending(o,self.buyer));o.refresh_from_db()
        self.assertFalse(s.release_stock(o,'cancelled'));self.item.refresh_from_db();self.assertEqual(self.item.stock,5)
    def test_failed_provider_cancellation_keeps_stock(self):
        o=self.reserve();o.stripe_session_id='cs_test_existing';o.save()
        api=MagicMock();api.checkout.Session.retrieve.side_effect=RuntimeError('network down')
        with patch('market.payments.gateway',return_value=api),self.assertRaises(RuntimeError): p.cancel_pending(o,self.buyer)
        self.item.refresh_from_db();self.assertEqual(self.item.stock,4)
    def test_payments_disabled_fail_closed(self):
        s.update_cart(self.buyer,self.item.pk,1);q=s.quote_token(self.buyer,s.cart_quote(self.buyer))
        with override_settings(PAYMENTS_MODE='disabled'),self.assertRaises(s.CommerceError): s.create_order(self.buyer,self.address,uuid.uuid4(),q)
        self.assertFalse(Order.objects.exists())
    def test_live_requires_approvals(self):
        with override_settings(PAYMENTS_MODE='live',STRIPE_SECRET_KEY='sk_live_unit_test_only',LIVE_APPROVED=False),self.assertRaises(s.CommerceError): s.payments_ready()
    def test_unverified_buyer_blocked(self):
        self.buyer.email_verified=False;self.buyer.save()
        with self.assertRaises(s.CommerceError): self.reserve()
    def test_address_ownership_enforced(self):
        self.address.user=self.other;self.address.save()
        with self.assertRaises(s.CommerceError): self.reserve()
    def test_foreign_delivery_not_silently_enabled(self):
        self.address.country='US';self.address.save()
        with self.assertRaises(s.CommerceError): self.reserve()
    def test_unready_seller_blocked(self):
        self.seller.stripe_ready=False;self.seller.save()
        with self.assertRaises(s.CommerceError): self.reserve()
    def test_own_purchase_blocked(self):
        with self.assertRaises(s.CommerceError): s.update_cart(self.owner,self.item.pk,1)
    def test_multiple_sellers_one_payment(self):
        s2=Seller.objects.create(user=self.other,kind='private',display_name='Second seller',accepted_terms_version='unit',status='approved',stripe_account_id='acct_second_fixture',stripe_ready=True,stripe_mode='test')
        p2=Product.objects.create(seller=s2,category=self.cat,title='Second item',description='Fixture',condition='used',price_cents=2000,shipping_cents=300,stock=1,status='active')
        s.update_cart(self.buyer,p2.pk,1);o=self.reserve()
        self.assertEqual(o.parts.count(),2);self.assertEqual(o.total_cents,10300)
    def test_valid_signature_processes_payment(self):
        o=self.reserve();raw,sig=self.sign(self.event(o))
        self.assertEqual(self.client.post('/payments/webhook/',raw,content_type='application/json',HTTP_STRIPE_SIGNATURE=sig).status_code,200)
        o.refresh_from_db();self.assertEqual(o.status,'paid')
    def test_invalid_signature_rejected(self):
        o=self.reserve();raw,_=self.sign(self.event(o))
        self.assertEqual(self.client.post('/payments/webhook/',raw,content_type='application/json',HTTP_STRIPE_SIGNATURE='fake').status_code,400)
        o.refresh_from_db();self.assertEqual(o.status,'pending')
    def test_duplicate_webhook_is_idempotent(self):
        o=self.reserve();p.process_event(self.event(o));self.assertFalse(p.process_event(self.event(o)))
        self.assertEqual(PaymentEvent.objects.count(),1);self.item.refresh_from_db();self.assertEqual(self.item.stock,4)
        self.assertEqual(Outbox.objects.filter(key__startswith='paid-').count(),2)
    def test_amount_mismatch_rejected(self):
        o=self.reserve()
        with self.assertRaises(s.CommerceError): p.process_event(self.event(o,amount_total=1))
        o.refresh_from_db();self.assertEqual(o.status,'pending')
    def test_mode_mismatch_rejected(self):
        o=self.reserve();e=self.event(o);e['livemode']=True
        with self.assertRaises(s.CommerceError): p.process_event(e)
    def test_connected_event_cannot_pay_platform_order(self):
        o=self.reserve();e=self.event(o);e['account']='acct_external'
        with self.assertRaises(s.CommerceError): p.process_event(e)
    def test_late_payment_held_not_silently_fulfilled(self):
        o=self.reserve();s.release_stock(o,'cancelled');s.mark_paid(self.session(o));o.refresh_from_db()
        self.assertEqual(o.status,'payment_review');self.assertTrue(o.payment_hold)
    def test_payment_return_url_cannot_mark_paid(self):
        o=self.reserve();r=self.client.get(o.get_absolute_url()+'?payment=success&paid=true');self.assertEqual(r.status_code,200)
        o.refresh_from_db();self.assertEqual(o.status,'pending')
    def test_order_isolation(self):
        o=self.reserve();self.client.force_login(self.other);self.assertEqual(self.client.get(o.get_absolute_url()).status_code,404)
    def test_seller_cannot_view_buyer_entire_order(self):
        o=self.paid();self.client.force_login(self.owner);self.assertEqual(self.client.get(o.get_absolute_url()).status_code,404)
        self.assertEqual(self.client.get('/sell/order/'+str(o.parts.get().pk)+'/').status_code,200)
    def test_nonstaff_operations_denied(self): self.assertEqual(self.client.get('/ops/').status_code,403)
    def test_seller_cross_product_edit_denied(self):
        self.client.force_login(self.other);Seller.objects.create(user=self.other,kind='private',display_name='Other',accepted_terms_version='unit',status='approved')
        self.assertEqual(self.client.get('/sell/product/'+str(self.item.pk)+'/').status_code,404)
    def test_csrf_is_required(self):
        client=Client(enforce_csrf_checks=True);client.force_login(self.buyer)
        self.assertEqual(client.post('/cart/'+str(self.item.pk)+'/update/',{'quantity':1}).status_code,403)
    def test_logout_is_post_only(self): self.assertEqual(self.client.get('/account/logout/').status_code,405)
    def test_untrusted_titles_escaped(self):
        self.item.title='<script>alert(1)</script>';self.item.save()
        r=self.client.get(self.item.get_absolute_url());self.assertContains(r,'&lt;script&gt;');self.assertNotContains(r,'<script>alert(1)</script>')
    def test_pending_listings_not_public(self):
        self.item.status='pending';self.item.save();self.assertEqual(self.client.get(self.item.get_absolute_url()).status_code,404)
    def test_shipping_permissions(self):
        o=self.paid();part=o.parts.get()
        with self.assertRaises(PermissionDenied): s.ship_part(self.other,part.pk,'Carrier','123')
        s.ship_part(self.owner,part.pk,'Carrier','123');part.refresh_from_db();self.assertEqual(part.status,'shipped')
    def test_only_buyer_can_confirm_receipt(self):
        o=self.paid();part=o.parts.get();s.ship_part(self.owner,part.pk,'Carrier','123')
        with self.assertRaises(PermissionDenied): s.receive_part(self.owner,part.pk)
        s.receive_part(self.buyer,part.pk);part.refresh_from_db();self.assertEqual(part.status,'delivered')
    def test_review_requires_delivered_purchase(self):
        o=self.paid();line=o.parts.get().lines.get()
        with self.assertRaises(s.CommerceError): s.make_review(self.buyer,line,5,'Text')
        part=o.parts.get();s.ship_part(self.owner,part.pk,'Carrier','123');s.receive_part(self.buyer,part.pk)
        line.refresh_from_db();s.make_review(self.buyer,line,5,'Actual fixture purchase')
        with self.assertRaises(s.CommerceError): s.make_review(self.buyer,line,5,'Duplicate')
    def test_case_isolation_and_payout_block(self):
        o=self.paid();part=o.parts.get();case=s.open_case(self.buyer,part.pk,'delivery','Where is it?')
        self.client.force_login(self.other);self.assertEqual(self.client.get(case.get_absolute_url()).status_code,404)
        part.status='delivered';part.delivered_at=timezone.now()-timedelta(days=10);part.save()
        with self.assertRaises(s.CommerceError): p.prepare_transfer(part.pk,self.staff)
    def test_refund_cannot_exceed_paid(self):
        part=self.paid().parts.get()
        with self.assertRaises(s.CommerceError): p.request_refund(part.pk,self.staff,8001)
        p.request_refund(part.pk,self.staff,5000)
        with self.assertRaises(s.CommerceError): p.request_refund(part.pk,self.staff,4000)
    def test_refund_nonstaff_denied(self):
        with self.assertRaises(PermissionDenied): p.request_refund(self.paid().parts.get().pk,self.buyer,100)
    def refund_object(self,r,status='succeeded'):
        return {'id':'re_'+r.pk.hex,'metadata':{'local_refund':str(r.pk)},'status':status,'amount':r.amount_cents,'currency':'eur','payment_intent':r.part.order.stripe_payment_intent}
    def test_partial_refund_cumulative_rounding_and_idempotency(self):
        part=self.paid().parts.get();r=p.request_refund(part.pk,self.staff,2000)
        p.apply_refund(self.refund_object(r));p.apply_refund(self.refund_object(r));part.refresh_from_db()
        self.assertEqual(part.refunded_cents,2000);self.assertEqual(part.commission_refunded_cents,200);self.assertEqual(part.payable_cents,5400)
    def test_pending_refund_not_treated_as_completed(self):
        part=self.paid().parts.get();r=p.request_refund(part.pk,self.staff,2000);p.apply_refund(self.refund_object(r,'pending'))
        part.refresh_from_db();self.assertEqual(part.refunded_cents,0)
    def test_post_transfer_refund_tracks_receivable(self):
        part=self.paid().parts.get();part.transferred_cents=7200;part.transfer_id='tr_fixture';part.transfer_state='done';part.save()
        r=p.request_refund(part.pk,self.staff,2000);p.apply_refund(self.refund_object(r));part.refresh_from_db()
        self.assertEqual(part.recovery_due_cents,1800)
    def test_failed_recovery_not_counted_as_money_returned(self):
        part=self.paid().parts.get();part.transferred_cents=7200;part.transfer_id='tr_fixture';part.transfer_state='done';part.save()
        r=p.request_refund(part.pk,self.staff,2000);p.apply_refund(self.refund_object(r))
        api=MagicMock();api.Transfer.create_reversal.side_effect=RuntimeError('timeout')
        with patch('market.payments.gateway',return_value=api),self.assertRaises(RuntimeError): p.recover_refund(r.pk)
        part.refresh_from_db();r.refresh_from_db();self.assertEqual(part.recovered_cents,0);self.assertEqual(r.recovery_cents,1800)
        api.Transfer.create_reversal.side_effect=None;api.Transfer.create_reversal.return_value=Obj(id='trr_fixture')
        with patch('market.payments.gateway',return_value=api): p.recover_refund(r.pk);p.recover_refund(r.pk)
        part.refresh_from_db();self.assertEqual(part.recovered_cents,1800);self.assertEqual(part.recovery_due_cents,0)
    def test_transfer_timeout_freezes_refunds(self):
        part=self.paid().parts.get();part.status='delivered';part.delivered_at=timezone.now()-timedelta(days=2);part.save()
        api=MagicMock();api.Account.retrieve.return_value=Obj(payouts_enabled=True,capabilities={'transfers':'active'});api.PaymentIntent.retrieve.return_value=Obj(status='succeeded',currency='eur',amount_received=8000,latest_charge='ch_fixture');api.Transfer.create.side_effect=RuntimeError('network unknown')
        with patch('market.payments.gateway',return_value=api),self.assertRaises(RuntimeError): p.transfer_part(part.pk,self.staff)
        part.refresh_from_db();self.assertEqual(part.transfer_state,'unknown');self.assertEqual(part.transfer_requested_cents,7200)
        with self.assertRaises(s.CommerceError): p.request_refund(part.pk,self.staff,1000)
        api.Transfer.create.side_effect=None;api.Transfer.create.return_value=Obj(id='tr_success')
        with patch('market.payments.gateway',return_value=api): p.transfer_part(part.pk,self.staff)
        part.refresh_from_db();self.assertEqual(part.transferred_cents,7200)
    def test_processor_dispute_stops_transfer(self):
        o=self.paid();e={'id':'evt_dispute','type':'charge.dispute.created','livemode':False,'data':{'object':{'payment_intent':o.stripe_payment_intent,'status':'needs_response'}}};p.process_event(e)
        o.refresh_from_db();self.assertTrue(o.payment_hold)
    def test_unallocated_external_refund_stops_transfer(self):
        o=self.paid();e={'id':'evt_external','type':'charge.refunded','livemode':False,'data':{'object':{'payment_intent':o.stripe_payment_intent,'amount_refunded':1000}}};p.process_event(e)
        o.refresh_from_db();self.assertTrue(o.payment_hold)
    def test_connected_account_readiness_not_redirect_based(self):
        self.seller.stripe_ready=False;self.seller.save();e={'id':'evt_acct','type':'account.updated','livemode':False,'data':{'object':{'id':self.seller.stripe_account_id,'details_submitted':True,'payouts_enabled':True,'capabilities':{'transfers':'active'}}}}
        p.process_event(e,connected=True);self.seller.refresh_from_db();self.assertTrue(self.seller.stripe_ready)
    def test_seller_legal_identity_is_snapshotted(self):
        o=self.reserve();self.seller.display_name='Changed';self.seller.save();self.assertEqual(o.parts.get().seller_name,'Test seller')
    def test_shipping_max_per_seller(self):
        p2=Product.objects.create(seller=self.seller,category=self.cat,title='Extra',description='Fixture',condition='new',price_cents=1000,shipping_cents=700,stock=3,status='active')
        s.update_cart(self.buyer,p2.pk,1);o=self.reserve();self.assertEqual(o.total_cents,9200)
    def test_whole_site_renders_with_real_database(self):
        for url in ['/','/cart/','/orders/','/account/','/saved/',self.item.get_absolute_url(),self.seller.get_absolute_url()]:
            with self.subTest(url=url): self.assertEqual(self.client.get(url).status_code,200)
        self.client.force_login(self.owner);self.assertEqual(self.client.get('/sell/').status_code,200)
        self.client.force_login(self.staff);self.assertEqual(self.client.get('/ops/').status_code,200)
    def test_health_does_not_leak_connection_details(self):
        response=self.client.get('/health/');self.assertEqual(response.json(),{'status':'ok'})
    def test_no_static_role_switch(self):
        response=self.client.get('/');self.assertNotContains(response,'Simuliraj uspješnu uplatu');self.assertNotContains(response,'localStorage')
    def test_image_reencoding(self):
        b=BytesIO();Image.new('RGB',(20,20),'red').save(b,'PNG')
        cleaned=clean_image(SimpleUploadedFile('image.png',b.getvalue(),content_type='image/png'))
        with Image.open(cleaned) as image: self.assertEqual(image.format,'JPEG');self.assertFalse(image.getexif())
    def test_svg_rejected_even_with_jpeg_extension(self):
        upload=SimpleUploadedFile('safe.jpg',b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',content_type='image/jpeg')
        with self.assertRaises(ValidationError): clean_image(upload)
    def test_image_size_limit(self):
        with self.assertRaises(ValidationError): clean_image(SimpleUploadedFile('big.jpg',b'x'*(5*1024*1024+1)))
    def test_email_case_insensitive_unique(self):
        with transaction.atomic(),self.assertRaises(Exception): User.objects.create_user('dup','BUYER@EXAMPLE.INVALID','test')

    def test_sdk_gateway_initializes_without_network(self):
        self.assertIs(p.gateway(),p.stripe)
        self.assertIsNotNone(p.stripe.default_http_client)
    def test_sdk_account_capabilities_converted(self):
        api=MagicMock();api.Account.retrieve.return_value=p.stripe.Account.construct_from({'id':'acct_test_fixture','details_submitted':True,'payouts_enabled':True,'capabilities':{'transfers':'active'}},'')
        with patch('market.payments.gateway',return_value=api): self.assertTrue(p.refresh_seller(self.owner))
    def test_sdk_refund_resource_converted(self):
        r=p.request_refund(self.paid().parts.get().pk,self.staff,2000)
        api=MagicMock();api.Refund.create.return_value=p.stripe.Refund.construct_from(self.refund_object(r),'')
        with patch('market.payments.gateway',return_value=api): p.execute_refund(r.pk)
        r.refresh_from_db();self.assertEqual(r.status,'succeeded')
    def test_checkout_timeout_preserves_attempt_and_stock(self):
        o=self.reserve();api=MagicMock();api.checkout.Session.create.side_effect=RuntimeError('unknown network outcome')
        with patch('market.payments.gateway',return_value=api),self.assertRaises(RuntimeError): p.start_checkout(o,self.buyer)
        o.refresh_from_db();self.assertIsNotNone(o.checkout_started_at);self.assertIsNone(o.stripe_session_id)
        with self.assertRaises(s.CommerceError): p.cancel_pending(o,self.buyer)
        self.item.refresh_from_db();self.assertEqual(self.item.stock,4)
    def test_expiry_webhook_reconciles_unknown_checkout(self):
        o=self.reserve();p.prepare_checkout(o,self.buyer)
        event=self.event(o);event['type']='checkout.session.expired';event['data']['object']['payment_status']='unpaid'
        p.process_event(event);p.process_event(event);o.refresh_from_db();self.item.refresh_from_db()
        self.assertEqual(o.status,'expired');self.assertEqual(self.item.stock,5)
    def test_checkout_retry_uses_same_idempotency_key(self):
        o=self.reserve();api=MagicMock();api.checkout.Session.create.side_effect=[RuntimeError('timeout'),Obj(id='cs_test_retry',url='https://checkout.stripe.com/c/pay/unit')]
        with patch('market.payments.gateway',return_value=api):
            with self.assertRaises(RuntimeError): p.start_checkout(o,self.buyer)
            self.assertEqual(p.start_checkout(o,self.buyer),'https://checkout.stripe.com/c/pay/unit')
        self.assertEqual(api.checkout.Session.create.call_args_list[0].kwargs,api.checkout.Session.create.call_args_list[1].kwargs)
    def test_stale_refund_is_not_resent(self):
        r=p.request_refund(self.paid().parts.get().pk,self.staff,1000);Refund.objects.filter(pk=r.pk).update(created_at=timezone.now()-timedelta(hours=25))
        with patch('market.payments.gateway') as api,self.assertRaises(s.CommerceError): p.execute_refund(r.pk)
        api.assert_not_called()
    def test_stale_transfer_is_not_resent(self):
        part=self.paid().parts.get();part.status='delivered';part.delivered_at=timezone.now()-timedelta(days=2);part.save();p.prepare_transfer(part.pk,self.staff)
        SellerOrder.objects.filter(pk=part.pk).update(transfer_requested_at=timezone.now()-timedelta(hours=25))
        with patch('market.payments.gateway') as api,self.assertRaises(s.CommerceError): p.transfer_part(part.pk,self.staff)
        api.assert_not_called()
    def test_stale_recovery_is_not_resent(self):
        part=self.paid().parts.get();part.transferred_cents=7200;part.transfer_id='tr_fixture';part.transfer_state='done';part.save()
        r=p.request_refund(part.pk,self.staff,2000);p.apply_refund(self.refund_object(r));p.prepare_recovery(r.pk)
        Refund.objects.filter(pk=r.pk).update(recovery_requested_at=timezone.now()-timedelta(hours=25))
        with patch('market.payments.gateway') as api,self.assertRaises(s.CommerceError): p.recover_refund(r.pk)
        api.assert_not_called()
    def test_pending_refund_blocks_shipping(self):
        part=self.paid().parts.get();p.request_refund(part.pk,self.staff,1000)
        with self.assertRaises(s.CommerceError): s.ship_part(self.owner,part.pk,'Carrier','unit')
    def test_case_opened_after_transfer_preparation_blocks_attempt(self):
        part=self.paid().parts.get();part.status='delivered';part.delivered_at=timezone.now()-timedelta(days=2);part.save();p.prepare_transfer(part.pk,self.staff)
        s.open_case(self.buyer,part.pk,'delivery','Check delivery')
        with patch('market.payments.gateway') as api,self.assertRaises(s.CommerceError): p.transfer_part(part.pk,self.staff)
        api.assert_not_called()
    def test_seller_can_create_persistent_product_not_simulation(self):
        self.client.force_login(self.owner)
        r=self.client.post('/sell/product/add/',{'title':'Created listing','category':self.cat.pk,'description':'Real database listing from a unit test','brand':'','condition':'new','stock':3,'safety_info':'Test only','price':'12.00','shipping':'3.00'})
        self.assertEqual(r.status_code,302)
        product=Product.objects.get(title='Created listing');self.assertEqual(product.seller_id,self.seller.pk);self.assertEqual(product.status,'pending');self.assertEqual(product.price_cents,1200)
    def test_stale_seller_stock_edit_rejected(self):
        self.client.force_login(self.owner);token=signing.dumps({'id':str(self.item.pk),'revision':self.item.revision,'stock':self.item.stock},salt='product-edit')
        self.reserve()
        r=self.client.post('/sell/product/'+str(self.item.pk)+'/',{'title':'Changed stale','category':self.cat.pk,'description':self.item.description,'brand':'','condition':'new','stock':5,'safety_info':'','price':'75','shipping':'5','edit_token':token})
        self.assertEqual(r.status_code,302);self.item.refresh_from_db();self.assertEqual(self.item.stock,4);self.assertNotEqual(self.item.title,'Changed stale')
    def test_new_account_cannot_bypass_email_via_seller_apply(self):
        self.other.email_verified=False;self.other.save();self.client.force_login(self.other)
        r=self.client.post('/sell/apply/',{'kind':'private','display_name':'Unverified','return_policy':'policy','accept':'on'})
        self.assertEqual(r.status_code,302);self.assertFalse(Seller.objects.filter(user=self.other).exists())

@override_settings(**TEST_SETTINGS)
class AccountTests(TestCase):
    def test_registration_hashes_password_and_sends_verification_to_outbox(self):
        client=Client();r=client.post('/account/signup/',{'username':'newmember','email':'NEW@EXAMPLE.INVALID','password1':'Unique-long-pass-91!!','password2':'Unique-long-pass-91!!','accept':'on'})
        self.assertEqual(r.status_code,302);user=User.objects.get(username='newmember');self.assertEqual(user.email,'new@example.invalid');self.assertTrue(user.check_password('Unique-long-pass-91!!'));self.assertFalse(user.email_verified)
        self.assertEqual(Outbox.objects.count(),1);self.assertNotIn('Unique-long-pass',Outbox.objects.get().body)
    def test_registration_can_be_disabled(self):
        with override_settings(REGISTRATION_OPEN=False):
            r=self.client.post('/account/signup/',{});self.assertEqual(r.status_code,200);self.assertFalse(User.objects.exists())
    def test_signup_cannot_create_staff(self):
        self.client.post('/account/signup/',{'username':'newmember','email':'new@example.invalid','password1':'Unique-long-pass-91!!','password2':'Unique-long-pass-91!!','accept':'on','is_staff':'true','is_superuser':'true'})
        u=User.objects.get();self.assertFalse(u.is_staff);self.assertFalse(u.is_superuser)
    def test_verification_requires_signed_token(self):
        u=User.objects.create_user('newmember','new@example.invalid','A-long-pass-123');self.client.post('/account/verify/forged/')
        u.refresh_from_db();self.assertFalse(u.email_verified)
    def test_verification_link_changes_only_intended_user(self):
        u=User.objects.create_user('newmember','new@example.invalid','A-long-pass-123');token=signing.dumps({'id':u.pk,'email':u.email,'password':hashlib.sha256(u.password.encode()).hexdigest()},salt='verify-email')
        r=self.client.post('/account/verify/'+token+'/');self.assertEqual(r.status_code,302);u.refresh_from_db();self.assertTrue(u.email_verified)
    def test_authenticated_pages_not_publicly_cacheable(self):
        u=User.objects.create_user('member','member@example.invalid','A-long-pass-123');self.client.force_login(u)
        self.assertEqual(self.client.get('/account/')['Cache-Control'],'private, no-store')
    def test_unknown_email_reset_does_not_disclose_account(self):
        r=self.client.post('/account/reset/',{'email':'nobody@example.invalid'});self.assertEqual(r.status_code,302)

@override_settings(**TEST_SETTINGS)
class ConcurrencyTests(TransactionTestCase):
    def test_postgresql_last_item_not_oversold(self):
        from django.db import connection,close_old_connections
        if connection.vendor!='postgresql': self.skipTest('Requires PostgreSQL row locking; run the supplied PostgreSQL CI job before launch.')
        from concurrent.futures import ThreadPoolExecutor
        import threading
        cat=Category.objects.create(name='Concurrency',slug='concurrency')
        owner=User.objects.create_user('owner','owner@example.invalid','Long-pass-123')
        seller=Seller.objects.create(user=owner,display_name='Seller',kind='business',accepted_terms_version='unit',status='approved',stripe_account_id='acct_concurrency',stripe_ready=True,stripe_mode='test')
        product=Product.objects.create(seller=seller,category=cat,title='Last item',description='Test',condition='new',price_cents=1000,stock=1,status='active')
        users=[]
        for n in range(2):
            user=User.objects.create_user('buyer'+str(n),f'b{n}@example.invalid','Long-pass-123',email_verified=True)
            address=Address.objects.create(user=user,recipient='Test',line1='Street 1',postcode='10115',city='Berlin')
            s.update_cart(user,product.pk,1);users.append((user.pk,address.pk,s.quote_token(user,s.cart_quote(user))))
        barrier=threading.Barrier(2)
        def work(data):
            close_old_connections();user=User.objects.get(pk=data[0]);address=Address.objects.get(pk=data[1]);barrier.wait()
            try: s.create_order(user,address,uuid.uuid4(),data[2]);return 'reserved'
            except s.CommerceError: return 'sold-out'
            finally: __import__('django.db',fromlist=['connections']).connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(work,users))
        self.assertCountEqual(results,['reserved','sold-out']);product.refresh_from_db();self.assertEqual(product.stock,0)
