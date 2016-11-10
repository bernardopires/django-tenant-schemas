===========================
Using django-tenant-schemas
===========================
Supported versions
------------------
You can use ``django-tenant-schemas`` with currently maintained versions of Django -- see the `Django's release process <https://docs.djangoproject.com/en/1.10/internals/release-process/>`_ and the present list of `Supported Versions <https://www.djangoproject.com/download/#supported-versions>`_.

It is necessary to use a PostgreSQL database. ``django-tenant-schemas`` will ensure compatibility with the minimum required version of the latest Django release. At this time that is PostgreSQL 9.2, the minimum for Django 1.10.

Creating a Tenant
-----------------
Creating a tenant works just like any other model in django. The first thing we should do is to create the ``public`` tenant to make our main website available. We'll use the previous model we defined for ``Client``.

.. code-block:: python

    from customers.models import Client

    # create your public tenant
    tenant = Client(domain_url='my-domain.com', # don't add your port or www here! on a local server you'll want to use localhost here
                    schema_name='public',
                    name='Schemas Inc.',
                    paid_until='2016-12-05',
                    on_trial=False)
    tenant.save()

Now we can create our first real tenant.

.. code-block:: python

    from customers.models import Client

    # create your first real tenant
    tenant = Client(domain_url='tenant.my-domain.com', # don't add your port or www here!
                    schema_name='tenant1',
                    name='Fonzy Tenant',
                    paid_until='2014-12-05',
                    on_trial=True)
    tenant.save() # migrate_schemas automatically called, your tenant is ready to be used!

Because you have the tenant middleware installed, any request made to ``tenant.my-domain.com`` will now automatically set your PostgreSQL's ``search_path`` to ``tenant1, public``, making shared apps available too. The tenant will be made available at ``request.tenant``. By the way, the current schema is also available at ``connection.schema_name``, which is useful, for example, if you want to hook to any of django's signals.

Any call to the methods ``filter``, ``get``, ``save``, ``delete`` or any other function involving a database connection will now be done at the tenant's schema, so you shouldn't need to change anything at your views.

Management commands
-------------------
Every command except tenant_command runs by default on all tenants. You can also create your own commands that run on every tenant by inheriting ``BaseTenantCommand``.

For example, if you have the following ``do_foo`` command in the ``foo`` app:

``foo/management/commands/do_foo.py``

.. code-block:: python

    from django.core.management.base import BaseCommand

    class Command(BaseCommand):
        def handle(self, *args, **options):
            do_foo()

You could create a wrapper command ``tenant_do_foo`` by using ``BaseTenantCommand`` like so:

``foo/management/commands/tenant_do_foo.py``

.. code-block:: python

    from tenant_schemas.management.commands import BaseTenantCommand

    class Command(BaseTenantCommand):
        COMMAND_NAME = 'do_foo'

To run only a particular schema, there is an optional argument called ``--schema``.

.. code-block:: bash

    ./manage.py migrate_schemas --schema=customer1

migrate_schemas
~~~~~~~~~~~~~~~

``migrate_schemas`` is the most important command on this app. The way it works is that it calls Django's ``migrate`` in two different ways. First, it calls ``migrate`` for the ``public`` schema, only syncing the shared apps. Then it runs ``migrate`` for every tenant in the database, this time only syncing the tenant apps.

.. warning::

   You should never directly call ``migrate``. We perform some magic in order to make ``migrate`` only migrate the appropriate apps.

.. code-block:: bash

    ./manage.py migrate_schemas

The options given to ``migrate_schemas`` are also passed to every ``migrate``. Hence you may find handy

.. code-block:: bash

    ./manage.py migrate_schemas --list

``migrate_schemas`` raises an exception when an tenant schema is missing.

tenant_command
~~~~~~~~~~~~~~

To run any command on an individual schema, you can use the special ``tenant_command``, which creates a wrapper around your command so that it only runs on the schema you specify. For example

.. code-block:: bash

    ./manage.py tenant_command loaddata

If you don't specify a schema, you will be prompted to enter one. Otherwise, you may specify a schema preemptively

.. code-block:: bash

    ./manage.py tenant_command loaddata --schema=customer1

createsuperuser
~~~~~~~~~~~~~~~

