import os
from setuptools import setup, find_packages
from version import get_git_version

def read_file(filename):
    """Read a file into a string"""
    path = os.path.abspath(os.path.dirname(__file__))
    filepath = os.path.join(path, filename)
    try:
        return open(filepath).read()
    except IOError:
        return ''

# Use the docstring of the __init__ file to be the description
DESC = " ".join(__import__('django_schemata').__doc__.splitlines()).strip()

setup(
    name = "django-schemata",
    version = get_git_version(),
    url = '',
    author = 'Vlada Macek',
    author_email = '',
    description = DESC,
    long_description = read_file('README'),
    packages = find_packages(),
    include_package_data = True,
    install_requires=read_file('requirements.txt'),
    classifiers = [
        'License :: OSI Approved :: MIT License',
        'Framework :: Django',
    ],
)
