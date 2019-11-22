=======================================
Specializing templates based on tenants
=======================================

Multitenant aware filesystem template loader
--------------------------------------------

The regular Django filesystem template loader does not vary the search path based on the current tenant. We provide a specialised version which does adapt. To use it add, add ``tenant_schemas.template_loaders.FilesystemLoader`` to your ``TEMPLATES`` configuration.

.. code-block:: python

    TEMPLATES = [
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": ["/path/to/templates"],
            ...
            "OPTIONS": {
                ...
                "loaders": [
                    "tenant_schemas.template_loaders.FilesystemLoader",
                    "django.template.loaders.app_directories.Loader",
                ]
            }
        }
    ]

    MULTITENANT_TEMPLATE_DIRS = ["/path/to/tenant/templates/%s"]

Like with the Django ``FilesystemLoader`` the first file found is used. The loader will first search for templates in the paths specified in ``MULTITENANT_TEMPLATE_DIRS`` before falling back to the static locations in the ``DIRS`` option.

The replacement string ``%s`` will be transposed with the tenant ``domain_url`` in ``MULTITENANT_TEMPLATE_DIRS``.

Multitenant aware cached template loader
----------------------------------------

To use template caching with the ``FilesystemLoader``, you must combine it with the ``CachedLoader``. If you do not, the first template located for any tenant is used for all following tenants.

The ``CachedLoader`` prefixes the cache key with the schema name of the tenant.

.. code-block:: python

    TEMPLATES = [
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": ["/path/to/templates"],
            ...
            "OPTIONS": {
                ...
                "loaders": [
                    (
                        "tenant_schemas.template_loaders.CachedLoader",
                        (
                            "tenant_schemas.template_loaders.FilesystemLoader",
                            "django.template.loaders.app_directories.Loader",
                        )
                    )
                ]
            }
        }
    ]
