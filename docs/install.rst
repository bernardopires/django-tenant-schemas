==================
Installation
==================
Assuming you have django installed, the first step is to install `django-tenant-schemas`.::

    pip install django-tenant-schemas

Basic Settings
==============
You'll have to make the following modifcations to your `settings.py` file.

Your `DATABASE_ENGINE` setting needs to be changed to::

    DATABASES = {
        'default': {
            'ENGINE': 'tenant_schemas.postgresql_backend',
            # ..
        }
    }
    
Add the middleware `tenant_schemas.middleware.TenantMiddleware` to the top of `MIDDLEWARE_CLASSES`, so that each request can be set to use the correct schema.::
    
    MIDDLEWARE_CLASSES = (
        'tenant_schemas.middleware.TenantMiddleware',
        #...
    )
    
The Tenant Model
================
Now we have to create your tenant model. To allow the flexibility of having any data in you want in your tenant, we have a mixin called `TenantMixin` which you *have to* inherit from. This Mixin only has two fields (`domain_url` and `schema_name`) and both are required. Here's an example, suppose we have an app named `customers` and we want to create a model called `client`.::

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
By default all apps will be synced to your `public` schema and to your tenant schemas. If you want to make use of shared and tenant-specific applications, there are two additional settings called `SHARED_APPS` and `TENANT_APPS`. `SHARED_APPS` is a tuple of strings just like `INSTALLED_APPS` and should contain all apps that you want to be synced to `public`. If `SHARED_APPS` is set, then these are the only apps that will be to your `public` schema! The same applies for `TENANT_APPS`, it expects a tuple of strings where each string is an app. If set, only those applications will be synced to all your tenants. Here's a sample setting::

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

You also have to set where your tenant model is.::

    TENANT_MODEL = "customers.Client" # app.Model
    
Now run `sync_schemas`, this will create the shared apps on the `public` schema. Note: your database should be empty if this is the first time you're running this command.::

    python manage.py sync_schemas --shared
    
.. warning::

   Never use `syncdb` as it would sync *all* your apps to `public`!
    
Lastly, you need to create a tenant whose schema is `public` and it's address is your domain URL. Please see the section on :doc:`use <use>`.

South Migrations
================
This app supports `South <http://south.aeracode.org/>`_  so if you haven't configured it yet and would like to:

For Django 1.1 or below::

    SOUTH_DATABASE_ADAPTER = 'south.db.postgresql_psycopg2'

For Django 1.2 or above::

    SOUTH_DATABASE_ADAPTERS = {
        'default': 'south.db.postgresql_psycopg2',
    }
    
You can list `south` under `TENANT_APPS` and `SHARED_APPS` if you want. 

Optional Settings
=================
By default `PUBLIC_SCHEMA_URL_TOKEN` is set to `None`, which means you can't serve different views on the same path. To be able to have tenant URL routing see the section below.

Tenant View-Routing
-------------------
We have a goodie called `PUBLIC_SCHEMA_URLCONF`. Suppose you have your main website at `example.com` and a customer at `customer.example.com`. You probably want your user to be routed to different views when someone requests `http://example.com/` and `http://customer.example.com/`. Because django only uses the string after the host name, this would be impossible, both would call the view at `/`. This is where `PUBLIC_SCHEMA_URLCONF` comes in handy. If set, when the `public` schema is being requested, the value of this variable will be used instead of `ROOT_URLCONF <https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-ROOT_URLCONF>`. So for example, if you have::

    PUBLIC_SCHEMA_URLCONF = 'myproject.urls_public'
    
When requesting the view `/login/` from the public tenant (your main website), it will search for this path on `PUBLIC_SCHEMA_URLCONF` instead of `ROOT_URLCONF`. 

Building Documentation
======================
Documentation is available in ``docs`` and can be built into a number of 
formats using `Sphinx <http://pypi.python.org/pypi/Sphinx>`_. To get started::

    pip install Sphinx
    cd docs
    make html

This creates the documentation in HTML format at ``docs/_build/html``.
