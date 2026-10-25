# Projekt 3 — Marketplace

Razvojna web-prezentacija marketplacea za firme i privatne osobe. Odvojeno od TimeIQ-a i B2B posredovanja.

## Web-pregled

[Otvori testnu stranicu](https://nedzad07sabic-cmd.github.io/projekt-3-marketplace/)

**Nije aktivna trgovina.** Svi početni artikli i prodavači su izmišljeni. Nema stvarnih korisničkih računa, provjere identiteta, naplate, isplate, dostave ili e-mailova. Prebacivanje između kupca, prodavača i administracije služi samo testiranju interfejsa; nije autentifikacija. Ne unosite stvarne lične ili finansijske podatke.

Testni podaci ostaju u pregledniku posjetioca kada je lokalna pohrana dostupna. Posjetioci ne dijele podatke. Administratorski prikaz mijenja samo lokalnu simulaciju, ne tuđi račun. Reset briše samo lokalni demo.

## Šta je uključeno

Katalog, pretraga, filteri, detalji artikla, korpa jednog prodavača, rezervacije, simulirane narudžbe, uređivanje i odobravanje oglasa, poruke u predmetu spora, povrati prije i poslije simulirane isplate, evidencija potraživanja i izvoz/uvoz testne kopije. Probna naknada i kalkulator nisu usvojeni cjenovnik ni prognoza zarade.

## Struktura

- `docs/index.html` — izgrađena samostalna web-stranica za GitHub Pages.
- `source/` — HTML predložak, CSS, programska logika i interfejs.
- `tests/core.test.js` — lokalni testovi logike.

## Razvoj

```sh
node tests/core.test.js
python source/build.py
```

Nema npm zavisnosti ni tajnih ključeva. Nakon izmjene izvora ponovo izgradite i commitujte `docs/index.html`. GitHub Pages objavljuje `main` → `/docs`.

## Prije stvarne prodaje

Potreban je zaseban produkcijski hosting/backend, stvarna autentifikacija i kontrola pristupa, baza, odobren pružalac plaćanja za firme i privatne osobe, provjereni webhook događaji, prodavačka verifikacija, sigurnosni pregled i odgovarajuća pravna/poreska priprema. GitHub Pages se ovdje koristi isključivo za prezentaciju prototipa, ne za e-trgovinu.

GitHub Pages pravila: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits

Kod demonstracije ne pristupa vanjskim API-jima. GitHub kao hosting provajder obrađuje tehničke zahtjeve posjetilaca prema svojim pravilima privatnosti.
