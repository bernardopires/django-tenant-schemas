from django.db.backends.postgresql_psycopg2.introspection import DatabaseIntrospection


class DatabaseSchemaIntrospection(DatabaseIntrospection):
    def get_table_list(self, cursor):
        "Returns a list of table names in the current database and schema."
        cursor.execute("""
            SELECT c.relname
            FROM pg_catalog.pg_class c
            LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind IN ('r', 'v', '')
                AND n.nspname = '%s'
                AND pg_catalog.pg_table_is_visible(c.oid)""" % self.connection.schema_name)
        return [row[0] for row in cursor.fetchall() if row[0] not in self.ignored_tables]

    def get_constraints(self, cursor, table_name):
        """
        Retrieves any constraints or keys (unique, pk, fk, check, index) across one or more columns.
        """
        constraints = {}
        # Loop over the key table, collecting things as constraints
        # This will get PKs, FKs, and uniques, but not CHECK
        cursor.execute("""
            SELECT
                kc.constraint_name,
                kc.column_name,
                c.constraint_type,
                array(SELECT table_name::text || '.' || column_name::text FROM information_schema.constraint_column_usage WHERE constraint_name = kc.constraint_name)
            FROM information_schema.key_column_usage AS kc
            JOIN information_schema.table_constraints AS c ON
                kc.table_schema = c.table_schema AND
                kc.table_name = c.table_name AND
                kc.constraint_name = c.constraint_name
            WHERE
                kc.table_schema = %s AND
                kc.table_name = %s
            ORDER BY kc.ordinal_position ASC
        """, [self.connection.schema_name, table_name])
        for constraint, column, kind, used_cols in cursor.fetchall():
            # If we're the first column, make the record
            if constraint not in constraints:
                constraints[constraint] = {
                    "columns": [],
                    "primary_key": kind.lower() == "primary key",
                    "unique": kind.lower() in ["primary key", "unique"],
                    "foreign_key": tuple(used_cols[0].split(".", 1)) if kind.lower() == "foreign key" else None,
                    "check": False,
                    "index": False,
                }
            # Record the details
            constraints[constraint]['columns'].append(column)
        # Now get CHECK constraint columns
        cursor.execute("""
            SELECT kc.constraint_name, kc.column_name
            FROM information_schema.constraint_column_usage AS kc
            JOIN information_schema.table_constraints AS c ON
                kc.table_schema = c.table_schema AND
                kc.table_name = c.table_name AND
                kc.constraint_name = c.constraint_name
            WHERE
                c.constraint_type = 'CHECK' AND
                kc.table_schema = %s AND
                kc.table_name = %s
        """, [self.connection.schema_name, table_name])
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
        cursor.execute("""
            SELECT
                c2.relname,
                ARRAY(
                    SELECT (SELECT attname FROM pg_catalog.pg_attribute WHERE attnum = i AND attrelid = c.oid)
                    FROM unnest(idx.indkey) i
                ),
                idx.indisunique,
                idx.indisprimary
            FROM pg_catalog.pg_class c, pg_catalog.pg_class c2,
                pg_catalog.pg_index idx, pg_catalog.pg_namespace n
            WHERE c.oid = idx.indrelid
                AND idx.indexrelid = c2.oid
                AND c.relname = %s
                AND c.relnamespace = n.oid
                AND n.nspname = %s
        """, [table_name, self.connection.schema_name])
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

    def get_table_description(self, cursor, table_name):
        "Returns a description of the table, with the DB-API cursor.description interface."
        # As cursor.description does not return reliably the nullable property,
        # we have to query the information_schema (#7783)
        cursor.execute("""
            SELECT column_name, is_nullable
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s""", [self.connection.schema_name, table_name])
        null_map = dict(cursor.fetchall())
        cursor.execute("SELECT * FROM %s LIMIT 1" % self.connection.ops.quote_name(table_name))
        return [FieldInfo(*((force_text(line[0]),) + line[1:6] + (null_map[force_text(line[0])] == 'YES',)))
                for line in cursor.description]

    def get_relations(self, cursor, table_name):
        """
        Returns a dictionary of {field_index: (field_index_other_table, other_table)}
        representing all relationships to the given table. Indexes are 0-based.
        """
        cursor.execute("""
            SELECT con.conkey, con.confkey, c2.relname
            FROM pg_catalog.pg_constraint con, pg_catalog.pg_class c1, pg_catalog.pg_class c2, pg_catalog.pg_namespace n
            WHERE c1.oid = con.conrelid
                AND c2.oid = con.confrelid
                AND c1.relnamespace = n.oid
                AND c2.relnamespace = n.oid
                AND con.relnamespace = n.oid
                AND n.nspname = '%s'
                AND c1.relname = %s
                AND con.contype = 'f'""", [self.connection.schema_name, table_name])
        relations = {}
        for row in cursor.fetchall():
            # row[0] and row[1] are single-item lists, so grab the single item.
            relations[row[0][0] - 1] = (row[1][0] - 1, row[2])
        return relations

    def get_key_columns(self, cursor, table_name):
        key_columns = []
        cursor.execute("""
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
            WHERE kcu.table_name = %s AND tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = %s""", [table_name, self.connectin.schema_name])
        key_columns.extend(cursor.fetchall())
        return key_columns

    def get_indexes(self, cursor, table_name):
        # This query retrieves each index on the given table, including the
        # first associated field name
        cursor.execute("""
            SELECT attr.attname, idx.indkey, idx.indisunique, idx.indisprimary
            FROM pg_catalog.pg_class c, pg_catalog.pg_class c2,
                pg_catalog.pg_index idx, pg_catalog.pg_attribute attr, pg_catalog.pg_namespace n
            WHERE c.oid = idx.indrelid
                AND idx.indexrelid = c2.oid
                AND attr.attrelid = c.oid
                AND attr.attnum = idx.indkey[0]
                AND c.relnamespace = n.oid
                AND n.nspname = %s
                AND c.relname = %s""", [self.connection.schema_name, table_name])
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
