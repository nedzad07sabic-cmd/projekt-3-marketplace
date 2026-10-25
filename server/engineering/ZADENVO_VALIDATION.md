# ZADENVO — provjera serverske instalacije

Datum provjere: **25.10.2026.**

## Najnoviji potvrđeni status

Nakon prvobitne SQLite provjere, 25.10.2026. završene su i provjere na stvarnom
lokalnom PostgreSQL-u te kroz Chromium preglednik:

| Provjera | Najnoviji rezultat |
|---|---|
| PostgreSQL 17.9 — čista instalacija | Migracije, sistemska provjera i provjere usklađenosti migracija uspješne. |
| Postojeći serverski testovi na PostgreSQL-u | **78/78 prošlo, 0 preskočenih, 0 grešaka**, uključujući konkurentnu kupovinu posljednjeg komada. |
| Chromium 151.0.7922.34 + zasebna PostgreSQL baza | **22/22 provjere prošle**, bez zabilježenih JavaScript grešaka. |

Detalje navode [PostgreSQL zapis](ZADENVO_POSTGRES_VALIDATION.md) i
[zapis provjere u pregledniku](ZADENVO_BROWSER_VALIDATION.md). Preglednik je provjerio
registraciju i testni potpisani link potvrde e-maila, moderaciju prodavača i oglasa,
dodavanje fotografije, prikaz zajedničkog kataloga nezavisnom kupcu, izračun cijene,
adresu, sačuvane artikle, pretragu, zaštitu administracije i mobilni prikaz.
Nepodešena naplata ostala je blokirana. Stvarni SMTP i Stripe/Connect tokovi nisu
izvršeni.

Sljedeći odjeljci čuvaju historijski tok prvih SQLite provjera; njihove tadašnje
blokade za PostgreSQL i preglednik razriješene su navedenim naknadnim provjerama.

## Historijski rezultat — prva SQLite provjera

Oporavljeni Django paket instaliran je u novo, izdvojeno Python okruženje.
Generisana je nedostajuća početna migracija `app/market/migrations/0001_initial.py`,
a zatim je primijenjena na potpuno novu lokalnu SQLite bazu. Provjere konfiguracije
i usklađenosti modela s migracijama završile su uspješno.

Postojeći testni paket pronašao je **78 testova: 77 uspješnih, 1 preskočen,
0 neuspješnih i 0 grešaka**. Preskočena je provjera zaključavanja posljednjeg
artikla pri istovremenoj kupovini jer ona zahtijeva PostgreSQL.
Ta prva SQLite runda nije predstavljala ponovno izvršavanje ranije spominjanih
78 PostgreSQL testova. Naknadno izvršavanje na PostgreSQL-u dokumentovano je iznad
i u zasebnom PostgreSQL zapisu.

## Okruženje i zavisnosti prve SQLite provjere

- Python: `3.12.14`.
- Izdvojeno okruženje: `/workspace/scratch/ccb17751d7f9/zadenvo-venv`.
- Instalirane su tačno verzije navedene u `app/requirements.txt`; taj fajl nije mijenjan.
- Django: `5.2.18`; Stripe SDK: `16.0.0`; Pillow: `13.0.0`.
- Početni pokušaj bez mrežnog pristupa nije pronašao pakete. Ponovljena instalacija
  s omogućenim pristupom službenom PyPI indeksu uspjela je.
- `python -m pip check`: `No broken requirements found.`
- U toj rundi nisu instalirani globalni Python paketi, sistemski servisi ni PostgreSQL.

Na početku nisu pronađeni `psql`, `pg_isready`, `postgres`, `initdb`, Docker ili Podman.
Nisu bile postavljene varijable veze `DATABASE_URL`, `PGHOST`, `PGDATABASE` ili
`PGUSER`. Zato PostgreSQL provjera nije izvršena u toj prvoj rundi. Naknadno je
omogućen izolirani PostgreSQL runtime iz službenih paketa, bez sistemske instalacije.

## Izvršeni koraci prve SQLite provjere

Komande su pokrenute iz direktorija `server/`, koristeći Python iz navedenog
izdvojenog okruženja:

```sh
python -m venv /workspace/scratch/ccb17751d7f9/zadenvo-venv
/workspace/scratch/ccb17751d7f9/zadenvo-venv/bin/python -m pip install \
  --disable-pip-version-check --retries 0 --timeout 20 \
  --index-url https://pypi.org/simple -r app/requirements.txt
/workspace/scratch/ccb17751d7f9/zadenvo-venv/bin/python tools/prepare_initial_schema.py
/workspace/scratch/ccb17751d7f9/zadenvo-venv/bin/python -m pip check
```

Skripta za pripremu sheme kreirala je početnu migraciju i prijavila
`No changes detected in app 'market'` pri neposrednoj dodatnoj provjeri.

