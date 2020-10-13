from tenant_schemas.management.commands import BaseTenantCommand


class Command(BaseTenantCommand):
    requires_system_checks = []
    COMMAND_NAME = 'collectstatic'
