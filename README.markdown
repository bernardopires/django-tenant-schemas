django-tenant-schemas
===============

This application enables [django](https://www.djangoproject.com/) powered websites to have multiple tenants via [PostgreSQL schemas](http://www.postgresql.org/docs/9.1/static/ddl-schemas.html)). A vital feature for every SaaS website.

Django provides currently no simple way to support multiple tenants using the same project instance, even when only the data is different. Because we don't want you running many copies of your project, you'll be able to have:

* Multiple customers running on the same instance
* Shared and Tenant-Specific data
* Tenant View-Routing

What are schemas
------------

A schema can be seen as a directory in an operating system, each directory (schema) with it's own set of files (tables and objects). This allows the same table name and objects to be used in different schemas without conflict. For an accurate description on schemas, see [PostgreSQL's official documentation on schemas](http://www.postgresql.org/docs/9.1/static/ddl-schemas.html).

Why schemas
------------

There are typically three solutions for solving the multinancy problem. 

1. Isolated Approach: Separate Databases. Each tenant has it's own database.

2. Semi Isolated Approach: Shared Database, Separate Schemas. One database for all tenants, but one schema per tenant.

3. Shared Approach: Shared Database, Shared Schema. All tenants share the same database and schema. There is a main tenant-table, where all other tables have a foreign key pointing to.

This application implements the second approach, which in our opinion, represents the ideal compromise between simplicity and performance.

* Simplicity: barely make any changes to your current code to support multitenancy. Plus, you only manage one database.
* Performance: make use of shared connections, buffers and memory.

Each solution has it's up and down sides, for a more in-depth discussion, see Microsoft's excelent article on [Multi-Tenant Data Architecture](http://msdn.microsoft.com/en-us/library/aa479086.aspx).

How it works
----------------

Tenants are identified via their host name (i.e tenant.domain.com). This information is stored on a table on the `public` schema. Whenever a request is made, the host name is used to match a tenant in the database. If there's a match the search path is updated to use this tenant's schema. So from now on all queries will take place at the tenant's schema. For example, suppose you have a tenant `customer` at http://customer.example.com. Any request incoming at `customer.example.com` will automatically use `customer`'s schema and make the tenant available at the request. If no tenant is found, a 404 error is raised. This means you should have a tenant for your main domain, typically using the `public` schema. For more information please read the [setup](#setup) section.

Shared and Tenant-Specific Applications
-------------------

###Tenant-Specific Applications###
Most of your applications are probably tenant-specific, that is, its data is not to be shared with any of the other tenants. This is the default and all your apps are not being shared with any other tenants.

###Shared Applications###

An application is considered to be shared when its tables are in the `public` schema. Some apps make sense being shared. Suppose you have some sort of public data set, for example, a table containing census data. You want every tenant to be able to query it. 

Right now, this is not possible, at least not in practical way. By default all models are being synced to every schema, including `public` and the tenant doesn't have access to `public`. Please take a look at the [tenant-schemas needs your help!](#tenant-schemas-needs-your-help) section if you have an idea on how to do this.

Setup
-----

Assuming you have django installed, you'll have to make the following modifcations to your `settings.py` file.

### Basic Settings ###

Your `DATABASE_ENGINE` setting needs to be changed to

    DATABASES = {
        'default': {
            'ENGINE': 'tenant_schemas.postgresql_backend',
            # ..
        }
    }
    
Add the middleware `tenant_schemas.middleware.TenantMiddleware` to the top of `MIDDLEWARE_CLASSES`, so that each request can be set to use the correct schema.
    
    MIDDLEWARE_CLASSES = (
        'tenant_schemas.middleware.TenantMiddleware',
        ...
    )
    
Don't forget to add `tenant_schemas` to your `INSTALLED_APPS`.
    
    INSTALLED_APPS = (
        ...
	    'tenant_schemas',
	    ...
	)
    
### The Tenant Model ###
    
Now we have to create your tenant model. To allow the flexibility of having any data in you want in your tenant, we have a mixin called `TenantMixin` which you *have to* inherit from. This Mixin only has two fields (`domain_url` and `schema_name`) and both are required. Here's an example, suppose we have an app named `customer` and we want to create a model called `client`.

	from tenant_schemas.models import TenantMixin
	
	class Client(TenantMixin):
		name = models.CharField(max_length=100)
		paid_until =  models.DateField()
		on_trial = models.BooleanField()
		created_on = models.DateField(auto_now_add=True)
        
        # default true, schema will be automatically created and synced when it is saved
        auto_create_schema = True 
    
Going back to `settings.py`, we can now set `TENANT_MODEL`.

    TENANT_MODEL = "customer.Client" # app.Model
    
Now run `syncdb`.

    python manage.py syncdb
    
Lastly, you need to create a tenant whose schema is `public` and it's address is your domain URL. Please see the section on [Using django-tenant-schemas](#using-django-tenant-schemas).

### South ###
	
This app supports [south](http://south.aeracode.org/), so if you haven't configured it yet,
    
	# For Django 1.1 or below:
	#SOUTH_DATABASE_ADAPTER = 'south.db.postgresql_psycopg2'
	# For Django 1.2 or above:
	SOUTH_DATABASE_ADAPTERS = {
	    'default': 'south.db.postgresql_psycopg2',
	}
    
### Optional Settings ###
By the default `PUBLIC_SCHEMA_URL_TOKEN` is set to `None`, which means you can't serve different views on the same path. To be able to have tenant URL routing see the section below.

Tenant View-Routing
------------------
We have a goodie called `PUBLIC_SCHEMA_URL_TOKEN`. Suppose you have your main website at `example.com` and a customer at `customer.example.com`. You probably want your user to be routed to different views when someone requests `http://example.com/` and `http://customer.example.com/`. Because django only uses the string after the host name, this would be impossible, both would call the view at `/`. This is where `PUBLIC_SCHEMA_URL_TOKEN` comes in handy. If set, the string `PUBLIC_SCHEMA_URL_TOKEN` will be prepended to the request's `path_info` when the `public` schema is being requested. So for example, if you have

    PUBLIC_SCHEMA_URL_TOKEN = '/main'
    
When requesting the view `/login/` from the public tenant (your main website), this will be translated to `/main/login/`. You can now edit your `urls.py` file to use another view for a request incoming at `/main/login/`. Every time a call is made at the public's hostname, `/main` will be prepended to the request's path info. This is of course invisible to the user, even though django will internally see it at as `/main/login/`, the user will still be seeing `/login/`. When receiving a request to a tenant using the `public` schema, this token is added automatically via our middleware. Here's a suggestion for a `urls.py` file.

    # settings.py
	PUBLIC_SCHEMA_URL_TOKEN = '/main'
	
	# urls.py
	urlpatterns = patterns('',
		url(r'^main/$', 'your_project.public_urls'),
		url(r'^', include('your_project.tenant_urls')),
	)
	
Where `public_urls.py` would contain the patterns for your main website, which is not specific to any tenant and `tenant_urls.py` would contain all your tenant-specific patterns.

As you may have noticed, calling `revert` or the `{% url %}` template tag would cause the wrong URL to be generated. This app comes with it's own versions for `revert`, `revert_lazy` (see [tenant_schemas/urlresolvers.py](https://github.com/bcarneiro/django-tenant-schemas/blob/master/tenant_schemas/urlresolvers.py)) and `{% url %}` (see [tenant_schemas/templatetags/tenant.py](https://github.com/bcarneiro/django-tenant-schemas/blob/master/tenant_schemas/templatetags/tenant.py)). But don't worry, they don't do anything magical, they just remove `PUBLIC_SCHEMA_URL_TOKEN` from the beginning of the URL.

Import the `reverse` and `reverse_lazy` methods where needed.

    from tenant_schemas.urlresolvers import reverse, reverse_lazy

To use the template tag, add the following line to the top of your template file.

    {% load url from tenant %}
    
This should not have any side-effects on your current code.

Using django-tenant-schemas
-------------------

Creating a Tenant works just like any other model in django. Following our previous example,
    
    from customer.models import Client
    
    tenant = Client(domain_url='tenant.my-domain.com', # don't add www here!
                    schema_name='tenant1', 
                    name='Fonzy Tenant',
                    paid_until='12/05/2014',
                    on_trial=True)
    tenant.save() # syncdb automatically called, your tenant is ready to be used!
    
    # create your public tenant
    tenant = Client(domain_url='my-domain.com', # don't add www here!
                    schema_name='public', 
                    name='Schemas Inc.',
                    paid_until='12/05/2016',
                    on_trial=False)
    tenant.save()

Because you have the tenant middleware installed, any request made to `tenant.my-domain.com` will now automatically set the schema to `tenant1` and the tenant will be made available at `request.tenant`. By the way, the current schema is also available at `connection.get_schema()`, which is useful, for example, if you want to hook to any of django's signals. 

Any call to the methods `filter`, `get`, `save`, `delete` or any other function involving a database connection will now be done at the tenant's schema, so you shouldn't need to change anything at your views.

Management commands
-------------------

Every command runs by default on all tenants. To run only a particular schema, there is an optional argument called `--schema`. You can create your own commands that run on every tenant by inheriting `BaseTenantCommand`. There is also an option called `--skip-public` to avoid running the command on the public tenant.

### ./manage.py sync_schemas ###

This command runs the `syncdb` command for every tenant in the database. Also creates the schema if necessary.

The options given to `sync_schemas` are passed to every `syncdb`. So if you
use South, you may find this handy:

    ./manage sync_schemas --migrate

### ./manage.py migrate_schemas ###

This command runs the South's `migrate` command for every tenant in the database.

The options given to `migrate_schemas` are passed to every `migrate`. Hence
you may find

    ./manage.py migrate_schemas --list

handy if you're curious. Or

    ./manage.py migrate_schemas myapp 0001_initial --fake

in case you're just switching your `myapp` application to use South migrations.

Running the tests
------------------------
    ./manage.py test tenant_schemas
If you're using South, don't forget to set `SOUTH_TESTS_MIGRATE = False`.

Updating your app's tests to work with tenant-schemas
------------------------
Because django will not create tenants for you during your tests, we have packed some custom test cases and other utilities. If you want a test to happen at any of the tenant's domain, you can use the test case `TenantTestCase`. It will automatically create a tenant for you, set the connection's schema to tenant's schema and make it available at `self.tenant`. We have also included a `TenantRequestFactory` and a `TenantClient` so that your requests will all take place at the tenant's domain automatically. Here's an example:

	from tenant_schemas.test.cases import TenantTestCase
	from tenant_schemas.test.client import TenantClient

	class BaseSetup(TenantTestCase):
		def setUp(self):
			self.c = TenantClient(self.tenant)
			
		def test_user_profile_view(self):
			response = self.c.get(reverse('user_profile'))
		    self.assertEqual(response.status_code, 200)

tenant-schemas needs your help!
------------------------

###Suggestions, bugs, ideas, patches, questions###
Are *highly* welcome! Feel free to write an issue for any feedback you have. :)

###Shared and Tenant-Specific Apps###
[`django-appschema`](https://bitbucket.org/cedarlab/django-appschema/overview) tries to solve this in a very hackish and dangerous way by altering django's app cache. This is not safe for on-the-fly creation of tenants, so this is not an option. [django-schemata](https://github.com/tuttle/django-schemata) partially solves it by forcing you to move your shared tables to the `public` schema. When syncing the tables for tenant-specific applications, the search path is set to `public` plus the tenant's schema, which means all tables that already exist on `public` will not be created when syncing. This is not ideal because it doesn't allow you have to applications that are both shared and tenant-specific. For example, you may need to have a user system for your main domain and another for your tenants. Or you may want to have `south` in both.

To enable this, an idea would be to let all models, both shared and tenant-specific to be synced. After the sync, the unnecessary models can be deleted from the database. There would be three arrays, `SHARED_APPS`, `TENANT_APPS` and `MUTUAL_APPS`. For example, when syncing the `public` schema, we can just iterate over `TENANT_APPS` deleting their tables. When syncing tenants, we delete the `SHARED_APPS` tables. We can then enable the tenants to also see the `public` schema. This is of course not very elegant, but shouldn't present a big hit on performance (how often do you sync your models?) and doesn't involve hacking django's cache.

An ever simpler solution would be if it were possible to select which models have to be synced. AFAIK this is not possible, syncdb is called for all models on `INSTALLED_APPS`.

Please send in your feedback at issue #1.

###Multi-Threading###
This is being used right now in production on a small project and I have made an attempt to make it thread-safe, but I'm a complete beginner at this subject. Any help on this would be *HIGHLY* appreciated. Can someone please check if the custom [postgresql_backend](https://github.com/bcarneiro/django-tenant-schemas/blob/master/tenant_schemas/postgresql_backend/base.py) is thread-safe? If there is a way to write a test for this, it would be awesome. Please send in your feedback at issue #2.

####Template tag `{% url %}`####
Basically 100% of the code was copied from Django's source, just to be able to remove `settings.PUBLIC_SCHEMA_URL_TOKEN` from the URL. There should be a smarter way to do this. Please send in your feedback at issue #3.

####2 Small to-dos at testing####
Take a look at [tenant_schemas/tests/schemas.py](https://github.com/bcarneiro/django-tenant-schemas/blob/master/tenant_schemas/tests/tenants.py) and search for the string `todo`.  Please send in your feedback at issue #4.

Final Notes
-----
This app is based off [django-schemata](https://github.com/tuttle/django-schemata). My intention initially was only to be a fork, but as my objectives differ significantly from django-schemata's, I've decided to create a new app. For example, whereas django-schemata only supports tenant creation via editing the settings file, this project allows tenants to be created on the fly, a feature virtually every SaaS project needs.
