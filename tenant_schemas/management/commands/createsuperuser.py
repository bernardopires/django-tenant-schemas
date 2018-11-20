from django.contrib.auth import get_user_model
from tenant_schemas.management.commands import TenantWrappedCommand
from django.contrib.auth.management.commands import createsuperuser
from django.conf import settings


class WrappedCommand(TenantWrappedCommand):
    COMMAND = createsuperuser.Command


user_model_in_shared_schema = get_user_model()._meta.app_label in settings.SHARED_APPS

Command = createsuperuser.Command if user_model_in_shared_schema else WrappedCommand

