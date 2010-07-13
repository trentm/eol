
# This is a Makefile for the `mk` tool. (Limited) details for that here:
# <http://svn.openkomodo.com/openkomodo/browse/mk>

import sys
import os
from os.path import join, dirname, normpath, abspath, exists, basename, expanduser
import re
from glob import glob
import codecs
import webbrowser

import mklib
assert mklib.__version_info__ >= (0,7,2)  # for `mklib.mk`
from mklib.common import MkError
from mklib import Task, mk
from mklib import sh


class bugs(Task):
    """open bug/issues page"""
    def make(self):
        webbrowser.open("http://github.com/trentm/eol/issues")

class site(Task):
    """open project page"""
    def make(self):
        webbrowser.open("http://github.com/trentm/eol")

class pypi(Task):
    """open project page"""
    def make(self):
        webbrowser.open("http://pypi.python.org/pypi/eol/")

class cut_a_release(Task):
    """automate the steps for cutting a release

    See 'docs/devguide.md' for details.
    """
    proj_name = "eol"
    version_py_path = "lib/eol.py"
    version_module = "eol"
    _changes_parser = re.compile(r'^## %s (?P<ver>[\d\.abc]+)'
        r'(?P<nyr>\s+\(not yet released\))?'
        r'(?P<body>.*?)(?=^##|\Z)' % proj_name, re.M | re.S)

    def make(self):
        DRY_RUN = False
        version = self._get_version()

        # Confirm
        if not DRY_RUN:
            answer = query_yes_no("* * *\n"
                "Are you sure you want cut a %s release?\n"
                "This will involved commits and a release to pypi." % version,
                default="no")
            if answer != "yes":
                self.log.info("user abort")
                return
            print "* * *"
        self.log.info("cutting a %s release", version)

        # Checks: Ensure there is a section in changes for this version.
        changes_path = join(self.dir, "CHANGES.md")
        changes_txt = changes_txt_before = codecs.open(changes_path, 'r', 'utf-8').read()
        changes_sections = self._changes_parser.findall(changes_txt)
        top_ver = changes_sections[0][0]
        if top_ver != version:
            raise MkError("top section in `CHANGES.md' is for "
                "version %r, expected version %r: aborting"
                % (top_ver, version))
        top_nyr = changes_sections[0][1]
        if not top_nyr:
            answer = query_yes_no("\n* * *\n"
                "The top section in `CHANGES.md' doesn't have the expected\n"
                "'(not yet released)' marker. Has this been released already?",
                default="yes")
            if answer != "no":
                self.log.info("abort")
                return
            print "* * *"
        top_body = changes_sections[0][2]
        if top_body.strip() == "(nothing yet)":
            raise MkError("top section body is `(nothing yet)': it looks like "
                "nothing has been added to this release")

        # Commits to prepare release.
        changes_txt = changes_txt.replace(" (not yet released)", "", 1)
        if not DRY_RUN and changes_txt != changes_txt_before:
            self.log.info("prepare `CHANGES.md' for release")
            f = codecs.open(changes_path, 'w', 'utf-8')
            f.write(changes_txt)
            f.close()
            sh.run('git commit %s -m "prepare for %s release"'
                % (changes_path, version), self.log.debug)

        # Tag version and push.
        curr_tags = set(t for t in _capture_stdout(["git", "tag", "-l"]).split('\n') if t)
        if not DRY_RUN and version not in curr_tags:
            self.log.info("tag the release")
            sh.run('git tag -a "%s" -m "version %s"' % (version, version),
                self.log.debug)
            sh.run('git push --tags', self.log.debug)

        # Release to PyPI.
        self.log.info("release to pypi")
        if not DRY_RUN:
            mk("pypi_upload")

        # Commits to prepare for future dev and push.
        next_version = self._get_next_version(version)
        self.log.info("prepare for future dev (version %s)", next_version)
        marker = "## %s %s\n" % (self.proj_name, version)
        if marker not in changes_txt:
            raise MkError("couldn't find `%s' marker in `%s' "
                "content: can't prep for subsequent dev" % (marker, changes_path))
        changes_txt = changes_txt.replace("## %s %s\n" % (self.proj_name, version),
            "## %s %s (not yet released)\n\n(nothing yet)\n\n## %s %s\n" % (
                self.proj_name, next_version, self.proj_name, version))
        if not DRY_RUN:
            f = codecs.open(changes_path, 'w', 'utf-8')
            f.write(changes_txt)
            f.close()

        ver_path = join(self.dir, normpath(self.version_py_path))
        ver_content = codecs.open(ver_path, 'r', 'utf-8').read()
        version_tuple = self._tuple_from_version(version)
        next_version_tuple = self._tuple_from_version(next_version)
        marker = "__version_info__ = %r" % (version_tuple,)
        if marker not in ver_content:
            raise MkError("couldn't find `%s' version marker in `%s' "
                "content: can't prep for subsequent dev" % (marker, ver_path))
        ver_content = ver_content.replace(marker,
            "__version_info__ = %r" % (next_version_tuple,))
        if not DRY_RUN:
            f = codecs.open(ver_path, 'w', 'utf-8')
            f.write(ver_content)
            f.close()

        if not DRY_RUN:
            sh.run('git commit %s %s -m "prep for future dev"' % (
                changes_path, ver_path))
            sh.run('git push')

    def _tuple_from_version(self, version):
        def _intify(s):
            try:
                return int(s)
            except ValueError:
                return s
        return tuple(_intify(b) for b in version.split('.'))

    def _get_next_version(self, version):
        last_bit = version.rsplit('.', 1)[-1]
        try:
            last_bit = int(last_bit)
        except ValueError: # e.g. "1a2"
            last_bit = int(re.split('[abc]', last_bit, 1)[-1])
        return version[:-len(str(last_bit))] + str(last_bit + 1)

    def _get_version(self):
        lib_dir = join(dirname(abspath(__file__)), "lib")
        sys.path.insert(0, lib_dir)
        try:
            mod = __import__(self.version_module)
            return mod.__version__
        finally:
            del sys.path[0]


