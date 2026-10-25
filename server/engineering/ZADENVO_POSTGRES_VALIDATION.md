# ZADENVO — ponovljena provjera na PostgreSQL-u

Datum: **25.10.2026.**

Testirana revizija: `d70a04320a36e9529b0bdefd663384ace4161503`.

## Potvrđeni rezultat

**Svih 78 postojećih serverskih testova prošlo je na stvarnom lokalnom
PostgreSQL-u 17.9, bez preskočenih testova, neuspjeha ili grešaka.**
Izvršen je i ranije preskočeni test
`test_postgresql_last_item_not_oversold`: dvije nezavisne konekcije istovremeno
pokušavaju rezervisati posljednji komad, a test potvrđuje tačno jednu uspješnu
rezervaciju, jedan odgovor da artikla nema i konačnu zalihu od nula komada.

Prije testova sve migracije primijenjene su na novu, praznu PostgreSQL bazu.
Django sistemska provjera i obje provjere usklađenosti migracija prošle su bez
problema. Kod aplikacije i `requirements.txt` nisu mijenjani za ovu provjeru.

Ovaj zapis dopunjuje `ZADENVO_VALIDATION.md`, koji dokumentuje prethodnu SQLite
provjeru s jednim preskočenim PostgreSQL testom. To ranije ograničenje sada je
razriješeno novim izvršavanjem; raniji zapis ostaje istorijski tačan.

## Stvarno izvršene provjere

Komande su pokrenute iz `server/app/` Python interpreterom iz postojećeg izdvojenog
okruženja `/workspace/scratch/ccb17751d7f9/zadenvo-venv`:

```sh
python manage.py migrate --noinput
python manage.py check
python manage.py migrate --check
python manage.py makemigrations --check --dry-run
python manage.py test market.tests --verbosity 2
```

| Provjera | Rezultat |
|---|---|
| Nova PostgreSQL baza | Sve migracije uspješno primijenjene. |
| Django `check` | `System check identified no issues (0 silenced).` |
| `migrate --check` | Izlazni kod 0; nema neprimijenjenih migracija. |
| `makemigrations --check --dry-run` | `No changes detected`. |
| Postojeći serverski testovi | `Ran 78 tests in 5.596s`; `OK`. |
| Konkurentna kupovina posljednjeg komada | `test_postgresql_last_item_not_oversold ... ok`. |
| Preskočeni testovi | **0**. |
| Greške ili neuspješni testovi | **0**. |

Osnovne varijable okruženja bile su `DEBUG=1`, `TESTING=1`,
`PAYMENTS_MODE=disabled` i lokalni e-mail backend u memoriji.
`DATABASE_URL` je privatno postavljen na izoliranu PostgreSQL bazu, a privremeni
direktorij za slike uklonjen je nakon testova.

Testne klase i dalje koriste svoje deklarisane testne postavke i mock odgovore
procesora plaćanja. To omogućava provjeru aplikacione logike bez stvarnih naplata,
isplata, povrata ili slanja e-mailova kupcima.

## Kako je omogućen PostgreSQL bez instaliranja sistema

Radno okruženje je Ubuntu 24.04, x86-64, s Python-om 3.12.14. Nije imalo PostgreSQL
server, klijente ni Docker. Preuzeti su službeni PGDG paketi za Ubuntu Noble preko
HTTPS-a. Njihov SHA-256 upoređen je s metapodacima službenog `Packages.gz` indeksa,
a sadržaj izdvojen pomoću `dpkg-deb --extract` u privremeni direktorij.

Nisu pokrenuti `apt install`, sistemski instalacijski skripti paketa ni sistemski
servisi. Nisu mijenjani OS računi, postojeće baze, aplikacione zavisnosti ili
produkcijski podaci. Glavne izvršne datoteke `postgres`, `initdb`, `pg_ctl` i `psql`
pokrenute su iz izdvojenog paketa; potrebne biblioteke tih izvršnih datoteka bile
su dostupne.

| Paket | Tačna verzija |
|---|---|
| `postgresql-17` | `17.9-1.pgdg24.04+1` |
| `postgresql-client-17` | `17.9-1.pgdg24.04+1` |
| `libpq5` | `18.3-1.pgdg24.04+1` |

