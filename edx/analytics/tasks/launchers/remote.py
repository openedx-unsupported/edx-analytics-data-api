"""Execute tasks on a remote EMR cluster."""

import argparse
import os
from subprocess import Popen
import sys
import uuid


STATIC_FILES_PATH = os.path.join(sys.prefix, 'share', 'edx.analytics.tasks')


def main():
    """Parse arguments and run the remote task."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--job-flow-id', help='EMR job flow to run the task', default=None)
    parser.add_argument('--job-flow-name', help='EMR job flow to run the task', default=None)
    parser.add_argument('--branch', help='git branch to checkout before running the task', default='release')
    parser.add_argument('--repo', help='git repository to clone')
    parser.add_argument('--remote-name', help='an identifier for this remote task')
    parser.add_argument('--wait', action='store_true', help='wait for the task to complete')
    parser.add_argument('--verbose', action='store_true', help='display very verbose output')
    parser.add_argument('--log-path', help='download luigi output streams after completing the task', default=None)
    parser.add_argument('--user', help='remote user name to connect as', default=None)
    arguments, extra_args = parser.parse_known_args()
    arguments.launch_task_arguments = extra_args

    uid = arguments.remote_name or str(uuid.uuid4())

    refresh_ansible_inventory_cache()
    return_code = run_task_playbook(arguments, uid)

    sys.exit(return_code)


def run_task_playbook(arguments, uid):
    """
    Execute the ansible playbook that triggers and monitors the remote task execution.

    Args:
        arguments (argparse.Namespace): The arguments that were passed in on the command line.
        uid (str): A unique identifier for this task execution.
    """
    extra_vars = convert_args_to_extra_vars(arguments, uid)
    args = ['task.yml', '-e', extra_vars]
    if arguments.user:
        args.extend(['-u', arguments.user])
    return run_ansible(tuple(args), arguments.verbose, executable='ansible-playbook')


def convert_args_to_extra_vars(arguments, uid):
    """
    Generate the set of variables that need to be passed in to ansible since they are expected to be set by the
    playbook.

    Args:
        arguments (argparse.Namespace): The arguments that were passed in on the command line.
        uid (str): A unique identifier for this task execution.
    """
    extra_vars = {
        'name': arguments.job_flow_id or arguments.job_flow_name,
        'branch': arguments.branch,
        'task_arguments': ' '.join(arguments.launch_task_arguments),
        'uuid': uid,
    }
    if arguments.repo:
        extra_vars['repo'] = arguments.repo
    if arguments.wait:
        extra_vars['wait_for_task'] = True
    if arguments.log_path:
        extra_vars['local_log_dir'] = arguments.log_path
    return ' '.join(["{}='{}'".format(k, extra_vars[k]) for k in extra_vars])


def refresh_ansible_inventory_cache():
    """
    Ensure the EC2 inventory cache is cleared before running ansible.

    Otherwise new resources will not be present in the inventory which will cause ansible to fail to connect to them.

    """
    executable_path = os.path.join(STATIC_FILES_PATH, 'ec2.py')
    with open('/dev/null', 'r+') as devnull:
        proc = Popen(
            [executable_path, '--refresh-cache'],
            stdin=devnull,
            cwd=STATIC_FILES_PATH
        )
        proc.wait()

    if proc.returncode != 0:
        raise RuntimeError('Unable to refresh ansible inventory cache.')


def run_ansible(args, verbose, executable='ansible'):
    """
    Execute ansible passing in the provided arguments.

    Args:
        args (iterable): A collection of arguments to pass to ansible on the command line.
        verbose (bool): Tell ansible to produce verbose output detailing exactly what commands it is executing.
        executable (str): The executable script to invoke on the command line.  Defaults to "ansible".

    """
    executable_path = os.path.join(sys.prefix, 'bin', executable)
    command = [executable_path, '-i', 'ec2.py'] + list(args)
    if verbose:
        command.append('-vvvv')

    env = dict(os.environ)
    env.update({
        # Ansible may be pulling down private git repos on the remote machine.  Forward the local agent so that the
        # remote machine can access any repos this one can.
        'ANSIBLE_SSH_ARGS': '-o ForwardAgent=yes',
        # These machines are dynamically created, so we don't know their host key.  In an ideal world we would store the
        # host key at provisioning time, however, that doesn't happen, so just trust we have the right machine.
        'ANSIBLE_HOST_KEY_CHECKING': 'False'
    })
    with open('/dev/null', 'r+') as devnull:
        proc = Popen(
            command,
            stdin=devnull,
            env=env,
            cwd=STATIC_FILES_PATH
        )
        proc.wait()

    return proc.returncode
