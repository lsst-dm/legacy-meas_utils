#!/usr/bin/env python
"""
Run with:
   python DetectTest.py
"""

import sys, os, math
from math import *

import unittest

import eups
import lsst.utils.tests as utilsTests
import lsst.pex.policy as pexPolicy
from lsst.pex.logging import Trace
import lsst.afw.detection as afwDet
import lsst.afw.image as afwImage
import lsst.meas.utils.sourceDetection as sourceDetection

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

class DetectTestCase(unittest.TestCase):
    """A test case for sourceDetection.py"""

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

    def tearDown(self):
        del self.psfPolicy
        del self.detPolicy
        del self.bckPolicy

    def testDetection(self):
        filename = os.path.join(eups.productDir("afwdata"),
                                "CFHT", "D4", 
                                "cal-53535-i-797722_1")
        bbox = afwImage.BBox(afwImage.PointI(32,32), 512, 512)
        exposure = afwImage.ExposureF(filename, 0,bbox)        
        psf = sourceDetection.makePsf(self.psfPolicy)
       
        bck, bckSubExp = sourceDetection.estimateBackground(
            exposure, self.bckPolicy, True
        )
        dsPositive, dsNegative = sourceDetection.detectSources(
            bckSubExp, psf, self.detPolicy
        )
        assert(not (dsPositive is None and dsNegative is None))

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

