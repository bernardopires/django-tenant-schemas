from django.db.backends.postgresql_psycopg2.creation import DatabaseCreation as OriginalDatabaseCreation
from tenant_schemas.utils import get_public_schema_name
from django.db import connection


class SharedDatabaseCreation(OriginalDatabaseCreation):
    """
    Implements the SHARED_MODELS feature by inserting public_schema_name (usually just "public")
    before table name on table creation in the SQL like this:
        REFERENCES "public"."table_name"
    """

    def sql_for_inline_foreign_key_references(self, model, field, known_models, style):
        """
        Return the SQL snippet defining the foreign key reference for a field.
        Code copied from django.db.backends.creation.BaseDatabaseCreation and modified.
        """

        qn = self.connection.ops.quote_name
        rel_to = field.rel.to
        if rel_to in known_models or rel_to == model:
            output = [style.SQL_KEYWORD('REFERENCES') + ' ' +
                      (style.SQL_TABLE(qn(get_public_schema_name())) + '.' if rel_to in connection.shared_models else '') +
                      style.SQL_TABLE(qn(rel_to._meta.db_table)) + ' (' +
                      style.SQL_FIELD(qn(rel_to._meta.get_field(
                          field.rel.field_name).column)) + ')' +
                      self.connection.ops.deferrable_sql()
            ]
            pending = False
        else:
            # We haven't yet created the table to which this field
            # is related, so save it for later.
            output = []
            pending = True

        return output, pending
