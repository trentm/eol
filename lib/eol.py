#!/usr/bin/env python3
# Copyright (c) 2005-2010 ActiveState Software Inc.

"""eol -- a tool for working with EOLs in text files

Usage:
  eol FILE...             # list EOL-style of file(s)
  eol -c NAME FILE...     # convert file(s) to given EOL-style
  eol -f NAME FILE...     # find files with the given EOL-style

`eol` is a tool for working with EOLs in text files: determining the
EOL type and converting between types. `eol.py` can also be used as
a Python module.

By default with the command-line interface, binary files are skipped
where "binary files" is any file with a null in the content (not perfect).

Please report inadequacies to <http://github.com/trentm/eol/issues>.
"""
# Nomenclature: (TODO)
#   eol                 the actual EOL string: '\n', '\r\n' or '\r'
#   eol-name            the EOL name: 'LF', 'CRLF', 'CR', 'NATIVE' or 'MIXED'
#   eol-english-name    English representation, e.g.: 'Windows (CRLF)'
#
#TODO:
# - module usage docstring and move command-line docstring
# - Add 'hint' for the suggested eol in eol_info_from_text()? Useful for
#   Komodo if there is a pref.
# - Add 'convert_stream_eol_type(stream, eol_type, n=1024)'? Where 'n'
#   is the read chunksize and this is generator: yields chunks.
# - __all__

__version_info__ = (0, 7, 6)
__version__ = '.'.join(map(str, __version_info__))

import os
import sys
import optparse
import logging
import glob
import stat
import errno



#---- globals

log = logging.getLogger("eol")


# The EOL types.
CR = "\r"
LF = "\n"
CRLF = "\r\n"
if sys.platform == "win32":
    NATIVE = CRLF
else:
    # Yes, LF is the native EOL even on Mac OS X. CR is just for
    # Mac OS <=9 (a.k.a. "Mac Classic")
    NATIVE = LF
class MIXED(object):
    """EOL for files with mixed EOLs"""
    pass


# Internal mappings.
_english_name_from_eol = {
    CRLF : "Windows (CRLF)",
    CR   : "Mac Classic (CR)",
    LF   : "Unix (LF)",
    MIXED: "Mixed",
    None : "No EOLs"
}
_eol_from_name = {
    "CRLF"  : CRLF,
    "CR"    : CR,
    "LF"    : LF,
    "NATIVE": NATIVE,
    "MIXED" : MIXED,
    "NONE"  : None,

    # Some convenience aliases.
    "DOS"    : CRLF,
    "WINDOWS": CRLF,
    "UNIX"   : LF,
}
_name_from_eol = {
    CRLF: "CRLF",
    CR  : "CR",
    LF  : "LF"
}


# Python 2/3 compat
try:
    _BASESTRING = basestring
except NameError:
    _BASESTRING = str
if sys.version_info[0] > 2:
    _BYTES_NULL = bytes([0])
else:
    _BYTES_NULL = '\0'



#---- public module interface

def english_name_from_eol(eol):
    r"""english_name_from_eol(EOL) -> English description for EOL

        >>> english_name_from_eol(LF)
        'Unix (LF)'
        >>> english_name_from_eol('\r\n')
        'Windows (CRLF)'
        >>> english_name_from_eol(CR)
        'Mac Classic (CR)'
        >>> english_name_from_eol(MIXED)
        'Mixed'
        >>> english_name_from_eol(None)
        'No EOLs'
    """
    try:
        return _english_name_from_eol[eol]
    except KeyError:
        raise ValueError("unknown EOL: %r" % eol)


def eol_from_name(name):
    r"""eol_from_name(NAME) -> EOL for this

     Return the EOL for the given name:

        >>> eol_from_name("LF")
        '\n'
        >>> eol_from_name("CRLF")
        '\r\n'
        >>> eol_from_name("CR")
        '\r'
        >>> eol_from_name("CRLF") == CRLF
        True
        >>> eol_from_name("NATIVE") == NATIVE
        True
        >>> eol_from_name("MIXED") == MIXED
        True
    """
    try:
        return _eol_from_name[name]
    except KeyError:
        raise ValueError("unknown EOL name: %r" % name)

