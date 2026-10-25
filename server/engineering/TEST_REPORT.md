> Arhivirani izvještaj iz originalnog serverskog ZIP paketa. Navedeni PostgreSQL rezultati nisu ponovljeni u ovom okruženju. Za aktuelnu provjeru Zadenvo verzije vidi `ZADENVO_VALIDATION.md`.

# Izvršene provjere — 25.10.2026.

Izolovano okruženje: Python 3.13.17, Django 5.2.18, PostgreSQL 17; bez korisnikovih procesorskih ključeva, stvarnog novca ili stvarnih ličnih podataka.

- PostgreSQL: 78 automatskih testova, svi prošli, uključujući paralelnu kupovinu posljednjeg komada i rollback višestruke korpe.
- SQLite: 78 testova, 77 prošlo; 1 PostgreSQL concurrency test očekivano preskočen.
- Django model/system check: bez prijavljenih problema.
- Static assets: collectstatic završen (132 izvorna statička fajla).
- Stripe SDK 16: adapter inicijalizacija i dekodiranje stvarnih tipova SDK objekata testirani; pozivi naplate/refund/transfer mreži zamijenjeni su mock objektima.
- Checkout network-unknown outcome: stock hold ne oslobađa se bez provjere procesora; ponovljeni poziv koristi isti idempotency ključ. Stari nerazriješeni pokušaji zahtijevaju ručnu provjeru.
- Browser test prethodnog izolovanog okruženja NIJE završen: preglednik nije mogao ostati pokrenut u raspoloživom okruženju. Ne tvrdi se vizuelna ili browser E2E potvrda na osnovu tog pokušaja.

## Granice potvrde
Ovi testovi ne potvrđuju stvarni Stripe račun, Connect prihvat privatnih prodavača, isplatu na banku, vanjski SMTP, produkcijski hosting, sigurnosnu reviziju, pravnu usklađenost, rad na korisnikovom telefonu, backup/restore ili opterećenje. Te provjere ostaju uslov puštanja prodaje.

## Ponovljivost
`app/market/tests/test_marketplace.py` sadrži testove. `engineering/browser_acceptance.py` je zaseban test za novu, izolovanu *_ci bazu; ne pokretati nad produkcijskim podacima. Naknadni GitHub Actions rezultati i browser izvještaj vode se zasebno kada budu stvarno izvršeni.

## Paket i prenos
Uspješni PostgreSQL/SQLite testovi koristili su migracije generisane Django komandom makemigrations u izolovanom okruženju. Zbog prekida konektorske veze ti generisani fajlovi nisu preneseni u ovaj ZIP. Priložena skripta reprodukuje generisanje iz modela; nije izvršena u ovom završnom lokalnom paketu, gdje Django nije instaliran. Zato build namjerno traži pripremljenu i sačuvanu migraciju prije nastavka.

Posljednja lokalna provjera: Python sintaksa svih izvornih fajlova i integritet ZIP-a. Nema tvrdnje da je Docker image iz ovog paketa izgrađen ili da je browser acceptance skripta prošla.
