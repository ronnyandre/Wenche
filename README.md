# Wenche

Wenche er et enkelt kommandolinjeverktøy for elektronisk innsending av regnskap og skattedokumenter til norske myndigheter via Altinn. Verktøyet er laget for holdingselskaper og småaksjeselskaper med lav aktivitet som ikke har behov for et fullverdig regnskapsprogram.

Autentisering skjer via Maskinporten med et selvgenerert RSA-nøkkelpar — ingen virksomhetssertifikat eller BankID-innlogging nødvendig.

## Støttede innsendinger

| Innsending | Mottaker | Status |
|---|---|---|
| Årsregnskap | Brønnøysundregistrene | Implementert |
| Aksjonærregisteroppgave (RF-1086) | Skatteetaten via Altinn | Implementert |
| Skattemelding for AS | Skatteetaten | Planlagt (fase 2) |

## Forutsetninger

- Python 3.11 eller nyere
- Registrert Maskinporten-klient hos Digdir (se [Registrer Maskinporten-klient](#registrer-maskinporten-klient))
- OpenSSL (for generering av nøkkelpar)

## Installasjon

```bash
git clone https://github.com/ditt-brukernavn/wenche.git
cd wenche
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Husk å aktivere det virtuelle miljøet hver gang du åpner en ny terminal:

```bash
source .venv/bin/activate
```

## Oppsett

### 1. Generer RSA-nøkkelpar

```bash
openssl genrsa -out maskinporten_privat.pem 2048
openssl rsa -in maskinporten_privat.pem -pubout -out maskinporten_offentlig.pem
```

Den private nøkkelen (`maskinporten_privat.pem`) skal aldri deles eller legges i git. Den offentlige nøkkelen lastes opp til Digdir under registrering.

### 2. Konfigurasjonsfil

```bash
cp config.example.yaml config.yaml
```

Fyll inn selskapsinfo, regnskapstall og aksjonærdata. Filen er kommentert og selvforklarende.

### 3. Miljøvariabler

```bash
cp .env.example .env
```

Fyll inn klient-ID fra Digdir og sti til privat nøkkel:

```
MASKINPORTEN_CLIENT_ID=din-client-id-her
MASKINPORTEN_PRIVAT_NOKKEL=maskinporten_privat.pem
```

For testmiljø i stedet for produksjon:

```
WENCHE_ENV=test
```

### Registrer Maskinporten-klient

Wenche bruker Maskinporten for maskin-til-maskin-autentisering. Registrering er gratis.

1. Gå til [samarbeid.digdir.no](https://samarbeid.digdir.no) og søk om tilgang som **Maskinporten-konsument**
2. Etter innvilgelse: logg inn på selvbetjeningsportalen
3. Opprett en ny Maskinporten-integrasjon
4. Last opp innholdet i `maskinporten_offentlig.pem`
5. Legg til scopes: `altinn:instances.read` og `altinn:instances.write`
6. Kopier klient-ID inn i `.env`

## Bruk

### Test uten innsending (anbefalt første gang)

Generer og valider dokumentene lokalt uten å sende noe til Altinn:

```bash
wenche send-aarsregnskap --dry-run
wenche send-aksjonaerregister --dry-run
```

`--dry-run` lagrer de genererte filene i gjeldende mappe slik at du kan inspisere dem.

### Send inn

```bash
wenche login
wenche send-aarsregnskap
wenche send-aksjonaerregister
wenche logout
```

`wenche login` autentiserer mot Maskinporten med din private nøkkel. Tokenet gjenbrukes for påfølgende kommandoer i samme sesjon.

### Alle kommandoer

```
wenche --help

Kommandoer:
  login                    Autentiser mot Maskinporten med RSA-nokkel
  logout                   Logg ut og slett lagret token
  send-aarsregnskap        Send inn arsregnskap til Bronnoysundregistrene
  send-aksjonaerregister   Send inn aksjonaerregisteroppgave (RF-1086)
  send-skattemelding       Send inn skattemelding for AS (ikke tilgjengelig enna)

Alternativer:
  --config TEXT            Sti til konfigurasjonsfil [standard: config.yaml]
  --dry-run                Generer dokument lokalt uten a sende til Altinn
```

## Frister

| Innsending | Frist |
|---|---|
| Aksjonærregisteroppgave | 31. januar |
| Årsregnskap | 31. juli |
| Skattemelding for AS | 31. mai |

## Sikkerhet

- `.env` og `config.yaml` skal aldri legges i git (de er lagt til i `.gitignore`)
- Innloggingstokenet lagres i `~/.wenche/token.json` med rettigheter begrenset til din bruker
- Wenche sender aldri data andre steder enn til ID-porten og Altinn

## Bidra

Bidrag er velkomne. Åpne gjerne en issue eller pull request. Særlig nyttig:

- Verifisering av iXBRL-format mot Brønnøysundregistrenes gjeldende taksonomi
- Implementasjon av skattemelding (krever systemleverandør-registrering hos Skatteetaten)
- Testing mot Altinn testmiljø (tt02)

## Lisens

MIT — se [LICENSE](LICENSE).
