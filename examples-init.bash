#!/usr/bin/bash

# configuration
DVCSTORE_DIR='/mnt/data/dvcstore'
PYTHON=python3

# safety
#   -e: exit on non-zero status,
#   -u: exit on undefined variables,
#   -o pipefail: prevent errors in pipeline from being masked
# http://redsymbol.net/articles/unofficial-bash-strict-mode/
# https://gist.github.com/mohanpedala/1e2ff5661761d3abd0385e8223e16425
set -euo pipefail

# try change directory to directory with this script
# best effort; do not fail if it fails
INIT_SCRIPT_PATH="$(realpath "$0")"
INIT_SCRIPT_DIR="${INIT_SCRIPT_PATH%/*}"
if [ -d "$INIT_SCRIPT_DIR" ]; then
    # shellcheck disable=SC2164
    cd "$INIT_SCRIPT_DIR"
fi

# initialize virtualenv, if needed
echo "Checking for virtualenv (.venv)"
if [ ! -e .venv/bin/activate ]; then
    $PYTHON -m venv .venv
fi

if [ -z "$VIRTUAL_ENV" ]; then
    echo "Run 'source .venv/bin/activate'"
    echo "then re-run this script '$0'"
    exit
fi

# virtualenv is initialized
echo "Installing 'patchscope' (in editable mode), and its dependencies"
pip install -q --upgrade --editable .[examples]

# configuring DVC remote
DVC_REMOTES="$(dvc remote list)"
if grep -q -F -e "$DVCSTORE_DIR" <<<"$DVC_REMOTES"; then
    echo "DVC storage looks to be configured correctly:"
    echo "    $DVC_REMOTES"
else
    echo "Adding local storage to .dvc/config.local"
    mkdir -p '.dvc/'
    cat <<-EOF >>.dvc/config.local
    [core]
        remote = local
    ['remote "local"']
        url = $DVCSTORE_DIR
EOF
fi

# check if we are inside Git repository, and if it is not the case,
# configure DVC to not require to be run from inside git repo
if [ "$(git rev-parse --is-inside-work-tree)" = "true" ]; then
    GIT_REPO_TOPLEVEL="$(realpath "$(git rev-parse --show-toplevel)")"
    if [ "$INIT_SCRIPT_DIR" != "$GIT_REPO_TOPLEVEL" ]; then
        echo "WARNING: possibly incorrect git repository found:"
        echo "- top directory of git repo:  $GIT_REPO_TOPLEVEL"
        echo "- directory with this script: $INIT_SCRIPT_DIR"
    fi
else
    echo "Not inside Git repository; configuring DVC to handle this case"
    dvc config --local core.no_scm true
fi


# getting data from DVC
echo "Retrieving data from DVC"
dvc pull
