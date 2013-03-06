django-tenant-schemas
===============
This application enables [django](https://www.djangoproject.com/) powered websites to have multiple tenants via [PostgreSQL schemas](http://www.postgresql.org/docs/9.1/static/ddl-schemas.html). A vital feature for every Software-as-a-Service website.

Django provides currently no simple way to support multiple tenants using the same project instance, even when only the data is different. Because we don't want you running many copies of your project, you'll be able to have:

* Multiple customers running on the same instance
* Shared and Tenant-Specific data
* Tenant View-Routing

What are schemas
----------------
A schema can be seen as a directory in an operating system, each directory (schema) with it's own set of files (tables and objects). This allows the same table name and objects to be used in different schemas without conflict. For an accurate description on schemas, see [PostgreSQL's official documentation on schemas](http://www.postgresql.org/docs/9.1/static/ddl-schemas.html).

Why schemas
-----------
There are typically three solutions for solving the multinancy problem. 

1. Isolated Approach: Separate Databases. Each tenant has it's own database.

2. Semi Isolated Approach: Shared Database, Separate Schemas. One database for all tenants, but one schema per tenant.

3. Shared Approach: Shared Database, Shared Schema. All tenants share the same database and schema. There is a main tenant-table, where all other tables have a foreign key pointing to.

This application implements the second approach, which in our opinion, represents the ideal compromise between simplicity and performance.

* Simplicity: barely make any changes to your current code to support multitenancy. Plus, you only manage one database.
* Performance: make use of shared connections, buffers and memory.

Each solution has it's up and down sides, for a more in-depth discussion, see Microsoft's excelent article on [Multi-Tenant Data Architecture](http://msdn.microsoft.com/en-us/library/aa479086.aspx).

How it works
------------
Tenants are identified via their host name (i.e tenant.domain.com). This information is stored on a table on the `public` schema. Whenever a request is made, the host name is used to match a tenant in the database. If there's a match, the search path is updated to use this tenant's schema. So from now on all queries will take place at the tenant's schema. For example, suppose you have a tenant `customer` at http://customer.example.com. Any request incoming at `customer.example.com` will automatically use `customer`'s schema and make the tenant available at the request. If no tenant is found, a 404 error is raised. This also means you should have a tenant for your main domain, typically using the `public` schema. For more information please read the [setup](https://django-tenant-schemas.readthedocs.org/en/latest/install.html) section.

What can this app do?
---------------------------------------
### As many tenants as you want ###
Each tenant has its data on a specific schema. Use a single project instance to serve as many as you want.

### Tenant-specific and shared apps ###
Tenant-specific apps do not share their data between tenants, but you can also have shared apps where the information is always available and shared between all.

### Tenant View-Routing ###
You can have different views for `http://customer.example.com/` and `http://example.com/`, even though Django only uses the string after the host name to identify which view to serve.

### Magic ###
Everyone loves magic! You'll be able to have all this barely having to change your code!

Setup & Documentation
-------------
Can be found at [django-tenant-schemas.readthedocs.org](https://django-tenant-schemas.readthedocs.org/en/latest/).
