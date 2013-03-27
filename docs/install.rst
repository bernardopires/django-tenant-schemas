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
        
        # everything below here is optional
        'django.contrib.auth', 
        'django.contrib.contenttypes', 
        'django.contrib.sessions', 
        'django.contrib.sites', 
        'django.contrib.messages', 
        'django.contrib.admin', 
    )
    
    TENANT_APPS = (
        # The following Django contrib apps must be in TENANT_APPS
        'django.contrib.auth',
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
We have a goodie called `PUBLIC_SCHEMA_URL_TOKEN`. Suppose you have your main website at `example.com` and a customer at `customer.example.com`. You probably want your user to be routed to different views when someone requests `http://example.com/` and `http://customer.example.com/`. Because django only uses the string after the host name, this would be impossible, both would call the view at `/`. This is where `PUBLIC_SCHEMA_URL_TOKEN` comes in handy. If set, the string `PUBLIC_SCHEMA_URL_TOKEN` will be prepended to the request's `path_info` when the `public` schema is being requested. So for example, if you have::

    PUBLIC_SCHEMA_URL_TOKEN = '/main'
    
When requesting the view `/login/` from the public tenant (your main website), this will be translated to `/main/login/`. You can now edit your `urls.py` file to use another view for a request incoming at `/main/login/`. Every time a call is made at the public's hostname, `/main` will be prepended to the request's path info. This is of course invisible to the user, even though django will internally see it at as `/main/login/`, the user will still be seeing `/login/`. When receiving a request to a tenant using the `public` schema, this token is added automatically via our middleware. Here's a suggestion for a `urls.py` file.::

    # settings.py
    PUBLIC_SCHEMA_URL_TOKEN = '/main'
    
    # urls.py
    urlpatterns = patterns('',
        url(r'^main/$', 'your_project.public_urls'),
        url(r'^', include('your_project.tenant_urls')),
    )
    
Where `public_urls.py` would contain the patterns for your main website, which is not specific to any tenant and `tenant_urls.py` would contain all your tenant-specific patterns.

As you may have noticed, calling `reverse` or the `{% url %}` template tag would cause the wrong URL to be generated. This app comes with it's own versions for `reverse <https://github.com/bcarneiro/django-tenant-schemas/blob/master/tenant_schemas/urlresolvers.py>`_, `reverse_lazy <https://github.com/bcarneiro/django-tenant-schemas/blob/master/tenant_schemas/urlresolvers.py>`_  and `{% url %} <https://github.com/bcarneiro/django-tenant-schemas/blob/master/tenant_schemas/templatetags/tenant.py>`_ but don't worry, they don't do anything magical, they just remove `PUBLIC_SCHEMA_URL_TOKEN` from the beginning of the URL.

Import the `reverse` and `reverse_lazy` methods where needed.::

    from tenant_schemas.urlresolvers import reverse, reverse_lazy

To use the template tag, add the following line to the top of your template file.::

    {% load url from tenant %}
    
This should not have any side-effects on your current code.

Building Documentation
======================
Documentation is available in ``docs`` and can be built into a number of 
formats using `Sphinx <http://pypi.python.org/pypi/Sphinx>`_. To get started::

    pip install Sphinx
    cd docs
    make html

This creates the documentation in HTML format at ``docs/_build/html``.
