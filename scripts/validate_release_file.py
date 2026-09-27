"""Validate a release manifest before any operator-controlled rollout."""

import json
import sys
from pathlib import Path

from scripts.release_manifest import manifest


def main():
    data = json.loads(Path(sys.argv[1]).read_text())
    checked = manifest(
        data['api']['image'],
        data['web']['image'],
        data['api']['commit'],
        data['web']['commit'],
    )
    if data['contract_version'] != checked['contract_version']:
        raise ValueError('incompatible contract version')
    print('Validated immutable image pair; this does not authorize deployment.')


if __name__ == '__main__':
    main()
