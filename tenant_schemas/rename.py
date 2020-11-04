from django.core.exceptions import ValidationError
from django.db import connection
from tenant_schemas.postgresql_backend.base import _is_valid_schema_name
from tenant_schemas.utils import schema_exists


def rename_schema(*, schema_name, new_schema_name):
    """
    This renames a schema to a new name. It checks to see if it exists first
    """
    cursor = connection.cursor()

    if schema_exists(new_schema_name):
        raise ValidationError("New schema name already exists")
    if not _is_valid_schema_name(new_schema_name):
        raise ValidationError("Invalid string used for the schema name.")

    sql = 'ALTER SCHEMA {0} RENAME TO {1}'.format(schema_name, new_schema_name)
    cursor.execute(sql)
    cursor.close()
