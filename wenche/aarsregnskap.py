"""
Innsending av årsregnskap til Brønnøysundregistrene via Altinn 3.
"""

import yaml

from wenche.altinn_client import AltinnClient
from wenche.models import (
    Aarsregnskap,
    Anleggsmidler,
    Balanse,
    Driftsinntekter,
    Driftskostnader,
    Eiendeler,
    Egenkapital,
    EgenkapitalOgGjeld,
    Finansposter,
    KortsiktigGjeld,
    LangsiktigGjeld,
    Omloepmidler,
    Resultatregnskap,
    Selskap,
)
from wenche.xbrl import generer_ixbrl


def les_config(config_fil: str) -> Aarsregnskap:
    """Leser config.yaml og returnerer et Aarsregnskap-objekt."""
    with open(config_fil, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    s = cfg["selskap"]
    selskap = Selskap(
        navn=s["navn"],
        org_nummer=s["org_nummer"],
        daglig_leder=s["daglig_leder"],
        styreleder=s["styreleder"],
        forretningsadresse=s["forretningsadresse"],
        stiftelsesaar=s["stiftelsesaar"],
        aksjekapital=s["aksjekapital"],
    )

    r = cfg["resultatregnskap"]
    resultat = Resultatregnskap(
        driftsinntekter=Driftsinntekter(
            salgsinntekter=r["driftsinntekter"]["salgsinntekter"],
            andre_driftsinntekter=r["driftsinntekter"]["andre_driftsinntekter"],
        ),
        driftskostnader=Driftskostnader(
            loennskostnader=r["driftskostnader"]["loennskostnader"],
            avskrivninger=r["driftskostnader"]["avskrivninger"],
            andre_driftskostnader=r["driftskostnader"]["andre_driftskostnader"],
        ),
        finansposter=Finansposter(
            utbytte_fra_datterselskap=r["finansposter"]["utbytte_fra_datterselskap"],
            andre_finansinntekter=r["finansposter"]["andre_finansinntekter"],
            rentekostnader=r["finansposter"]["rentekostnader"],
            andre_finanskostnader=r["finansposter"]["andre_finanskostnader"],
        ),
    )

    b = cfg["balanse"]
    balanse = Balanse(
        eiendeler=Eiendeler(
            anleggsmidler=Anleggsmidler(
                aksjer_i_datterselskap=b["eiendeler"]["anleggsmidler"]["aksjer_i_datterselskap"],
                andre_aksjer=b["eiendeler"]["anleggsmidler"]["andre_aksjer"],
                langsiktige_fordringer=b["eiendeler"]["anleggsmidler"]["langsiktige_fordringer"],
            ),
            omloepmidler=Omloepmidler(
                kortsiktige_fordringer=b["eiendeler"]["omloepmidler"]["kortsiktige_fordringer"],
                bankinnskudd=b["eiendeler"]["omloepmidler"]["bankinnskudd"],
            ),
        ),
        egenkapital_og_gjeld=EgenkapitalOgGjeld(
            egenkapital=Egenkapital(
                aksjekapital=b["egenkapital_og_gjeld"]["egenkapital"]["aksjekapital"],
                overkursfond=b["egenkapital_og_gjeld"]["egenkapital"]["overkursfond"],
                annen_egenkapital=b["egenkapital_og_gjeld"]["egenkapital"]["annen_egenkapital"],
            ),
            langsiktig_gjeld=LangsiktigGjeld(
                laan_fra_aksjonaer=b["egenkapital_og_gjeld"]["langsiktig_gjeld"]["laan_fra_aksjonaer"],
                andre_langsiktige_laan=b["egenkapital_og_gjeld"]["langsiktig_gjeld"]["andre_langsiktige_laan"],
            ),
            kortsiktig_gjeld=KortsiktigGjeld(
                leverandoergjeld=b["egenkapital_og_gjeld"]["kortsiktig_gjeld"]["leverandoergjeld"],
                skyldige_offentlige_avgifter=b["egenkapital_og_gjeld"]["kortsiktig_gjeld"]["skyldige_offentlige_avgifter"],
                annen_kortsiktig_gjeld=b["egenkapital_og_gjeld"]["kortsiktig_gjeld"]["annen_kortsiktig_gjeld"],
            ),
        ),
    )

    return Aarsregnskap(
        selskap=selskap,
        regnskapsaar=cfg["regnskapsaar"],
        resultatregnskap=resultat,
        balanse=balanse,
    )


def valider(regnskap: Aarsregnskap) -> list[str]:
    """
    Validerer regnskapet og returnerer en liste med feilmeldinger.
    Tom liste betyr OK.
    """
    feil = []

    if not regnskap.balanse.er_i_balanse():
        diff = regnskap.balanse.differanse()
        feil.append(
            f"Balansen går ikke opp: eiendeler og egenkapital+gjeld "
            f"avviker med {diff:+,} NOK."
        )

    if len(regnskap.selskap.org_nummer.replace(" ", "")) != 9:
        feil.append("Organisasjonsnummeret må være 9 siffer.")

    return feil


def send_inn(regnskap: Aarsregnskap, klient: AltinnClient, dry_run: bool = False) -> None:
    """
    Sender inn årsregnskapet til Brønnøysundregistrene via Altinn.

    dry_run=True genererer og validerer iXBRL-dokumentet uten å sende.
    """
    feil = valider(regnskap)
    if feil:
        print("\nValidering mislyktes:")
        for f in feil:
            print(f"  - {f}")
        raise SystemExit(1)

    print("Validering OK.")

    ixbrl = generer_ixbrl(regnskap)
    print(f"iXBRL-dokument generert ({len(ixbrl):,} bytes).")

    if dry_run:
        utfil = f"aarsregnskap_{regnskap.regnskapsaar}_{regnskap.selskap.org_nummer}.html"
        with open(utfil, "wb") as f:
            f.write(ixbrl)
        print(f"Dry-run: dokument lagret til {utfil} — ingenting sendt til Altinn.")
        return

    print("Sender årsregnskap til Brønnøysundregistrene via Altinn...")
    instans = klient.opprett_instans("aarsregnskap", regnskap.selskap.org_nummer)
    klient.last_opp_data(
        "aarsregnskap",
        instans,
        data=ixbrl,
        content_type="application/xhtml+xml",
        data_type="aarsregnskap",
    )
    klient.fullfoor_instans("aarsregnskap", instans)

    status = klient.hent_status("aarsregnskap", instans)
    print(f"Status: {status.get('status', {}).get('value', 'ukjent')}")
    print("Årsregnskap sendt inn.")