class clean(Task):
    """Clean generated files and dirs."""
    def make(self):
        patterns = [
            "dist",
            "build",
            "MANIFEST",
            "*.pyc",
            "lib/*.pyc",
        ]
        for pattern in patterns:
            p = join(self.dir, pattern)
            for path in glob(p):
                sh.rm(path, log=self.log)

class sdist(Task):
    """python setup.py sdist"""
    def make(self):
        sh.run_in_dir("%spython setup.py sdist --formats zip"
                        % _setup_command_prefix(),
                      self.dir, self.log.debug)

class pypi_upload(Task):
    """Upload release to pypi."""
    def make(self):
        sh.run_in_dir("%spython setup.py sdist --formats zip upload"
                % _setup_command_prefix(),
            self.dir, self.log.debug)

        sys.path.insert(0, join(self.dir, "lib"))
        url = "http://pypi.python.org/pypi/eol/"
        import webbrowser
        webbrowser.open_new(url)

class blog_release(Task):
    """Put together a blog post for the latest release."""
    title = "ANN: python-markdown2 %(version)s -- A fast and complete Python implementation of Markdown"
    title ="eol %(version)s -- a script and Python module for working with text file end-of-line (EOL) characters",

    body = r"""
        # Where?

        - Project Page: <http://github.com/trentm/eol>
        - PyPI: <http://pypi.python.org/pypi/eol/>

        # What's new?

        %(whatsnew)s

        Full changelog: <http://github.com/trentm/eol/tree/master/CHANGES.md#files>

        # What is 'eol'?

        `eol` is both a command-line script `eol` and a Python module `eol` for working
        with end-of-line chars in text files.

        ## Command line usage

            # list EOL-style of files
            $ eol *
            configure: Unix (LF)
            build.bat: Windows (CRLF)
            snafu.txt: Mixed, predominantly Unix (LF)

            # find files with a given EOL-style
            $ eol -f CRLF -x .svn -r ~/src/python
            /Users/trentm/src/python/Doc/make.bat
            /Users/trentm/src/python/Lib/email/test/data/msg_26.txt
            /Users/trentm/src/python/Lib/encodings/cp720.py
            ...

            # convert EOL-style of files
            $ eol -c LF foo.c
            converted `foo.c' to LF EOLs

        ## Module usage

            >>> import eol
            >>> eol.eol_info_from_path("configure")
            ('\n', '\n')         # (<detected-eols>, <suggested-eols>)
            >>> eol.eol_info_from_path("build.bat")
            ('\r\n', '\r\n')
            >>> eol.eol_info_from_path("snafu.txt")
            (<class 'eol.MIXED'>, '\n')

        See the [README](http://github.com/trentm/eol#readme) for full usage
        information.

        Cheers,
        Trent

        --
        Trent Mick
        trentm@gmail.com
        http://trentm.com/blog/
    """

    def _parse_changes_txt(self):
        changes_md = open(join(self.dir, "CHANGES.md")).read()
        sections = re.split(r'\n(?=##)', changes_md)
        for section in sections[1:]:
            first, tail = section.split('\n', 1)
            if "not yet released" in first:
                continue
            break

        whatsnew_text = tail.strip()
        version = first.strip().split()[-1]
        if version.startswith("v"):
            version = version[1:]

        return version, whatsnew_text

    def make(self):
        import textwrap
        import getpass
        if getpass.getuser() != "trentm":
            raise RuntimeError("You're not `trentm`. That's not "
                "expected here.")

        version, whatsnew = self._parse_changes_txt()
        data = {
            "whatsnew": whatsnew,
            "version": version,
        }
        body = textwrap.dedent(self.body) % data

        # Ensure all the footer lines end with two spaces: markdown syntax
        # for <br/>.
        lines = body.splitlines(False)
        idx = lines.index("Cheers,") - 1
        for i in range(idx, len(lines)):
            lines[i] += '  '
        body = '\n'.join(lines)

        try:
            import markdown2
        except ImportError:
            sys.path.insert(0, expanduser("~/tm/python-markdown2/lib"))
            import markdown2
            del sys.path[0]
        extras = {
            "demote-headers": 2,
        }
        body_html = markdown2.markdown(body, extras=extras)

        path = "tmp/eol-%s.blog.html" % version
        f = codecs.open(path, 'w', 'utf-8')
        f.write(body_html)
        f.close()
        self.log.info("wrote `%s'", path)


