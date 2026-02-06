#!/usr/bin/env python

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".devcontainer" / "dev.env")

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "starshield.settings")
    os.environ.setdefault("DJANGO_CONFIGURATION", "Dev")

    from configurations.management import execute_from_command_line

    execute_from_command_line(sys.argv)
