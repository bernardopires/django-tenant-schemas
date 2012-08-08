from optparse import make_option
from django.conf import settings
from django.core.management import call_command, get_commands, load_command_class
from django.core.management.base import BaseCommand
from django.db import connection
from tenant_schemas.utils import get_tenant_model

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
        # instantiate
        obj = super(BaseTenantCommand, cls).__new__(cls, *args, **kwargs)

        app_name = get_commands()[obj.COMMAND_NAME]
        if isinstance(app_name, BaseCommand):
            # If the command is already loaded, use it directly.
            cmdclass = app_name
        else:
            cmdclass = load_command_class(app_name, obj.COMMAND_NAME)

        # inherit the options from the original command
        obj.option_list = cmdclass.option_list
        #print obj.option_list
        obj.option_list += (
            make_option("-s", "--schema", dest="schema_name"),
            )
        # prepend the command's original help with the info about schemata iteration
        obj.help = "Calls %s for all registered schemata. You can use regular %s options. "\
                   "Original help for %s: %s"\
        % (obj.COMMAND_NAME, obj.COMMAND_NAME, obj.COMMAND_NAME,\
           getattr(cmdclass, 'help', 'none'))
        return obj

    def execute_command(self, tenant, command_name, *args, **options):
        print
        print self.style.NOTICE("=== Switching to schema '")\
              + self.style.SQL_TABLE(tenant.schema_name)\
        + self.style.NOTICE("' then calling %s:" % command_name)

        # sets the schema for the connection
        connection.set_tenant(tenant)

        # call the original command with the args it knows
        call_command(command_name, *args, **options)

    def handle(self, *args, **options):
        """
        Iterates a command over all registered schemata.
        """
        if options['schema_name']:
            # only run on a particular schema
            self.execute_command(get_tenant_model().objects.get(schema_name=options['schema_name']), self.COMMAND_NAME, *args, **options)
        else:
            for tenant in get_tenant_model().objects.all():
                self.execute_command(tenant, self.COMMAND_NAME, *args, **options)