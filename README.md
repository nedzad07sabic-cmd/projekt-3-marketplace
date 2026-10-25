# Zadenvo — marketplace u razvoju

Zadenvo je odabrani radni naziv zasebnog marketplacea za poslovne i privatne prodavače. Ova razvojna grana sadrži vraćeni serverski kod iz ranijeg paketa, uz pripremu baze i radni identitet. **Aplikacija još nije objavljena kao aktivna trgovina.**

## Gdje je stvarna aplikacija

- `server/app/` — Django aplikacija, korisnički računi, katalog, prodavači, narudžbe, administracija i integracija naplate.
- `server/app/market/migrations/` — sačuvane migracije baze.
- `server/deploy/` — konfiguracija PostgreSQL/Docker/HTTPS instalacije.
- `server/engineering/ZADENVO_VALIDATION.md` — rezultati provjera ove radne verzije i njihova ograničenja.
- `engineering/brand/ZADENVO.md` — radni identitet i stvarni status provjere naziva/domene.
- `engineering/SERVER_RELEASE_STATUS.md` — trenutni status integracije.

Naplata je podrazumijevano isključena. Domena `zadenvo.com` je kandidat; nije kupljena ni konfigurirana. Provjera prava na naziv nije završena.

## Lokalno pokretanje

Potpune upute su u [server/README.md](server/README.md). Iz korijena ovog repozitorija:

```sh
cd server/app
python -m venv .venv
# Aktiviraj virtualno okruženje prema svom operativnom sistemu.
pip install -r requirements.txt
# Postavi DEBUG=1 i SITE_URL=http://localhost:8000 u privatnom app/.env.
python manage.py migrate
python manage.py bootstrap
python manage.py createsuperuser
python manage.py runserver
```

`bootstrap` ne dodaje lažne kupce, artikle ili recenzije. Za razvoj se može koristiti SQLite; produkcija zahtijeva PostgreSQL. Raniji korak generisanja prve migracije više nije potreban za novu instalaciju: migracije su dio koda.

## Historijski prototip

`source/`, `tests/core.test.js` i `docs/index.html` čuvaju raniji demonstracijski interfejs s izmišljenim podacima. On nije povezan s novom bazom i ne predstavlja serversku aplikaciju. GitHub Pages koristi `main` → `/docs`; rad u `server-platform-v1` ne objavljuje serversku trgovinu.

[Postojeći demonstracijski pregled](https://nedzad07sabic-cmd.github.io/projekt-3-marketplace/) ostaje historijski demo. Za server je potreban zaseban hosting. TimeIQ i B2B posredovanje su zasebni projekti.

## Prije objave

Vidi [prihvatne kriterije](server/engineering/ACCEPTANCE.md) i [upute za instalaciju](server/engineering/DEPLOYMENT_BS.md). Treba završiti PostgreSQL provjere, stvarne testne tokove procesora plaćanja, e-mail, hosting, sigurnosne kopije i pravnu pripremu. Nisu kupljene nove usluge niti uključena stvarna naplata.
