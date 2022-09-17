#!/bin/sh
set -e
set -x
pytest \
    --failed-first \
    --exitfirst \
    $@