def name_from_eol(eol):
    r"""name_from_eol(EOL) -> EOL name for this

     Return the EOL shortcut string for the given EOL type:

        >>> name_from_eol("\n")
        'LF'
        >>> name_from_eol("\r\n")
        'CRLF'
        >>> name_from_eol("\r")
        'CR'
    """
    try:
        return _name_from_eol[eol]
    except KeyError:
        raise ValueError("unknown EOL: %r" % eol)


def eol_info_from_text(text):
    r"""eol_info_from_text(TEXT) -> (EOL, SUGGESTED-EOL)

    Return a 2-tuple containing:
    1) The detected end-of-line: one of CR, LF, CRLF, MIXED or None.
    2) The suggested end-of-line to use for this text: one of CR, LF or
       CRLF. This is the typically the most common EOL used in the text,
       preferring the native EOL when ambiguous.

        >>> eol_info_from_text('foo\nbar')
        ('\n', '\n')
        >>> eol_info_from_text('foo\r\nbar')
        ('\r\n', '\r\n')
        >>> eol_info_from_text('foo') == (None, NATIVE)  # no EOLs in text
        True
        >>> eol_info_from_text('\nfoo\nbar\r\n') == (MIXED, '\n')  # mixed text
        True
    """
    if sys.version_info[0] > 2 and type(text) == bytes:
        numCRLFs = text.count(bytes([13, 10]))
        numCRs   = text.count(bytes([13])) - numCRLFs
        numLFs   = text.count(bytes([10])) - numCRLFs
    else:
        numCRLFs = text.count("\r\n")
        numCRs   = text.count("\r") - numCRLFs
        numLFs   = text.count("\n") - numCRLFs

    if numCRLFs == numLFs == numCRs == 0:
        return (None, NATIVE)

    # One a tie, prefer the native EOL.
    eols = [(numCRLFs, CRLF == NATIVE, CRLF),
            (numCRs,   CR   == NATIVE, CR),
            (numLFs,   LF   == NATIVE, LF)]
    eols.sort()

    if eols[0][0] or eols[1][0]:
        return (MIXED, eols[-1][-1])
    else:
        return (eols[-1][-1], eols[-1][-1])

def eol_info_from_stream(stream):
    """eol_info_from_stream(STREAM) -> (EOL, SUGGESTED-EOL)

    Return EOL info for the given file stream.
    See eol_info_from_text() docstring for details.
    """
    return eol_info_from_text(stream.read())

def eol_info_from_path(path):
    """eol_info_from_stream(PATH) -> (EOL, SUGGESTED-EOL)

    Return EOL info for the given file path.
    See eol_info_from_text() docstring for details.
    """
    fin = open(path, "rb")
    try:
        content = fin.read()
    finally:
        fin.close()
    return eol_info_from_text(content)

def eol_info_from_path_patterns(path_patterns, recursive=False,
                                includes=[], excludes=[]):
    """Generate EOL info for the given paths.

    Yields 3-tuples: (PATH, EOL, SUGGESTED-EOL)
    See eol_info_from_text() docstring for details.
    """
    from os.path import islink
    assert not isinstance(path_patterns, _BASESTRING), \
        "'path_patterns' must be a sequence, not a string: %r" % path_patterns
    for path in _paths_from_path_patterns(path_patterns,
                                          recursive=recursive,
                                          includes=includes,
                                          excludes=excludes):
        try:
            fin = open(path, "rb")
        except EnvironmentError:
            _, ex, _ = sys.exc_info()
            if ex.errno in (errno.ENOENT, errno.EISDIR) and islink(path):
                log.debug("skipped `%s': symlink" % path)
                continue
            raise
        try:
            content = fin.read()
        finally:
            fin.close()
        if _BYTES_NULL in content:
            log.debug("skipped `%s': binary file (null in content)" % path)
            continue
        eol, suggested_eol = eol_info_from_text(content)
        yield path, eol, suggested_eol


