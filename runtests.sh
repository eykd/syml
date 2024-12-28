#!/bin/sh
set -e
set -x
ruff check --fix
ruff format
pytest \
    --failed-first \
    --exitfirst \
    --random-order \
    --cov=syml \
    --cov-branch \
    --disable-warnings \
    --verbose \
    --no-cov-on-fail $@
mypy
