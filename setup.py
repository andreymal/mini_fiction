#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from setuptools import setup, find_packages

if sys.version_info < (3, 4):
    print("mini_fiction requires Python 3.4 or later.")
    sys.exit(1)


def read_requirements(f, links):
    with open(f, 'r') as fp:
        reqs = fp.read().splitlines()
    result = []
    for line in reqs:
        if not line or line.startswith('#'):
            continue
        if line.startswith('git+'):
            links.append(line)
            result.append(line.rsplit('#egg=', 1)[-1])
        else:
            result.append(line)
    return result


deplinks = []
requirements = read_requirements('requirements.txt', deplinks)
optional_requirements = read_requirements('optional-requirements.txt', deplinks)


import mini_fiction


setup(
    name='mini_fiction',
    version=mini_fiction.__version__,
    description='CMS for fanfics',
    author='andreymal',
    author_email='andriyano-31@mail.ru',
    license='GPLv3',
    url='https://github.com/andreymal/mini_fiction',
    platforms='any',
    packages=find_packages(),
    install_requires=requirements,
    dependency_links=deplinks,
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'mini_fiction=mini_fiction.management.main:run'
        ],
    },
    extras_require={
        'full': optional_requirements,
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: Flask',
        'License :: OSI Approved',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Internet :: WWW/HTTP :: WSGI',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
    ],
)