def convert_text_eol(text, eol):
    r"""convert_text_eol(TEXT, EOL-TYPE) -> converted text

    Convert the given text to the given EOL type.

        >>> s = 'line0\nline1\r\nline2\nline3\nline4\r\nline5'
        >>> convert_text_eol(s, LF)
        'line0\nline1\nline2\nline3\nline4\nline5'
        >>> convert_text_eol(s, CRLF)
        'line0\r\nline1\r\nline2\r\nline3\r\nline4\r\nline5'
    """
    if eol not in (LF, CRLF, CR):
        raise ValueError("illegal EOL: %r" % eol)
    import re
    return re.sub(b'\r\n|\r|\n', bytes(eol, 'utf-8'), text)


def convert_path_eol(path, eol, skip_binary_content=True, log=log):
    """convert_path_eol(PATH, EOL)

    Convert the given file (in-place) to the given EOL. If no
    changes are necessary the file is not touched.
    """
    fin = open(path, "rb")
    try:
        original = fin.read()
    finally:
        fin.close()
    if skip_binary_content and _BYTES_NULL in original:
        log.debug("skipped `%s': binary file (null in content)" % path)
        return
    converted = convert_text_eol(original, eol)
    if original != converted:
        log.info("converted `%s' to %s EOLs", path, name_from_eol(eol))
        fout = open(path, "wb")
        try:
            fout.write(converted)
        finally:
            fout.close()
    else:
        log.debug("skipped `%s': no change required", path)


def convert_path_patterns_eol(path_patterns, eol, recursive=False,
                              excludes=[]):
    """Convert the given paths (in-place) to the given EOL.  If no
    changes are necessary the file is not touched.
    """
    assert not isinstance(path_patterns, _BASESTRING), \
        "'path_patterns' must be a sequence, not a string: %r" % path_patterns
    for path in _paths_from_path_patterns(path_patterns,
                                          recursive=recursive,
                                          excludes=excludes):
        convert_path_eol(path, eol)


def mixed_eol_lines_in_text(text, eol=None):
    r"""mixed_eol_lines_in_text(TEXT[, EOL]) -> LINE-NUMBERS...

        "text" is the text to analyze
        "eol" indicates the expected EOL for each line: one of LF,
            CR or CRLF. It may also be left out (or None) to indicate
            that the most common EOL in the text is the expected one.

    Return a list of line numbers (0-based) with an EOL that does not
    match the expected EOL.

        >>> s = 'line0\nline1\r\nline2\nline3\nline4\r\nline5'
        >>> mixed_eol_lines_in_text(s)
        [1, 4]
        >>> mixed_eol_lines_in_text(s, CRLF)
        [0, 2, 3]
    """
    lines = text.splitlines(1)
    LFs = []; CRs = []; CRLFs = []
    for i in range(len(lines)):
        line = lines[i]
        if line.endswith(CRLF): CRLFs.append(i)
        elif line.endswith(LF): LFs.append(i)
        elif line.endswith(CR): CRs.append(i)

    # Determine the expected EOL.
    if eol is None:
        eol_data = [(len(CRLFs), CRLF == NATIVE, CRLF),
                    (len(CRs),   CR   == NATIVE, CR),
                    (len(LFs),   LF   == NATIVE, LF)]
        eol_data.sort() # last in list is the most common, native EOL on a tie
        eol = eol_data[-1][-1]

    # Get the list of lines with unexpected EOLs.
    if eol == LF:
        mixed_eol_lines = CRs + CRLFs
    elif eol == CR:
        mixed_eol_lines = LFs + CRLFs
    elif eol == CRLF:
        mixed_eol_lines = CRs + LFs
    else:
        raise ValueError("illegal 'eol' value: %r" % eol)
    mixed_eol_lines.sort()
    return mixed_eol_lines



