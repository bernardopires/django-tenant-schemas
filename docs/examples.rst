===========================
Examples
===========================
Tenant Tutorial
-----------------
This app comes with an interactive tutorial to teach you how to use ``django-tenant-schemas`` and to demonstrate its capabilities. This example project is available under `examples/tenant_tutorial <https://github.com/bernardopires/django-tenant-schemas/blob/master/examples/tenant_tutorial>`_. 

Setup Instructions
~~~~~~~~~~~~~~~~~~

**Prerequisites**: This tutorial requires `uv <https://docs.astral.sh/uv/>`_, a fast Python package manager. Install it by following the `uv installation guide <https://docs.astral.sh/uv/getting-started/installation/>`_.

1. **Check dependencies**: Navigate to the tutorial directory and run the ``check`` management command:

.. code-block:: bash

    cd examples/tenant_tutorial
    ./manage.py check

2. **Configure the database**: Edit the ``settings.py`` file to configure the ``DATABASES`` variable for your PostgreSQL setup. The default configuration expects a PostgreSQL database named ``tenant_tutorial`` with user ``postgres`` and password ``root`` on localhost.

.. code-block:: bash

   echo "SELECT 1 AS test" | ./manage.py dbshell

3. **Run initial migrations**: Use ``migrate_schemas`` instead of the regular ``migrate`` command:

.. code-block:: bash

    ./manage.py migrate_schemas --shared

4. **Create the public tenant**: Use ``create_client`` command (defined in ``customers`` app:

.. code-block:: bash

    ./manage.py create_client public localhost "Tutorial Public Tenant" --description "Public tenant for tutorial validation"

4. **Start the development server**:

.. code-block:: bash

    ./manage.py runserver localhost:9000

All other steps will be explained by following the tutorial, just open ``http://localhost:9000`` in your browser.

**Important Notes:**

- Always use ``migrate_schemas`` instead of ``migrate`` when working with tenant schemas
- The tutorial uses ``ALLOWED_HOSTS = ['*']`` for development convenience - be more restrictive in production
- Make sure PostgreSQL is installed and running before starting the tutorial
