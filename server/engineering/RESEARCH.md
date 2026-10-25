# Osnova funkcionalnog dizajna — 25.10.2026.

## Šta je stvarno pregledano
Amazon.de početna stranica vratila je provjeru protiv robota / zahtjev za JavaScript. Zato nije izvršena prijavljena kupovina niti pregled zatvorenog Seller Central sistema. Pregledani su službeni javni vodiči, ne svi Amazonovi interni procesi.

- https://sell.amazon.de/online-verkaufen — registracija prodavača, listing, prikaz ponude i obrada narudžbi.
- https://sell.amazon.de/programme/versand-durch-haendler — prodavač upravlja robom i izvršenjem pošiljke.
- https://sell.amazon.de/versenden — različiti modeli izvršenja; ne preuzimamo obećanja o Amazonovoj logistici.

Izvorno podržane funkcionalne oblasti: kupac, prodavač, artikli, zalihe, plaćanja, narudžbe, pošiljke i povrati. Naš interfejs, struktura koda i radni tokovi su novi. Nisu kopirani logotipi, fotografije, katalog, korisnički sadržaj ili Amazonov izvorni kod. Nema Primea, FBA mreže, automatske preporuke na Amazonovom nivou ili tvrdnje o istoj skali.

## Tehnički izvori
- https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits — Pages nije dozvoljeni besplatni hosting za online biznis/e-commerce niti za osjetljive transakcije.
- https://www.djangoproject.com/download/ — podržana 5.2 LTS grana; testno okruženje instalira 5.2.18.
- https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/ — tajne, DEBUG, hostovi, HTTPS, baza, e-mail, static/media i sigurnosne kopije.
- https://docs.stripe.com/webhooks — potpis provjeren na izvornom tijelu, ponavljanja događaja.
- https://docs.stripe.com/connect/separate-charges-and-transfers — platforma naplaćuje, transferi povezanim prodavačkim računima su odvojeni.
- https://docs.stripe.com/connect/migrate-to-controller-properties — Accounts v1 controller properties; kod ne koristi legacy `type=express` parametar.
- https://docs.stripe.com/connect/merchant-of-record — pravno definisanje trgovca ne rješava sam izgled stranice.

## Naše projektne odluke (nisu preuzete kao činjenice od Amazona)
Django + PostgreSQL, originalni responzivni interfejs, početna država DE, EUR, više prodavača u korpi, seller fulfillment, jedan transfer po prodavačkom dijelu narudžbe. Zamjenjujemo raniji nepotvrđeni prijedlog WordPress/Dokan samostalnom serverskom aplikacijom; nije kupljena Dokan licenca. Sedmodnevni operativni pregled isplate je podesiva razvojna pretpostavka, nije zakonski rok niti escrow garancija.
