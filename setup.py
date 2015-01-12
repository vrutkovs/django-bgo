from setuptools import setup

import os

# Put here required packages or
# Uncomment one or more lines below in the install_requires section
# for the specific client drivers/modules your application needs.
packages = ['Django==1.7',
            'static3',
            'django_pdb',
            'django-bootstrap3']

if 'REDISCLOUD_URL' in os.environ and 'REDISCLOUD_PORT' in os.environ and 'REDISCLOUD_PASSWORD' in os.environ:
    packages.append('django-redis-cache')
    packages.append('hiredis')

setup(name='BGO', version='1.0',
      description='Build.gnome.org replacement',
      author='Vadim Rutkovsky', author_email='vrutkovs@redhat.com',
      url='https://pypi.python.org/pypi',
      install_requires=packages,)
