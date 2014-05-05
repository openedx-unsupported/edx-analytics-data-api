"""
Gather data using Sqoop table dumps run on RDBMS databases.
"""
import json

import luigi
import luigi.hadoop
import luigi.hdfs
import luigi.configuration

from edx.analytics.tasks.url import ExternalURL
from edx.analytics.tasks.url import get_target_from_url
from edx.analytics.tasks.url import url_path_join


def load_sqoop_cmd():
    """Get path to sqoop command from Luigi configuration."""
    return luigi.configuration.get_config().get('sqoop', 'command', 'sqoop')


class SqoopImportTask(luigi.hadoop.BaseHadoopJobTask):
    """
    An abstract task that uses Sqoop to read data out of a database and
    writes it to a file in CSV format.

    In order to protect the database access credentials they are
    loaded from an external file which can be secured appropriately.
    The credentials file is expected to be JSON formatted and contain
    a simple map specifying the host, port, username password and
    database.

    Parameters:
        credentials: Path to the external access credentials file.
        destination: The directory to write the output files to.
        table_name: The name of the table to import.
        num_mappers: The number of map tasks to ask Sqoop to use.
        where:  A 'where' clause to be passed to Sqoop.  Note that
            no spaces should be embedded and special characters should
            be escaped.  For example:  --where "id\<50".
        verbose: Print more information while working.

    Example Credentials File::

        {
            "host": "db.example.com",
            "port": "3306",
            "username": "exampleuser",
            "password": "example password",
            "database": "exampledata"
        }
    """
    # TODO: Defaults from config file
    credentials = luigi.Parameter()
    destination = luigi.Parameter()
    table_name = luigi.Parameter()
    num_mappers = luigi.Parameter(default=None)
    where = luigi.Parameter(default=None)
    verbose = luigi.BooleanParameter(default=False)

    def requires(self):
        return {
            'credentials': ExternalURL(url=self.credentials),
        }

    def output(self):
        return get_target_from_url(url_path_join(self.destination, self.table_name))

    def job_runner(self):
        """Use simple runner that gets args from the job and passes through."""
        return SqoopImportRunner()

    def get_arglist(self, password_file):
        """Returns list of arguments for running Sqoop."""
        arglist = [load_sqoop_cmd(), 'import']
        # Generic args should be passed to sqoop first, followed by import-specific args.
        arglist.extend(self.generic_args(password_file))
        arglist.extend(self.import_args())
        return arglist

    def generic_args(self, password_target):
        """Returns list of arguments used by all Sqoop commands, using credentials read from file."""
        cred = self._get_credentials()
        url = self.connection_url(cred)
        generic_args = ['--connect', url, '--username', cred['username']]

        if self.verbose:
            generic_args.append('--verbose')

        # write password to temp file object, and pass name of file to Sqoop:
        with password_target.open('w') as password_file:
            password_file.write(cred['password'])
            password_file.flush()
        generic_args.extend(['--password-file', password_target.path])

        return generic_args

    def import_args(self):
        """Returns list of arguments specific to Sqoop import."""
        arglist = ['--table', self.table_name, '--warehouse-dir', self.destination]
        if self.num_mappers is not None:
            arglist.extend(['--num-mappers', str(self.num_mappers)])
        if self.where is not None:
            arglist.extend(['--where', str(self.where)])

        return arglist

    def connection_url(self, _cred):
        """Construct connection URL from provided credentials."""
        raise NotImplementedError  # pragma: no cover

    def _get_credentials(self):
        """
        Gathers the secure connection parameters from an external file
        and uses them to establish a connection to the database
        specified in the secure parameters.

        Returns:
            A dict containing credentials.
        """
        cred = {}
        with self.input()['credentials'].open('r') as credentials_file:
            cred = json.load(credentials_file)
        return cred


class SqoopImportFromMysql(SqoopImportTask):
    """
    An abstract task that uses Sqoop to read data out of a database and
    writes it to a file in CSV format.

    Output format is defined by meaning of --mysql-delimiters option,
    which defines defaults used by mysqldump tool:

    * fields delimited by comma
    * lines delimited by \n
    * delimiters escaped by backslash
    * delimiters optionally enclosed by single quotes (')

    """

    def connection_url(self, cred):
        """Construct connection URL from provided credentials."""
        return 'jdbc:mysql://{host}/{database}'.format(**cred)

    def import_args(self):
        """Returns list of arguments specific to Sqoop import from a Mysql database."""
        arglist = super(SqoopImportFromMysql, self).import_args()
        arglist.extend(['--direct', '--mysql-delimiters'])
        return arglist


class SqoopImportRunner(luigi.hadoop.JobRunner):
    """Runs a SqoopImportTask by shelling out to sqoop."""

    def run_job(self, job):
        """Runs a SqoopImportTask by shelling out to sqoop."""
        # Create a temp file in HDFS to store the password,
        # so it isn't echoed by the hadoop job code.
        # It should be deleted when it goes out of scope
        # (using __del__()), but safer to just make sure.
        try:
            password_target = luigi.hdfs.HdfsTarget(is_tmp=True)
            arglist = job.get_arglist(password_target)
            luigi.hadoop.run_and_track_hadoop_job(arglist)
        finally:
            password_target.remove()
