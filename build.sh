#!/bin/bash
set -e

export TERM=dumb
unset COLORTERM

pip install --no-color -r requirements.txt