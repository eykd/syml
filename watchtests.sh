#!/usr/bin/env bash
set -x
while sleep 1; do find . -iname '*.py' | entr -d ./runtests.sh; done