The command ``createsuperuser`` is already automatically wrapped to have a ``schema`` flag. Create a new super user with

.. code-block:: bash

    ./manage.py createsuperuser --username=admin --schema=customer1


list_tenants
~~~~~~~~~~~~

Prints to standard output a tab separated list of schema:domain_url values for each tenant.

.. code-block:: bash

    for t in $(./manage.py list_tenants | cut -f1);
    do
        ./manage.py tenant_command dumpdata --schema=$t --indent=2 auth.user > ${t}_users.json;
    done


Utils
-----

There are several utils available in `tenant_schemas.utils` that can help you in writing more complicated applications.


.. function:: schema_context(schema_name)

This is a context manager. Database queries performed inside it will be executed in against the passed ``schema_name``.

.. code-block:: python

    from tenant_schemas.utils import schema_context

    with schema_context(schema_name):
        # All comands here are ran under the schema `schema_name`

    # Restores the `SEARCH_PATH` to its original value


.. function:: tenant_context(tenant_object)

This context manager is very similiar to the ``schema_context`` function,
but it takes a tenant model object as the argument instead.

.. code-block:: python

    from tenant_schemas.utils import tenant_context

    with tenant_context(tenant):
        # All commands here are ran under the schema from the `tenant` object

    # Restores the `SEARCH_PATH` to its original value



.. function:: schema_exists(schema_name)

Returns ``True`` if a schema exists in the current database.

.. code-block:: python

    from django.core.exceptions import ValidationError
    from django.utils.text import slugify

    from tenant_schemas.utils import schema_exists

    class TenantModelForm:
        # ...

        def clean_schema_name(self)
            schema_name = self.cleaned_data["schema_name"]
            schema_name = slugify(schema_name).replace("-", "")
            if schema_exists(schema_name):
                raise ValidationError("A schema with this name already exists in the database")
            else:
                return schema_name


.. function:: get_tenant_model()

Returns the class of the tenant model.

.. function:: get_public_schema_name()

Returns the name of the public schema (from settings or the default ``public``).


.. function:: get_limit_set_calls()

Returns the ``TENANT_LIMIT_SET_CALLS`` setting or the default (``False``). See below.


Logging
-------

The optional ``TenantContextFilter`` can be included in ``settings.LOGGING`` to add the current ``schema_name`` and ``domain_url`` to the logging context.

.. code-block:: python

    # settings.py
    LOGGING = {
        'filters': {
            'tenant_context': {
                '()': 'tenant_schemas.log.TenantContextFilter'
            },
        },
        'formatters': {
            'tenant_context': {
                'format': '[%(schema_name)s:%(domain_url)s] '
                '%(levelname)-7s %(asctime)s %(message)s',
            },
        },
        'handlers': {
            'console': {
                'filters': ['tenant_context'],
            },
        },
    }

This will result in logging output that looks similar to:

.. code-block:: text

    [example:example.com] DEBUG 13:29 django.db.backends: (0.001) SELECT ...


Performance Considerations
--------------------------

The hook for ensuring the ``search_path`` is set properly happens inside the ``DatabaseWrapper`` method ``_cursor()``, which sets the path on every database operation. However, in a high volume environment, this can take considerable time. A flag, ``TENANT_LIMIT_SET_CALLS``, is available to keep the number of calls to a minimum. The flag may be set in ``settings.py`` as follows:

.. code-block:: python

    #in settings.py:
    TENANT_LIMIT_SET_CALLS = True

When set, ``django-tenant-schemas`` will set the search path only once per request. The default is ``False``.


Third Party Apps
----------------

Celery
~~~~~~

Support for Celery is available at `tenant-schemas-celery <https://github.com/maciej-gol/tenant-schemas-celery>`_.

django-debug-toolbar
~~~~~~~~~~~~~~~~~~~~

`django-debug-toolbar <https://github.com/django-debug-toolbar/django-debug-toolbar>`_ routes need to be added to ``urls.py`` (both public and tenant) manually.

.. code-block:: python

    from django.conf import settings
    from django.conf.urls import include
    if settings.DEBUG:
        import debug_toolbar

        urlpatterns += patterns(
            '',
            url(r'^__debug__/', include(debug_toolbar.urls)),
        )
