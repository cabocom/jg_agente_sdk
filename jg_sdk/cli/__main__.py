# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Punto de ejecución directa para 'python -m jg_sdk.cli'."""

import sys

from jg_sdk.cli import main

if __name__ == "__main__":
    sys.exit(main())
