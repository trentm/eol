`eol` is both a command-line script `eol` and a Python module `eol` for working
with end-of-line chars in text files.

This project lives here: <http://github.com/trentm/eol>

## Installation

To install in your Python's global site-packages use one of the
following:

    pip install eol
    pypm install eol   # if you use ActivePython (http://www.activestate.com/activepython)

But you use a
[virtualenvs](http://www.arthurkoziel.com/2008/10/22/working-virtualenv/),
right? If so, then use one of the following:

    pip -E path/to/env install eol
    pypm -E path/to/env install eol


## Command-line examples

**List the EOL-style** of given paths:

    $ eol *.txt
    foo_cr.txt: Mac Classic (CR)
    foo_crlf.txt: Windows (CRLF)
    foo_empty.txt: No EOLs
    foo_lf.txt: Unix (LF)
    foo_mixed.txt: Mixed, predominantly Unix (LF)

Recursively:
    
    $ eol -r ~/src/redis
    /Users/trentm/src/redis/.gitignore: Unix (LF)
    /Users/trentm/src/redis/BETATESTING.txt: Unix (LF)
    /Users/trentm/src/redis/BUGS: Unix (LF)
    /Users/trentm/src/redis/COPYING: Unix (LF)
    ...
    /Users/trentm/src/redis/zmalloc.h: Unix (LF)
    /Users/trentm/src/redis/.git/HEAD: Unix (LF)
    /Users/trentm/src/redis/.git/config: Unix (LF)
    ...
    /Users/trentm/src/redis/client-libraries/README: Unix (LF)
    /Users/trentm/src/redis/design-documents/REDIS-CLUSTER: Unix (LF)
    /Users/trentm/src/redis/doc/AppendOnlyFileHowto.html: Unix (LF)
    /Users/trentm/src/redis/doc/AuthCommand.html: Unix (LF)
    ...

**Find files** with the given EOL-style:

    $ eol -f crlf -x .svn -r ~/src/python
    /Users/trentm/src/python/Doc/make.bat
    /Users/trentm/src/python/Lib/email/test/data/msg_26.txt
    /Users/trentm/src/python/Lib/encodings/cp720.py
    /Users/trentm/src/python/Lib/test/decimaltestdata/and.decTest
    ...
    /Users/trentm/src/python/PC/VS8.0/x64.vsprops
    /Users/trentm/src/python/PCbuild/pcbuild.sln
    ...

**Convert files** to a given EOL-style:

    $ eol ~/src/python/Tools/msi/merge.py
    /Users/trentm/src/python/Tools/msi/merge.py: Windows (CRLF)
    $ eol -c cr ~/src/python/Tools/msi/merge.py
    
    # But who really wants CR (aka Mac Classic, '\r') EOLs.
    # "native" is an alias for the EOL-style native to the current platform
    $ eol -c native ~/src/python/Tools/msi/merge.py
    converted `/Users/trentm/src/python/Tools/msi/merge.py' to LF EOLs
    $ eol ~/src/python/Tools/msi/merge.py
    /Users/trentm/src/python/Tools/msi/merge.py: Unix (LF)


## Module examples

**List the EOL-style** of given paths:

    >>> import eol, glob
    >>> for path in glob.glob("*.txt")
    >>> for path in glob.glob("*.txt"):
    ...   print path, eol.eol_info_from_path(path)
    ... 
    foo_cr.txt ('\r', '\r')         # (<detected-eols>, <suggested-eols>)
    foo_crlf.txt ('\r\n', '\r\n')
    foo_empty.txt (None, '\n')      # suggests the native EOL for empty content
    foo_lf.txt ('\n', '\n')
    foo_mixed.txt (<class 'eol.MIXED'>, '\n')

Recursively:
    
    >>> for i in eol.eol_info_from_path_patterns(["/Users/trentm/src/redis"], recursive=True): print i
    ... 
    ('/Users/trentm/src/redis/.gitignore', '\n', '\n')
    ('/Users/trentm/src/redis/BETATESTING.txt', '\n', '\n')
    ('/Users/trentm/src/redis/BUGS', '\n', '\n')
    ('/Users/trentm/src/redis/COPYING', '\n', '\n')
    ...

**Convert files** to a given EOL-style:

    >>> path = "/Users/trentm/src/python/Tools/msi/merge.py"
    >>> eol.eol_info_from_path(path)
    ('\r\n', '\r\n')
    >>> eol.convert_path_eol(path, "\n")
    >>> eol.eol_info_from_path(path)
    ('\n', '\n')