#---- internal support stuff

## {{{ http://code.activestate.com/recipes/577230/ (r4)
def _should_include_path(path, includes, excludes):
    """Return True iff the given path should be included."""
    from os.path import basename
    from fnmatch import fnmatch

    base = basename(path)
    if includes:
        for include in includes:
            if fnmatch(base, include):
                try:
                    log.debug("include `%s' (matches `%s')", path, include)
                except (NameError, AttributeError):
                    pass
                break
        else:
            try:
                log.debug("exclude `%s' (matches no includes)", path)
            except (NameError, AttributeError):
                pass
            return False
    for exclude in excludes:
        if fnmatch(base, exclude):
            try:
                log.debug("exclude `%s' (matches `%s')", path, exclude)
            except (NameError, AttributeError):
                pass
            return False
    return True

def _walk(top, topdown=True, onerror=None, follow_symlinks=False):
    """A version of `os.walk()` with a couple differences regarding symlinks.

    1. follow_symlinks=False (the default): A symlink to a dir is
       returned as a *non*-dir. In `os.walk()`, a symlink to a dir is
       returned in the *dirs* list, but it is not recursed into.
    2. follow_symlinks=True: A symlink to a dir is returned in the
       *dirs* list (as with `os.walk()`) but it *is conditionally*
       recursed into (unlike `os.walk()`).

       A symlinked dir is only recursed into if it is to a deeper dir
       within the same tree. This is my understanding of how `find -L
       DIR` works.
    """
    import os
    from os.path import join, isdir, islink, abspath

    # We may not have read permission for top, in which case we can't
    # get a list of the files the directory contains.  os.path.walk
    # always suppressed the exception then, rather than blow up for a
    # minor reason when (say) a thousand readable directories are still
    # left to visit.  That logic is copied here.
    try:
        names = os.listdir(top)
    except OSError:
        _, err, _ = sys.exc_info()
        if onerror is not None:
            onerror(err)
        return

    dirs, nondirs = [], []
    if follow_symlinks:
        for name in names:
            if isdir(join(top, name)):
                dirs.append(name)
            else:
                nondirs.append(name)
    else:
        for name in names:
            path = join(top, name)
            if islink(path):
                nondirs.append(name)
            elif isdir(path):
                dirs.append(name)
            else:
                nondirs.append(name)

    if topdown:
        yield top, dirs, nondirs
    for name in dirs:
        path = join(top, name)
        if follow_symlinks and islink(path):
            # Only walk this path if it links deeper in the same tree.
            top_abs = abspath(top)
            link_abs = abspath(join(top, os.readlink(path)))
            if not link_abs.startswith(top_abs + os.sep):
                continue
        for x in _walk(path, topdown, onerror, follow_symlinks=follow_symlinks):
            yield x
    if not topdown:
        yield top, dirs, nondirs

