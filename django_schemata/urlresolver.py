from django.conf import settings
from django.core.urlresolvers import reverse as reverse_default
from django.utils.functional import lazy

def reverse(viewname, urlconf=None, args=None, kwargs=None, prefix=None, current_app=None):
    url = reverse_default(viewname, urlconf, args, kwargs, prefix, current_app)
    if url.startswith(settings.SCHEMA_DEPENDENT_TOKEN):
        url = url[5:]
    return url

reverse_lazy = lazy(reverse, str)