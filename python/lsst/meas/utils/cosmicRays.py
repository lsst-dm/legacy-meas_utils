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
Add CRs to a frame
"""
import os
import pdb                          # we may want to say pdb.set_trace()
import unittest

import lsst.afw.geom as afwGeom
import lsst.afw.image as afwImage
import lsst.afw.math as afwMath

import lsst.afw.display.ds9 as ds9

try:
    type(verbose)
except NameError:
    verbose = 0

def addCosmicRays(image, nCR=100, emin=800, emax=1000, seed=None):
    """Add nCR fake cosmic rays to a frame, with pixel values between emin and emax (and some extra associated fainter pixels too)"""
    #
    if seed is None:
        seed = int(afwMath.makeStatistics(image, afwMath.MAX).getValue())
    if seed == 0:
        seed = 1

    width = image.getWidth()
    height = image.getHeight()
    
    rand = afwMath.Random(afwMath.Random.RANLUX, seed)

    for i in range(nCR):
        #
        # Initial point in CR
        #
        x = rand.uniformInt(width)
        y = rand.uniformInt(height)
        amp = emin + rand.uniformInt(emax - emin)
        #
        # Extra contamination at about the initial amplitude
        #
        badPixels = []
        while True:
            badPixels.append([x, y, amp + 0.1*(emax - emin)*rand.uniform()])
            
            if rand.uniform() > 0.5:
                break

            x += rand.uniformInt(3) - 1
            y += rand.uniformInt(3) - 1
        #
        # Add a little extra CR flux to the pixels surrounding badPixels
        #
        for x, y, amp in badPixels:
            while rand.uniform() < 0.5:
                image.set(x, y, amp*rand.uniform())
                
                x += rand.uniformInt(3) - 1
                y += rand.uniformInt(3) - 1
        #
        # And set the initial badPixels themselves
        #
        for x, y, amp in badPixels:
            if x >= 0 and x < width and y >= 0 and y < height:
                image.set(x, y, amp)

def run(exit=False):
    """Run the tests"""
    if False:
        import eups
        dataDir = eups.productDir("afwdata")
        if not dataDir:
            raise RuntimeError("Must set up afwdata to run me")

        im = afwImage.ImageF(os.path.join(dataDir, "871034p_1_img.fits"))
    else:
        im = afwImage.ImageF(afwGeom.Extent2I(256, 256))

    addCosmicRays(im, nCR=100, emin=800, emax=1000)
    
    ds9.mtv(im)
    
if __name__ == "__main__":
    run(True)