_NOT_SPECIFIED = ("NOT", "SPECIFIED")
def _paths_from_path_patterns(path_patterns, files=True, dirs="never",
                              recursive=True, includes=None, excludes=None,
                              skip_dupe_dirs=False,
                              follow_symlinks=False,
                              on_error=_NOT_SPECIFIED):
    """_paths_from_path_patterns([<path-patterns>, ...]) -> file paths

    Generate a list of paths (files and/or dirs) represented by the given path
    patterns.

        "path_patterns" is a list of paths optionally using the '*', '?' and
            '[seq]' glob patterns.
        "files" is boolean (default True) indicating if file paths
            should be yielded
        "dirs" is string indicating under what conditions dirs are
            yielded. It must be one of:
              never             (default) never yield dirs
              always            yield all dirs matching given patterns
              if-not-recursive  only yield dirs for invocations when
                                recursive=False
            See use cases below for more details.
        "recursive" is boolean (default True) indicating if paths should
            be recursively yielded under given dirs.
        "includes" is a list of file patterns to include in recursive
            searches.
        "excludes" is a list of file and dir patterns to exclude.
            (Note: This is slightly different than GNU grep's --exclude
            option which only excludes *files*.  I.e. you cannot exclude
            a ".svn" dir.)
        "skip_dupe_dirs" can be set True to watch for and skip
            descending into a dir that has already been yielded. Note
            that this currently does not dereference symlinks.
        "follow_symlinks" is a boolean indicating whether to follow
            symlinks (default False). To guard against infinite loops
            with circular dir symlinks, only dir symlinks to *deeper*
            dirs are followed.
        "on_error" is an error callback called when a given path pattern
            matches nothing:
                on_error(PATH_PATTERN)
            If not specified, the default is look for a "log" global and
            call:
                log.error("`%s': No such file or directory")
            Specify None to do nothing.

    Typically this is useful for a command-line tool that takes a list
    of paths as arguments. (For Unix-heads: the shell on Windows does
    NOT expand glob chars, that is left to the app.)

    Use case #1: like `grep -r`
      {files=True, dirs='never', recursive=(if '-r' in opts)}
        script FILE     # yield FILE, else call on_error(FILE)
        script DIR      # yield nothing
        script PATH*    # yield all files matching PATH*; if none,
                        # call on_error(PATH*) callback
        script -r DIR   # yield files (not dirs) recursively under DIR
        script -r PATH* # yield files matching PATH* and files recursively
                        # under dirs matching PATH*; if none, call
                        # on_error(PATH*) callback

    Use case #2: like `file -r` (if it had a recursive option)
      {files=True, dirs='if-not-recursive', recursive=(if '-r' in opts)}
        script FILE     # yield FILE, else call on_error(FILE)
        script DIR      # yield DIR, else call on_error(DIR)
        script PATH*    # yield all files and dirs matching PATH*; if none,
                        # call on_error(PATH*) callback
        script -r DIR   # yield files (not dirs) recursively under DIR
        script -r PATH* # yield files matching PATH* and files recursively
                        # under dirs matching PATH*; if none, call
                        # on_error(PATH*) callback

    Use case #3: kind of like `find .`
      {files=True, dirs='always', recursive=(if '-r' in opts)}
        script FILE     # yield FILE, else call on_error(FILE)
        script DIR      # yield DIR, else call on_error(DIR)
        script PATH*    # yield all files and dirs matching PATH*; if none,
                        # call on_error(PATH*) callback
        script -r DIR   # yield files and dirs recursively under DIR
                        # (including DIR)
        script -r PATH* # yield files and dirs matching PATH* and recursively
                        # under dirs; if none, call on_error(PATH*)
                        # callback
    """
    from os.path import basename, exists, isdir, join, normpath, abspath, \
                        lexists, islink, realpath
    from glob import glob

    assert not isinstance(path_patterns, _BASESTRING), \
        "'path_patterns' must be a sequence, not a string: %r" % path_patterns
    if includes is None: includes = []
    if excludes is None: excludes = []
    GLOB_CHARS = '*?['

    if skip_dupe_dirs:
        searched_dirs = set()

    for path_pattern in path_patterns:
        # Determine the set of paths matching this path_pattern.
        for glob_char in GLOB_CHARS:
            if glob_char in path_pattern:
                paths = glob(path_pattern)
                break
        else:
            if follow_symlinks:
                paths = exists(path_pattern) and [path_pattern] or []
            else:
                paths = lexists(path_pattern) and [path_pattern] or []
        if not paths:
            if on_error is None:
                pass
            elif on_error is _NOT_SPECIFIED:
                try:
                    log.error("`%s': No such file or directory", path_pattern)
                except (NameError, AttributeError):
                    pass
            else:
                on_error(path_pattern)

        for path in paths:
            if (follow_symlinks or not islink(path)) and isdir(path):
                if skip_dupe_dirs:
                    canon_path = normpath(abspath(path))
                    if follow_symlinks:
                        canon_path = realpath(canon_path)
                    if canon_path in searched_dirs:
                        continue
                    else:
                        searched_dirs.add(canon_path)

                # 'includes' SHOULD affect whether a dir is yielded.
                if (dirs == "always"
                    or (dirs == "if-not-recursive" and not recursive)
                   ) and _should_include_path(path, includes, excludes):
                    yield path

                # However, if recursive, 'includes' should NOT affect
                # whether a dir is recursed into. Otherwise you could
                # not:
                #   script -r --include="*.py" DIR
                if recursive and _should_include_path(path, [], excludes):
                    for dirpath, dirnames, filenames in _walk(path,
                            follow_symlinks=follow_symlinks):
                        dir_indeces_to_remove = []
                        for i, dirname in enumerate(dirnames):
                            d = join(dirpath, dirname)
                            if skip_dupe_dirs:
                                canon_d = normpath(abspath(d))
                                if follow_symlinks:
                                    canon_d = realpath(canon_d)
                                if canon_d in searched_dirs:
                                    dir_indeces_to_remove.append(i)
                                    continue
                                else:
                                    searched_dirs.add(canon_d)
                            if dirs == "always" \
                               and _should_include_path(d, includes, excludes):
                                yield d
                            if not _should_include_path(d, [], excludes):
                                dir_indeces_to_remove.append(i)
                        for i in reversed(dir_indeces_to_remove):
                            del dirnames[i]
                        if files:
                            for filename in sorted(filenames):
                                f = join(dirpath, filename)
                                if _should_include_path(f, includes, excludes):
                                    yield f

            elif files and _should_include_path(path, includes, excludes):
                yield path
