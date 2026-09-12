#!/bin/bash

cd "$(dirname "$0")"
./refresh_and_deploy.sh
status=$?
printf '\nFinished with exit code %s. Press Enter to close.\n' "$status"
read -r
exit "$status"