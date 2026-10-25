# Zadenvo — serverski marketplace (radni naziv)

Odvojen projekt od TimeIQ.eu i B2B posredovanja. Originalni interfejs i stvarni serverski tokovi; **nije Amazonov kod ili kopija brenda**.

## Nova aplikacija

`app/` sadrži Django aplikaciju sa stvarnim korisničkim računima, bazom, provjerom pristupa, registracijom firmi/privatnih prodavača, moderacijom oglasa, fotografijama, višestrukim prodavačima u korpi, narudžbama, rezervacijama zaliha, evidencijom pošiljki, predmetima podrške i provjerenim kupovinama za recenzije.

Kod Stripe integracije sadrži Checkout, potpisane webhookove, Connect onboarding, transfere, povrate i odvojenu evidenciju naplate potraživanja. **Ova integracija još nije potvrđena na korisnikovom procesorskom računu.** Podrazumijevani režim je `disabled`; nema probnog dugmeta koje lažno označava uplatu uspješnom.

`deploy/` sadrži Docker Compose za PostgreSQL, aplikaciju, radne zadatke, Caddy/HTTPS i skriptu privatne sigurnosne kopije. `ci/` ima primjer automatizovanog PostgreSQL testa. Dokumentacija je u `engineering/`.

## Pokretanje za razvoj

```sh
cd app
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Lokalno postavi DEBUG=1 i SITE_URL=http://localhost:8000 u app/.env.
python manage.py migrate
python manage.py bootstrap
python manage.py createsuperuser
python manage.py runserver
# U drugom terminalu, istom okruženju:
python manage.py process_jobs --loop
```

Za lokalni razvoj `DEBUG=1` dopušta SQLite i konzolni e-mail. Proizvodi, kupci i recenzije **ne dodaju se automatski**. U javnom okruženju koristi PostgreSQL, SMTP i HTTPS; registracije ostaju zatvorene dok nisu odobreni pravni dokumenti.

## Testovi

```sh
TESTING=1 python manage.py test market.tests --verbosity 2
```

Testovi uključuju stvarnu bazu, server odgovore i potpisivanje testnih webhookova. Pozivi naplate/transfera u unit testovima imaju eksplicitne mock zamjene; to nije potvrda stvarnog bankovnog prometa. PostgreSQL test konkurentnog pokušaja kupovine posljednjeg artikla preskače se na SQLiteu.

## Važno prije objave

Pročitaj `engineering/DEPLOYMENT_BS.md`, `engineering/ACCEPTANCE.md` i `engineering/STATUS.md`. Ne uključuj `live` bez potvrđenog prihvatanja marketplacea i privatnih prodavača, testnih procesorskih transakcija, pravne/poreske pripreme, zaštite administratora i provjerenog backupa.

Raniji `source/` i `tests/core.test.js` ostaju kao istorijski prototip, **nisu backend nove aplikacije**. GitHub Pages nije hosting za ovu aplikaciju niti aktivnu trgovinu. Postojeća Pages adresa može služiti samo nekomercijalnom pregledu statusa projekta.

Nije dodijeljena nova open-source licenca za poslovni kod. Licence zavisnosti ostaju njihove.

## Integracija u repozitorij
Ovaj kod je izdvojen iz ranijeg `Projekt_3_Marketplace_Server_v1.zip` i uključen pod `server/` u razvojnu granu `server-platform-v1`. Izvorna evidencija paketa sačuvana je u `SOURCE_PACKAGE_MANIFEST.json`; ona opisuje originalni ZIP, ne izmijenjeno izdanje.

Sačuvana početna migracija omogućuje instalaciju preko `python manage.py migrate`, bez generisanja šeme na produkcijskom serveru. Za naredne izmjene modela normalno kreirati nove migracije; ne prepisivati početnu historiju.

Najnoviji stvarno izvršeni testovi navedeni su u `engineering/ZADENVO_VALIDATION.md`. Stari `TEST_REPORT.md` je arhivirani izvještaj ranijeg paketa. GitHub Pages nije hosting ove aplikacije.