## end of http://code.activestate.com/recipes/577230/ }}}


# Recipe: pretty_logging (0.1.2)
class _PerLevelFormatter(logging.Formatter):
    """Allow multiple format string -- depending on the log level.

    A "fmtFromLevel" optional arg is added to the constructor. It can be
    a dictionary mapping a log record level to a format string. The
    usual "fmt" argument acts as the default.
    """
    def __init__(self, fmt=None, datefmt=None, fmtFromLevel=None):
        logging.Formatter.__init__(self, fmt, datefmt)
        if fmtFromLevel is None:
            self.fmtFromLevel = {}
        else:
            self.fmtFromLevel = fmtFromLevel
    def format(self, record):
        record.lowerlevelname = record.levelname.lower()
        if record.levelno in self.fmtFromLevel:
            #XXX This is a non-threadsafe HACK. Really the base Formatter
            #    class should provide a hook accessor for the _fmt
            #    attribute. *Could* add a lock guard here (overkill?).
            _saved_fmt = self._fmt
            self._fmt = self.fmtFromLevel[record.levelno]
            try:
                return logging.Formatter.format(self, record)
            finally:
                self._fmt = _saved_fmt
        else:
            return logging.Formatter.format(self, record)

def _setup_logging():
    hdlr = logging.StreamHandler(sys.stdout)
    defaultFmt = "%(name)s: %(lowerlevelname)s: %(message)s"
    fmtFromLevel = {logging.DEBUG: "%(name)s: %(message)s",
                    logging.INFO: "%(message)s"}
    fmtr = _PerLevelFormatter(fmt=defaultFmt, fmtFromLevel=fmtFromLevel)
    hdlr.setFormatter(fmtr)
    logging.root.addHandler(hdlr)

class _NoReflowFormatter(optparse.IndentedHelpFormatter):
    """An optparse formatter that does NOT reflow the description."""
    def format_description(self, description):
        return description or ""



#---- mainline

