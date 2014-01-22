"""Remote Task

Usage: 
  remote-task [--job-flow-id=ID] [--branch=BRANCH] [--repo=REPO] [--name=NAME] [--verbose] [<launch-task-args>]

Options:
  --job-flow-id=ID      EMR job flow to run the task
  --branch=BRANCH       git branch to checkout before running the task [default: release]
  --repo=REPO           git repository to clone
  --name=NAME           an identifier for this task
  --verbose             display very verbose output
  <launch-task-args>    a single-quoted string of arguments to pass-through to launch-task on the remote machine
"""


import os
from subprocess import Popen
import sys
import uuid

from docopt import docopt


def main():
    arguments = docopt(__doc__)

    change_directory_to_ansible_script_home()

    extra_vars = convert_cli_arguments_to_ansible_extra_vars(arguments)
    
    run_ansible_playbook(arguments.get('--verbose', False), extra_vars)


def change_directory_to_ansible_script_home():
    os.chdir(os.path.join(sys.prefix, 'share', 'edx.analytics.tasks'))


def convert_cli_arguments_to_ansible_extra_vars(arguments):
    uid = arguments.get('--name') or str(uuid.uuid4())
    extra_vars = {
        'name': arguments['--job-flow-id'],
        'branch': arguments.get('--branch', 'release'),
        'task_arguments': arguments.get('<launch-task-args>', '') + ' >/tmp/{0}.out 2>/tmp/{0}.err'.format(uid),
        'uuid': uid,
    }
    if arguments['--repo']:
        extra_vars['repo'] = arguments['--repo']
    return ' '.join(["{}='{}'".format(k, extra_vars[k]) for k in extra_vars])


def run_ansible_playbook(verbose, extra_vars):
    ansible_playbook_path = os.path.join(sys.prefix, 'bin', 'ansible-playbook')
    command = [
         ansible_playbook_path, '-i', 'ec2.py', 'task.yml', '-e', extra_vars
    ]
    if verbose:
        command.append('-vvvv')

    env = dict(os.environ)
    env.update({
        'ANSIBLE_SSH_ARGS': '-o ForwardAgent=yes'
    })

    with open('/dev/null', 'rw') as devnull:
        proc = Popen(command, stdin=devnull, env=env)
        proc.communicate()
