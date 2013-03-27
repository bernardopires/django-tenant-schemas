from optparse import make_option
from django.conf import settings
from django.core.management import call_command, get_commands, load_command_class
from django.core.management.base import BaseCommand
from django.db import connection
from tenant_schemas.utils import get_tenant_model, get_public_schema_name

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
            cmdclass = app_name
        else:
            cmdclass = load_command_class(app_name, obj.COMMAND_NAME)

        # inherit the options from the original command
        obj.option_list = cmdclass.option_list
        obj.option_list += (
            make_option("-s", "--schema", dest="schema_name"),
        )
        obj.option_list += (
            make_option("-p", "--skip-public", dest="skip_public", action="store_true", default=False),
        )

        # prepend the command's original help with the info about schemata iteration
        obj.help = "Calls %s for all registered schemata. You can use regular %s options. "\
                   "Original help for %s: %s"\
        % (obj.COMMAND_NAME, obj.COMMAND_NAME, obj.COMMAND_NAME,\
           getattr(cmdclass, 'help', 'none'))
        return obj

    def execute_command(self, tenant, command_name, *args, **options):
        verbosity = int(options.get('verbosity'))

        if verbosity >= 1:
            print
            print self.style.NOTICE("=== Switching to schema '")\
                  + self.style.SQL_TABLE(tenant.schema_name)\
            + self.style.NOTICE("' then calling %s:" % command_name)

        connection.set_tenant(tenant)

        # call the original command with the args it knows
        call_command(command_name, *args, **options)

    def handle(self, *args, **options):
        """
        Iterates a command over all registered schemata.
        """
        if options['schema_name']:
            # only run on a particular schema
            connection.set_schema_to_public()
            self.execute_command(get_tenant_model().objects.get(schema_name=options['schema_name']), self.COMMAND_NAME, *args, **options)
        else:
            for tenant in get_tenant_model().objects.all():
                if not(options['skip_public'] and tenant.schema_name == get_public_schema_name()):
                    self.execute_command(tenant, self.COMMAND_NAME, *args, **options)
