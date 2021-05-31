Welcome to django-pg-tenants documentation!
===============================================
This application enables `Django <https://www.djangoproject.com/>`_ powered websites to have multiple tenants via `PostgreSQL schemas <http://www.postgresql.org/docs/9.2/static/ddl-schemas.html>`_. A vital feature for every Software-as-a-Service website.

Django provides currently no simple way to support multiple tenants using the same project instance, even when only the data is different. Because we don't want you running many copies of your project, you'll be able to have:

* Multiple customers running on the same instance
* Shared and Tenant-Specific data
* Tenant View-Routing

What are schemas?
-----------------
A schema can be seen as a directory in an operating system, each directory (schema) with it's own set of files (tables and objects). This allows the same table name and objects to be used in different schemas without conflict. For an accurate description on schemas, see `PostgreSQL's official documentation on schemas <http://www.postgresql.org/docs/9.2/static/ddl-schemas.html>`_.

Why schemas?
------------
There are typically three solutions for solving the multitenancy problem.

1. Isolated Approach: Separate Databases. Each tenant has it's own database.

2. Semi Isolated Approach: Shared Database, Separate Schemas. One database for all tenants, but one schema per tenant.

3. Shared Approach: Shared Database, Shared Schema. All tenants share the same database and schema. There is a main tenant-table, where all other tables have a foreign key pointing to.

This application implements the second approach, which in our opinion, represents the ideal compromise between simplicity and performance.

* Simplicity: barely make any changes to your current code to support multitenancy. Plus, you only manage one database.
* Performance: make use of shared connections, buffers and memory.

Each solution has it's up and down sides, for a more in-depth discussion, see Microsoft's excellent article on `Multi-Tenant Data Architecture <http://msdn.microsoft.com/en-us/library/aa479086.aspx>`_.

How it works
------------
Tenants are identified via their host name (i.e tenant.domain.com). This information is stored on a table on the ``public`` schema. Whenever a request is made, the host name is used to match a tenant in the database. If there's a match, the search path is updated to use this tenant's schema. So from now on all queries will take place at the tenant's schema. For example, suppose you have a tenant ``customer`` at http://customer.example.com. Any request incoming at ``customer.example.com`` will automatically use ``customer``'s schema and make the tenant available at the request. If no tenant is found, a 404 error is raised. This also means you should have a tenant for your main domain, typically using the ``public`` schema. For more information please read the [setup](#setup) section.

Shared and Tenant-Specific Applications
---------------------------------------
Tenant-Specific Applications
++++++++++++++++++++++++++++
Most of your applications are probably tenant-specific, that is, its data is not to be shared with any of the other tenants.

Shared Applications
+++++++++++++++++++
An application is considered to be shared when its tables are in the ``public`` schema. Some apps make sense being shared. Suppose you have some sort of public data set, for example, a table containing census data. You want every tenant to be able to query it. This application enables shared apps by always adding the ``public`` schema to the search path, making these apps also always available.

Contents
--------

.. toctree::
   :maxdepth: 2

   install
   use
   advanced_usage
   examples
   templates
   test
   involved

