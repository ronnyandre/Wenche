"""
Innsending av skattemelding for AS via Skatteetaten/Altinn.

STATUS: Krever registrering som systemleverandør hos Skatteetaten.
Modulen er klargjort for implementasjon, men kan ikke sende inn
til Skatteetatens API uten en godkjent systemleverandør-klient.

Slik registrerer du deg:
  1. Gå til https://skatteetaten.github.io/api-dokumentasjon/
  2. Les dokumentasjonen for "Skattemelding for næringsdrivende"
  3. Registrer systemet ditt som systemleverandør
  4. Oppdater .env med SKATTEETATEN_CLIENT_ID og konfigurer
     Maskinporten-tilgang

Fristen for skattemelding for AS er normalt 31. mai.
"""

import os

from wenche.altinn_client import AltinnClient
from wenche.models import Aarsregnskap


def send_inn(
    regnskap: Aarsregnskap,
    klient: AltinnClient,
    dry_run: bool = False,
) -> None:
    """
    Sender inn skattemelding for AS.

    Ikke implementert ennå — avventer registrering som systemleverandør.
    """
    raise NotImplementedError(
        "\nSkattemelding via API krever registrering som systemleverandør hos Skatteetaten.\n"
        "\nSlik kommer du i gang:\n"
        "  1. Les dokumentasjonen: https://skatteetaten.github.io/api-dokumentasjon/\n"
        "  2. Registrer deg som systemleverandør (gratis)\n"
        "  3. Implementer Maskinporten-autentisering i wenche/auth.py\n"
        "  4. Implementer skattemelding-innsending her\n"
        "\nInntil videre kan du sende inn skattemeldingen manuelt på:\n"
        "  https://www.skatteetaten.no/"
    )
