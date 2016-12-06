#!/bin/bash -xe
. /edx/app/analytics_api/venvs/analytics_api/bin/activate

cd /edx/app/analytics_api/analytics_api

make diff.report
coverage xml
bash ./scripts/build-stats-to-datadog.sh
