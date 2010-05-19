#!/usr/bin/env python

import sys
import os
from setuptools import setup, find_packages



_top_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_top_dir, "lib"))
try:
    import eol
finally:
    del sys.path[0]
README = open(os.path.join(_top_dir, 'README.markdown')).read()

setup(name='eol',
    version=eol.__version__,
    description="a command-line script and Python module for working with text file end-of-line (EOL) characters",
    long_description=README,
    classifiers=filter(None, """
        Development Status :: 5 - Production/Stable
        Environment :: Console
        Intended Audience :: Developers
        License :: OSI Approved :: MIT License
        Operating System :: OS Independent
        Programming Language :: Python :: 2
        Topic :: Software Development :: Libraries :: Python Modules
        """.split('\n')),
    keywords='eol cli cr crlf lf',
    author='Trent Mick',
    author_email='trentm@gmail.com',
    maintainer='Trent Mick',
    maintainer_email='trentm@gmail.com',
    url='http://github.com/trentm/eol',
    license='MIT',
    packages=find_packages('lib'),
    package_dir = {'': 'lib'},
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts':
            ['eol=eol:main']
    }
)

