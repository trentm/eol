#!/usr/bin/env python
# Copyright (c) 2010 ActiveState Software Inc.
# License: MIT (http://www.opensource.org/licenses/mit-license.php)

import os
import sys
from pprint import pprint
import unittest
import doctest

from testlib import TestError, TestSkipped, tag


class DocTestsTestCase(unittest.TestCase):
    def test_api(self):
        if sys.version_info[:2] < (2,4):
            raise TestSkipped("no DocFileTest in Python <=2.3")
        test = doctest.DocFileTest("api.doctests")
        test.runTest()

    if sys.version_info[0] == 2:
        def test_api2(self):
            """API tests for Python 2 syntax"""
            if sys.version_info[:2] < (2,4):
                raise TestSkipped("no DocFileTest in Python <=2.3")
            test = doctest.DocFileTest("api2.doctests")
            test.runTest()
    
    if sys.version_info[0] > 2:
        def test_api3(self):
            """API tests for Python 3 syntax"""
            test = doctest.DocFileTest("api3.doctests")
            test.runTest()

    def test_internal(self):
        import eol
        doctest.testmod(eol)

