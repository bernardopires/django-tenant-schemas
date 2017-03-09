==============
Advanced Usage
==============

Custom tenant strategies (custom middleware support)
====================================================
By default, ``django-tenant-schemas``'s strategies for determining the correct tenant involve extracting it from the URL (e.g. ``mytenant.mydomain.com``). This is done through a middleware, typically ``TenantMiddleware``.

In some situations, it might be useful to use **alternative tenant selection strategies**. For example, consider a website with a fixed URL. An approach for this website might be to pass the tenant through a special header, or to determine it in some other manner based on the request (e.g. using an OAuth token mapped to a tenant). ``django-tenant-schemas`` offer an **easily extensible way to provide your own middleware** with minimal code changes.

To add custom tenant selection strategies, you need to **subclass the** ``BaseTenantMiddleware`` **class and implement its** ``get_tenant`` **method**. This method accepts the current ``request`` object through which you can determine the tenant to use. In addition, for backwards-compatibility reasons, the method also accepts the tenant model class (``TENANT_MODEL``) and the ``hostname`` of the current request. **You should return an instance of your** ``TENANT_MODEL`` **class** from this function.
After creating your middleware, you should make it the top-most middleware in your list. You should only have one subclass of ``BaseTenantMiddleware`` per project.

Note that you might also wish to extend the other provided middleware classes, such as ``TenantMiddleware``. For example, you might want to chain several strategies together, and you could do so by subclassing the original strategies and manipulating the call to ``super``'s ``get_tenant``.


Example: Determine tenant from HTTP header
------------------------------------------
Suppose you wanted to determine the current tenant based on a request header (``X-DTS-SCHEMA``). You might implement a simple middleware such as:

.. code-block:: python

    class XHeaderTenantMiddleware(BaseTenantMiddleware):
        """
        Determines tenant by the value of the ``X-DTS-SCHEMA`` HTTP header.
        """
        def get_tenant(self, model, hostname, request):
            schema_name = request.META.get('HTTP_X_DTS_SCHEMA', get_public_schema_name())
            return model.objects.get(schema_name=schema_name)

Your application could now specify the tenant with the ``X-DTS-SCHEMA`` HTTP header. In scenarios where you are configuring individual tenant websites by yourself, each with its own ``nginx`` configuration to redirect to the right tenant, you could use a configuration such as the one below:


.. code-block:: nginx

    # /etc/nginx/conf.d/multitenant.conf

    upstream web {
        server localhost:8000;
    }

    server {
        listen 80 default_server;
        server_name _;

        location / {
            proxy_pass http://web;
            proxy_set_header Host $host;
        }
    }

    server {
        listen 80;
        server_name example.com www.example.com;

        location / {
            proxy_pass http://web;
            proxy_set_header Host $host;
            proxy_set_header X-DTS-SCHEMA example; # triggers XHeaderTenantMiddleware
        }
    }
