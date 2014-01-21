import os.path
import logging

import boto
import argparse

import luigi
import luigi.configuration
import luigi.hadoop

from stevedore.extension import ExtensionManager

log = logging.getLogger(__name__)

DEFAULT_CONFIGURATION_FILE = 'default.cfg'


def main():
    # Load tasks configured using entry_points
    # TODO: launch tasks by their entry_point name
    ExtensionManager('edx.analytics.tasks')

    # Include default configuration file with task defaults
    # TODO: add a config argument to specify the location of the file
    configuration = luigi.configuration.get_config()
    configuration.add_config_path(DEFAULT_CONFIGURATION_FILE)

    if not os.path.isfile(DEFAULT_CONFIGURATION_FILE):
        log.warning('Default configuration file not found:', DEFAULT_CONFIGURATION_FILE)

    # Tell luigi what dependencies to pass to the Hadoop nodes
    # - argparse is not included by default in python 2.6
    luigi.hadoop.attach(argparse)

    # TODO: setup logging for tasks or configured logging mechanism

    # Launch Luigi using the default builder
    luigi.run()
