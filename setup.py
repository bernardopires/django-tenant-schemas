#!/usr/bin/env python

from os.path import exists
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

from tenant_schemas import __version__

setup(
    name='django-tenant-schemas',
    version=__version__,
    author='Bernardo Pires Carneiro',
    author_email='carneiro.be@gmail.com',
    packages=['tenant_schemas'],
    scripts=[],
    url='https://github.com/bcarneiro/django-tenant-schemas',
    license='MIT',
    description='Tenant support for Django using PostgreSQL schemas.',
    long_description=open('README.markdown').read() if exists("README.markdown") else "",
    install_requires=[
        "Django >= 1.2.0"
    ],
)
