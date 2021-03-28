#!/usr/bin/env bash
set -o nounset
set -o pipefail
set -o errexit

python3 -m unittest discover tests