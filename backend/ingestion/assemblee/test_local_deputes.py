"""
Test local de la function d'ingestion des députés.
Usage :
    cd backend
    source .venv/bin/activate
    python -m ingestion.assemblee.test_local_deputes
"""

import logging
import sys

from ingestion.assemblee.deputes import handle

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

if __name__ == "__main__":
    result = handle({}, {})
    print(result)
