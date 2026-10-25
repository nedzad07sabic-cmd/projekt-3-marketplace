# Zadenvo — status serverske integracije

Datum: 25.10.2026. Razvojna grana: `server-platform-v1`.

## U ovoj verziji

- Raniji serverski ZIP je oporavljen i stvarni Django izvor uključen pod `server/`. Porijeklo i hash izvornog paketa navedeni su u `SERVER_SOURCE_IMPORT.json`.
- Generisana je i sačuvana početna migracija `server/app/market/migrations/0001_initial.py`.
- Na novoj lokalnoj PostgreSQL 17.9 bazi prošli su migracije, provjera konfiguracije i provjera usklađenosti modela.
- Zadenvo je primijenjen na podrazumijevani naziv, zajedničko zaglavlje, administratorske oznake, CSS paletu, favicon i SVG znakove.
- Svih **78/78 postojećih serverskih testova prošlo je na PostgreSQL-u 17.9, bez preskočenih testova ili grešaka**. Izvršena je i provjera konkurentne kupovine posljednjeg komada.
- U Chromium pregledniku 151.0.7922.34, nad odvojenom PostgreSQL bazom, prošle su **22/22 provjere**, bez zabilježenih JavaScript grešaka. Provjereni su registracija i potpisani link potvrde e-maila, moderacija prodavača i oglasa, fotografija artikla, zajednički katalog za nezavisnog kupca, izračun cijene, adresa, sačuvani artikli, pretraga, zaštita administracije i mobilni prikaz. Naplata bez konfiguracije ostala je blokirana.
- `collectstatic` je završen. Serverski render početne stranice, prijave i admin prijave vraća HTTP 200 uz Zadenvo oznaku; odabrani korisnički tokovi naknadno su provjereni i kroz stvarni preglednik.
- Provjerene su putanje instalacije nakon premještanja pod `server/`; CI je i dalje samo primjer, nije aktiviran workflow.

## Preostalo

Nisu potvrđeni Docker image i instalacija kroz Compose, javni hosting/TLS, stvarna SMTP isporuka, backup/restore ili vanjski Stripe/Connect tokovi. Lokalna provjera u pregledniku nije test stvarne naplate niti slanja e-maila. Serverski procesorski pozivi i dalje su provjereni kontrolisanim mock odgovorima.

`PAYMENTS_MODE=disabled` ostaje podrazumijevano. `zadenvo.com` je kandidat s RDAP odgovorom bez pronađene registracije, ali domena nije kupljena niti povezana. [Službeni DPMA upit za tačan naziv ZADENVO](brand/zadenvo.dpma-check-2026-10-25.json), izvršen 25.10.2026., vratio je 0 rezultata. Potpuna provjera sličnih znakova i ranijih prava, uključujući nezavisne EUIPO/WIPO provjere, nije završena.

Ovo je izvor serverske aplikacije na razvojnoj grani, ne potvrda javnog lansiranja. `main`, postojeći Pages demo, TimeIQ i B2B projekt nisu ciljevi ove izmjene.

## Historijski zapis i detaljni rezultati

Prva lokalna provjera koristila je SQLite: 77 testova prošlo je, a jedan PostgreSQL test bio je preskočen. Taj historijski rezultat ostaje evidentiran. Naknadno je ista postojeća testna zbirka stvarno ponovo izvršena na PostgreSQL-u, sa svih 78 uspješnih testova; to nije preuzeta tvrdnja iz starog ZIP paketa.

- [Pregled validacije i historijska SQLite provjera](../server/engineering/ZADENVO_VALIDATION.md)
- [PostgreSQL: 78/78 testova i čista migracija](../server/engineering/ZADENVO_POSTGRES_VALIDATION.md)
- [Chromium: 22/22 provjere korisničkih tokova](../server/engineering/ZADENVO_BROWSER_VALIDATION.md)
