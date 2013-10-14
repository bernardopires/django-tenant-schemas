from django.db.backends.postgresql_psycopg2.creation import DatabaseCreation as OriginalDatabaseCreation
from django.db.backends.util import truncate_name
from tenant_schemas.utils import get_public_schema_name


class SharedDatabaseCreation(OriginalDatabaseCreation):
    """Implements the SHARED_MODELS feature.

    Insert public_schema_name (usually "public") before table name
    on table creation in the SQL like this:
        REFERENCES "public"."table_name"
    if the model is in SHARED_MODELS or is a model of an app in SHARED_APPS.
    """

    def sql_for_inline_foreign_key_references(self, model, field, known_models, style):
        """Return the SQL snippet defining the foreign key reference for a field.

        Original code copied from django.db.backends.creation.BaseDatabaseCreation.
        It is modified only with public schema name insert before table name.
        """

        qn = self.connection.ops.quote_name
        rel_to = field.rel.to
        if rel_to in known_models or rel_to == model:
            if rel_to in self.connection.shared_models and rel_to not in self.connection.tenant_models:
                table_prefix = style.SQL_TABLE(qn(get_public_schema_name())) + '.'
                print rel_to, "FORCED TO PUBLIC"
            else:
                table_prefix = ''
            output = [style.SQL_KEYWORD('REFERENCES') + ' ' +
                      table_prefix +
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

    def sql_for_pending_references(self, model, style, pending_references):
        """Returns any ALTER TABLE statements to add constraints after the fact.

        Original code copied from django.db.backends.creation.BaseDatabaseCreation.
        It is modified only with public schema name insert before table name.
        """
        opts = model._meta
        if (not opts.managed or opts.swapped) and model not in self.connection.shared_models:
            return []
        qn = self.connection.ops.quote_name
        final_output = []
        if model in pending_references:
            for rel_class, f in pending_references[model]:
                rel_opts = rel_class._meta
                r_table = rel_opts.db_table
                r_col = f.column
                table = opts.db_table
                col = opts.get_field(f.rel.field_name).column
                # For MySQL, r_name must be unique in the first 64 characters.
                # So we are careful with character usage here.
                r_name = '%s_refs_%s_%s' % (
                    r_col, col, self._digest(r_table, table))
                if model in self.connection.shared_models and model not in self.connection.tenant_models:
                    table_prefix = qn(get_public_schema_name()) + "."
                else:
                    table_prefix = ''
                final_output.append(style.SQL_KEYWORD('ALTER TABLE') +
                                    ' %s ADD CONSTRAINT %s FOREIGN KEY (%s) REFERENCES %s%s (%s)%s;' %
                                    (qn(r_table),
                                     qn(truncate_name(r_name, self.connection.ops.max_name_length())),
                                     qn(r_col),
                                     # insert '"public".' in front of table name if model is shared.
                                     table_prefix,
                                     qn(table),
                                     qn(col),
                                     self.connection.ops.deferrable_sql()))
            del pending_references[model]
        return final_output
