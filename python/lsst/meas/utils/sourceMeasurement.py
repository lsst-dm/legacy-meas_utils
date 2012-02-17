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

import math
import lsst.pex.policy        as pexPolicy
import lsst.pex.logging       as pexLog
import lsst.pex.policy        as policy
import lsst.meas.algorithms   as measAlg
import lsst.afw.detection     as afwDetection
import lsst.afw.geom          as afwGeom
import lsst.afw.coord         as afwCoord
import lsst.afw.display.ds9   as ds9


def computeSkyCoords(wcs, sourceSet):
    log = pexLog.Log(pexLog.getDefaultLog(), 'lsst.meas.utils.sourceMeasurement.computeSkyCoords')
    if sourceSet is None:
        log.log(Log.WARN, "No SourceSet provided" )
        return
    if wcs is None:
        log.log(Log.WARN, "No WCS provided")

    for s in sourceSet:
        (radec, raErr, decErr) = xyToRaDec(
            s.getXFlux(), 
            s.getYFlux(),
            s.getXFluxErr(), 
            s.getYFluxErr(), 
            wcs)
        s.setRaDecFlux(radec)
        s.setRaFluxErr(raErr)
        s.setDecFluxErr(decErr)

        (radec, raErr, decErr) = xyToRaDec(
            s.getXAstrom(), 
            s.getYAstrom(),
            s.getXAstromErr(), 
            s.getYAstromErr(), 
            wcs)
        s.setRaDecAstrom(radec)
        s.setRaAstromErr(raErr)
        s.setDecAstromErr(decErr)

        # No errors for XPeak, YPeak
        s.setRaDecPeak(wcs.pixelToSky(s.getXPeak(), s.getYPeak()))

        # Simple RA/decl == Astrom versions
        s.setRa(s.getRaAstrom())
        s.setRaErrForDetection(s.getRaAstromErr())
        s.setDec(s.getDecAstrom())
        s.setDecErrForDetection(s.getDecAstromErr())

def xyToRaDec(x,y, xErr, yErr, wcs, pixToSkyAffineTransform=None):
        """Use wcs to transform pixel coordinates x, y and their errors to 
        sky coordinates ra, dec with errors. If the caller does not provide an
        affine approximation to the pixel->sky WCS transform, an approximation
        is automatically computed (and used to propagate errors). For sources
        from exposures far from the poles, a single approximation can be reused
        without introducing much error.

        Note that the affine transform is expected to take inputs in units of
        pixels to outputs in units of degrees. This is an artifact of WCSLIB
        using degrees as its internal angular unit.

        """
        sky = wcs.pixelToSky(x, y)
        if pixToSkyAffineTransform is None:
            pixToSkyAffineTransform = wcs.linearizePixelToSky(sky)
        
        t = pixToSkyAffineTransform
        varRa  = t[0]**2 * xErr**2 + t[2]**2 * yErr**2
        varDec = t[1]**2 * xErr**2 + t[3]**2 * yErr**2
        raErr =  math.sqrt(varRa ) * afwGeom.degrees
        decErr = math.sqrt(varDec) * afwGeom.degrees

        return (sky, raErr, decErr)
                
