# Development Guide

## How to cut a release

1. Edit "CHANGES.markdown": Remove "(not yet released)" from the header for this
   version and commit.

        vi CHANGES.markdown
        git commit CHANGES.markdown -m "preparing $VERSION release"

2. Tag this release:

        git tag -a v$VERSION -m "version $VERSION"

3. Push changes.

        git push

4. Release an 'sdist' package to pypi.

        mk pypi_upload

5. Prep for subsequent dev. Increment version (`__version__` in
   `lib/eol.py`) and add a section to "CHANGES.markdown" as follows:

        ## eol $NEWVERSION (not yet released)

        (nothing yet)

   and commit and push:

        git commit -a -m "prep for future dev"
        git push
        

