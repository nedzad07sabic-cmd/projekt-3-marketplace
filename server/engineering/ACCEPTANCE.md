# Prihvat prije stvarne prodaje

- [ ] Korisnik odabrao novu marku/domenu i odobrio konkretan hosting i trošak.
- [ ] Odvojena produkcijska baza i mediji; ne dijeli TimeIQ podatke.
- [ ] HTTPS, sigurnosni headeri, cookie/CSRF, rate-limit i administrator MFA provjereni na hostu.
- [ ] Registracija, e-mail potvrda, reset lozinke i email retry rade sa stvarnim SMTP provajderom.
- [ ] Firma i povremeni privatni prodavač prihvaćeni od procesora u pisanoj potvrdi.
- [ ] Pravni status trgovca i odgovornost platforme odgovaraju implementiranom toku naplate.
- [ ] Izvršeni testni hosted Checkout, 3DS, odbijena kartica, napušten checkout i istek rezervacije.
- [ ] Potpisani stvarni testni webhook, redoslijed/duplikati događaja i promašena isporuka provjereni.
- [ ] Transakcija s dva prodavača: zalihe, pošiljke, naknade i transferi usklađeni.
- [ ] PostgreSQL konkurentni test posljednjeg artikla prošao.
- [ ] Djelimični/puni povrat prije i poslije transfera, neuspjela reversal i potraživanje pregledani.
- [ ] Provjeren idempotentni oporavak nakon prekida procesorskog zahtjeva i prekida baze.
- [ ] Definisan postupak nakon isteka procesorskog idempotency prozora; stariji neriješeni transferi/povrati se ne ponavljaju naslijepo.
- [ ] Procesorski sporovi, izgubljeni sporovi i vanjski refund usklađeni ručno; nema lažno slobodnog salda.
- [ ] Izdavanje računa i poreski tretman robe/platformskih naknada odobreni i postavljeni.
- [ ] Pravne stranice stvarno odobrene; nisu generički placeholderi.
- [ ] Provjere prodavača, pravila kategorija, product-safety, prijava nezakonitog sadržaja, prigovor i rokovi podrške uređeni.
- [ ] GDPR retencija, zahtjevi pristupa/brisanja i DAC7 prikupljanje/izvještavanje riješeni.
- [ ] Kontrolisano učitavanje slike, sigurnosna provjera koda i zavisnosti, backup i restore.
- [ ] Monitoring, rezervni fond za refund/chargeback i imenovan operater podrške.
- [ ] Potvrđeno opterećenje i operativni limit, bez obećanja Amazonove skale.

Stavke se ne označavaju automatski na osnovu lokalnih unit testova. Ovaj dokument nije dokaz da su ispunjene.
