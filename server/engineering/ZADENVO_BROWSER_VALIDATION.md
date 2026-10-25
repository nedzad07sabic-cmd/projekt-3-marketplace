# ZADENVO — provjera aplikacije kroz preglednik

Datum: **25.10.2026.**

**Prošla su sva 22 koraka postojeće provjere kroz preglednik**, uz lokalni Django
server i zasebnu PostgreSQL bazu. Izlazni kod procesa bio je 0. Sirovi, sanitizirani
rezultat sačuvan je u [validation/browser-2026-10-25.json](validation/browser-2026-10-25.json).

Testiran je aplikacijski kod revizije `d70a04320a36e9529b0bdefd663384ace4161503`.
Jedine izmjene izvršnog koda u ovoj provjeri odnose se na pomoćni
`browser_acceptance.py`: izbor izvršne datoteke preglednika, privremeni izlazni
direktorij, ispis napretka i bilježenje stvarnog tipa baze. Poslovna logika nije
mijenjana. Verzija tog pomoćnog koda nalazi se uz ovaj izvještaj.

## Okruženje i izolacija

| Stavka | Stvarno korišteno |
|---|---|
| Python / Django | 3.12.14 / 5.2.18 |
| PostgreSQL | 17.9, izdvojeni lokalni klaster |
| Baza | `zadenvo_browser_ci`, prazna prije migracija i pripreme kategorija |
| Aplikacija | `http://127.0.0.1:8000`, `runserver --noreload` |
| Playwright za Python | 1.62.0; dodatni testni paket, nije produkcijska zavisnost |
| Preglednik | Chrome for Testing headless shell 151.0.7922.34 |
| Veliki prikaz | 1440 × 1000 CSS piksela |
| Mobilni prikaz | 390 × 844 CSS piksela, Chromium emulacija |
| Testni računi | Odvojene sesije kupca, prodavača i operatera; adrese `example.invalid` |
| Naplata | `PAYMENTS_MODE=disabled` |
| E-mail | Lokalni backend u memoriji i aplikacijski outbox; bez SMTP slanja |

Zaštite pomoćnog programa zahtijevaju `DEBUG=1`, `TESTING=1`, naziv baze sa završetkom
`_ci` i odsustvo ranijih `qa_` korisnika. Baza za ovu provjeru odvojena je od baze
serverskog testnog paketa. Nisu korišteni podaci stvarnih kupaca ili prodavača.

## Potvrđeni tokovi

| Korak | Rezultat |
|---|---|
| Početna stranica | HTTP 200, očekivani naslov i Zadenvo izgled; sadržaj staje u veliki prikaz. |
| Registracija kupca | Obrazac stvara zapis u bazi; potpisani link iz lokalnog outboxa potvrđuje adresu. |
| Registracija prodavača | Odvojena sesija stvara zaseban račun i potvrđuje adresu istim lokalnim postupkom. |
| Prijava privatnog prodavača | Profil čeka pregled; odobrenje operatera ostaje zapisano u bazi. |
| Unos artikla | Naslov, cijena, zaliha i priložena testna slika ostaju zapisani; status čeka pregled. |
| Pristup prije odobrenja | Kupac dobija HTTP 404 za neodobreni oglas. |
| Odobrenje oglasa | Operater potvrđuje pregled; aktivni oglas postaje vidljiv nezavisnoj sesiji kupca. |
| Korpa | Server prikazuje 75,00 EUR za testni artikl i 5,00 EUR dostave, ukupno 80,00 EUR. |
| Adresa dostave | Unesena sintetička adresa ostaje dostupna u korpi. |
| Isključena naplata | Dugme za naručivanje i nastavak na plaćanje ostaje onemogućeno. |
| Sačuvani artikli | Odabrani artikl pojavljuje se na listi kupca. |
| Administratorski pristup | Obični kupac dobija HTTP 403 za `/ops/`. |
| Pretraga | Vraća stvarni odobreni testni zapis; nepostojeći pojam daje prazno stanje. |
| Mobilni prikaz | Sadržaj staje u širinu 390 CSS piksela bez horizontalnog prelijevanja stranice. |
| JavaScript greške | Nije zabilježen nijedan `pageerror` na nadziranoj stranici kupca. |

