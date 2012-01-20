#!/usr/bin/env python
# 
# LSST Data Management System
# Copyright 2008, 2009, 2010 LSST Corporation.
# 
# This product includes software developed by the
# LSST Project (http://www.lsst.org/).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the LSST License Statement and 
# the GNU General Public License along with this program.  If not, 
# see <http://www.lsstcorp.org/LegalNotices/>.
#
import sys
import os
import unittest

import eups
import lsst.utils.tests as utilsTests
import lsst.afw.detection as afwDet
import lsst.afw.geom as afwGeom
import lsst.afw.image as afwImage
import lsst.meas.utils.sourceDetection as sourceDetection

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

class DetectTestCase(unittest.TestCase):
    """A test case for sourceDetection.py"""

    def setUp(self):
        self.psfConfig = sourceDetection.makePsf.ConfigClass()
        self.detConfig = sourceDetection.detectSources.ConfigClass()
        self.bckConfig = sourceDetection.estimateBackground.ConfigClass()

    def tearDown(self):
        del self.psfConfig
        del self.detConfig
        del self.bckConfig

    def testDetection(self):
        filename = os.path.join(eups.productDir("afwdata"),
                                "CFHT", "D4", 
                                "cal-53535-i-797722_1")
        bbox = afwGeom.Box2I(afwGeom.Point2I(32, 32), afwGeom.Extent2I(512, 512))
        exposure = afwImage.ExposureF(filename, 0, bbox, afwImage.LOCAL)        
        psf = sourceDetection.makePsf(self.psfConfig)
       
        bck, bckSubExp = sourceDetection.estimateBackground(
            exposure, self.bckConfig, True
        )
        dsPositive, dsNegative = sourceDetection.detectSources(
            bckSubExp, psf, self.detConfig
        )
        self.assertFalse(dsPositive is None and dsNegative is None)

def suite():
    """Returns a suite containing all the test cases in this module."""

    utilsTests.init()

    suites = []

    if not eups.productDir("afwdata"):
        print >> sys.stderr, "afwdata is not setting up; skipping test"
    else:        
        suites += unittest.makeSuite(DetectTestCase)

    suites += unittest.makeSuite(utilsTests.MemoryTestCase)
    return unittest.TestSuite(suites)

def run(exit=False):
    """Run the tests"""
    utilsTests.run(suite(), exit)

if __name__ == "__main__":
    run(True)

