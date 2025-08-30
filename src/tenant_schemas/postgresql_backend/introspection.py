from __future__ import unicode_literals

from collections import namedtuple

from django.db.backends.base.introspection import (
    BaseDatabaseIntrospection, FieldInfo, TableInfo,
)
try:
    # Django >= 1.11
    from django.db.models.indexes import Index
except ImportError:
    Index = None
from django.utils.encoding import force_str

fields = FieldInfo._fields
if 'default' not in fields:
    fields += ('default',)

FieldInfo = namedtuple('FieldInfo', fields)


class DatabaseSchemaIntrospection(BaseDatabaseIntrospection):
    # Maps type codes to Django Field types.
    data_types_reverse = {
        16: 'BooleanField',
        17: 'BinaryField',
        20: 'BigIntegerField',
        21: 'SmallIntegerField',
        23: 'IntegerField',
        25: 'TextField',
        700: 'FloatField',
        701: 'FloatField',
        869: 'GenericIPAddressField',
        1042: 'CharField',  # blank-padded
        1043: 'CharField',
        1082: 'DateField',
        1083: 'TimeField',
        1114: 'DateTimeField',
        1184: 'DateTimeField',
        1266: 'TimeField',
        1700: 'DecimalField',
        2950: 'UUIDField',
    }

    ignored_tables = []

    _get_table_list_query = """
        SELECT c.relname, c.relkind
        FROM pg_catalog.pg_class c
        LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind IN ('r', 'v')
           AND n.nspname = %(schema)s;
    """

    _get_table_description_query = """
        SELECT column_name, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = %(table)s
          AND table_schema = %(schema)s
    """

    _get_relations_query = """
        SELECT c2.relname, a1.attname, a2.attname
        FROM pg_constraint con
            LEFT JOIN pg_class c1 ON con.conrelid = c1.oid
            LEFT JOIN pg_class c2 ON con.confrelid = c2.oid
            LEFT JOIN pg_attribute a1 ON c1.oid = a1.attrelid AND a1.attnum = con.conkey[1]
            LEFT JOIN pg_attribute a2 ON c2.oid = a2.attrelid AND a2.attnum = con.confkey[1]
            LEFT JOIN pg_catalog.pg_namespace n1 ON n1.oid = con.connamespace
        WHERE c1.relname = %(table)s
            AND n1.nspname = %(schema)s
            AND con.contype = 'f'
    """

    _get_key_columns_query = """
        SELECT kcu.column_name, ccu.table_name AS referenced_table, ccu.column_name AS referenced_column
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
            pg_catalog.pg_index idx, pg_catalog.pg_attribute attr
        WHERE c.oid = idx.indrelid
            AND idx.indexrelid = c2.oid
            AND attr.attrelid = c.oid
            AND attr.attnum = idx.indkey[0]
            AND c.relname = %(table)s
            AND n.nspname = %(schema)s
    """

    _get_constraints_query = """
        SELECT
            c.conname,
            array(
                SELECT attname
                FROM (
                    SELECT unnest(c.conkey) AS colid,
                           generate_series(1, array_length(c.conkey, 1)) AS arridx
                ) AS cols
                  JOIN pg_attribute AS ca ON cols.colid = ca.attnum
                WHERE ca.attrelid = c.conrelid
                ORDER BY cols.arridx
            ),
            c.contype,
            (SELECT fkc.relname || '.' || fka.attname
            FROM pg_attribute AS fka
              JOIN pg_class AS fkc ON fka.attrelid = fkc.oid
            WHERE fka.attrelid = c.confrelid
              AND fka.attnum = c.confkey[1]),
            cl.reloptions
        FROM pg_constraint AS c
        JOIN pg_class AS cl ON c.conrelid = cl.oid
        JOIN pg_namespace AS ns ON cl.relnamespace = ns.oid
        WHERE ns.nspname = %(schema)s AND cl.relname = %(table)s
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
            indexname, array_agg(attname ORDER BY rnum), indisunique, indisprimary,
            array_agg(ordering ORDER BY rnum), amname, exprdef, s2.attoptions
        FROM (
            SELECT
                row_number() OVER () as rnum, c2.relname as indexname,
                idx.*, attr.attname, am.amname,
                CASE
                    WHEN idx.indexprs IS NOT NULL THEN
                        pg_get_indexdef(idx.indexrelid)
                END AS exprdef,
                CASE am.amname
                    WHEN 'btree' THEN
                        CASE (option & 1)
                            WHEN 1 THEN 'DESC' ELSE 'ASC'
                        END
                END as ordering,
                c2.reloptions as attoptions
            FROM (
                SELECT
                    *, unnest(i.indkey) as key, unnest(i.indoption) as option
                FROM pg_index i
            ) idx
            LEFT JOIN pg_class c ON idx.indrelid = c.oid
            LEFT JOIN pg_class c2 ON idx.indexrelid = c2.oid
            LEFT JOIN pg_am am ON c2.relam = am.oid
            LEFT JOIN pg_attribute attr ON attr.attrelid = c.oid AND attr.attnum = idx.key
            LEFT JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE c.relname = %(table)s
              AND n.nspname = %(schema)s
        ) s2
        GROUP BY indexname, indisunique, indisprimary, amname, exprdef, attoptions;
    """

    def get_field_type(self, data_type, description):
        field_type = super(DatabaseSchemaIntrospection, self).get_field_type(data_type, description)
        if description.default and 'nextval' in description.default:
            if field_type == 'IntegerField':
                return 'AutoField'
            elif field_type == 'BigIntegerField':
                return 'BigAutoField'
        return field_type

    def get_table_list(self, cursor):
        """
        Returns a list of table and view names in the current schema.
        """
        cursor.execute(self._get_table_list_query, {
            'schema': self.connection.schema_name
        })

        return [
            TableInfo(row[0], {'r': 't', 'v': 'v'}.get(row[1]))
            for row in cursor.fetchall()
            if row[0] not in self.ignored_tables
        ]

    def get_table_description(self, cursor, table_name):
        """
        Returns a description of the table, with the DB-API cursor.description interface.
        """

        # As cursor.description does not return reliably the nullable property,
        # we have to query the information_schema (#7783)
        cursor.execute(self._get_table_description_query, {
            'schema': self.connection.schema_name,
            'table': table_name
        })
        field_map = {line[0]: line[1:] for line in cursor.fetchall()}
        cursor.execute('SELECT * FROM %s LIMIT 1' % self.connection.ops.quote_name(table_name))

        return [
            FieldInfo(*(
                (force_str(line[0]),) +
                line[1:6] +
                (field_map[force_str(line[0])][0] == 'YES', field_map[force_str(line[0])][1])
            )) for line in cursor.description
        ]

    def get_relations(self, cursor, table_name):
        """
        Returns a dictionary of {field_name: (field_name_other_table, other_table)}
        representing all relationships to the given table.
        """
        cursor.execute(self._get_relations_query, {
            'schema': self.connection.schema_name,
            'table': table_name
        })
        relations = {}
        for row in cursor.fetchall():
            relations[row[1]] = (row[2], row[0])

        return relations

    def get_key_columns(self, cursor, table_name):
        cursor.execute(self._get_key_columns_query, {
            'schema': self.connection.schema_name,
            'table': table_name
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
            # row[1] (idx.indkey) is stored in the DB as an array. It comes out as
            # a string of space-separated integers. This designates the field
            # indexes (1-based) of the fields that have indexes on the table.
            # Here, we skip any indexes across multiple fields.
            if ' ' in row[1]:
                continue
            if row[0] not in indexes:
                indexes[row[0]] = {'primary_key': False, 'unique': False}
            # It's possible to have the unique and PK constraints in separate indexes.
            if row[3]:
                indexes[row[0]]['primary_key'] = True
            if row[2]:
                indexes[row[0]]['unique'] = True
        return indexes

    def get_constraints(self, cursor, table_name):
        """
        Retrieves any constraints or keys (unique, pk, fk, check, index) across
        one or more columns. Also retrieve the definition of expression-based
        indexes.
        """
        constraints = {}
        # Loop over the key table, collecting things as constraints. The column
        # array must return column names in the same order in which they were
        # created
        # The subquery containing generate_series can be replaced with
        # "WITH ORDINALITY" when support for PostgreSQL 9.3 is dropped.
        cursor.execute(self._get_constraints_query, {
            'schema': self.connection.schema_name,
            'table': table_name,
        })

        for constraint, columns, kind, used_cols, options in cursor.fetchall():
            constraints[constraint] = {
                "columns": columns,
                "primary_key": kind == "p",
                "unique": kind in ["p", "u"],
                "foreign_key": tuple(used_cols.split(".", 1)) if kind == "f" else None,
                "check": kind == "c",
                "index": False,
                "definition": None,
                "options": options,
            }

        # Now get indexes
        cursor.execute(self._get_index_constraints_query, {
            'schema': self.connection.schema_name,
            'table': table_name,
        })

        for index, columns, unique, primary, orders, type_, definition, options in cursor.fetchall():
            if index not in constraints:
                constraints[index] = {
                    "columns": columns if columns != [None] else [],
                    "orders": orders if orders != [None] else [],
                    "primary_key": primary,
                    "unique": unique,
                    "foreign_key": None,
                    "check": False,
                    "index": True,
                    "type": Index.suffix if type_ == 'btree' and Index else type_,
                    "definition": definition,
                    "options": options,
                }
        return constraints
