#!/usr/bin/env bash
# Verify the reviewed Linux binary before executing it; never install a moving tag.
set -euo pipefail
lint_directory=$(mktemp -d)
trap 'rm -rf "$lint_directory"' EXIT
curl --fail --silent --show-error --location --retry 2 --max-time 60 \
  https://github.com/rhysd/actionlint/releases/download/v1.7.12/actionlint_1.7.12_linux_amd64.tar.gz \
  -o "$lint_directory/actionlint.tar.gz"
printf '%s  %s\n' \
  8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8 \
  "$lint_directory/actionlint.tar.gz" | sha256sum --check --status
tar -xzf "$lint_directory/actionlint.tar.gz" -C "$lint_directory" actionlint
"$lint_directory/actionlint" .github/workflows/*.yml .github/workflow-templates/*.yml