Za instalaciju i testove korišten je novi privremeni direktorij izvan repozitorija,
s bazom `clean.sqlite3` i zasebnim direktorijem za slike. Varijable okruženja bile su:

```text
DEBUG=1
TESTING=1
PAYMENTS_MODE=disabled
DATABASE_URL=sqlite:///<apsolutna-putanja-privremene-baze>
MEDIA_ROOT=<apsolutna-putanja-privremenog-direktorija-za-slike>
```

Sljedeće komande zatim su izvršene iz `server/app/`, sve s izlaznim kodom `0`:

```sh
python manage.py migrate --noinput
python manage.py check
python manage.py migrate --check
python manage.py makemigrations --check --dry-run
python manage.py test market.tests --verbosity 2
```

Rezultati:

| Provjera | Potvrđeno stanje |
|---|---|
| Nova SQLite baza | Sve Django i marketplace migracije uspješno primijenjene. |
| Django `check` | `System check identified no issues (0 silenced).` |
| `migrate --check` | Nema neprimijenjenih migracija. |
| `makemigrations --check --dry-run` | `No changes detected`. |
| Postojeći testovi | `Ran 78 tests`; `OK (skipped=1)`; trajanje testova 1,490 sekundi. |
| Zavisnosti | `No broken requirements found.` |

Testna baza i privremeni fajlovi uklonjeni su nakon provjere. Django test runner
koristio je zasebnu SQLite bazu u memoriji, a ne razvojnu ili produkcijsku bazu.

## Šta rezultat pokriva

Postojeći testovi obuhvataju registraciju i potvrdu e-maila, zabranu stvaranja
administratorskog računa kroz običnu registraciju, izolaciju narudžbi i prodavačkih
podataka, provjeru CSRF-a, escaping nepouzdanih naslova, trajno evidentiranje artikala,
rezervaciju i oslobađanje zaliha, kontrolu cijena, idempotentne webhookove i provjere
potpisa, obradu povrata i transfera te serversko renderovanje važnih korisničkih stranica.

Osnovno okruženje imalo je isključenu naplatu. Testne klase privremeno postavljaju
`PAYMENTS_MODE=test`, koriste izričite lažne testne vrijednosti i kontrolisane mock
odgovore procesora. Ova provjera ne potvrđuje stvarnu Stripe Checkout naplatu,
Connect onboarding, bankovne transfere ili povrate. Nisu poslane stvarne transakcije
ni poruke kupcima.

## Trenutno preostala ograničenja

- Nisu potvrđeni Docker image i Compose instalacija, javni hosting/TLS, stvarni SMTP,
  sigurnosne kopije ili obnova baze.
- Nisu potvrđeni registracija domene, potpuna prava na brend, uslovi prodaje ili
  vanjski testni tokovi stvarnog Stripe/Connect računa.
- DPMA upit za tačan naziv `ZADENVO` vratio je 0 rezultata 25.10.2026.;
  [zapis upita](../../engineering/brand/zadenvo.dpma-check-2026-10-25.json) nije
  potpuna provjera sličnih naziva, neregistrovanih ranijih prava ili nezavisnih EUIPO/WIPO
  evidencija.
- Ovaj rezultat potvrđuje lokalnu serversku instalaciju i navedene testove; ne znači
  da je marketplace javno objavljen ili spreman za stvarne kupce.

## Historijska SQLite provjera nakon brendiranja

Nakon primjene naziva, administracijskih oznaka i SVG/CSS identiteta ponovo je izvršen cijeli postojeći paket: **78 testova, 77 uspješnih, 1 očekivano preskočen, bez grešaka** (2,850 sekundi). `check` i provjera migracija ostali su uredni.

Na još jednoj novoj privremenoj SQLite bazi, Django klijent potvrdio je HTTP 200 i naziv Zadenvo (uključujući uppercase prikaz) na početnoj stranici, prijavi kupca i administratorskoj prijavi. Katalog je ostao prazan, a naplata isključena. Provjereno je svih pet ključnih CSS/SVG stavki u statičkom manifestu. Privremena baza je uklonjena.

Završni `collectstatic` je tada izvršen: 135 datoteka je kopirano i 405 obrada završeno. Prisustvo CSS-a, favicon-a i tri SVG znaka potvrđeno je u manifestu.

Vektorski natpis je renderovan i vizuelno pregledan. U toj rundi pregled stranica u pregledniku nije izvršen jer Chromium još nije bio dostupan. Naknadno je pokrenut Chromium 151.0.7922.34 i uspješno završene 22 provjere iz odvojenog browser zapisa. PostgreSQL konkurentni test također je naknadno izvršen i prošao; prva serverska provjera nije korištena kao zamjena za te rezultate.
