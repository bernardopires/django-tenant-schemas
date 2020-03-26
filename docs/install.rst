============
Installation
============

Assuming you have django installed, the first step is to install ``django-tenant-schemas``.

.. code-block:: bash

    pip install django-tenant-schemas

Basic Settings
==============
You'll have to make the following modifications to your ``settings.py`` file.

Your ``DATABASE_ENGINE`` setting needs to be changed to

.. code-block:: python

    DATABASES = {
        'default': {
            'ENGINE': 'tenant_schemas.postgresql_backend',
            # ..
        }
    }

Add `tenant_schemas.routers.TenantSyncRouter` to your `DATABASE_ROUTERS` setting, so that the correct apps can be synced, depending on what's being synced (shared or tenant).

.. code-block:: python

    DATABASE_ROUTERS = (
        'tenant_schemas.routers.TenantSyncRouter',
    )

Add the middleware ``tenant_schemas.middleware.TenantMiddleware`` to the top of ``MIDDLEWARE_CLASSES``, so that each request can be set to use the correct schema.

If the hostname in the request does not match a valid tenant ``domain_url``, a HTTP 404 Not Found will be returned.

If you'd like to raise ``DisallowedHost`` and a HTTP 400 response instead, use the ``tenant_schemas.middleware.SuspiciousTenantMiddleware``.

If you'd like to serve the public tenant for unrecognised hostnames instead, use ``tenant_schemas.middleware.DefaultTenantMiddleware``. To use a tenant other than the public tenant, create a subclass and register it instead.

If you'd like a different tenant selection technique (e.g. using an HTTP Header), you can define a custom middleware. See :ref:`Advanced Usage`.

.. code-block:: python

    from tenant_schemas.middleware import DefaultTenantMiddleware

    class MyDefaultTenantMiddleware(DefaultTenantMiddleware):
        DEFAULT_SCHEMA_NAME = 'default'

.. code-block:: python

    MIDDLEWARE_CLASSES = (
        'tenant_schemas.middleware.TenantMiddleware',
        # 'tenant_schemas.middleware.SuspiciousTenantMiddleware',
        # 'tenant_schemas.middleware.DefaultTenantMiddleware',
        # 'myproject.middleware.MyDefaultTenantMiddleware',
        #...
    )

.. code-block:: python

    TEMPLATES = [
        {
            'BACKEND': # ...
            'DIRS': [],
            'APP_DIRS': True,
            'OPTIONS': {
                'context_processors': [
                    # ...
                    'django.template.context_processors.request',
                    # ...
                ]
            }
        }
    ]

The Tenant Model
================
Now we have to create your tenant model. Your tenant model can contain whichever fields you want, however, you **must** inherit from ``TenantMixin``. This Mixin only has two fields (``domain_url`` and ``schema_name``) and both are required. Here's an example, suppose we have an app named ``customers`` and we want to create a model called ``Client``.

.. code-block:: python

    from django.db import models
    from tenant_schemas.models import TenantMixin

    class Client(TenantMixin):
        name = models.CharField(max_length=100)
        paid_until =  models.DateField()
        on_trial = models.BooleanField()
        created_on = models.DateField(auto_now_add=True)

        # default true, schema will be automatically created and synced when it is saved
        auto_create_schema = True

Before creating the migrations, we must configure a few specific settings.

Configure Tenant and Shared Applications
========================================
To make use of shared and tenant-specific applications, there are two settings called ``SHARED_APPS`` and ``TENANT_APPS``. ``SHARED_APPS`` is a tuple of strings just like ``INSTALLED_APPS`` and should contain all apps that you want to be synced to ``public``. If ``SHARED_APPS`` is set, then these are the only apps that will be synced to your ``public`` schema! The same applies for ``TENANT_APPS``, it expects a tuple of strings where each string is an app. If set, only those applications will be synced to all your tenants. Here's a sample setting

.. code-block:: python

    SHARED_APPS = (
        'tenant_schemas',  # mandatory, should always be before any django app
        'customers', # you must list the app where your tenant model resides in

        'django.contrib.contenttypes',

        # everything below here is optional
        'django.contrib.auth',
        'django.contrib.sessions',
        'django.contrib.sites',
        'django.contrib.messages',
        'django.contrib.admin',
    )

    TENANT_APPS = (
        'django.contrib.contenttypes',

        # your tenant-specific apps
        'myapp.hotels',
        'myapp.houses',
    )

    INSTALLED_APPS = (
        'tenant_schemas',  # mandatory, should always be before any django app

        'customers',
        'django.contrib.contenttypes',
        'django.contrib.auth',
        'django.contrib.sessions',
        'django.contrib.sites',
        'django.contrib.messages',
        'django.contrib.admin',
        'myapp.hotels',
        'myapp.houses',
    )

You also have to set where your tenant model is.

.. code-block:: python

    TENANT_MODEL = "customers.Client" # app.Model

Now you must create your app migrations for ``customers``:

.. code-block:: bash

    python manage.py makemigrations customers

The command ``migrate_schemas --shared`` will create the shared apps on the ``public`` schema. Note: your database should be empty if this is the first time you're running this command.

