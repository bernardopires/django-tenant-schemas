django-schemata
===============

**BEWARE! THIS IS AN EXPERIMENTAL CODE! Created this as a proof of concept
and never had a chance to test it thoroughly, not speaking about the
production run, as our team changed the plans.  While I was very excited
during coding it, I unfortunately have no use for schemata currently.  I'd
love to hear how the code is really doing and if you find something that
should be fixed, I'll gladly reviewpull your patches.  **

This project adds the [PostgreSQL schema](http://www.postgresql.org/docs/8.4/static/ddl-schemas.html)
support to [Django](http://www.djangoproject.com/). The schema, which can
be seen as a namespace in which any database object exists, allows to isolate
the database objects even when they have the same names. You can have same set
of tables, indices, sequences etc. many times under the single database.

In case you're not using schemata, your objects lie in the default schema
`public` and because the default `search_path` contains `public`,
you don't have to care.

Why to care?
------------

It's simple: 

* One code
* One instance
* One shared buffering
* One connection
* One database
* One schema for one customer
* You scale up to the stars

Using schemata can be very useful if you run the Software as a service (SaaS)
server for multiple customers. Typically for *multiple* databases you had *single*
project code, cloned many times and that required strong maintenance effort. 

So until recently you were forced to maintain multiple Django instances even
when the code did the same things, only the data varied. With the invention
of multiple databases support in Django it was possible to use it for SaaS,
yet using schemata was found to bring even more advantages.

This code was inspired by the [A better way : SaaS with Django and PostgreSQL Schemas](http://tidbids.posterous.com/saas-with-django-and-postgresql-schemas)
blog post and the [django-appschema](https://bitbucket.org/cedarlab/django-appschema/src)
application.

Going underneath
----------------

Like `django-appschema` this project infers the proper schema to switch to
from the hostname found in each web request. You're expected to point
multiple HTTP domains of your customers handled by your (Apache/WSGI) server
to the single Django instance supporting schemata.

**Warning:** This application was **not tested in the multithreading**
environment, we configure our mod_wsgi to run each Django instance
as mutiple separated processes.

Unlike `django-appschema`, this project seeks for the **maximum simplicity**
(added layer and toolset must be as thin as possible so the data path is clear):

* Minimalistic code.
* **No hacking** of `INSTALLED_APPS`, `syncdb` or `migrate` commands...
  (they had enough with [South](http://south.aeracode.org/)).
* Schema definitions are not stored in the database, but in `settings`'s dict.
  That allows you to flexibly and uniformly configure the differences between
  individual domains. `django-schemata` only requires `schema_name` sub-key,
  but you're free to store additional configuration there. 

Shared applications
-------------------

Not yet.

The reason why `django-appschema` became hackish is that it tries to
sync/migrate both isolated and shared applications in a single run. The app is
*shared* if it has its tables in the `public` schema, hence they're accessible
by every domain. That's because `public` schema is always checked after the
object was not found in its "home" schema. 

The support for shared application will be added to `django-schemata` as soon
as it becomes clear it is required. And we strive to add the support
in a more simple way: `ALTER TABLE table SET SCHEMA schema` looks
*very promising*. We believe it's bearable for the admin to do some extra
setup steps, when the code stays simple. 

Setup
-----

`django-schemata` requires the following `settings.py` modifications:

	# We wrap around the PostgreSQL backend.
    DATABASE_ENGINE = 'django_schemata.postgresql_backend'

    # Schema switching upon web requests.
    MIDDLEWARE_CLASSES = (
        'django_schemata.middleware.SchemataMiddleware',
        ...
	)
	
	# We also offer some management commands.
	INSTALLED_APPS = (
		...
	    'django_schemata',
	    ...
	)
	
	# We need to assure South of the real db backends for all databases.
	# Otherwise it dies in uncertainty.
	# For Django 1.1 or below:
	#SOUTH_DATABASE_ADAPTER = 'south.db.postgresql_psycopg2'
	# For Django 1.2 or above:
	SOUTH_DATABASE_ADAPTERS = {
	    'default': 'south.db.postgresql_psycopg2',
	}
	
	# This maps all HTTP domains to all schemata we want to support.
	# All of your supported customers need to be registered here. 
	SCHEMATA_DOMAINS = {
	    'localhost': {
	    	'schema_name': 'localhost',
	    	'additional_data': ...
	    },
	    'first-client.com': {
	    	'schema_name': 'firstclient',
	    },
	    'second-client.com': {
	    	'schema_name': 'secondclient',
	    },
	}

Management commands
-------------------

### ./manage.py manage_schemata ###

As soon as you add your first domain to `settings.SCHEMATA_DOMAINS`, you can
run this. PostgreSQL database is inspected and yet-not-existing schemata
are added. Current ones are not touched (command is safe to re-run).

Later more capabilities will be added here.

### ./manage.py sync_schemata ###

This command runs the `syncdb` command for every registered database schema.
You can sync **all** of your apps and domains in a single run. 

The options given to `sync_schemata` are passed to every `syncdb`. So if you
use South, you may find this handy:

    ./manage sync_schemata --migrate

### ./manage.py migrate_schemata ###

This command runs the South's `migrate` command for every registered database
schema.

The options given to `migrate_schemata` are passed to every `migrate`. Hence
you may find

    ./manage.py migrate_schemata --list

handy if you're curious or

    ./manage.py migrate_schemata myapp 0001_initial --fake

in case you're just switching `myapp` application to use South migrations.

Bug report? Idea? Patch?
------------------------

We're happy to incorporate your patches and ideas. Please either fork and send
pull requests or just send the patch.

Discuss this project! Please report bugs.

Success stories are highly welcome.

Thank you.