def main(argv=sys.argv):
    _setup_logging()
    log.setLevel(logging.INFO)

    # Parse options.
    parser = optparse.OptionParser(prog="eol", usage='',
        version="%prog " + __version__, description=__doc__,
        formatter=_NoReflowFormatter())
    parser.add_option("-v", "--verbose", dest="log_level",
        action="store_const", const=logging.DEBUG,
        help="more verbose output")
    parser.add_option("-q", "--quiet", dest="log_level",
        action="store_const", const=logging.WARNING,
        help="quieter output (just warnings and errors)")
    parser.set_default("log_level", logging.INFO)
    parser.add_option("--test", action="store_true",
        help="run self-test and exit (use 'eol.py -v --test' for verbose test output)")
    parser.add_option("-c", "--convert", metavar="NAME",
        help='convert file(s) to the given EOL; NAME must be one of "LF", '
            '"CRLF", "CR", "NATIVE" or the "unix", "dos" or "windows" aliases '
            '(case-insensitive)')
    parser.add_option("-f", "--find", metavar="NAME",
        help='find and list file(s) with the given EOL-style; '
            'NAME must be one of "LF", "CRLF", "CR", "NATIVE", '
            '"NONE", "MIXED" or the "unix", "dos", or "windows" aliases '
            '(case-insensitive)')
    parser.add_option("-r", "--recursive", action="store_true",
        help='recursively search directories', default=False)
    parser.add_option("-x", "--skip", action="append", metavar="PATTERN",
        help="patterns to excluding in determining files")
    opts, path_patterns = parser.parse_args()
    log.setLevel(opts.log_level)
    actions = []
    if opts.test: actions.append("test")
    if opts.convert: actions.append("convert")
    if opts.find: actions.append("find")
    if not actions:
        actions = ["list"]
    elif len(actions) > 1:
        log.error("cannot specify more than one of --convert, --test "
            "and --find at once")
        return 1
    action = actions[-1]
    log.debug("action: %r" % action)
    if action == "convert":
        eol = eol_from_name(opts.convert.upper())
        if eol not in (CRLF, LF, CR):
            raise ValueError("illegal EOL name for conversion: %r"
                % opts.convert.upper())
    elif action == "find":
        eol = eol_from_name(opts.find.upper())

    # Perform action.
    if action == "test":
        log.debug("run eol.py self-test...")
        import doctest
        results = doctest.testmod()
        return results.failed
    elif action == "list":
        for path, eol, suggested_eol \
                in eol_info_from_path_patterns(path_patterns, opts.recursive,
                    excludes=opts.skip):
            if eol is MIXED:
                log.info("%s: %s, predominantly %s", path,
                    english_name_from_eol(eol),
                    english_name_from_eol(suggested_eol))
            else:
                log.info("%s: %s", path, english_name_from_eol(eol))
    elif action == "convert":
        for path in _paths_from_path_patterns(path_patterns,
                recursive=opts.recursive, excludes=opts.skip):
            convert_path_eol(path, eol)
    elif action == "find":
        for path, path_eol, suggested_eol in eol_info_from_path_patterns(
                path_patterns, opts.recursive, excludes=opts.skip):
            if path_eol == eol:
                log.info("%s", path)

    return 0

## {{{ http://code.activestate.com/recipes/577258/ (r4)
if __name__ == "__main__":
    try:
        retval = main(sys.argv)
    except KeyboardInterrupt:
        sys.exit(1)
    except SystemExit:
        raise
    except:
        import traceback, logging
        if not log.handlers and not logging.root.handlers:
            logging.basicConfig()
        skip_it = False
        exc_info = sys.exc_info()
        if hasattr(exc_info[0], "__name__"):
            exc_class, exc, tb = exc_info
            if isinstance(exc, IOError) and exc.args[0] == 32:
                # Skip 'IOError: [Errno 32] Broken pipe': often a cancelling of `less`.
                skip_it = True
            if not skip_it:
                tb_path, tb_lineno, tb_func = traceback.extract_tb(tb)[-1][:3]
                log.error("%s (%s:%s in %s)", exc_info[1], tb_path,
                    tb_lineno, tb_func)
        else:  # string exception
            log.error(exc_info[0])
        if not skip_it:
            if log.isEnabledFor(logging.DEBUG):
                print()
                traceback.print_exception(*exc_info)
            sys.exit(1)
    else:
        sys.exit(retval)
## end of http://code.activestate.com/recipes/577258/ }}}
