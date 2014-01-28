
import argparse
import os
from subprocess import Popen
import sys
import uuid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--job-flow-id', help='EMR job flow to run the task')
    parser.add_argument('--branch', help='git branch to checkout before running the task', default='release')
    parser.add_argument('--repo', help='git repository to clone')
    parser.add_argument('--remote-name', help='an identifier for this remote task')
    parser.add_argument('--verbose', action='store_true', help='display very verbose output')
    arguments, extra_args = parser.parse_known_args()
    arguments.launch_task_arguments = extra_args

    change_directory_to_ansible_script_home()

    extra_vars = convert_cli_arguments_to_ansible_extra_vars(arguments)
    
    run_ansible_playbook(arguments.verbose, extra_vars)


def change_directory_to_ansible_script_home():
    os.chdir(os.path.join(sys.prefix, 'share', 'edx.analytics.tasks'))


def convert_cli_arguments_to_ansible_extra_vars(arguments):
    uid = arguments.remote_name or str(uuid.uuid4())
    extra_vars = {
        'name': arguments.job_flow_id,
        'branch': arguments.branch,
        'task_arguments': ' '.join(arguments.launch_task_arguments) + ' >/tmp/{0}.out 2>/tmp/{0}.err'.format(uid),
        'uuid': uid,
    }
    if arguments.repo:
        extra_vars['repo'] = arguments.repo
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
