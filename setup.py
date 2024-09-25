from os.path import exists

from setuptools import find_packages
from setuptools import setup

setup(
    name="django-tenant-schemas",
    author="Bernardo Pires Carneiro",
    author_email="carneiro.be@gmail.com",
    packages=find_packages(),
    scripts=[],
    url="https://github.com/bcarneiro/django-tenant-schemas",
    license="MIT",
    description="Tenant support for Django using PostgreSQL schemas.",
    long_description=open("README.rst").read() if exists("README.rst") else "",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Framework :: Django",
        "Framework :: Django :: 3.2",
        "Framework :: Django :: 4.2",
        "Framework :: Django :: 5.1",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Database",
        "Topic :: Software Development :: Libraries",
    ],
    install_requires=["Django>=3.2", "ordered-set", "psycopg2-binary"],
    setup_requires=["setuptools-scm"],
    use_scm_version=True,
    zip_safe=False,
)
