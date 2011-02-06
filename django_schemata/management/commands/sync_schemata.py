from django.conf import settings
from django.core.management import call_command, get_commands, load_command_class
from django.core.management.base import BaseCommand
from django.db import connection

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
        # prepend the command's original help with the info about schemata iteration
        obj.help = "Calls %s for all registered schemata. You can use regular %s options. " \
                   "Original help for %s: %s" \
                   % (obj.COMMAND_NAME, obj.COMMAND_NAME, obj.COMMAND_NAME, \
                      getattr(cmdclass, 'help', 'none'))
        return obj

    def handle(self, *args, **options):
        """
        Iterates a command over all registered schemata.
        """
        for domain_name in settings.SCHEMATA_DOMAINS:

            print
            print self.style.NOTICE("=== Switching to domain ") \
                + self.style.SQL_TABLE(domain_name) \
                + self.style.NOTICE(" then calling %s:" % self.COMMAND_NAME)

            # sets the schema for the connection
            connection.set_schemata_domain(domain_name)

            # call the original command with the args it knows
            call_command(self.COMMAND_NAME, *args, **options)


class Command(BaseSchemataCommand):
    COMMAND_NAME = 'syncdb'