.. code-block:: bash

    python manage.py migrate_schemas --shared

.. warning::

   Never use ``migrate`` as it would sync *all* your apps to ``public``!

Lastly, you need to create a tenant whose schema is ``public`` and it's address is your domain URL. Please see the section on :doc:`use <use>`.

You can also specify extra schemas that should be visible to all queries using
``PG_EXTRA_SEARCH_PATHS`` setting.

.. code-block:: python

   PG_EXTRA_SEARCH_PATHS = ['extensions']

``PG_EXTRA_SEARCH_PATHS`` should be a list of schemas you want to make visible
globally.

.. tip::

   You can create a dedicated schema to hold postgresql extensions and make it
   available globally. This helps avoid issues caused by hiding the public
   schema from queries.

Working with Tenant specific schemas
====================================
Since each Tenant has it's own schema in the database you need a way to tell Django what
schema to use when using the management commands.

A special management command ``tenant_command`` has been added to allow you to
execute Django management commands in the context of a specific Tenant schema.

.. code-block:: python

    python manage.py tenant_command loaddata --schema=my_tenant test_fixture

.. warning::

   Depending on the configuration of your applications, the command you execute
   may impact shared data also.

Creating a new Tenant
=====================
See `Creating a new Tenant <use.html#creating-a-tenant>`_ for more details on how to create a new Tenant in our
application.


Optional Settings
=================

.. attribute:: PUBLIC_SCHEMA_NAME

    :Default: ``'public'``

    The schema name that will be treated as ``public``, that is, where the ``SHARED_APPS`` will be created.

Tenant View-Routing
-------------------

.. attribute:: PUBLIC_SCHEMA_URLCONF

    :Default: ``None``

    We have a goodie called ``PUBLIC_SCHEMA_URLCONF``. Suppose you have your main website at ``example.com`` and a customer at ``customer.example.com``. You probably want your user to be routed to different views when someone requests ``http://example.com/`` and ``http://customer.example.com/``. Because django only uses the string after the host name, this would be impossible, both would call the view at ``/``. This is where ``PUBLIC_SCHEMA_URLCONF`` comes in handy. If set, when the ``public`` schema is being requested, the value of this variable will be used instead of `ROOT_URLCONF <https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-ROOT_URLCONF>`_. So for example, if you have

    .. code-block:: python

        PUBLIC_SCHEMA_URLCONF = 'myproject.urls_public'

    When requesting the view ``/login/`` from the public tenant (your main website), it will search for this path on ``PUBLIC_SCHEMA_URLCONF`` instead of ``ROOT_URLCONF``.

Separate projects for the main website and tenants (optional)
-------------------------------------------------------------
In some cases using the ``PUBLIC_SCHEMA_URLCONF`` can be difficult. For example, `Django CMS <https://www.django-cms.org/>`_ takes some control over the default Django URL routing by using middlewares that do not play well with the tenants. Another example would be when some apps on the main website need different settings than the tenants website. In these cases it is much simpler if you just run the main website `example.com` as a separate application.

If your projects are ran using a WSGI configuration, this can be done by creating a filed called ``wsgi_main_website.py`` in the same folder as ``wsgi.py``.

.. code-block:: python

    # wsgi_main_website.py
    import os
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings_public")

    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()

If you put this in the same Django project, you can make a new ``settings_public.py`` which points to a different ``urls_public.py``. This has the advantage that you can use the same apps that you use for your tenant websites.

Or you can create a completely separate project for the main website.

Caching
-------

To enable tenant aware caching you can set the `KEY_FUNCTION <https://docs.djangoproject.com/en/1.8/ref/settings/#std:setting-CACHES-KEY_FUNCTION>`_ setting to use the provided ``make_key`` helper function which
adds the tenants ``schema_name`` as the first key prefix.

.. code-block:: python

    CACHES = {
        "default": {
            ...
            'KEY_FUNCTION': 'tenant_schemas.cache.make_key',
            'REVERSE_KEY_FUNCTION': 'tenant_schemas.cache.reverse_key',
        },
    }

The ``REVERSE_KEY_FUNCTION`` setting is only required if you are using the `django-redis <https://github.com/niwinz/django-redis>`_ cache backend.

Configuring your Apache Server (optional)
=========================================
Here's how you can configure your Apache server to route all subdomains to your django project so you don't have to setup any subdomains manually.

.. code-block:: apacheconf

    <VirtualHost 127.0.0.1:8080>
        ServerName mywebsite.com
        ServerAlias *.mywebsite.com mywebsite.com
        WSGIScriptAlias / "/path/to/django/scripts/mywebsite.wsgi"
    </VirtualHost>

`Django's Deployment with Apache and mod_wsgi <https://docs.djangoproject.com/en/dev/howto/deployment/wsgi/modwsgi/>`_ might interest you too.

Building Documentation
======================
Documentation is available in ``docs`` and can be built into a number of
formats using `Sphinx <http://pypi.python.org/pypi/Sphinx>`_. To get started

.. code-block:: bash

    pip install Sphinx
    cd docs
    make html

This creates the documentation in HTML format at ``docs/_build/html``.

