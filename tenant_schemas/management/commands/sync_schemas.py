import traceback
import itertools
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import get_apps, get_models, get_model
from django.db.models.signals import post_syncdb
from django.contrib.sites import models as site_app
from django.contrib.sites.management import create_default_site
if "south" in settings.INSTALLED_APPS:
    from south.management.commands.syncdb import Command as SyncdbCommand
else:
    from django.core.management.commands.syncdb import Command as SyncdbCommand
from django.db import connection, connections, router, transaction, models, DatabaseError
from django.core.management.base import NoArgsCommand
from django.core.management import call_command
from django.core.management.color import no_style
from django.core.management.sql import custom_sql_for_model, emit_post_sync_signal, emit_pre_sync_signal
from django.utils.importlib import import_module
from django.utils.datastructures import SortedDict
from tenant_schemas.utils import get_tenant_model, get_public_schema_name
from tenant_schemas.management.common import SyncCommon
from tenant_schemas.postgresql_backend.base import original_backend


# Get models from "app.model" format and put it in a list
public_models = [model for model in [get_model(*model.split('.')) for
                                     model in getattr(settings, 'SHARED_MODELS', [])
                                     ]
                 ]


class SharedDatabaseCreation(original_backend.DatabaseCreation):
    """
    Implements the SHARED_MODELS feature by inserting public_schema_name
    before table name on table creation in the SQL.
    """

    def sql_for_inline_foreign_key_references(self, model, field, known_models, style):
        """
        Return the SQL snippet defining the foreign key reference for a field.
        Code copied from django.db.backends.creation.BaseDatabaseCreation
        """
        qn = self.connection.ops.quote_name
        rel_to = field.rel.to
        if rel_to in known_models or rel_to == model:
            output = [style.SQL_KEYWORD('REFERENCES') + ' ' +
                (style.SQL_TABLE(qn(get_public_schema_name())) + '.' if rel_to in public_models else '') +
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


class SyncdbModifiedCommand(NoArgsCommand):
    option_list = SyncdbCommand.option_list + SyncCommon.option_list
    help = "Create the database tables for all apps in INSTALLED_APPS"\
           " whose tables haven't already been created."

    def handle_noargs(self, **options):
        """
        Implement SHARED_MODELS feature by changing connection.creation
        default instance to a schema-aware instance.
        Code copied from default syncdb command.
        """
        verbosity = int(options.get('verbosity'))
        interactive = options.get('interactive')
        show_traceback = options.get('traceback')
        load_initial_data = options.get('load_initial_data')

        self.style = no_style()

        # Import the 'management' module within each installed app, to register
        # dispatcher events.
        for app_name in settings.INSTALLED_APPS:
            try:
                import_module('.management', app_name)
            except ImportError as exc:
                # This is slightly hackish. We want to ignore ImportErrors
                # if the "management" module itself is missing -- but we don't
                # want to ignore the exception if the management module exists
                # but raises an ImportError for some reason. The only way we
                # can do this is to check the text of the exception. Note that
                # we're a bit broad in how we check the text, because different
                # Python implementations may not use the same text.
                # CPython uses the text "No module named management"
                # PyPy uses "No module named myproject.myapp.management"
                msg = exc.args[0]
                if not msg.startswith('No module named') or 'management' not in msg:
                    raise

        db = options.get('database')
        connection = connections[db]
        connection.creation = SharedDatabaseCreation(connection)
        cursor = connection.cursor()

        # Get a list of already installed *models* so that references work right.
        tables = connection.introspection.table_names()
        seen_models = connection.introspection.installed_models(tables)
        created_models = set()
        pending_references = {}

        # Build the manifest of apps and models that are to be synchronized
        all_models = [
            (app.__name__.split('.')[-2],
                [m for m in models.get_models(app, include_auto_created=True)
                if router.allow_syncdb(db, m)])
            for app in models.get_apps()
        ]

        def model_installed(model):
            opts = model._meta
            converter = connection.introspection.table_name_converter
            return not ((converter(opts.db_table) in tables) or
                (opts.auto_created and converter(opts.auto_created._meta.db_table) in tables))

        manifest = SortedDict(
            (app_name, list(filter(model_installed, model_list)))
            for app_name, model_list in all_models
        )

        create_models = set([x for x in itertools.chain(*manifest.values())])
        emit_pre_sync_signal(create_models, verbosity, interactive, db)

        # Create the tables for each model
        if verbosity >= 1:
            self.stdout.write("Creating tables ...\n")
        with transaction.commit_on_success_unless_managed(using=db):
            for app_name, model_list in manifest.items():
                for model in model_list:
                    # Create the model's database table, if it doesn't already exist.
                    if verbosity >= 3:
                        self.stdout.write("Processing %s.%s model\n"
                                          % (app_name, model._meta.object_name))
                    sql, references = connection.creation.sql_create_model(
                                                          model, self.style, seen_models)
                    seen_models.add(model)
                    created_models.add(model)
                    for refto, refs in references.items():
                        pending_references.setdefault(refto, []).extend(refs)
                        if refto in seen_models:
                            sql.extend(connection.creation.sql_for_pending_references(
                                                           refto, self.style, pending_references))
                    sql.extend(connection.creation.sql_for_pending_references(
                        model, self.style, pending_references))
                    if verbosity >= 1 and sql:
                        self.stdout.write("Creating table %s\n" % model._meta.db_table)
                    for statement in sql:
                        if verbosity >= 3:
                            self.stdout.write(statement)
                        cursor.execute(statement)
                    tables.append(connection.introspection.table_name_converter(model._meta.db_table))

        # Send the post_syncdb signal, so individual apps
        # can do whatever they need to do at this point.
        emit_post_sync_signal(created_models, verbosity, interactive, db)

        # The connection may have been closed by a syncdb handler.
        cursor = connection.cursor()

        # Install custom SQL for the app (but only if this is a model we've just created)
        if verbosity >= 1:
            self.stdout.write("Installing custom SQL ...\n")
        for app_name, model_list in manifest.items():
            for model in model_list:
                if model in created_models:
                    custom_sql = custom_sql_for_model(model, self.style, connection)
                    if custom_sql:
                        if verbosity >= 2:
                            self.stdout.write("Installing custom SQL for %s.%s model\n"
                                              % (app_name, model._meta.object_name))
                        try:
                            with transaction.commit_on_success_unless_managed(using=db):
                                for sql in custom_sql:
                                    if verbosity >= 3:
                                        self.stdout.write(sql)
                                    cursor.execute(sql)
                        except Exception as e:
                            self.stderr.write("Failed to install custom SQL for %s.%s model: %s\n"
                                              % (app_name, model._meta.object_name, e))
                            if show_traceback:
                                traceback.print_exc()
                    else:
                        if verbosity >= 3:
                            self.stdout.write("No custom SQL for %s.%s model\n"
                                              % (app_name, model._meta.object_name))

        if verbosity >= 1:
            self.stdout.write("Installing indexes ...\n")
        # Install SQL indices for all newly created models
        for app_name, model_list in manifest.items():
            for model in model_list:
                if model in created_models:
                    index_sql = connection.creation.sql_indexes_for_model(model, self.style)
                    if index_sql:
                        if verbosity >= 2:
                            self.stdout.write("Installing index for %s.%s model\n"
                                              % (app_name, model._meta.object_name))
                        try:
                            with transaction.commit_on_success_unless_managed(using=db):
                                for sql in index_sql:
                                    if verbosity >= 3:
                                        self.stdout.write(sql)
                                    cursor.execute(sql)
                        except Exception as e:
                            self.stderr.write("Failed to install index for %s.%s model: %s\n" % \
                                                (app_name, model._meta.object_name, e))

        # Load initial_data fixtures (unless that has been disabled)
        if load_initial_data:
            call_command('loaddata', 'initial_data', verbosity=verbosity,
                         database=db, skip_validation=True)


class Command(SyncCommon):
    help = "Sync schemas based on TENANT_APPS and SHARED_APPS settings"
    option_list = SyncdbCommand.option_list + SyncCommon.option_list

    def handle_noargs(self, **options):
        super(Command, self).handle_noargs(**options)

        if "south" in settings.INSTALLED_APPS:
            self.options["migrate"] = False

        # save original settings
        for model in get_models(include_auto_created=True):
            setattr(model._meta, 'was_managed', model._meta.managed)

        # Django sites app would insert the default example.com at every new schema creation
        # into the public table, so we just disconnect that signal before emitted
        if self.schema_name and site_app.Site in public_models:
            post_syncdb.disconnect(create_default_site, site_app)

        ContentType.objects.clear_cache()

        if self.sync_public:
            self.sync_public_apps()
        if self.sync_tenant:
            self.sync_tenant_apps(self.schema_name)

        # restore settings
        for model in get_models(include_auto_created=True):
            model._meta.managed = model._meta.was_managed

    def _set_managed_apps(self, included_apps):
        """ sets which apps are managed by syncdb """
        for model in get_models(include_auto_created=True):
            model._meta.managed = False

        verbosity = int(self.options.get('verbosity'))
        for app_model in get_apps():
            app_name = app_model.__name__.replace('.models', '')
            if hasattr(app_model, 'models') and app_name in included_apps:
                for model in get_models(app_model, include_auto_created=True):
                    model._meta.managed = True and model._meta.was_managed
                    if model._meta.managed and verbosity >= 3:
                        self._notice("=== Include Model: %s: %s" % (app_name, model.__name__))

    def _sync_tenant(self, tenant):
        self._notice("=== Running syncdb for schema: %s" % tenant.schema_name)
        connection.set_tenant(tenant, include_public=False)
        SyncdbModifiedCommand().execute(**self.options)

    def sync_tenant_apps(self, schema_name=None):
        apps = self.tenant_apps or self.installed_apps
        self._set_managed_apps(apps)
        self.options['load_initial_data'] = False

        if schema_name:
            tenant = get_tenant_model().objects.get(schema_name=schema_name)
            self._sync_tenant(tenant)
        else:
            all_tenants = get_tenant_model().objects.exclude(schema_name=get_public_schema_name())
            if not all_tenants:
                self._notice("No tenants found!")

            for tenant in all_tenants:
                self._sync_tenant(tenant)

    def sync_public_apps(self):
        apps = self.shared_apps or self.installed_apps
        self._set_managed_apps(apps)
        self._notice("=== Running syncdb for schema public")
        SyncdbModifiedCommand().execute(**self.options)
