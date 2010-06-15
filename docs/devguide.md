# Development Guide

## How to cut a release

Either run `mk cut_a_release` or manually do the following:

1. Edit "CHANGES.md": Remove "(not yet released)" from the header for this
   version and commit.

        vi CHANGES.md
        git commit CHANGES.md -m "preparing $VERSION release"

2. Tag this release:

        git tag -a $VERSION -m "version $VERSION"

3. Push changes.

        git push --tags

4. Release an 'sdist' package to pypi.

        mk pypi_upload

5. Prep for subsequent dev. Increment version (`__version__` in
   `lib/eol.py`) and add a section to "CHANGES.md" as follows:

        ## eol $NEWVERSION (not yet released)

        (nothing yet)

   and commit and push:

        git commit -a -m "prep for future dev"
        git push
        

