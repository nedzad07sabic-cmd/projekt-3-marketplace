# Zadenvo — marketplace u razvoju

Zadenvo je odabrani radni naziv zasebnog marketplacea za poslovne i privatne prodavače. Ova razvojna grana sadrži vraćeni serverski kod iz ranijeg paketa, uz pripremu baze i radni identitet. **Aplikacija još nije objavljena kao aktivna trgovina.**

## Gdje je stvarna aplikacija

- `server/app/` — Django aplikacija, korisnički računi, katalog, prodavači, narudžbe, administracija i integracija naplate.
- `server/app/market/migrations/` — sačuvane migracije baze.
- `server/deploy/` — konfiguracija PostgreSQL/Docker/HTTPS instalacije.
- [Pregled validacije](server/engineering/ZADENVO_VALIDATION.md) — najnoviji rezultati i historijski zapis SQLite provjera.
- [PostgreSQL validacija](server/engineering/ZADENVO_POSTGRES_VALIDATION.md) — čista instalacija i svih 78 serverskih testova.
- [Provjera u pregledniku](server/engineering/ZADENVO_BROWSER_VALIDATION.md) — 22 provjere stvarnih korisničkih tokova u lokalnom Chromium pregledniku.
- `engineering/brand/ZADENVO.md` — radni identitet i stvarni status provjere naziva/domene.
- `engineering/SERVER_RELEASE_STATUS.md` — trenutni status integracije.

Naplata je podrazumijevano isključena. Domena `zadenvo.com` je kandidat; nije kupljena ni konfigurirana. Provjera prava na naziv nije završena.

## Najnovije potvrđene provjere

Provjere od 25.10.2026. izvršene su nad stvarnom aplikacijom i odvojenim lokalnim PostgreSQL bazama:

| Provjera | Rezultat |
|---|---|
| Čista instalacija na PostgreSQL-u 17.9 | Migracije, sistemska provjera i provjere usklađenosti migracija prošle. |
| Postojeći serverski testovi | **78/78 prošlo, 0 preskočenih**, uključujući istovremenu kupovinu posljednjeg komada. |
| Chromium 151.0.7922.34 | **22/22 provjere prošle**, bez zabilježenih JavaScript grešaka. |

Provjere u pregledniku obuhvatile su registraciju, potvrdu e-maila testnim potpisanim linkom, prodavačku prijavu i moderaciju, dodavanje artikla s fotografijom, prikaz istog artikla drugom kupcu, izračun cijene, adresu, sačuvane artikle, pretragu, zaštitu administracije i mobilni prikaz. Nepodešena naplata ostala je blokirana. Stvarna SMTP isporuka i vanjski Stripe/Connect tokovi nisu provjereni.

Službeni DPMA upit za tačan naziv `ZADENVO` vratio je **0 rezultata**; [zapis konkretnog upita](engineering/brand/zadenvo.dpma-check-2026-10-25.json) ne predstavlja potpunu provjeru sličnih naziva niti konačnu potvrdu prava na brend.

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

Vidi [prihvatne kriterije](server/engineering/ACCEPTANCE.md) i [upute za instalaciju](server/engineering/DEPLOYMENT_BS.md). Preostaju provjera Docker instalacije i javnog hostinga, stvarni testni Stripe/Connect tokovi, SMTP isporuka, sigurnosne kopije i obnova, potpuna provjera prava na naziv i pravna priprema. Nisu kupljene nove usluge niti uključena stvarna naplata.
