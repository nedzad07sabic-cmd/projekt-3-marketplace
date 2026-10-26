# Zadenvo — kontrolisana priprema servera

Ove upute dopunjuju `../engineering/DEPLOYMENT_BS.md`. Ne potvrđuju da je server
već instaliran ili da je javna prodaja otvorena. Ne mijenjaju TimeIQ.

## Prije instalacije

Potrebni su odobreni odvojeni hosting, Docker Compose, domena i privatne postavke.
Za pomoćne alate za backup na hostu potreban je Python 3.10 ili noviji.

Kopirati primjere u privatne `server/app/.env` i `server/deploy/.env`. Za početak
ostaviti `REGISTRATION_OPEN=0` i `PAYMENTS_MODE=disabled`. Postaviti `DEBUG=0`,
`TESTING=0`, `TRUST_PROXY=1`, `MEDIA_ROOT=/data/media`, stvarni HTTPS origin i
odgovarajući `ALLOWED_HOSTS`. Database URL i Compose POSTGRES_PASSWORD moraju
koristiti istu lozinku; specijalni znakovi u URL-u moraju biti URL-kodirani.

Ne slati lozinke u razgovor i ne uključivati popunjene `.env` datoteke u Git.
Pristup bazi i aplikacijskom portu treba ostati privatan; javni su samo proxy portovi.

## Prva instalacija — još nije izvršena za korisnika

Iz `server/deploy/`:

```sh
docker compose config --quiet
docker compose build
docker compose up -d db
docker compose run --rm web --check
docker compose run --rm web python manage.py migrate --noinput
docker compose run --rm web python manage.py bootstrap
docker compose run --rm web python manage.py createsuperuser
docker compose run --rm web python manage.py enroll_admin IME_ADMINA
docker compose up -d web jobs proxy
docker compose ps
```

`web --check` poziva provjeru konfiguracije preko novog entrypointa. Uobičajeno
pokretanje web/jobs provjerava Django i već primijenjene migracije; ne mijenja
shemu automatski. Kad je PAYMENTS_MODE=live, pokretanje traži i uspješan postojeći
`readiness`. Prolaz tog pregleda nije zamjena za vanjske testove naplate i stvarna
odobrenja. Kreiranje administratora i MFA ostaju interaktivni privatni koraci.

Proxy čeka uspješnu provjeru zdravlja web-servisa. Healthcheck provjerava lokalni
HTTP endpoint koji u aplikaciji provjerava bazu. Ne provjerava vanjski TLS,
ispravnost pošiljki, SMTP ili Stripe; status unhealthy sam po sebi ne restartuje
kontejner. Produkcijski nadzor i alarmi ostaju zaseban posao.

## Konzistentna sigurnosna kopija uz planirani zastoj

Nova backup komanda namjerno NE zaustavlja servise i NE briše ranije kopije.
Za prvu, jednostavnu strategiju traži period bez pisanja u bazu i slike. Operater
mora osigurati da nema drugih administrativnih procesa ili vanjskih pisaca.

```sh
# Iz server/deploy/, samo u prethodno dogovorenom terminu održavanja:
docker compose stop proxy web jobs
mkdir -p /PRIVATE/BACKUPS
chmod 700 /PRIVATE/BACKUPS
sh backup.sh /PRIVATE/BACKUPS --maintenance-confirmed
# Tek nakon provjere izlaznog koda / poruke o uspješnom završetku:
docker compose up -d web jobs proxy
```

Komanda odbija aktivne web/jobs/proxy servise. Izvršava pg_dump u custom formatu,
kopira direktorij media u zasebnom kontejneru koji pokreće samo tar, računa SHA-256,
provjerava arhivu i tek tada objavljuje kompletan direktorij kopije. Datoteke su
privatne (0600), direktorij 0700. Greška uklanja samo nepotpunu kopiju tekućeg
pokušaja, ne starije kopije. Servisi se ne pokreću sami nakon greške: operater ih
mora vratiti nakon provjere. Za strategiju bez zastoja potrebna je dodatna priprema.

Backup mora biti izvan repozitorija, šifrovan i kopiran na odvojeno mjesto. Ova
komanda ne ugovara takvo skladište, ne šifruje ga i ne kreira automatski raspored.

## Provjera integriteta i obnova

```sh
python3 ../tools/verify_backup.py /PRIVATE/BACKUPS/zadenvo-TAČNA-OZNAKA
```

Provjeravaju se veličine i hashovi, zaglavlje PostgreSQL arhive, gzip integritet,
putanje i tipovi media zapisa. Ne izvlači se sadržaj, ne izvršava SQL i ne mijenja
se baza. Podrazumijevani limit raspakovane media arhive je 20 GiB.

**To nije proba obnove.** Sljedeći obavezni test je vraćanje pouzdane kopije u novu,
odvojenu PostgreSQL bazu i prazni direktorij medija, bez pristupa produkcijskim
podacima. U toj probi treba uporediti evidenciju korisnika/narudžbi i dostupnost
fotografija. Komanda za prepisivanje postojeće produkcijske baze nije dodana.
PostgreSQL upozorava da obnova izvršava kod iz dumpa, zato koristiti samo vlastite,
pouzdane kopije i izolovano okruženje. SHA-256 sam po sebi ne potvrđuje porijeklo.

## Testovi dopune

Iz korijena repozitorija:

```sh
python -m unittest discover -s server/tools/tests -v
```

Oni ne traže Docker, PostgreSQL, Stripe ključeve ili slanje e-mailova. Testiraju
pravila i pomoćne komande, a ne kompletnu instalaciju. CI primjer je ispravljen,
ali i dalje nije aktivan GitHub Actions workflow.

Izvori korišteni pri pripremi:
- https://docs.docker.com/compose/how-tos/startup-order/
- https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/
- https://www.postgresql.org/docs/17/app-pgrestore.html