class test(Task):
    """Run all tests (except known failures)."""
    def make(self):
        for ver, python in self._gen_pythons():
            if ver < (2,3):
                # Don't support Python < 2.3.
                continue
            #elif ver >= (3, 0):
            #    # Don't yet support Python 3.
            #    continue
            ver_str = "%s.%s" % ver
            print "-- test with Python %s (%s)" % (ver_str, python)
            assert ' ' not in python
            sh.run_in_dir("%s test.py -- -knownfailure" % python,
                join(self.dir, "test"))

    def _python_ver_from_python(self, python):
        assert ' ' not in python
        o = os.popen('''%s -c "import sys; print(sys.version)"''' % python)
        ver_str = o.read().strip()
        ver_bits = re.split("\.|[^\d]", ver_str, 2)[:2]
        ver = tuple(map(int, ver_bits))
        return ver

    def _gen_python_names(self):
        yield "python"
        for ver in [(2,4), (2,5), (2,6), (2,7), (3,0), (3,1)]:
            yield "python%d.%d" % ver
            if sys.platform == "win32":
                yield "python%d%d" % ver

    def _gen_pythons(self):
        import which  # `pypm|pip install which`
        python_from_ver = {}
        for name in self._gen_python_names():
            for python in which.whichall(name):
                ver = self._python_ver_from_python(python)
                if ver not in python_from_ver:
                    python_from_ver[ver] = python
        for ver, python in sorted(python_from_ver.items()):
            yield ver, python


class todo(Task):
    """Print out todo's and xxx's in the docs area."""
    @property
    def excludes(self):
        yield ".git"
        for line in open(join(self.dir, ".gitignore")):
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                continue
            line = line.strip('/')
            yield line
    def make(self):
        excludes = list(self.excludes)
        for path in _paths_from_path_patterns(['.'], excludes=excludes):
            self._dump_pattern_in_path("TO\DO\\|XX\X", path)

    def _dump_pattern_in_path(self, pattern, path):
        os.system("grep -nH '%s' '%s'" % (pattern, path))



#---- internal support stuff

## {{{ http://code.activestate.com/recipes/577058/ (r2)
def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes" or "no".
    """
    valid = {"yes":"yes",   "y":"yes",  "ye":"yes",
             "no":"no",     "n":"no"}
    if default == None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while 1:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return default
        elif choice in valid.keys():
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "\
                             "(or 'y' or 'n').\n")
## end of http://code.activestate.com/recipes/577058/ }}}


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
    except OSError, err:
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

    assert not isinstance(path_patterns, basestring), \
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


_g_version = None
def _get_version():
    global _g_version
    if _g_version is None:
        sys.path.insert(0, join(dirname(__file__), "lib"))
        try:
            import cmdln
            _g_version = cmdln.__version__
        finally:
            del sys.path[0]
    return _g_version

def _setup_command_prefix():
    prefix = ""
    if sys.platform == "darwin":
        # http://forums.macosxhints.com/archive/index.php/t-43243.html
        # This is an Apple customization to `tar` to avoid creating
        # '._foo' files for extended-attributes for archived files.
        prefix = "COPY_EXTENDED_ATTRIBUTES_DISABLE=1 "
    return prefix

def _capture_stdout(argv):
    import subprocess
    p = subprocess.Popen(argv, stdout=subprocess.PIPE)
    return p.communicate()[0]
