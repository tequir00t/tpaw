#!/bin/bash

dir=$(dirname $0)

# flake8 (runs pep8 and pyflakes)
flake8 $dir/tpaw $dir/tests
if [ $? -ne 0 ]; then
    echo "Exiting due to flake8 errors. Fix and re-run to finish tests."
    exit $?
fi

# pylint
output=$(pylint --rcfile=$dir/.pylintrc $dir/tpaw 2> /dev/null)
if [ -n "$output" ]; then
    echo "--pylint--"
    echo -e "$output"
fi

# pep257
find $dir/tpaw -name [A-Za-z_]\*.py | grep  -v "/tests/" | xargs pep257 2>&1

exit 0
