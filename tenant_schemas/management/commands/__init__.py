import django
from django.conf import settings
from django.core.management import (
    call_command,
    get_commands,
    load_command_class,
)
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from six.moves import input
from tenant_schemas.utils import get_public_schema_name, get_tenant_model


class BaseTenantCommand(BaseCommand):
    """
    Generic command class useful for iterating any existing command
    over all schemata. The actual command name is expected in the
    class variable COMMAND_NAME of the subclass.
    """

    def __new__(cls, *args, **kwargs):
        """
        Sets option_list and help dynamically.
        """
        obj = super(BaseTenantCommand, cls).__new__(cls, *args, **kwargs)

        app_name = get_commands()[obj.COMMAND_NAME]
        if isinstance(app_name, BaseCommand):
            # If the command is already loaded, use it directly.
            obj._original_command = app_name
        else:
            obj._original_command = load_command_class(app_name, obj.COMMAND_NAME)

        # prepend the command's original help with the info about schemata
        # iteration
        obj.help = (
            "Calls {cmd} for all registered schemata. You can use regular "
            "{cmd} options.\n\nOriginal help for {cmd}:\n\n{help}".format(
                cmd=obj.COMMAND_NAME,
                help=getattr(obj._original_command, "help", "none"),
            )
        )

        return obj

    def add_arguments(self, parser):
        super(BaseTenantCommand, self).add_arguments(parser)
        parser.add_argument("-s", "--schema", dest="schema_name")
        parser.add_argument(
            "-p",
            "--skip-public",
            dest="skip_public",
            action="store_true",
            default=False,
        )
        # use the privately held reference to the underlying command to invoke
        # the add_arguments path on this parser instance
        self._original_command.add_arguments(parser)

    def execute_command(self, tenant, command_name, *args, **options):
        verbosity = int(options.get("verbosity"))

        if verbosity >= 1:
            print()
            print(
                self.style.NOTICE("=== Switching to schema '")
                + self.style.SQL_TABLE(tenant.schema_name)
                + self.style.NOTICE("' then calling %s:" % command_name)
            )

        connection.set_tenant(tenant)

        # call the original command with the args it knows
        call_command(command_name, *args, **options)

    def handle(self, *args, **options):
        """
        Iterates a command over all registered schemata.
        """
        arguments = ["schema_name", "skip_public"]
        if options["schema_name"]:
            # only run on a particular schema
            connection.set_schema_to_public()
            self.execute_command(
                get_tenant_model().objects.get(schema_name=options["schema_name"]),
                self.COMMAND_NAME,
                *args,
                **{k: v for k, v in options.items() if k not in arguments}
            )
        else:
            for tenant in get_tenant_model().objects.all():
                if not (
                    options["skip_public"]
                    and tenant.schema_name == get_public_schema_name()
                ):
                    self.execute_command(
                        tenant,
                        self.COMMAND_NAME,
                        *args,
                        **{k: v for k, v in options.items() if k not in arguments}
                    )


class InteractiveTenantOption(object):
    def add_arguments(self, parser):
        parser.add_argument("command")
        parser.add_argument(
            "-s", "--schema", dest="schema_name", help="specify tenant schema"
        )

    def get_tenant_from_options_or_interactive(self, **options):
        TenantModel = get_tenant_model()
        all_tenants = TenantModel.objects.all()

        if not all_tenants:
            raise CommandError(
                """There are no tenants in the system.
To learn how create a tenant, see:
https://django-tenant-schemas.readthedocs.io/en/latest/use.html#creating-a-tenant"""
            )

        if options.get("schema_name"):
            tenant_schema = options["schema_name"]
        else:
            while True:
                tenant_schema = input("Enter Tenant Schema ('?' to list schemas): ")
                if tenant_schema == "?":
                    print(
                        "\n".join(
                            [
                                "%s - %s" % (t.schema_name, t.domain_url,)
                                for t in all_tenants
                            ]
                        )
                    )
                else:
                    break

        if tenant_schema not in [t.schema_name for t in all_tenants]:
            raise CommandError("Invalid tenant schema, '%s'" % (tenant_schema,))

        return TenantModel.objects.get(schema_name=tenant_schema)


class TenantWrappedCommand(InteractiveTenantOption, BaseCommand):
    """
    Generic command class useful for running any existing command
    on a particular tenant. The actual command name is expected in the
    class variable COMMAND_NAME of the subclass.
    """

    def __new__(cls, *args, **kwargs):
        obj = super(TenantWrappedCommand, cls).__new__(cls, *args, **kwargs)
        obj.command_instance = obj.COMMAND()
        return obj

    def add_arguments(self, parser):
        super(TenantWrappedCommand, self).add_arguments(parser)
        self.command_instance.add_arguments(parser)

    def handle(self, *args, **options):
        tenant = self.get_tenant_from_options_or_interactive(**options)
        connection.set_tenant(tenant)

        self.command_instance.execute(*args, **options)


class SyncCommon(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant",
            action="store_true",
            dest="tenant",
            default=False,
            help="Tells Django to populate only tenant applications.",
        )
        parser.add_argument(
            "--shared",
            action="store_true",
            dest="shared",
            default=False,
            help="Tells Django to populate only shared applications.",
        )
        parser.add_argument(
            "--app_label",
            action="store",
            dest="app_label",
            nargs="?",
            help="App label of an application to synchronize the state.",
        )
        parser.add_argument(
            "--migration_name",
            action="store",
            dest="migration_name",
            nargs="?",
            help=(
                "Database state will be brought to the state after that "
                'migration. Use the name "zero" to unapply all migrations.'
            ),
        )
        parser.add_argument("-s", "--schema", dest="schema_name")
        parser.add_argument(
            "--executor",
            action="store",
            dest="executor",
            default=None,
            help="Executor for running migrations [standard (default)|parallel]",
        )

    def handle(self, *args, **options):
        self.sync_tenant = options.get("tenant")
        self.sync_public = options.get("shared")
        self.schema_name = options.get("schema_name")
        self.executor = options.get("executor")
        self.installed_apps = settings.INSTALLED_APPS
        self.args = args
        self.options = options

        if self.schema_name:
            if self.sync_public:
                raise CommandError(
                    "schema should only be used with the --tenant switch."
                )
            elif self.schema_name == get_public_schema_name():
                self.sync_public = True
            else:
                self.sync_tenant = True
        elif not self.sync_public and not self.sync_tenant:
            # no options set, sync both
            self.sync_tenant = True
            self.sync_public = True

        if hasattr(settings, "TENANT_APPS"):
            self.tenant_apps = settings.TENANT_APPS
        if hasattr(settings, "SHARED_APPS"):
            self.shared_apps = settings.SHARED_APPS

    def _notice(self, output):
        if int(self.options.get("verbosity", 1)) >= 1:
            self.stdout.write(self.style.NOTICE(output))
