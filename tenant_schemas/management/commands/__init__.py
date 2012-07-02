from optparse import make_option
from django.conf import settings
from django.core.management import call_command, get_commands, load_command_class
from django.core.management.base import BaseCommand
from django.db import connection
from tenant_schemas.utils import get_tenant_model

class BaseSchemataCommand(BaseCommand):
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
        obj = super(BaseSchemataCommand, cls).__new__(cls, *args, **kwargs)
        # load the command class
        cmdclass = load_command_class(get_commands()[obj.COMMAND_NAME], obj.COMMAND_NAME)
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

    def execute_command(self, schema, command_name, *args, **options):
        print
        print self.style.NOTICE("=== Switching to schema '")\
              + self.style.SQL_TABLE(schema)\
        + self.style.NOTICE("' then calling %s:" % command_name)

        # sets the schema for the connection
        connection.set_schema(schema)

        # call the original command with the args it knows
        call_command(command_name, *args, **options)

    def handle(self, *args, **options):
        """
        Iterates a command over all registered schemata.
        """
        if options['schema_name']:
            # only run on a particular schema
            self.execute_command(options['schema_name'], self.COMMAND_NAME, *args, **options)
        else:
            for tenant in get_tenant_model().objects.all():
                options['schema_name'] = tenant.schema_name
                self.execute_command(tenant.schema_name, self.COMMAND_NAME, *args, **options)