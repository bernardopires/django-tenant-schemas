===========================
Using django-tenant-schemas
===========================
Creating a Tenant 
-----------------
This works just like any other model in django. The first thing we should do is to create the `public` tenant to make our main website available. We'll use the previous model we defined for `Client`.::

    from customer.models import Client
    
    # create your public tenant
    tenant = Client(domain_url='my-domain.com', # don't add www here!
                    schema_name='public', 
                    name='Schemas Inc.',
                    paid_until='2016-12-05',
                    on_trial=False)
    tenant.save()
    
Now we can create our first real tenant.::

    from customer.models import Client
    
    # create your first real tenant
    tenant = Client(domain_url='tenant.my-domain.com', # don't add www here!
                    schema_name='tenant1', 
                    name='Fonzy Tenant',
                    paid_until='2014-12-05',
                    on_trial=True)
    tenant.save() # sync_schemas automatically called, your tenant is ready to be used!
    
Because you have the tenant middleware installed, any request made to `tenant.my-domain.com` will now automatically set your PostgreSQL's `search_path` to `tenant1` and `public`, making shared apps available too. The tenant will be made available at `request.tenant`. By the way, the current schema is also available at `connection.get_schema()`, which is useful, for example, if you want to hook to any of django's signals. 

Any call to the methods `filter`, `get`, `save`, `delete` or any other function involving a database connection will now be done at the tenant's schema, so you shouldn't need to change anything at your views.

Management commands
-------------------
Every command runs by default on all tenants. To run only a particular schema, there is an optional argument called `--schema`. You can create your own commands that run on every tenant by inheriting `BaseTenantCommand`. There is also an option called `--skip-public` to avoid running the command on the public tenant.::

    ./manage.py sync_schemas 

This is the most important command on this app. The way it works is that it calls Django's `syncdb` in two different ways. First, it calls `syncdb` for the `public` schema, only syncing the shared apps. Then it runs `syncdb` for every tenant in the database, this time only syncing the tenant apps. 

.. warning::

   You should never directly call `syncdb`. We perform some magic in order to make `syncdb` only sync the appropriate apps.

The options given to `sync_schemas` are passed to every `syncdb`. So if you use South, you may find this handy::

    ./manage sync_schemas --migrate
    
You can also use the option `--tenant` to only sync tenant apps or `--shared` to only sync shared apps.::

    ./manage.py migrate_schemas 

This command runs the South's `migrate` command for every tenant in the database.

The options given to `migrate_schemas` are passed to every `migrate`. Hence
you may find::

    ./manage.py migrate_schemas --list

handy if you're curious. Or::

    ./manage.py migrate_schemas myapp 0001_initial --fake

in case you're just switching your `myapp` application to use South migrations.
