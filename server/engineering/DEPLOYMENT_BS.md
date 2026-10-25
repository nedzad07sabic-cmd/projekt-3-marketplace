# Zadenvo — priprema sačuvanih migracija

Iz korijena repozitorija prvo uđi u `server/`. Sve putanje u nastavku (`app/`, `deploy/`) odnose se na taj direktorij. Početna migracija je dio koda; za novu bazu pokreni `python app/manage.py migrate`. Komandom `python app/manage.py makemigrations --check --dry-run` provjeri da modeli i migracije odgovaraju. Nemoj ponovo generisati početnu migraciju na produkciji.

Domena `zadenvo.com` je kandidat, nije registrirana ili povezana u ovom zadatku. `SITE_NAME=Zadenvo` je radni prikaz, ne dokaz prava na naziv.

# Objava na odvojenom serveru

Ovo je serverska aplikacija, ne HTML datoteka. GitHub čuva kod. GitHub Pages ne pokreće Python, bazu ni ovaj marketplace i nije namijenjen stvarnoj prodaji. Ne mijenjati TimeIQ hosting, bazu ili domenu za ovaj projekt.

## Potrebno
Odvojen Linux/Docker server i nova domena; PostgreSQL baza; privatne tajne aplikacije; SMTP; odobren Stripe marketplace / Connect model i, posebno, povremeni privatni prodavači; pravni dokumenti i operativna provjera. Korisnik bira hosting i odobrava njegove troškove. Ovaj paket ne kupuje server, domenu ili licence.

## Instalacija
1. Klonirati repozitorij na zaseban server. Kopirati `app/.env.example` u `app/.env` i `deploy/.env.example` u `deploy/.env`.
2. Generisati zasebne jake tajne za DJANGO_SECRET_KEY i PostgreSQL. Ne objavljivati ih u GitHubu ili chatu. DATABASE_URL mora koristiti isti PostgreSQL password kao deploy/.env (URL-encode specijalnih znakova).
3. SITE_URL i ALLOWED_HOSTS moraju biti nova domena. DNS A/AAAA usmjeriti na odabrani server. Ne koristiti postojeću TimeIQ domenu bez zasebnog odobrenja.
4. Iz `deploy/`: `docker compose build`, zatim `docker compose up -d db`.
5. `docker compose run --rm web python manage.py migrate`
6. `docker compose run --rm web python manage.py bootstrap`
7. `docker compose run --rm web python manage.py createsuperuser`
8. `docker compose run --rm web python manage.py enroll_admin IME_ADMINA` — privatni terminal, sačuvati OTP u authenticatoru i ne spremati URI u javne logove.
9. `docker compose up -d web jobs proxy`. Samo proxy portovi 80/443 su javni; baza i web port nisu izloženi.
10. Provjeriti HTTPS, hostove, `/health/`, aplikacijske logove i MFA administraciju.

## Prvo staging, zatim prihvatni test
REGISTRATION_OPEN=0 i PAYMENTS_MODE=disabled po defaultu. Ne pretvarati ovo u javnu prodavnicu samo promjenom banera. Za privatno prihvatno testiranje koristiti testne Stripe ključeve, odvojene testne povezane račune i testne e-mail adrese.

PAYMENTS_MODE=test zahtijeva sk_test_ ključ i oba whsec_ sekreta. Snapshot API verzija u kodu je 2025-02-24.acacia; podesiti kompatibilnu verziju na webhook endpointu. API integraciju i Accounts v1 controller konfiguraciju treba potvrditi za konkretni Stripe račun; v2 migracija nije uključena.

Platformski endpoint `/payments/webhook/`: checkout.session.completed, checkout.session.expired, refund.created, refund.updated, refund.failed, charge.refunded, charge.dispute.created, charge.dispute.closed.
Connect endpoint `/payments/webhook/connect/`: account.updated sa zasebnim signing secretom. Ne koristiti platformski secret za taj endpoint.

Prodavač se registruje, potvrđuje e-mail, podnosi profil, administrator ga odobrava, zatim sam prolazi hosted onboarding. Povratak s onboardinga nije dokaz provjere. Status ažurira potpisani događaj ili server retrieve.

## E-mail
SMTP mora biti potvrđen za domenu. Queue worker `process_jobs --loop` šalje potvrde registracije, plaćanja, pošiljke i povrata. Password reset koristi Django SMTP direktno. Konzolni backend je samo lokalni razvoj, ne isporuka korisniku. Outbox isporuka je retry/at-least-once: prekid nakon SMTP prihvata a prije DB potvrde može poslati duplikat. Po iscrpljenju pokušaja alarm i ručna obrada su obavezni.

## Finansije i obaveze
Transfer na povezani Stripe račun nije bankovna isplata. Platforma ne pruža escrow. Kartice se ne upisuju u našu bazu. Provizije su integer cents/basis points; snapshot fee po stavci + najviša stopa iz korpe na dostavu tog prodavača. Pravilo mora biti usvojeno u ugovoru prije live prodaje.

Automatski stock restock radi samo za neplaćene, potvrđeno istekle/otkazane narudžbe. Povrat novca ne znači da je vraćena roba pregledana, zato ne povećava automatski fizičku zalihu.

Dashboard refund mimo aplikacije i procesorski spor blokiraju transfere i traže ručno usklađenje. Ne izbrisati tu blokadu bez provjere Stripe evidencije. Prenos odgovornosti, privatni prodavači, porezi, računi, GDPR, DSA/GPSR, ambalaža/elektronika gdje primjenjivo i DAC7 zahtijevaju odvojenu provjeru. Export ledger nije DAC7 obrazac.

## Backup i objava
`sh backup.sh /privatni/backup` iz deploy/. Šifrovati i čuvati odvojeno od servera; testirati vraćanje baze i slika. Tajne čuvati odvojeno. `python manage.py check --deploy` i `python manage.py readiness` su obavezne provjere, ali nisu zamjena za pravnu i vanjsku sigurnosnu reviziju.

Ne puštati javnu naplatu dok svi kriteriji iz ACCEPTANCE.md nisu potvrđeni. Posebno: testovi konkurentne kupovine na PostgreSQLu, potvrđena transakcija testnog procesora, djelimični/puni povrat poslije transfera, stvarna e-mail dostava, backup/restore i pravno prihvatljiv tok novca.
