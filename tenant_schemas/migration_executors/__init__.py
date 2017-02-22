from tenant_schemas.migration_executors.base import BaseMigrationExecutor
from tenant_schemas.migration_executors.parallel import ParallelExecutor
from tenant_schemas.migration_executors.standard import StandardExecutor


def get_executor(name=None):
    for klass in BaseMigrationExecutor.__subclasses__():
        if klass.name == name:
            return klass

    raise NotImplementedError(
        'No migration executor with name {name}'.format(name=name)
    )
