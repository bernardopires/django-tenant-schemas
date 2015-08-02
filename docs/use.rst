===========================
Using django-tenant-schemas
===========================
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

    ./manage.py sync_schemas --schema=customer1

migrate_schemas    
~~~~~~~~~~~~~~~

If you're on Django 1.7 or newer, ``migrate_schemas`` is the most important command on this app. The way it works is that it calls Django's ``migrate`` in two different ways. First, it calls ``migrate`` for the ``public`` schema, only syncing the shared apps. Then it runs ``migrate`` for every tenant in the database, this time only syncing the tenant apps.

.. warning::

   You should never directly call ``migrate``. We perform some magic in order to make ``migrate`` only migrate the appropriate apps.

.. code-block:: bash

    ./manage.py migrate_schemas

The options given to ``migrate_schemas`` are also passed to every ``migrate``. Hence you may find handy

.. code-block:: bash

    ./manage.py migrate_schemas --list

sync_schemas
~~~~~~~~~~~~

If you're on Django 1.6 or older, we also packed ``sync_schemas``. It will also respect the ``SHARED_APPS`` and ``TENANT_APPS`` settings, so if you're syncing the ``public`` schema it will only sync ``SHARED_APPS``. If you're syncing tenants, it will only migrate ``TENANT_APPS``.

.. warning::

   You should never directly call ``syncdb``. We perform some magic in order to make ``syncdb`` only sync the appropriate apps.

The options given to ``sync_schemas`` are passed to every ``syncdb``. So if you use South, you may find this handy

.. code-block:: bash

    ./manage.py sync_schemas --migrate

You can also use the option ``--tenant`` to only sync tenant apps or ``--shared`` to only sync shared apps.

.. code-block:: bash

    ./manage.py sync_schemas --shared # will only sync the public schema

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

    ./manage.py createsuperuser --username='admin' --schema=customer1


list_tenants
~~~~~~~~~~~~

Prints to standard output a tab separated list of schema:domain_url values for each tenant.

.. code-block:: bash

    for t in $(./manage.py list_tenants | cut -f1);
    do
        ./manage.py tenant_command dumpdata --schema=$t --indent=2 auth.user > ${t}_users.json;
    done


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
