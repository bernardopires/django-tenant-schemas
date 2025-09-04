import os

from tenant_schemas.migration_executors.base import MigrationExecutor
from tenant_schemas.migration_executors.parallel import ParallelExecutor
from tenant_schemas.migration_executors.standard import StandardExecutor


def get_executor(codename=None):
    codename = codename or os.environ.get('EXECUTOR', StandardExecutor.codename)

    for klass in MigrationExecutor.__subclasses__():
        if klass.codename == codename:
            return klass

    raise NotImplementedError('No executor with codename %s' % codename)