Server se identifikovao kao:

```text
PostgreSQL 17.9 (Ubuntu 17.9-1.pgdg24.04+1) on x86_64-pc-linux-gnu,
compiled by gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0, 64-bit
```

To je ista glavna PostgreSQL verzija, 17, kao u postojećem `deploy/compose.yml`.
Ovim nije provjereno pokretanje same Docker Compose konfiguracije.

Okruženje mapira samo UID 0, a PostgreSQL odbija pokretanje kao root. Zato je
korišten zaseban procesni korisnički namespace s `unshare --user --map-user=65534`.
Proces u njemu vidi postojeći nepriviligovani identitet `nobody`, bez dodavanja
novog OS korisnika ili izmjene sistemskih datoteka. Pokušaj mapiranja i grupa nije
bio podržan; korišteno je samo uspješno UID mapiranje.

## Izolacija i predaja provjeri kroz preglednik

- Server sluša samo na `127.0.0.1`, na privremeno dodijeljenom portu `56853`.
- TCP i lokalna autentikacija koriste `scram-sha-256` i nasumičnu, isključivo testnu
  lozinku. Lozinka nije upisana u repozitorij ili ovaj dokument.
- Klaster i Unix socket nalaze se u privatnom privremenom direktoriju.
- `zadenvo_backend_ci` korištena je za čistu instalaciju. Django je napravio i
  nakon testova uklonio zasebnu testnu bazu.
- Posebna prazna baza `zadenvo_browser_ci` pripremljena je za provjeru u pregledniku.
  Podaci testnog paketa ne koriste se kao podaci te provjere.
- Klaster je nakon serverskih testova ostavljen privremeno pokrenut za tu odvojenu
  provjeru. Naknadno zaustavljanje potvrđuje završni zapis provjere u pregledniku.

Privremeni lokalni izvori dokaza:

```text
/workspace/scratch/ccb17751d7f9/zadenvo-pg-runtime/backend-validation.log
/workspace/scratch/ccb17751d7f9/zadenvo-pg-runtime/manifest.json
```

Ove datoteke pripadaju prolaznom testnom okruženju. Potvrđeni sažetak i porijeklo
paketa sačuvani su u ovom dokumentu.

## Službeni izvori i kontrolni zbrojevi

- [PostgreSQL paketi za Ubuntu](https://www.postgresql.org/download/linux/ubuntu/)
- [PGDG indeks za Noble amd64](https://apt.postgresql.org/pub/repos/apt/dists/noble-pgdg/main/binary-amd64/)
- [Dokumentacija za PostgreSQL 17 initdb](https://www.postgresql.org/docs/17/app-initdb.html)

| Paket | SHA-256 preuzetog paketa, potvrđen u službenom indeksu |
|---|---|
| [postgresql-17](https://apt.postgresql.org/pub/repos/apt/pool/main/p/postgresql-17/postgresql-17_17.9-1.pgdg24.04+1_amd64.deb) | `baf66f76e7fd89d691a5641da74194195e9826590750fcd0976683fb26ef4f3e` |
| [postgresql-client-17](https://apt.postgresql.org/pub/repos/apt/pool/main/p/postgresql-17/postgresql-client-17_17.9-1.pgdg24.04+1_amd64.deb) | `646c30a7160394da7d95a96e9efabc56ae57387907fd62b676f487cea02f5fc8` |
| [libpq5](https://apt.postgresql.org/pub/repos/apt/pool/main/p/postgresql-18/libpq5_18.3-1.pgdg24.04+1_amd64.deb) | `79915c8c7f8ae908a600e97260491856199311e83c6ea6c4ea4966e89ee1e95c` |

## Praktična granica rezultata

Ova provjera potvrđuje instalaciju sheme, postojeće serverske testove i konkretan
slučaj konkurentne rezervacije na PostgreSQL-u. Ne potvrđuje produkcijsko opterećenje,
stvarni Stripe račun ili bankovne tokove, javni hosting, SMTP, TLS, backup i obnovu,
pravnu pripremu ili spremnost za otvaranje prodaje. Rezultat pregleda kroz preglednik
evidentira se odvojeno.
