from django import forms
from django.core import signing
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import User,Seller,Product,Address,SupportCase,Review
from .services import cents
from .images import clean_image

class SignupForm(UserCreationForm):
    accept=forms.BooleanField(label='Prihvatam uslove platforme i potvrđujem da sam punoljetan/na.')
    class Meta:
        model=User
        fields=['username','email','password1','password2','accept']
        labels={'username':'Korisničko ime','email':'E-mail'}
    def clean_email(self):
        email=self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists(): raise ValidationError('Ova adresa nije dostupna za novu registraciju.')
        return email

class SellerForm(forms.ModelForm):
    accept=forms.BooleanField(label='Prihvatam uslove za prodavače i potvrđujem tačnost unesenih podataka.')
    class Meta:
        model=Seller
        fields=['kind','display_name','description','legal_notice','return_policy']
        labels={'kind':'Vrsta prodavača','display_name':'Naziv prodavnice / javno ime','description':'O prodavnici','legal_notice':'Podaci firme za javnu objavu','return_policy':'Pravila dostave i povrata'}
        widgets={'description':forms.Textarea(attrs={'rows':3}),'legal_notice':forms.Textarea(attrs={'rows':4}),'return_policy':forms.Textarea(attrs={'rows':4})}
    def clean(self):
        data=super().clean()
        if data.get('kind')=='business' and not data.get('legal_notice','').strip(): self.add_error('legal_notice','Poslovni prodavač mora unijeti podatke firme.')
        if not data.get('return_policy','').strip(): self.add_error('return_policy','Navedi pravila koja važe za tvoju prodaju.')
        return data

class ProductForm(forms.ModelForm):
    edit_token=forms.CharField(widget=forms.HiddenInput,required=False)
    price=forms.CharField(label='Cijena u EUR')
    shipping=forms.CharField(label='Dostava u EUR')
    image=forms.FileField(label='Fotografija artikla (JPEG, PNG ili WebP, do 5 MB)',required=False)
    class Meta:
        model=Product
        fields=['title','category','description','brand','condition','stock','safety_info']
        labels={'title':'Naziv artikla','category':'Kategorija','description':'Opis artikla','brand':'Brend','condition':'Stanje','stock':'Broj dostupnih komada','safety_info':'Proizvođač, odgovorna osoba i sigurnosni podaci (gdje je primjenjivo)'}
        widgets={'description':forms.Textarea(attrs={'rows':6}),'safety_info':forms.Textarea(attrs={'rows':3})}
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['category'].queryset=self.fields['category'].queryset.filter(enabled=True)
        if self.instance and not self.instance._state.adding:
            self.fields['edit_token'].initial=signing.dumps({'id':str(self.instance.pk),'revision':self.instance.revision,'stock':self.instance.stock},salt='product-edit')
            self.fields['price'].initial=f'{self.instance.price_cents/100:.2f}'
            self.fields['shipping'].initial=f'{self.instance.shipping_cents/100:.2f}'
        else: self.fields['shipping'].initial='0.00'
    def clean_price(self): return cents(self.cleaned_data['price'])
    def clean_shipping(self):
        n=cents(self.cleaned_data['shipping'],True)
        if n>50000: raise ValidationError('Dostava je iznad dopuštenog iznosa.')
        return n
    def clean_image(self):
        image=self.cleaned_data.get('image')
        return clean_image(image) if image else None

class AddressForm(forms.ModelForm):
    class Meta:
        model=Address
        fields=['recipient','line1','line2','postcode','city']
        labels={'recipient':'Ime i prezime primaoca','line1':'Ulica i kućni broj','line2':'Dodatak adrese (opcionalno)','postcode':'Poštanski broj','city':'Grad'}
    def clean_postcode(self):
        p=self.cleaned_data['postcode'].strip()
        if not (p.isascii() and p.isdigit() and len(p)==5): raise ValidationError('Unesi njemački poštanski broj od 5 cifara.')
        return p

class CheckoutForm(forms.Form):
    address=forms.ModelChoiceField(queryset=Address.objects.none(),label='Adresa dostave')
    token=forms.UUIDField(widget=forms.HiddenInput)
    quote=forms.CharField(widget=forms.HiddenInput)
    agree=forms.BooleanField(label='Pregledao/la sam artikle, prodavače, dostavu i uslove kupovine.')
    def __init__(self,*args,user,**kwargs):
        super().__init__(*args,**kwargs);self.fields['address'].queryset=Address.objects.filter(user=user)

class ShipForm(forms.Form):
    carrier=forms.CharField(label='Dostavna služba',max_length=60)
    tracking=forms.CharField(label='Broj pošiljke',max_length=100)

class CaseForm(forms.ModelForm):
    body=forms.CharField(label='Opiši problem',max_length=5000,widget=forms.Textarea(attrs={'rows':4}))
    class Meta: model=SupportCase;fields=['reason'];labels={'reason':'Razlog'}
class MessageForm(forms.Form):
    body=forms.CharField(label='Poruka',max_length=5000,widget=forms.Textarea(attrs={'rows':4}))
class RefundForm(forms.Form):
    amount=forms.CharField(label='Iznos povrata u EUR')
    confirm=forms.BooleanField(label='Potvrđujem povrat kupcu. Ova radnja pokreće zahtjev procesoru plaćanja.')
    def clean_amount(self): return cents(self.cleaned_data['amount'])
class ReviewForm(forms.ModelForm):
    class Meta:
        model=Review;fields=['rating','body'];labels={'rating':'Ocjena (1–5)','body':'Tvoje iskustvo'}
        widgets={'body':forms.Textarea(attrs={'rows':4})}
