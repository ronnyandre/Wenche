"""
Generering av iXBRL-dokument for årsregnskap.

iXBRL (inline XBRL) er det formatet Brønnøysundregistrene krever.
Det er et HTML-dokument med innebygde XBRL-tagger som gjør at tallene
er maskinlesbare og kan vises i en nettleser.

Taksonomi: Norsk GAAP (NRS) forenklet for små foretak.
Namespace og konseptnavn er basert på Brønnøysundregistrenes tekniske
spesifikasjon. Se: https://www.brreg.no/lag-og-foreninger/regnskap/

NOTE: Verifiser eksakte konseptnavn mot gjeldende taksonomi-versjon
før første reelle innsending.
"""

import textwrap
from datetime import date

from wenche.models import Aarsregnskap


def _f(verdi: int) -> str:
    """Formater et tall for visning (tusenskilletegn, norsk format)."""
    return f"{verdi:,.0f}".replace(",", " ")


def generer_ixbrl(regnskap: Aarsregnskap) -> bytes:
    """
    Genererer et iXBRL-dokument fra et Aarsregnskap-objekt.
    Returnerer dokumentet som UTF-8-kodet bytes.
    """
    s = regnskap.selskap
    r = regnskap.resultatregnskap
    b = regnskap.balanse
    aar = regnskap.regnskapsaar
    periode_start = f"{aar}-01-01"
    periode_slutt = f"{aar}-12-31"
    dato_i_dag = date.today().isoformat()

    # XBRL-kontekster
    # c1 = øyeblikksbilde (balansedato)
    # c2 = periode (hele regnskapsåret) for resultatregnskap
    xbrl_contexts = f"""
    <xbrli:context id="c1">
      <xbrli:entity>
        <xbrli:identifier scheme="http://www.brreg.no/organisasjonsnummer">
          {s.org_nummer}
        </xbrli:identifier>
      </xbrli:entity>
      <xbrli:period>
        <xbrli:instant>{periode_slutt}</xbrli:instant>
      </xbrli:period>
    </xbrli:context>
    <xbrli:context id="c2">
      <xbrli:entity>
        <xbrli:identifier scheme="http://www.brreg.no/organisasjonsnummer">
          {s.org_nummer}
        </xbrli:identifier>
      </xbrli:entity>
      <xbrli:period>
        <xbrli:startDate>{periode_start}</xbrli:startDate>
        <xbrli:endDate>{periode_slutt}</xbrli:endDate>
      </xbrli:period>
    </xbrli:context>
    <xbrli:unit id="NOK">
      <xbrli:measure>iso4217:NOK</xbrli:measure>
    </xbrli:unit>
    """

    def tag(konsept: str, verdi: int, kontekst: str = "c1") -> str:
        """Lager en inline XBRL-tagg med synlig verdi."""
        return (
            f'<ix:nonFraction name="no-gaap:{konsept}" '
            f'contextRef="{kontekst}" unitRef="NOK" '
            f'decimals="0" format="ixt:num-dot-decimal">'
            f"{verdi}"
            f"</ix:nonFraction>"
        )

    dok = textwrap.dedent(f"""\
    <?xml version="1.0" encoding="UTF-8"?>
    <html
      xmlns="http://www.w3.org/1999/xhtml"
      xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"
      xmlns:ixt="http://www.xbrl.org/inlineXBRL/transformation/2020-02-12"
      xmlns:xbrli="http://www.xbrl.org/2003/instance"
      xmlns:xbrldi="http://xbrl.org/2006/xbrldi"
      xmlns:iso4217="http://www.xbrl.org/2003/iso4217"
      xmlns:no-gaap="http://xbrl.nrs.no/no-gaap/2022-12-31"
      xmlns:link="http://www.xbrl.org/2003/linkbase"
      xmlns:xlink="http://www.w3.org/1999/xlink">
    <head>
      <meta charset="UTF-8"/>
      <title>Årsregnskap {aar} — {s.navn}</title>
      <ix:header>
        <ix:hidden>
          {xbrl_contexts}
        </ix:hidden>
        <ix:references>
          <link:schemaRef
            xlink:type="simple"
            xlink:href="http://xbrl.nrs.no/no-gaap/2022-12-31/no-gaap-small-2022-12-31.xsd"/>
        </ix:references>
      </ix:header>
    </head>
    <body>
      <h1>Årsregnskap {aar}</h1>
      <p>
        <strong>Selskap:</strong> {s.navn}<br/>
        <strong>Organisasjonsnummer:</strong> {s.org_nummer}<br/>
        <strong>Regnskapsperiode:</strong> {periode_start} – {periode_slutt}<br/>
        <strong>Daglig leder:</strong> {s.daglig_leder}<br/>
        <strong>Styreleder:</strong> {s.styreleder}<br/>
        <strong>Dato signert:</strong> {dato_i_dag}
      </p>

      <h2>Resultatregnskap</h2>
      <table border="1" cellpadding="4" style="border-collapse:collapse">
        <tr><th>Post</th><th>Beløp (NOK)</th></tr>

        <tr><td>Driftsinntekter</td>
            <td>{tag("SalesRevenue", r.driftsinntekter.salgsinntekter, "c2")} </td></tr>
        <tr><td>Andre driftsinntekter</td>
            <td>{tag("OtherOperatingIncome", r.driftsinntekter.andre_driftsinntekter, "c2")}</td></tr>
        <tr><td><strong>Sum driftsinntekter</strong></td>
            <td><strong>{tag("TotalOperatingIncome", r.driftsinntekter.sum, "c2")}</strong></td></tr>

        <tr><td>Lønnskostnader</td>
            <td>{tag("WagesAndSalaries", r.driftskostnader.loennskostnader, "c2")}</td></tr>
        <tr><td>Avskrivninger</td>
            <td>{tag("DepreciationAmortisation", r.driftskostnader.avskrivninger, "c2")}</td></tr>
        <tr><td>Andre driftskostnader</td>
            <td>{tag("OtherOperatingExpenses", r.driftskostnader.andre_driftskostnader, "c2")}</td></tr>
        <tr><td><strong>Sum driftskostnader</strong></td>
            <td><strong>{tag("TotalOperatingExpenses", r.driftskostnader.sum, "c2")}</strong></td></tr>

        <tr><td><strong>Driftsresultat</strong></td>
            <td><strong>{tag("OperatingProfit", r.driftsresultat, "c2")}</strong></td></tr>

        <tr><td>Utbytte fra datterselskap</td>
            <td>{tag("DividendsFromSubsidiaries", r.finansposter.utbytte_fra_datterselskap, "c2")}</td></tr>
        <tr><td>Andre finansinntekter</td>
            <td>{tag("OtherFinancialIncome", r.finansposter.andre_finansinntekter, "c2")}</td></tr>
        <tr><td>Rentekostnader</td>
            <td>{tag("InterestExpense", r.finansposter.rentekostnader, "c2")}</td></tr>
        <tr><td>Andre finanskostnader</td>
            <td>{tag("OtherFinancialExpenses", r.finansposter.andre_finanskostnader, "c2")}</td></tr>

        <tr><td><strong>Resultat før skatt</strong></td>
            <td><strong>{tag("ProfitLossBeforeTax", r.resultat_foer_skatt, "c2")}</strong></td></tr>
        <tr><td><strong>Årsresultat</strong></td>
            <td><strong>{tag("ProfitLoss", r.aarsresultat, "c2")}</strong></td></tr>
      </table>

      <h2>Balanse per {periode_slutt}</h2>
      <table border="1" cellpadding="4" style="border-collapse:collapse">
        <tr><th>Post</th><th>Beløp (NOK)</th></tr>

        <tr><td colspan="2"><strong>EIENDELER</strong></td></tr>
        <tr><td>Aksjer i datterselskap</td>
            <td>{tag("InvestmentsInSubsidiaries", b.eiendeler.anleggsmidler.aksjer_i_datterselskap)}</td></tr>
        <tr><td>Andre aksjer</td>
            <td>{tag("OtherInvestments", b.eiendeler.anleggsmidler.andre_aksjer)}</td></tr>
        <tr><td>Langsiktige fordringer</td>
            <td>{tag("OtherLongTermReceivables", b.eiendeler.anleggsmidler.langsiktige_fordringer)}</td></tr>
        <tr><td><strong>Sum anleggsmidler</strong></td>
            <td><strong>{tag("TotalNonCurrentAssets", b.eiendeler.anleggsmidler.sum)}</strong></td></tr>

        <tr><td>Kortsiktige fordringer</td>
            <td>{tag("TradeAndOtherCurrentReceivables", b.eiendeler.omloepmidler.kortsiktige_fordringer)}</td></tr>
        <tr><td>Bankinnskudd</td>
            <td>{tag("CashAndCashEquivalents", b.eiendeler.omloepmidler.bankinnskudd)}</td></tr>
        <tr><td><strong>Sum omløpsmidler</strong></td>
            <td><strong>{tag("TotalCurrentAssets", b.eiendeler.omloepmidler.sum)}</strong></td></tr>

        <tr><td><strong>SUM EIENDELER</strong></td>
            <td><strong>{tag("Assets", b.eiendeler.sum)}</strong></td></tr>

        <tr><td colspan="2"><strong>EGENKAPITAL OG GJELD</strong></td></tr>
        <tr><td>Aksjekapital</td>
            <td>{tag("IssuedCapital", b.egenkapital_og_gjeld.egenkapital.aksjekapital)}</td></tr>
        <tr><td>Overkursfond</td>
            <td>{tag("SharePremium", b.egenkapital_og_gjeld.egenkapital.overkursfond)}</td></tr>
        <tr><td>Annen egenkapital</td>
            <td>{tag("RetainedEarnings", b.egenkapital_og_gjeld.egenkapital.annen_egenkapital)}</td></tr>
        <tr><td><strong>Sum egenkapital</strong></td>
            <td><strong>{tag("Equity", b.egenkapital_og_gjeld.egenkapital.sum)}</strong></td></tr>

        <tr><td>Lån fra aksjonær</td>
            <td>{tag("LongTermLiabilitiesToRelatedParties", b.egenkapital_og_gjeld.langsiktig_gjeld.laan_fra_aksjonaer)}</td></tr>
        <tr><td>Andre langsiktige lån</td>
            <td>{tag("OtherLongTermLiabilities", b.egenkapital_og_gjeld.langsiktig_gjeld.andre_langsiktige_laan)}</td></tr>
        <tr><td><strong>Sum langsiktig gjeld</strong></td>
            <td><strong>{tag("TotalNonCurrentLiabilities", b.egenkapital_og_gjeld.langsiktig_gjeld.sum)}</strong></td></tr>

        <tr><td>Leverandørgjeld</td>
            <td>{tag("TradeAndOtherPayables", b.egenkapital_og_gjeld.kortsiktig_gjeld.leverandoergjeld)}</td></tr>
        <tr><td>Skyldige offentlige avgifter</td>
            <td>{tag("CurrentTaxLiabilities", b.egenkapital_og_gjeld.kortsiktig_gjeld.skyldige_offentlige_avgifter)}</td></tr>
        <tr><td>Annen kortsiktig gjeld</td>
            <td>{tag("OtherCurrentLiabilities", b.egenkapital_og_gjeld.kortsiktig_gjeld.annen_kortsiktig_gjeld)}</td></tr>
        <tr><td><strong>Sum kortsiktig gjeld</strong></td>
            <td><strong>{tag("TotalCurrentLiabilities", b.egenkapital_og_gjeld.kortsiktig_gjeld.sum)}</strong></td></tr>

        <tr><td><strong>SUM EGENKAPITAL OG GJELD</strong></td>
            <td><strong>{tag("EquityAndLiabilities", b.egenkapital_og_gjeld.sum)}</strong></td></tr>
      </table>
    </body>
    </html>
    """)

    return dok.encode("utf-8")
