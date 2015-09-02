# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Test cases covering L{twisted.python.zippath}.
"""

from __future__ import absolute_import, division, print_function

import os
import zipfile

from twisted.test.test_paths import AbstractFilePathTests
from twisted.python.zippath import ZipArchive
from twisted.python.filepath import FilePath


def zipit(dirname, zfname):
    """
    Create a zipfile on zfname, containing the contents of dirname'
    """
    dirname = FilePath(dirname)._getPathAsSameTypeAs('')
    zfname = FilePath(zfname)._getPathAsSameTypeAs('')

    zf = zipfile.ZipFile(zfname, "w")

    for root, ignored, files, in os.walk(dirname):
        for fname in files:
            fspath = os.path.join(root, fname)
            arcpath = os.path.join(root, fname)[len(dirname)+1:]
            zf.write(fspath, arcpath)
    zf.close()



class ZipFilePathTests(AbstractFilePathTests):
    """
    Test various L{ZipPath} path manipulations as well as reprs for L{ZipPath}
    and L{ZipArchive}.
    """
    def setUp(self):
        AbstractFilePathTests.setUp(self)
        zipit(self.cmn, self.cmn + b'.zip')
        self.path = ZipArchive(self.cmn + b'.zip')
        self.root = self.path
        self.all = [x.replace(self.cmn, self.cmn + b'.zip') for x in self.all]
        self.nativecmn = FilePath(self.cmn)._getPathAsSameTypeAs('')


    def test_zipPathRepr(self):
        """
        Make sure that invoking ZipPath's repr prints the correct class name
        and an absolute path to the zip file.
        """
        child = self.path.child("foo")
        pathRepr = "ZipPath(%r)" % (
            os.path.abspath(self.nativecmn + ".zip" + os.sep + 'foo'),)

        # Check for an absolute path
        self.assertEqual(repr(child), pathRepr)

        # Create a path to the file rooted in the current working directory
        relativeCommon = self.nativecmn.replace(os.getcwd() + os.sep, "", 1) + ".zip"
        relpath = ZipArchive(relativeCommon)
        child = relpath.child("foo")

        # Check using a path without the cwd prepended
        self.assertEqual(repr(child), pathRepr)


    def test_zipPathReprParentDirSegment(self):
        """
        The repr of a ZipPath with C{".."} in the internal part of its path
        includes the C{".."} rather than applying the usual parent directory
        meaning.
        """
        child = self.path.child("foo").child("..").child("bar")
        pathRepr = "ZipPath(%r)" % (
            self.nativecmn + ".zip" + os.sep.join(["", "foo", "..", "bar"]))
        self.assertEqual(repr(child), pathRepr)


    def test_zipPathReprEscaping(self):
        """
        Bytes in the ZipPath path which have special meaning in Python
        string literals are escaped in the ZipPath repr.
        """
        child = self.path.child("'")
        path = self.nativecmn + ".zip" + os.sep.join(["", "'"])
        pathRepr = "ZipPath('%s')" % (path,)
        self.assertEqual(repr(child), pathRepr)


    def test_zipArchiveRepr(self):
        """
        Make sure that invoking ZipArchive's repr prints the correct class
        name and an absolute path to the zip file.
        """
        pathRepr = 'ZipArchive(%r)' % (os.path.abspath(self.nativecmn + '.zip'),)

        # Check for an absolute path
        self.assertEqual(repr(self.path), pathRepr)

        # Create a path to the file rooted in the current working directory
        relativeCommon = self.nativecmn.replace(os.getcwd() + os.sep, "", 1) + ".zip"
        relpath = ZipArchive(relativeCommon)

        # Check using a path without the cwd prepended
        self.assertEqual(repr(relpath), pathRepr)
