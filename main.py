#!/usr/bin/env python3
"""Point d'entrée : python main.py {fetch,sort,import}"""

import sys

from spotify_sort.cli import main

if __name__ == "__main__":
    sys.exit(main())
