from django.conf import settings
from django.db import connection

class SchemataMiddleware(object):
    """
    This middleware should be placed at the very top of the middleware stack.
    Selects the proper database schema using the request host. Can fail in
    various ways which is better than corrupting or revealing data...
    """
    def process_request(self, request):
        hostname_without_port = request.get_host().split(':')[0]
        request.schema_domain_name = hostname_without_port
        request.schema_domain = connection.set_schemata_domain(request.schema_domain_name)
        #print request.schema_domain["schema_name"]

        print settings.ROOT_URLCONF


        if request.schema_domain["schema_name"] != "public" and request.path_info[-1] == '/':
            request.path_info = "/firm" + request.path_info[1:]
        #   settings.ROOT_URLCONF = settings.ROOT_SCHEMA_URLCONF
        #else:
        #    settings.ROOT_URLCONF = settings.ROOT_NO_SCHEMA_URLCONF


    # The question remains whether it's necessary to unset the schema
    # when the request finishes...
