# ZVNE-CPMS — OCPP 1.6 Central System i EVSE simulator

Ovaj repozitorij pripremljen je za laboratorijsku vježbu iz predmeta **Osnove električnih i hibridnih vozila**. Cilj vježbe je upoznati komunikaciju između sustava za upravljanje punionicama (Central System / CPMS) i punionice (EVSE) pomoću protokola OCPP 1.6 JSON.

Repozitorij sadrži dva alata za rad s OCPP 1.6 namijenjena lokalnom testiranju, obrazovanju i demonstracijama:

- `ocpp_server.py` — Central System (server) bez vanjskih ovisnosti koji prihvaća OCPP WebSocket veze i izlaže web sučelje.
- `ocpp_evse_simulator.py` — samostalan EVSE simulator koji poslužuje korisničko sučelje u pregledniku za simulaciju punionica.

**Sadržaj**

- [Laboratorijska vježba](#laboratorijska-vježba)
- [Upotreba](#upotreba)
- [Personalizirane vjerodajnice i vrijednosti](#personalizirane-vjerodajnice-i-vrijednosti)
- [Dnevnici i stanje](#dnevnici-i-stanje)
- [Prilagodba](#prilagodba)
- [Bilješke za razvoj](#bilje%C5%A1ke-za-razvoj)

## Laboratorijska vježba

U datoteci `ocpp_server.py` dio ključne programske logike zamijenjen je komentarima označenima s `TODO ISPIT`. Student treba pronaći sve takve komentare, razumjeti okolni kod i implementirati nedostajuće dijelove bez promjene zadanog OCPP sučelja.

Zadaci obuhvaćaju:

- definiranje personaliziranog identiteta punionice, lozinke i RFID oznake prema vlastitom JMBAG-u;
- autorizaciju korisničke RFID oznake;
- spremanje aktivne transakcije nakon prihvaćenog `StartTransaction` zahtjeva;
- slanje i obradu udaljenog pokretanja punjenja pomoću `RemoteStartTransaction`;
- slanje udaljenog zaustavljanja aktivne transakcije pomoću `RemoteStopTransaction`;
- pronalaženje i uklanjanje završene transakcije nakon `StopTransaction` zahtjeva.

Od studenta se očekuje da:

1. implementira sve dijelove označene komentarima `TODO ISPIT`;
2. koristi vlastite personalizirane vrijednosti prema pravilima iz teksta zadatka;
3. ne mijenja WebSocket, HTTP, UI ni ostali pomoćni kod osim ako je to izričito zatraženo;
4. pokrene Central System i EVSE simulator te demonstrira ispravan tijek komunikacije;
5. zna objasniti razliku između autentikacije punionice i autorizacije RFID oznake;
6. zna objasniti uloge poruka `Authorize`, `StartTransaction`, `StopTransaction`, `RemoteStartTransaction`, `RemoteStopTransaction` i `MeterValues`;
7. zna objasniti zašto potvrda udaljene naredbe još ne znači da je transakcija stvarno započela ili završila.

Preporučeni demonstracijski tijek:

```text
Authorize
RemoteStartTransaction
StartTransaction
MeterValues
RemoteStopTransaction
StopTransaction
```

Student treba koristiti dnevnike i web sučelje Central Systema kako bi pokazao aktivnu transakciju, mjerne vrijednosti, stanje udaljene autorizacije i završetak transakcije.

## Upotreba

Zahtjevi: Python 3.8+ (nema vanjskih paketa).

Pokretanje Central System-a (server + UI):

```bash
python3 ocpp_server.py --port 3000
```

- Server osluškuje OCPP WebSocket veze na `ws://<host>:<port>/OCPP/<chargerId>` (zadano `127.0.0.1:3000`).
- Web sučelje servera poslužuje se na zadanom UI portu (zadano `127.0.0.1:3001`). Otvorite http://127.0.0.1:3001/ za pregled sesija, dnevnika i slanje udaljenih naredbi (Remote Start/Stop).

Pokretanje EVSE simulatora (poslužuje simulator UI):

```bash
python3 ocpp_evse_simulator.py
```

- Simulator ispisuje lokalnu adresu i opcionalno otvara preglednik. Kroz UI povežite simuliranu punionicu s Central System-om.

Tipični tijek:

1. Pokrenite `ocpp_server.py`.
2. Pokrenite `ocpp_evse_simulator.py` i otvorite ispisani URL u pregledniku.
3. U `ocpp_server.py` dovršite personalizirane vrijednosti u `AUTHORIZED_CHARGERS` i `AUTHORIZED_TAGS`.
4. U simulatoru postavite `cpUrl` na `ws://localhost:3000/OCPP`, unesite svoj `Charger ID`, `Password` i `Tag`, te kliknite Connect.

## Personalizirane vjerodajnice i vrijednosti

- Autorizirane punionice definiraju se u `ocpp_server.py` u varijabli `AUTHORIZED_CHARGERS`.
- Autorizirane RFID oznake definiraju se u `AUTHORIZED_TAGS`.
- Za praktičnu provjeru koristite identifikator punionice, lozinku i RFID oznaku izvedene iz vlastitog JMBAG-a prema pravilima iz teksta zadatka.
- Početne vrijednosti `FER-<JMBAG>`, `LOZINKA-PREMA-UPUTI` i `TAG-<JMBAG>` u web sučeljima potrebno je zamijeniti vlastitim podacima.
- Postavke servera poput intervala heartbeat-a i uzorkovanja metera nalaze se u `SERVER_CONFIG`.

## Dnevnici i stanje

- Dnevnici se zapisuju u direktorij `logs/` koji se stvara pored skripti. Datoteke uključuju `server.log`, `auth.log` i dnevničke datoteke po punionici poput `<chargerId>.log`.
- Server UI vraća snapshot aktivnih sesija i nedavnih zapisa preko `/api/state`.

## Prilagodba

- Za dodavanje ili uklanjanje autoriziranih punionica ili tagova, uredite `AUTHORIZED_CHARGERS` i `AUTHORIZED_TAGS` u `ocpp_server.py`.
- UI datoteke su statični HTML-ovi u repozitoriju (`ocpp_server_ui.html`, `ocpp_evse_simulator.html`).

## Bilješke za razvoj

- Obje Python skripte namjerno su bez vanjskih ovisnosti radi jednostavnog pokretanja na sustavima s instaliranim samo sustavnim Pythonom.
- Server implementira minimalni skup OCPP 1.6 naredbi dovoljan za demonstracije (BootNotification, Heartbeat, Authorize, Start/StopTransaction, MeterValues, StatusNotification, DataTransfer).
