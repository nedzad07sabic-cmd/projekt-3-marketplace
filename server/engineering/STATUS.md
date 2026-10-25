# Zadenvo — status aplikacije

## Implementirano u kodu
Django registracija i sesije; hash lozinke; potvrda e-maila; reset lozinke; shared server database; poslovni/privatni seller profili; odobravanje; izvorni responzivni interfejs; unos i provjera fotografija; pretraga/filteri/sortiranje/paginacija; sačuvani artikli; više prodavača u korpi; snapshot cijena, uslova i naknada; transakcijska rezervacija zaliha; procesorski Checkout adapter; webhook signature/idempotency; ručno evidentirana pošiljka i kupčeva potvrda prijema; predmeti podrške i poruke; recenzije iz završenih kupovina; provizije; transfer adapter; refund adapter i potraživanja poslije transfera; audit; email outbox; PostgreSQL/Docker/HTTPS konfiguracija; MFA za admina u produkcijskim postavkama.

## Nije predstavljeno kao završeno
Nema aktivnog hostinga ili odabrane domene za ovu serversku aplikaciju. Nema postavljenih stvarnih korisničkih tajni, bankovnih isplata, pružaočeve potvrde privatnih prodavača, vanjskog procesorskog E2E testa ili pravnog odobrenja. Nema kurirske API provjere isporuke, automatskog izdavanja zakonski validnih prodavačkih računa, dovršene DAC7 prijave, svih međunarodnih poreskih/currency pravila ili prevoda čitavog sajta. Nema Amazonove logistike, aukcija, više ponuda istog kataloškog artikla ili kapaciteta ogromnog marketplacea.

Nema seed korisnika, izmišljenih javnih proizvoda ni proizvoljnog biranja admin uloge. Raniji lokalni demo nije povezan na bazu i ne treba ga koristiti za prodaju.

## Zašto je prodaja isključena po defaultu
Živi novac i podaci ne aktiviraju se pukim uklanjanjem oznake demo. Stvarni računi i baza postoje u aplikaciji, dok adapter za naplatu treba privatnu konfiguraciju i prihvat. `readiness` vraća blokadu dok nedostaju obavezne postavke. To je sigurnosni uslov, ne fingirana naplata.

Dostupni testovi ne zamjenjuju eksterni sigurnosni pregled i produkcijsku operativnu spremnost. Stvarno izvršene provjere i njihova ograničenja navedeni su u ZADENVO_VALIDATION.md; TEST_REPORT.md čuva raniju evidenciju.

Kod je vraćen iz izvornog ZIP paketa pod `server/` u razvojnoj grani. Inicijalna migracija je generisana i sačuvana uz aplikaciju. Aktuelne provjere i preostale granice navedene su u `ZADENVO_VALIDATION.md`; ovaj zapis ne potvrđuje produkcijsku objavu.