Tabelom su objedinjene povezane provjere; svih 22 pojedinačnih naziva nalazi se u
JSON zapisu. Nakon automatiziranog prolaska vizuelno su pregledane snimke početne
stranice u velikom i mobilnom prikazu. Znak, naziv, pretraga, kategorije, obrazac
filtera i podnožje bili su čitljivi i bez uočenog preklapanja. Velika snimka nastala
je prije unosa artikla, a mobilna nakon odobrenja sintetičkog oglasa.

Snimke su interni, privremeni dokazi provjere. Nisu dodane u repozitorij i ne
predstavljaju javne ponude ili produkcijske korisnike.

## Ponovljivo pokretanje

Iz korijena repozitorija, u izdvojenom Python okruženju:

```sh
python -m pip install -r server/requirements-test.txt
python -m playwright install chromium --only-shell
```

Pripremiti novu, isključivo testnu PostgreSQL bazu čiji naziv završava s `_ci`, pa
postaviti privatni `DATABASE_URL` u okruženju. Ne unositi tu vrijednost u
repozitorij. I server i pomoćni program trebaju isto okruženje:

```sh
export DEBUG=1 TESTING=1 PAYMENTS_MODE=disabled REGISTRATION_OPEN=1
export SITE_URL=http://127.0.0.1:8000
export EMAIL_BACKEND=django.core.mail.backends.locmem.EmailBackend
export BROWSER_ARTIFACT_DIR="$(mktemp -d /tmp/zadenvo-browser.XXXXXX)"
export MEDIA_ROOT="$BROWSER_ARTIFACT_DIR/media"
```

U prvom terminalu, nakon postavljanja tih varijabli:

```sh
cd server/app
python manage.py migrate --noinput
python manage.py bootstrap
python manage.py runserver 127.0.0.1:8000 --noreload
```

U drugom terminalu s istim okruženjem, iz korijena repozitorija:

```sh
python server/engineering/browser_acceptance.py
```

Za ponavljanje treba nova čista testna baza: program namjerno odbija bazu koja
već sadrži `qa_` korisnike. Nakon rada zaustaviti samo testni server i testni klaster.

Ako postoji kompatibilna službena izvršna datoteka preglednika, moguće je postaviti
`BROWSER_EXECUTABLE_PATH` na njenu putanju. U ovom okruženju standardni CDN vratio
je HTML poruku umjesto ZIP arhive, pa je preuzet isti traženi preglednik iz
službenog Google Chrome for Testing izvora:

- [Metapodaci verzije 151.0.7922.34](https://googlechromelabs.github.io/chrome-for-testing/151.0.7922.34.json)
- [Službeni Linux headless shell](https://storage.googleapis.com/chrome-for-testing-public/151.0.7922.34/linux64/chrome-headless-shell-linux64.zip)
- [Playwright: instalacija preglednika](https://playwright.dev/python/docs/browsers)
- [Playwright: izbor izvršne datoteke](https://playwright.dev/python/docs/api/class-browsertype#browser-type-launch-option-executable-path)

Preuzeta arhiva imala je 120.231.126 bajtova; provjera ZIP integriteta prošla je.
Lokalno izračunati SHA-256 arhive je
`3cfc2bd00d1bafcf8a68dc74c9c92bb7150ddc8d26ade948a776316e1cec4f14`.
Taj zbroj identifikuje korištenu arhivu; nije nezavisno poređenje s objavljenim
Googleovim kontrolnim zbrojem. Preglednik i njegovi paketi nisu dio aplikacijskog
repozitorija ili produkcijske slike.

## Završetak i granice rezultata

Lokalni Django proces zaustavljen je pri izlasku iz testnog pokretača. Nakon
provjere zaustavljen je i privremeni PostgreSQL klaster; `pg_ctl` je potvrdio
`server stopped` s izlaznim kodom 0.

Rezultat potvrđuje opisane lokalne tokove, rad sa stvarnom bazom i konkretne
prikaze. Potvrda adrese preko lokalnog outboxa ne provjerava isporuku e-maila.
Onemogućeno dugme za naplatu ne provjerava kupovinu preko stvarnog ili testnog
Stripe računa. Mobilni prikaz nije provjera fizičkog uređaja, Safarija ili svih
preglednika. Nisu provjereni produkcijski hosting, Docker Compose, HTTPS/TLS,
opterećenje, backup i obnova niti potpunost pravne pripreme.

Zasebna provjera svih 78 serverskih testova na PostgreSQL-u, uključujući istovremenu
rezervaciju posljednjeg artikla, dokumentovana je u
[ZADENVO_POSTGRES_VALIDATION.md](ZADENVO_POSTGRES_VALIDATION.md).
