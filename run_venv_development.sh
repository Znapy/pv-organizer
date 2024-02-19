#!/usr/bin/env bash
# Launch the development environment: pylsp in pv-organizer venv and spyder in spyder venv.

ss -tulpn | grep 2087
set -e

OLD_PYTHONPATH="$PYTHONPATH"
export PYTHONPATH="$( dirname -- "$( readlink -f -- "$0"; )"; )"

OLD_MYPYPATH="$MYPYPATH"
export MYPYPATH="$PYTHONPATH"

echo "PYTHONPATH is: $PYTHONPATH"
bash -c "source $PYTHONPATH/.venv/bin/activate && pylsp --tcp" &
bash -c "source ~/env-py/spyder/bin/activate && spyder --new-instance --conf-dir '$PYTHONPATH/.spyproject/spyder-py3'"

export PYTHONPATH="$OLD_PYTHONPATH"
export MYPYPATH="$OLD_MYPYPATH"
