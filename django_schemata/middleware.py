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

    # The question remains whether it's necessary to unset the schema
    # when the request finishes...
