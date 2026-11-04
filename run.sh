#!/bin/bash
# Run an Isaac Sim demo script with conda stripped from the environment.
unset CONDA_PREFIX CONDA_DEFAULT_ENV CONDA_SHLVL PYTHONPATH
export PATH=$(echo "$PATH" | tr ':' '\n' | grep -v miniconda3 | paste -sd:)
exec ~/isaacsim/python.sh "$@"
