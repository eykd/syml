#!/bin/sh
set -e
set -x
pytest \
    --failed-first \
    --exitfirst \
    --cov=syml \
    --cov-branch \
    --no-cov-on-fail \
    $@
