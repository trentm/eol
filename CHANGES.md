# eol Changelog

## eol 0.7.6 (not yet released)

- ensure test/*.doctests are in the sdist

## eol 0.7.5

- [Issue #3] Add "dos", "windows" and "unix" aliases for specifying an eol
  style. E.g. can now do `eol -c dos foo.bat` to convert to DOS-style EOLs.
- [Issue #4] Fix a few Python 3 compat issues, add some more test cases.

## eol 0.7.4

- Python 3 support (not heavily tested yet)
- Starter test suite

## eol 0.7.3

- Switch to `optparse` for option processing. Benefit is that you can have
  options after the "FILE" argument(s).

## eol 0.7.2

- Fix error with `eol -h` (jeesh).

## eol 0.7.1

- Add a 'mk cut_a_release' task to help with releases.
- Fix issue #1: spelling of "predominantly". Thanks [userd on
  reddit](http://www.reddit.com/r/Python/comments/c61nu/eolpy_a_tool_for_working_with_text_file_endofline/)!

## eol 0.7.0

- Fix `main` for setuptools/distribute entry points.
- Fix handling of dir symlinks for `eol -f ...`.
- Pull out into separate project at <http://github.com/trentm/eol>.

## eol 0.6.0

(Started maintaining this log 6 May 2010. This was the state of eol.py
in my personal "sandbox/tools" area before pulling out to this project.)
