# -*- coding: utf-8 -*-

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
    def sql_create_model(self, model, style, known_models=set()):
        """
        Returns the SQL required to create a single model, as a tuple of:
            (list_of_sql, pending_references_dict)
        Original code copied from django.db.backends.postgresql_psycopg2.creation.DatabaseCreation.
        Modified with schema name insertion before table name depending on public or shared models.
        """
        opts = model._meta
        if not opts.managed or opts.proxy or opts.swapped:
            return [], {}
        final_output = []
        table_output = []
        pending_references = {}
        qn = self.connection.ops.quote_name
        for f in opts.local_fields:
            col_type = f.db_type(connection=self.connection)
            tablespace = f.db_tablespace or opts.db_tablespace
            if col_type is None:
                # Skip ManyToManyFields, because they're not represented as
                # database columns in this table.
                continue
            # Make the definition (e.g. 'foo VARCHAR(30)') for this field.
            field_output = [style.SQL_FIELD(qn(f.column)),
                style.SQL_COLTYPE(col_type)]
            # Oracle treats the empty string ('') as null, so coerce the null
            # option whenever '' is a possible value.
            null = f.null
            if (f.empty_strings_allowed and not f.primary_key and
                    self.connection.features.interprets_empty_strings_as_nulls):
                null = True
            if not null:
                field_output.append(style.SQL_KEYWORD('NOT NULL'))
            if f.primary_key:
                field_output.append(style.SQL_KEYWORD('PRIMARY KEY'))
            elif f.unique:
                field_output.append(style.SQL_KEYWORD('UNIQUE'))
            if tablespace and f.unique:
                # We must specify the index tablespace inline, because we
                # won't be generating a CREATE INDEX statement for this field.
                tablespace_sql = self.connection.ops.tablespace_sql(
                    tablespace, inline=True)
                if tablespace_sql:
                    field_output.append(tablespace_sql)
            if f.rel and f.db_constraint:
                ref_output, pending = self.sql_for_inline_foreign_key_references(
                    model, f, known_models, style)
                if pending:
                    pending_references.setdefault(f.rel.to, []).append(
                        (model, f))
                else:
                    field_output.extend(ref_output)
            table_output.append(' '.join(field_output))
        for field_constraints in opts.unique_together:
            table_output.append(style.SQL_KEYWORD('UNIQUE') + ' (%s)' %
                ", ".join(
                    [style.SQL_FIELD(qn(opts.get_field(f).column))
                     for f in field_constraints]))

        full_statement = [style.SQL_KEYWORD('CREATE TABLE') + ' ' +
                          style.SQL_TABLE(self._table_prefix(model) + qn(opts.db_table)) + ' (']
        for i, line in enumerate(table_output):  # Combine and add commas.
            full_statement.append(
                '    %s%s' % (line, ',' if i < len(table_output) - 1 else ''))
        full_statement.append(')')
        if opts.db_tablespace:
            tablespace_sql = self.connection.ops.tablespace_sql(
                opts.db_tablespace)
            if tablespace_sql:
                full_statement.append(tablespace_sql)
        full_statement.append(';')
        final_output.append('\n'.join(full_statement))

        if opts.has_auto_field:
            # Add any extra SQL needed to support auto-incrementing primary
            # keys.
            auto_column = opts.auto_field.db_column or opts.auto_field.name
            autoinc_sql = self.connection.ops.autoinc_sql(opts.db_table,
                                                          auto_column)
            if autoinc_sql:
                for stmt in autoinc_sql:
                    final_output.append(stmt)

        return final_output, pending_references

    def sql_indexes_for_field(self, model, f, style):
        output = []
        if f.db_index or f.unique:
            qn = self.connection.ops.quote_name
            db_table = model._meta.db_table
            tablespace = f.db_tablespace or model._meta.db_tablespace
            if tablespace:
                tablespace_sql = self.connection.ops.tablespace_sql(tablespace)
                if tablespace_sql:
                    tablespace_sql = ' ' + tablespace_sql
            else:
                tablespace_sql = ''

            def get_index_sql(index_name, opclass=''):
                return (style.SQL_KEYWORD('CREATE INDEX') + ' ' +
                        style.SQL_TABLE(qn(truncate_name(index_name, self.connection.ops.max_name_length()))) + ' ' +
                        style.SQL_KEYWORD('ON') + ' ' +
                        style.SQL_TABLE(self._table_prefix(model) + qn(db_table)) + ' ' +
                        "(%s%s)" % (style.SQL_FIELD(qn(f.column)), opclass) +
                        "%s;" % tablespace_sql)

            if not f.unique:
                output = [get_index_sql('%s_%s' % (db_table, f.column))]

            # Fields with database column types of `varchar` and `text` need
            # a second index that specifies their operator class, which is
            # needed when performing correct LIKE queries outside the
            # C locale. See #12234.
            db_type = f.db_type(connection=self.connection)
            if db_type.startswith('varchar'):
                output.append(get_index_sql('%s_%s_like' % (db_table, f.column),
                                            ' varchar_pattern_ops'))
            elif db_type.startswith('text'):
                output.append(get_index_sql('%s_%s_like' % (db_table, f.column),
                                            ' text_pattern_ops'))
        return output

    def sql_for_inline_foreign_key_references(self, model, field, known_models, style):
        """Return the SQL snippet defining the foreign key reference for a field.

        Original code copied from django.db.backends.creation.BaseDatabaseCreation.
        It is modified only with public schema name insert before table name.
        """

        qn = self.connection.ops.quote_name
        rel_to = field.rel.to
        if rel_to in known_models or rel_to == model:
            output = [style.SQL_KEYWORD('REFERENCES') + ' ' +
                      style.SQL_TABLE(self._table_prefix(rel_to) + qn(rel_to._meta.db_table)) + ' (' +
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
        It is modified with public schema name insert before table name.
        """
        opts = model._meta
        # Check for the original state with was_managed.
        # This way we can still instruct sycndb command to not create tables for desired models, but create foreign keys
        # e.g. if 'django.contrib.auth.User' is in SHARED_MODELS, we set it managed to False, but
        # was_managed is still True so in this case we create the foreign keys but not tables for them.
        if not opts.was_managed or opts.swapped:
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
                final_output.append(style.SQL_KEYWORD('ALTER TABLE') +
                                    ' %s ADD CONSTRAINT %s FOREIGN KEY (%s) REFERENCES %s%s (%s)%s;' %
                                    (qn(r_table),
                                     qn(truncate_name(r_name, self.connection.ops.max_name_length())),
                                     qn(r_col),
                                     self._table_prefix(model),
                                     qn(table),
                                     qn(col),
                                     self.connection.ops.deferrable_sql()))
            del pending_references[model]
        return final_output

    def _table_prefix(self, model):
        """
        Return the proper table prefix based on SHARED_APPS, TENANT_APPS, SHARED_MODELS settings and current schema.
        """
        qn = self.connection.ops.quote_name
        if model in self.connection.shared_models:
            return qn(get_public_schema_name()) + '.'
        elif model in self.connection.tenant_apps_models:
            return qn(self.connection.get_schema()) + '.'
        else:
            # models only in SHARED_APPS models don't need table prefix, because
            # when we need to operate on public schema, search path is set exclusively to it.
            return ''
