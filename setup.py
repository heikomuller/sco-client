#! /usr/bin/env python

from setuptools import setup

setup(
    name='sco-client',
    version='0.5.1',
    description='Library to interact with Standard Cortical Observer Web API',
    keywords='neuroscience vision cortex ',
    author='Heiko Mueller',
    author_email='heiko.muller@gmail.com',
    url='https://github.com/heikomuller/sco-client',
    license='GPLv3',
    packages=['scocli'],
    package_data={'': ['LICENSE']},
    install_requires=[
        'python-dateutil',
        'requests',
        'sco-datastore',
        'sco-engine'
    ]
)
