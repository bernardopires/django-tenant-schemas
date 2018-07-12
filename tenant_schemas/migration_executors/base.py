import logging
import os
import sys

from django.conf import settings
from django.core.management.commands.migrate import Command as MigrateCommand
from django.db import transaction
from tenant_schemas.utils import get_public_schema_name


class MigrationExecutor(object):
    codename = None
    LOGGER_NAME = 'migration'

    def __init__(self, args, options):
        self.args = args
        self.options = options
        self.logger = self.get_or_create_logger()

    def run_migrations(self, tenants):
        public_schema_name = get_public_schema_name()
        if public_schema_name in tenants:
            self.logger.info("Started migration for public tenant")
            self.run_migration(public_schema_name)
            tenants.pop(tenants.index(public_schema_name))
        if tenants:
            self.logger.info("Started migrations for {} private tenants".format(len(tenants)))
            self.run_tenant_migrations(tenants)

    def run_migration(self, schema_name, allow_atomic=True):
        from django.core.management import color
        from django.core.management.base import OutputWrapper
        from django.db import connection

        style = color.color_style()
        executor_codename = self.codename

        def style_func(msg):
            return '[%s:%s] %s' % (
                style.NOTICE(executor_codename),
                style.NOTICE(schema_name),
                msg
            )

        stdout = OutputWrapper(sys.stdout)
        stdout.style_func = style_func
        stderr = OutputWrapper(sys.stderr)
        stderr.style_func = style_func
        if int(self.options.get('verbosity', 1)) >= 1:
            stdout.write(style.NOTICE("=== Running migrate for schema %s" % schema_name))

        connection.set_schema(schema_name)

        try:
            MigrateCommand(stdout=stdout, stderr=stderr).execute(*self.args, **self.options)
        except Exception as e:
            self.logger.error('Migration fails for tenant {}. Error: {}'.format(schema_name, str(e)))
            raise

        try:
            transaction.commit()
            connection.close()
            connection.connection = None
        except transaction.TransactionManagementError:
            if not allow_atomic:
                raise

            # We are in atomic transaction, don't close connections
            pass

        connection.set_schema_to_public()

    def run_tenant_migrations(self, tenant):
        raise NotImplementedError

    @classmethod
    def get_or_create_logger(cls):
        """
        Return logger for migration executor.
        Configure logger handlers if they are not already configured
        """
        logger = logging.getLogger(cls.LOGGER_NAME)
        if len(logger.handlers) == 0:
            logger_path = getattr(settings, 'TENANT_MIGRATION_LOGGER_PATH', '')
            hdlr = logging.FileHandler(os.path.join(logger_path, '{}.log'.format(cls.LOGGER_NAME)))
            formatter = logging.Formatter('[%(asctime)s][%(levelname)s] %(message)s')
            hdlr.setFormatter(formatter)
            logger.addHandler(hdlr)
            logger.setLevel(logging.INFO)

        return logger
