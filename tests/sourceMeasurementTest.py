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

"""
Run with:
   python MeasureTest.py
"""

import sys, os, math
from math import *

import pdb
import unittest
import random
import time

import eups
import lsst.utils.tests as utilsTests
import lsst.pex.policy as pexPolicy
import lsst.meas.utils.sourceDetection as sourceDetection
import lsst.meas.utils.sourceMeasurement as sourceMeasurement
import lsst.afw.image as afwImage

import lsst.afw.display.ds9 as ds9

try:
    type(display)
except NameError:
    display = False

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

class SourceMeasurementTestCase(unittest.TestCase):
    """A test case for SourceMeasurementStage.py"""

    def setUp(self):

        self.psfPolicy = pexPolicy.Policy.createPolicy(
            pexPolicy.DefaultPolicyFile("meas_utils", "PsfDictionary.paf", "policy")
        )
        self.detPolicy = pexPolicy.Policy.createPolicy(
            pexPolicy.DefaultPolicyFile("meas_utils", "DetectionDictionary.paf", "policy")
        )
        self.bckPolicy = pexPolicy.Policy.createPolicy(
            pexPolicy.DefaultPolicyFile("meas_utils", "BackgroundDictionary.paf", "policy")
        )
        self.moPolicy = pexPolicy.Policy.createPolicy(
            pexPolicy.DefaultPolicyFile(
                "meas_utils", "MeasureSourcesDictionary.paf", "policy"
            )
        )

    def tearDown(self):
        del self.psfPolicy
        del self.bckPolicy
        del self.detPolicy
        del self.moPolicy

    def testSingleInputExposure(self):
        filename = os.path.join(
            eups.productDir("afwdata"), "CFHT", "D4", "cal-53535-i-797722_1"
        )
        bbox = afwImage.BBox(afwImage.PointI(32,32), 512, 512)
        exposure =  afwImage.ExposureF(filename, 0, bbox)
        psf = sourceDetection.makePsf(self.psfPolicy)
       
        bck, bckSubExp = sourceDetection.estimateBackground(
            exposure, self.bckPolicy, True
        )
        dsPositive, dsNegative = sourceDetection.detectSources(
            bckSubExp, psf, self.detPolicy
        )
        fpList = []
        if dsPositive:
            fpList.append([dsPositive.getFootprints(), True])
        if dsNegative:
            fpList.append([dsNegative.getFootprints(), False])
        
        sourceMeasurement.sourceMeasurement(bckSubExp, psf, fpList, self.moPolicy)
        del exposure
        del bckSubExp
        del psf
       
def suite():
    """Returns a suite containing all the test cases in this module."""

    utilsTests.init()

    suites = []

    if not eups.productDir("afwdata"):
        print >> sys.stderr, "afwdata is not setting up; skipping test"
    else:
        suites += unittest.makeSuite(SourceMeasurementTestCase)
    suites += unittest.makeSuite(utilsTests.MemoryTestCase)
    return unittest.TestSuite(suites)

def run(exit=False):
    """Run the tests"""
    utilsTests.run(suite(), exit)

if __name__ == "__main__":
    run(True)
