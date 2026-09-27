"""Validate immutable paired image/source identifiers; never deploy from a moving tag."""

import argparse
import json
import re
from pathlib import Path


def manifest(api_image: str, web_image: str, api_sha: str, web_sha: str) -> dict:
    for image in (api_image, web_image):
        if not re.fullmatch(r'[a-z0-9./_-]+@sha256:[0-9a-f]{64}', image):
            raise ValueError(
                'release images must be registry-qualified immutable digests'
            )
    for revision in (api_sha, web_sha):
        if not re.fullmatch(r'[0-9a-f]{40}', revision):
            raise ValueError('release revisions must be full Git commit SHAs')
    return {
        'contract_version': '1',
        'api': {'image': api_image, 'commit': api_sha},
        'web': {'image': web_image, 'commit': web_sha},
        'production_authorized': False,
    }


def main():
    parser = argparse.ArgumentParser()
    for field in ('api-image', 'web-image', 'api-sha', 'web-sha'):
        parser.add_argument('--' + field, required=True)
    parser.add_argument('--output', type=Path, default=Path('release.json'))
    args = parser.parse_args()
    args.output.write_text(
        json.dumps(
            manifest(args.api_image, args.web_image, args.api_sha, args.web_sha),
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    main()
