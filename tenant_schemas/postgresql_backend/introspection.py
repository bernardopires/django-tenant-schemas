from django.db.backends.base.introspection import TableInfo
from django.db.backends.postgresql_psycopg2.introspection import (
    DatabaseIntrospection,
    FieldInfo,
)
from django.utils.encoding import force_text


def _build_table_info(row):
    return TableInfo(row[0], {'r': 't', 'v': 'v'}.get(row[1]))


def _build_field_info(col, field_map):
    col_name = force_text(col[0])

    info_args = [col_name]
    info_args.extend(col[1:6])

    # is nullable
    info_args.append(field_map[col_name][0] == 'YES')

    # default value
    info_args.append(field_map[col_name][1])

    return FieldInfo(*info_args)


class DatabaseSchemaIntrospection(DatabaseIntrospection):
    _get_table_list_query = """
        SELECT c.relname, c.relkind
        FROM pg_catalog.pg_class c
        LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind IN ('r', 'v', '')
            AND n.nspname = %(schema)s
            AND pg_catalog.pg_table_is_visible(c.oid)
    """

    _get_table_description_query = """
        SELECT column_name, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = %(table)s
            AND table_schema = %(schema)s
    """

    _get_relations_query = """
        SELECT c2.relname, a1.attname, a2.attname, con.conkey, con.confkey
        FROM pg_catalog.pg_constraint con
        LEFT JOIN pg_catalog.pg_class c1 ON con.conrelid = c1.oid
        LEFT JOIN pg_catalog.pg_class c2 ON con.confrelid = c2.oid
        LEFT JOIN pg_catalog.pg_attribute a1 ON c1.oid = a1.attrelid
            AND a1.attnum = con.conkey[1]
        LEFT JOIN pg_catalog.pg_attribute a2 ON c2.oid = a2.attrelid
            AND a2.attnum = con.confkey[1]
        LEFT JOIN pg_catalog.pg_namespace n1 ON n1.oid = c1.connamespace
        WHERE c1.relname = %(table)s
            AND n1.nspname = %(schema)s
            AND con.contype = 'f'
    """

    _get_key_columns_query = """
        SELECT kcu.column_name, ccu.table_name AS referenced_table,
            ccu.column_name AS referenced_column
        FROM information_schema.constraint_column_usage ccu
        LEFT JOIN information_schema.key_column_usage kcu
            ON ccu.constraint_catalog = kcu.constraint_catalog
                AND ccu.constraint_schema = kcu.constraint_schema
                AND ccu.constraint_name = kcu.constraint_name
        LEFT JOIN information_schema.table_constraints tc
            ON ccu.constraint_catalog = tc.constraint_catalog
                AND ccu.constraint_schema = tc.constraint_schema
                AND ccu.constraint_name = tc.constraint_name
        WHERE kcu.table_name = %(table)s
            AND kcu.table_schame = %(schema)s
            AND tc.constraint_type = 'FOREIGN KEY'
    """

    _get_indexes_query = """
        SELECT attr.attname, idx.indkey, idx.indisunique, idx.indisprimary
        FROM pg_catalog.pg_class c, pg_catalog.pg_class c2,
            pg_catalog.pg_index idx, pg_catalog.pg_attribute attr,
            pg_catalog.pg_namespace n
        WHERE c.oid = idx.indrelid
            AND idx.indexrelid = c2.oid
            AND attr.attrelid = c.oid
            AND attr.attnum = idx.indkey[0]
            AND c.relnamespace = n.oid
            AND c.relname = %(table)s
            AND n.nspname = %(schema)s
    """

    _get_constaints_query = """
        SELECT
            kc.constraint_name,
            kc.column_name,
            c.constraint_type,
            array(SELECT table_name::text || '.' || column_name::text
                  FROM information_schema.constraint_column_usage
                  WHERE constraint_name = kc.constraint_name)
        FROM information_schema.key_column_usage AS kc
        JOIN information_schema.table_constraints AS c ON
            kc.table_schema = c.table_schema AND
            kc.table_name = c.table_name AND
            kc.constraint_name = c.constraint_name
        WHERE
            kc.table_schema = %(schema)s AND
            kc.table_name = %(table)s
        ORDER BY kc.ordinal_position ASC
    """

    _get_check_constraints_query = """
        SELECT kc.constraint_name, kc.column_name
        FROM information_schema.constraint_column_usage AS kc
        JOIN information_schema.table_constraints AS c ON
            kc.table_schema = c.table_schema AND
            kc.table_name = c.table_name AND
            kc.constraint_name = c.constraint_name
        WHERE
            c.constraint_type = 'CHECK' AND
            kc.table_schema = %(schema)s AND
            kc.table_name = %(table)s
    """

    _get_index_constraints_query = """
        SELECT
            c2.relname,
            ARRAY(
                SELECT (
                    SELECT attname
                    FROM pg_catalog.pg_attribute
                    WHERE attnum = i AND attrelid = c.oid
                )
                FROM unnest(idx.indkey) i
            ),
            idx.indisunique,
            idx.indisprimary
        FROM pg_catalog.pg_class c, pg_catalog.pg_class c2,
            pg_catalog.pg_index idx, pg_catalog.pg_namespace n
        WHERE c.oid = idx.indrelid
            AND idx.indexrelid = c2.oid
            AND n.oid = c.relnamespace
            AND c.relname = %(table)s
            AND n.nspname = %(schema)s
    """

    def get_table_list(self, cursor):
        """
        Returns a list of table names in the current database and schema.
        """

        cursor.execute(self._get_table_list_query, {
            'schema': self.connection.schema_name,
        })

        return [
            _build_table_info(row)
            for row in cursor.fetchall()
            if row[0] not in self.ignored_tables
        ]

    def get_table_description(self, cursor, table_name):
        """
        Returns a description of the table, with the DB-API
        cursor.description interface.
        """

        # As cursor.description does not return reliably the nullable property,
        # we have to query the information_schema (#7783)
        cursor.execute(self._get_table_description_query, {
            'schema': self.connection.schema_name,
            'table': table_name
        })

        field_map = {line[0]: line[1:] for line in cursor.fetchall()}

        cursor.execute('SELECT * FROM %s.%s LIMIT 1' % (
            self.connection.schema_name,
            self.connection.ops.quote_name(table_name),
        ))

        return [
            _build_field_info(line, field_map)
            for line in cursor.description
        ]

    def get_relations(self, cursor, table_name):
        """
        Returns a dictionary of
        {field_name: (field_name_other_table, other_table)}
        representing all relationships to the given table.
        """
        cursor.execute(self._get_relations_query, {
            'schema': self.connection.schema_name,
            'table': table_name,
        })
        relations = {}
        for row in cursor.fetchall():
            relations[row[1]] = (row[2], row[0])
        return relations

    def get_key_columns(self, cursor, table_name):
        cursor.execute(self._get_key_columns_query, {
            'schema': self.connection.schema_name,
            'table': table_name,
        })
        return list(cursor.fetchall())

    def get_indexes(self, cursor, table_name):
        # This query retrieves each index on the given table, including the
        # first associated field name
        cursor.execute(self._get_indexes_query, {
            'schema': self.connection.schema_name,
            'table': table_name,
        })

        indexes = {}
        for row in cursor.fetchall():
            # row[1] (idx.indkey) is stored in the DB as an array.
            # It comes out as a string of space-separated integers.
            # This designates the field indexes (1-based) of the fields
            # that have indexes on the table. Here, we skip any indexes
            # across multiple fields.
            if ' ' in row[1]:
                continue
            if row[0] not in indexes:
                indexes[row[0]] = {'primary_key': False, 'unique': False}
            # It's possible to have the unique and PK constraints
            # in separate indexes.
            if row[3]:
                indexes[row[0]]['primary_key'] = True
            if row[2]:
                indexes[row[0]]['unique'] = True
        return indexes

    def get_constraints(self, cursor, table_name):
        """
        Retrieves any constraints or keys (unique, pk, fk, check, index)
        across one or more columns.
        """
        constraints = {}

        # Loop over the key table, collecting things as constraints
        # This will get PKs, FKs, and uniques, but not CHECK
        cursor.execute(self._get_constaints_query, {
            'schema': self.connection.schema_name,
            'table': table_name,
        })

        for constraint, column, kind, used_cols in cursor.fetchall():
            # If we're the first column, make the record
            if constraint not in constraints:
                constraints[constraint] = {
                    "columns": [],
                    "primary_key": kind.lower() == "primary key",
                    "unique": kind.lower() in ["primary key", "unique"],
                    "foreign_key":
                        tuple(used_cols[0].split(".", 1))
                        if kind.lower() == "foreign key"
                        else None,
                    "check": False,
                    "index": False,
                }
            # Record the details
            constraints[constraint]['columns'].append(column)

        # Now get CHECK constraint columns
        cursor.execute(self._get_check_constraints_query, {
            'schema': self.connection.schema_name,
            'table': table_name,
        })

        for constraint, column in cursor.fetchall():
            # If we're the first column, make the record
            if constraint not in constraints:
                constraints[constraint] = {
                    "columns": [],
                    "primary_key": False,
                    "unique": False,
                    "foreign_key": None,
                    "check": True,
                    "index": False,
                }
            # Record the details
            constraints[constraint]['columns'].append(column)

        # Now get indexes
        cursor.execute(self._get_index_constraints_query, {
            'schema': self.connection.schema_name,
            'table': table_name,
        })

        for index, columns, unique, primary in cursor.fetchall():
            if index not in constraints:
                constraints[index] = {
                    "columns": list(columns),
                    "primary_key": primary,
                    "unique": unique,
                    "foreign_key": None,
                    "check": False,
                    "index": True,
                }

        return constraints
