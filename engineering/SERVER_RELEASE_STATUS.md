# Zadenvo — status serverske integracije

Datum: 25.10.2026. Razvojna grana: `server-platform-v1`.

## U ovoj verziji

- Raniji serverski ZIP je oporavljen i stvarni Django izvor uključen pod `server/`. Porijeklo i hash izvornog paketa navedeni su u `SERVER_SOURCE_IMPORT.json`.
- Generisana je i sačuvana početna migracija `server/app/market/migrations/0001_initial.py`.
- Na novoj lokalnoj SQLite bazi prošli su migracije, provjera konfiguracije i provjera usklađenosti modela.
- Zadenvo je primijenjen na podrazumijevani naziv, zajedničko zaglavlje, administratorske oznake, CSS paletu, favicon i SVG znakove.
- Postojećih 78 serverskih testova ponovo je izvršeno nakon brendiranja: **77 je prošlo, 1 PostgreSQL test je preskočen, nema grešaka**.
- `collectstatic` je završen. Serverski render početne stranice, prijave i admin prijave vraća HTTP 200 uz Zadenvo oznaku.
- Provjerene su putanje instalacije nakon premještanja pod `server/`; CI je i dalje samo primjer, nije aktiviran workflow.

## Preostalo

Nisu potvrđeni PostgreSQL konkurentni test, puni browser E2E, Docker image, javni hosting, stvarna e-mail isporuka, backup/restore ili vanjski Stripe/Connect tokovi. Raniji PostgreSQL rezultat iz ZIP-a nije rezultat ove runde.

`PAYMENTS_MODE=disabled` ostaje podrazumijevano. `zadenvo.com` je kandidat s RDAP odgovorom bez pronađene registracije, ali domena nije kupljena niti povezana. Provjera žiga nije završena.

Ovo je izvor serverske aplikacije na razvojnoj grani, ne potvrda javnog lansiranja. `main`, postojeći Pages demo, TimeIQ i B2B projekt nisu ciljevi ove izmjene.

Detaljni rezultati: `server/engineering/ZADENVO_VALIDATION.md`.
