# Zadenvo — odabrani radni identitet

Korisnik je 25.10.2026. izabrao **ZADENVO** i odobrio nastavak razvoja pod tim radnim imenom. Raniji MERAVIO je historijski kandidat.

## Identitet

- Naziv u interfejsu: **Zadenvo**; naglašeni natpis: **ZADENVO**.
- Izgovor za potrebe predstavljanja: **za-den-vo**.
- Opis: marketplace za poslovne i privatne prodavače.
- Kratka poruka: **Pronađi svoje.**
- Paleta: tamnoplava `#15283E`, tirkizna `#116C63`, bijela `#FFFFFF`.
- Znak: jednostavan geometrijski **Z**, uz čitljiv natpis; bez kopiranja tuđih logotipa.

Ovo je razvojni identitet. Nema registracije žiga, kupovine domene ili tvrdnje o završenoj pravnoj provjeri.

## Šta je stvarno provjereno

Direktni upit javnom Verisign RDAP registru za `zadenvo.com` vratio je HTTP 404 (nema pronađene registracije) 25.10.2026. u 18:58:36 UTC. Sačuvan zapis je `zadenvo.domain-check-2026-10-25.json`. To nije potvrđena narudžba registratora niti rezervacija domene.

U preliminarnoj javnoj web-pretrazi nije pronađena prepoznatljiva istoimena firma ili marketplace. Pretraženi su tačan naziv i varijante ZADENO, ZADENCO, ZAVENVO, ZADENVA, SADENVO i ZADEVO. Nepovezani tekstualni nalazi nisu tretirani kao potvrda trgovačkog brenda. Web-pretraga nije potpuni registar ranijih prava.

## Granice provjere žiga

- [DPMAregister](https://register.dpma.de/DPMAregister/marke/basis): 25.10.2026. podnesen je normalni formular s upitom `marke=ZADENVO`, bez ograničenja klase, datuma ili samo važećih zapisa. Njemački, evropski i međunarodni skup zapisa bili su uključeni. Odgovor HTTP 200 potvrdio je **0 rezultata za taj upit**. Sanitiziran zapis je `zadenvo.dpma-check-2026-10-25.json`; privatno stanje formulara nije sačuvano u repozitoriju.
- [TMview](https://www.tmdn.org/tmview/): dostupna je aplikacijska stranica, bez rezultata pretrage u korištenom pristupu.
- [EUIPO eSearch](https://euipo.europa.eu/eSearch/): pristup je vratio grešku 502.
- [WIPO Global Brand Database](https://branddb.wipo.int/): CAPTCHA je spriječila dobijanje rezultata.

Nulti rezultat navedenog DPMA upita nije nezavisna provjera EUIPO/WIPO niti procjena sličnih znakova. DPMA ne jamči potpunost i tačnost svojih evropskih i međunarodnih zapisa. Prema [smjernicama DPMA](https://www.dpma.de/english/trade_marks/trade_mark_search/index.html), provjera treba obuhvatiti identične i slične ranije znakove te relevantna EU i međunarodna prava. Ta provjera ostaje otvorena.

## Primjena u kodu

Serverska aplikacija je pod `server/app/`. Podrazumijevani `SITE_NAME` je radni naziv, uz mogućnost konfiguracije. Kandidat za domenu nije upisan kao aktivni origin, e-mail ili povratna adresa naplate. `PAYMENTS_MODE=disabled` ostaje početna vrijednost.

Repozitorij ostaje `nedzad07sabic-cmd/projekt-3-marketplace`; radna grana je `server-platform-v1`. Aplikacija još nije produkcijski objavljena. TimeIQ i B2B projekt nisu dio ovih izmjena.
