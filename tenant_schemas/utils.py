from django.conf import settings
from django.db.models.loading import get_model

def get_tenant_model():
    return get_model(*settings.TENANT_MODEL.split("."))

def clean_tenant_url(url_string):
    """
    Removes the TENANT_TOKEN from a particular string
    """
    if url_string.startswith(settings.TENANT_URL_TOKEN):
        url_string = url_string[5:]
    return url_string


def remove_www_and_dev(self, hostname):
    """
    Removes www. and dev. from the beginning of the address. Only for
    routing purposes. www.test.com/login/ and test.com/login/ should
    find the same tenant.
    """
    if hostname.startswith("www.") or hostname.startswith("dev."):
        return hostname[4:]

    return hostname