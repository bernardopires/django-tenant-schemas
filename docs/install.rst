==================
Installation
==================
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
    
Add the middleware ``tenant_schemas.middleware.TenantMiddleware`` to the top of ``MIDDLEWARE_CLASSES``, so that each request can be set to use the correct schema.

.. code-block:: python
    
    MIDDLEWARE_CLASSES = (
        'tenant_schemas.middleware.TenantMiddleware',
        #...
    )
    
Make sure you have ``django.core.context_processors.request`` listed under ``TEMPLATE_CONTEXT_PROCESSORS`` else the tenant will not be available at ``request``.

.. code-block:: python

    TEMPLATE_CONTEXT_PROCESSORS = (
        'django.core.context_processors.request',
        #...
    )
    
The Tenant Model
================
Now we have to create your tenant model. To allow the flexibility of having any data in you want in your tenant, we have a mixin called ``TenantMixin`` which you **have to** inherit from. This Mixin only has two fields (``domain_url`` and ``schema_name``) and both are required. Here's an example, suppose we have an app named ``customers`` and we want to create a model called ``Client``.

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

Configure Tenant and Shared Applications
========================================
By default all apps will be synced to your ``public`` schema and to your tenant schemas. If you want to make use of shared and tenant-specific applications, there are two additional settings called ``SHARED_APPS`` and ``TENANT_APPS``. ``SHARED_APPS`` is a tuple of strings just like ``INSTALLED_APPS`` and should contain all apps that you want to be synced to ``public``. If ``SHARED_APPS`` is set, then these are the only apps that will be to your ``public`` schema! The same applies for ``TENANT_APPS``, it expects a tuple of strings where each string is an app. If set, only those applications will be synced to all your tenants. Here's a sample setting

.. code-block:: python

    SHARED_APPS = (
        'tenant_schemas',  # mandatory
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
        # The following Django contrib apps must be in TENANT_APPS
        'django.contrib.contenttypes',

        # your tenant-specific apps
        'myapp.hotels',
        'myapp.houses', 
    )

    INSTALLED_APPS = SHARED_APPS + TENANT_APPS
    
.. warning::

   As of now it's not possible to have a centralized ``django.contrib.auth``.

You also have to set where your tenant model is.

.. code-block:: python

    TENANT_MODEL = "customers.Client" # app.Model
    
Now run ``sync_schemas``, this will create the shared apps on the ``public`` schema. Note: your database should be empty if this is the first time you're running this command.

.. code-block:: bash
    # < django 1.7
    python manage.py sync_schemas --shared

    # >= django 1.7
    python manage.py migrate_schemas --shared
    
.. warning::

   Never use ``syncdb`` as it would sync *all* your apps to ``public``!
    
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

South Migrations
================
This app supports `South <http://south.aeracode.org/>`_  so if you haven't configured it yet and would like to:

For Django 1.1 or below

.. code-block:: python

    SOUTH_DATABASE_ADAPTER = 'south.db.postgresql_psycopg2'

For Django 1.2 or above

.. code-block:: python

    SOUTH_DATABASE_ADAPTERS = {
        'default': 'south.db.postgresql_psycopg2',
    }
    
You can list ``south`` under ``TENANT_APPS`` and ``SHARED_APPS`` if you want.

We override ``south``'s ``syncdb`` and ``migrate`` command, so you'll need to change your ``INSTALLED_APPS`` to

.. code-block:: python

    # < django 1.7
    INSTALLED_APPS = SHARED_APPS + TENANT_APPS + ('tenant_schemas',)

    # >= django 1.7
    INSTALLED_APPS = ('tenant_schemas',) + SHARED_APPS + TENANT_APPS
    
This makes sure ``tenant_schemas`` is the last on the list and therefore always has precedence when running an overridden command. In Django 1.7 the precedence order was `reversed <https://docs.djangoproject.com/en/dev/releases/1.7/#management-commands-and-order-of-installed-apps>`_ so 'tenant_schemas' must be the first app instead of the last.


Optional Settings
=================

.. attribute:: PUBLIC_SCHEMA_NAME

    :Default: ``'public'``
    
    The schema name that will be treated as ``public``, that is, where the ``SHARED_APPS`` will be installed.
    
.. attribute:: TENANT_CREATION_FAKES_MIGRATIONS

    :Default: ``'True'``
    
    Sets if the models will be synced directly to the last version and all migration subsequently faked. Useful in the cases where migrations can not be faked and need to be ran individually. Be aware that setting this to `False` may significantly slow down the process of creating tenants. Only relevant if `South <http://south.aeracode.org/>`_ is used.

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

Or you can create a completely separate project for the main website, but be aware that if you specify a PostgreSQL database in the ``DATABASES`` setting in ``settings.py``, Django will use its default ``public`` schema as `described in the PostgreSQL documentation <http://www.postgresql.org/docs/9.2/static/ddl-schemas.html#DDL-SCHEMAS-PUBLIC>`_.

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
