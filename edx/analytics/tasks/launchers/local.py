"""
Main method for running tasks.

  Invoke a task by running `launch-task` with task's classname and
  arguments for Luigi and for the task.  Use `remote-task` to run
  to submit the task to run on an EMR cluster.

Example command lines for various tasks:

* CourseEnrollmentChangesPerDay:

  launch-task --local-scheduler CourseEnrollmentChangesPerDay
        --name mytest --src input --include 'tracking*' --include '2012*'
        --dest output7

  remote-task --job-flow-id <job-id> --branch <branch-name> --remote-name run-20140204
        --local-scheduler CourseEnrollmentChangesPerDay
        --name run-20140204 --src s3://edx-all-tracking-logs --include 'prod-edx*/tracking.*-201312*.gz'
        --include 'prod-edx*/tracking.*-2014*.gz' --dest s3://edx-analytics-scratch/output

"""

import os.path
import logging

import boto
import argparse
import filechunkio
import cjson

import luigi
import luigi.configuration
import luigi.hadoop

from stevedore.extension import ExtensionManager

log = logging.getLogger(__name__)

OVERRIDE_CONFIGURATION_FILE = 'override.cfg'


def main():
    # In order to see errors during extension loading, you can uncomment the next line.
    # logging.basicConfig(level=logging.DEBUG)

    # Load tasks configured using entry_points
    # TODO: launch tasks by their entry_point name
    ExtensionManager('edx.analytics.tasks')

    configuration = luigi.configuration.get_config()
    if os.path.exists(OVERRIDE_CONFIGURATION_FILE):
        configuration.add_config_path(OVERRIDE_CONFIGURATION_FILE)

    # Tell luigi what dependencies to pass to the Hadoop nodes
    # - argparse is not included by default in python 2.6, but is required by luigi.
    # - boto is used for all direct interactions with s3.
    # - cjson is used for all parsing event logs.
    # - filechunkio is used for multipart uploads of large files to s3.
    luigi.hadoop.attach(argparse, boto, cjson, filechunkio)

    # TODO: setup logging for tasks or configured logging mechanism

    # Launch Luigi using the default builder
    luigi.run()


if __name__ == '__main__':
    main()
