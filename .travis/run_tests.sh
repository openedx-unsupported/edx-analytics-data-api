#!/bin/bash -xe
. /edx/app/analytics_api/venvs/analytics_api/bin/activate

cd /edx/app/analytics_api/analytics_api

make validate
