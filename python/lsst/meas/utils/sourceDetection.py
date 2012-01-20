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

import lsstDebug
from lsst.pex.logging import Log

import lsst.daf.persistence as dafPersist
import lsst.pex.config as pexConf
import lsst.afw.detection as afwDet
import lsst.afw.display.ds9 as ds9
import lsst.afw.geom as afwGeom
import lsst.afw.image as afwImage
import lsst.afw.math as afwMath
import lsst.meas.algorithms as measAlg

class DetectionConfig(pexConf.Config):
    minPixels = pexConf.RangeField(
        doc="detected sources with fewer than the specified number of pixels will be ignored",
        dtype=int, optional=True, default=1, min=0,
    )
    nGrow = pexConf.RangeField(
        doc="How many pixels to to grow detections",
        dtype=int, optional=True, default=1, min=0,
    )
    thresholdValue = pexConf.RangeField(
        doc="value assigned to the threshold object used in detection",
        dtype=float, optional=True, default=5.0, min=0.0,
    )
    thresholdType = pexConf.ChoiceField(
        doc="specifies the desired flavor of Threshold",
        dtype=str, optional=True, default="stdev",
        allowed={
            "variance": "threshold applied to image variance",
            "stdev": "threshold applied to image std deviation",
            "value": "threshold applied to image value"
        }
    )
    thresholdPolarity = pexConf.ChoiceField(
        doc="specifies whether to detect positive, or negative sources, or both",
        dtype=str, optional=True, default="positive",
        allowed={
            "positive": "detect only positive sources",
            "negative": "detect only negative sources",
            "both": "detect both positive and negative sources",
        }
    )

class BackgroundConfig(pexConf.Config):
    statisticsProperty = pexConf.ChoiceField(
        doc="type of statistic to use for grid points",
        dtype=str, default="MEANCLIP",
        allowed={
            "MEANCLIP": "clipped mean",
            "MEAN": "unclipped mean",
            "MEDIAN": "median",
            }
        )
    undersampleStyle = pexConf.ChoiceField(
        doc="behaviour if there are too few points in grid for requested interpolation style",
        dtype=str, default="THROW_EXCEPTION",
        allowed={
            "THROW_EXCEPTION": "throw an exception if there are too few points",
            "REDUCE_INTERP_ORDER": "use an interpolation style with a lower order.",
            "INCREASE_NXNYSAMPLE": "Increase the number of samples used to make the interpolation grid.",
            }
        )
    binSize = pexConf.RangeField(
        doc="how large a region of the sky should be used for each background point",
        dtype=int, default=256, min=10
        )
    algorithm = pexConf.ChoiceField(
        doc="how to interpolate the background values. This maps to an enum; see afw::math::Background",
        dtype=str, default="NATURAL_SPLINE", optional=True,
        allowed={
            "NATURAL_SPLINE" : "cubic spline with zero second derivative at endpoints",
            "AKIMA_SPLINE": "higher-level nonlinear spline that is more robust to outliers",
            "NONE": "No background estimation is to be attempted",
            }
        )

    def validate(self):
        pexConf.Config.validate(self)
        # Allow None to be used as an equivalent for "NONE", even though C++ expects the latter.
        if self.algorithm is None:
            self.algorithm = "NONE"

class MakePsfConfig(pexConf.Config):
    algorithm = pexConf.Field( # this should probably be a registry
        dtype = str,
        doc = "name of the psf algorithm to use",
        default = "DoubleGaussian",
    )
    width = pexConf.Field(
        dtype = int,
        doc = "specify the PSF's width (pixels)",
        default = 5,
        check = lambda x: x > 0,
    )
    height = pexConf.Field(
        dtype = int,
        doc = "specify the PSF's height (pixels)",
        default = 5,
        check = lambda x: x > 0,
    )
    params = pexConf.ListField(
        dtype = float,
        doc = "specify additional parameters as required for the algorithm" ,
        maxLength = 3,
        default = (1.0,),
    )


def makePsf(config):
    """Construct a Psf
    
    @param[in] config: an instance of MakePsfConfig
    
    A thin wrapper around lsst.afw.detection.createPsf
    
    @todo It would be better to use a registry, but this requires rewriting afwDet.createPsf
    """
    params = [
        config.algorithm,
        config.width,
        config.height,
    ]
    params += list(config.params)
        
    return afwDet.createPsf(*params)
makePsf.ConfigClass = MakePsfConfig

def addExposures(exposureList):
    """
    Add a set of exposures together. 
    Assumes that all exposures in set have the same dimensions
    """
    exposure0 = exposureList[0]
    image0 = exposure0.getMaskedImage()

    addedImage = image0.Factory(image0, True)
    addedImage.setXY0(image0.getXY0())

    for exposure in exposureList[1:]:
        image = exposure.getMaskedImage()
        addedImage += image

    addedExposure = exposure0.Factory(addedImage, exposure0.getWcs())
    return addedExposure

def getBackground(image, backgroundConfig):
    """
    Make a new Exposure which is exposure - background
    """
    backgroundConfig.validate();
    nx = image.getWidth() / backgroundConfig.binSize + 1
    ny = image.getHeight() / backgroundConfig.binSize + 1

    sctrl = afwMath.StatisticsControl()
    try:
        sctrl.setAndMask(image.getMask().getPlaneBitMask("DETECTED"))
    except AttributeError:
        pass

    bctrl = afwMath.BackgroundControl(backgroundConfig.algorithm, nx, ny,
                                      backgroundConfig.undersampleStyle, sctrl,
                                      backgroundConfig.statisticsProperty)

    #return a background object
    return afwMath.makeBackground(image, bctrl)
    
def estimateBackground(exposure, backgroundConfig, subtract=True):
    """
    Estimate exposure's background using parameters in backgroundConfig.  
    If subtract is true, make a copy of the exposure and subtract the background.  
    Return background, backgroundSubtractedExposure
    """
    displayEstimateBackground = lsstDebug.Info(__name__).displayEstimateBackground

    maskedImage = exposure.getMaskedImage()

    sctrl = afwMath.StatisticsControl()
    sctrl.setAndMask(maskedImage.getMask().getPlaneBitMask("DETECTED")) # ignore detected pixels

    background = getBackground(maskedImage, backgroundConfig)

    if not background:
        raise RuntimeError, "Unable to estimate background for exposure"
    
    if displayEstimateBackground > 1:
        ds9.mtv(background.getImageF(), title="background", frame=1)

    if not subtract:
        return background, None

    bbox = maskedImage.getBBox(afwImage.PARENT)
    backgroundSubtractedExposure = exposure.Factory(exposure, bbox, afwImage.PARENT, True)
    copyImage = backgroundSubtractedExposure.getMaskedImage().getImage()
    copyImage -= background.getImageF()

    if displayEstimateBackground:
        ds9.mtv(backgroundSubtractedExposure, title="subtracted")

    return background, backgroundSubtractedExposure

def setEdgeBits(maskedImage, goodBBox, edgeBitmask):
    """Set the edgeBitmask bits for all of maskedImage outside goodBBox"""
    msk = maskedImage.getMask()

    mx0, my0 = maskedImage.getXY0()
    for x0, y0, w, h in ([0, 0,
                          msk.getWidth(), goodBBox.getBeginY() - my0],
                         [0, goodBBox.getEndY() - my0, msk.getWidth(),
                          maskedImage.getHeight() - (goodBBox.getEndY() - my0)],
                         [0, 0,
                          goodBBox.getBeginX() - mx0, msk.getHeight()],
                         [goodBBox.getEndX() - mx0, 0,
                          maskedImage.getWidth() - (goodBBox.getEndX() - mx0), msk.getHeight()],
                         ):
        edgeMask = msk.Factory(msk, afwGeom.BoxI(afwGeom.PointI(x0, y0),
                                                 afwGeom.ExtentI(w, h)), afwImage.LOCAL)
        edgeMask |= edgeBitmask

def thresholdImage(image, thresholdValue, thresholdType, thresholdParity, extraThreshold, minPixels):
    """Threshold the convolved image, returning a FootprintSet.
    Helper function for detectSources().

    @param image The (optionally convolved) MaskedImage to threshold
    @param thresholdValue Value for the threshold
    @param thresholdType Type of threshold
    @param thresholdParity Parity of threshold
    @param extraThreshold Threshold multiplier to apply (faint sources discarded, footprints unaffected)
    @param minPixels Minimum number of pixels in footprint
    @return FootprintSet
    """
    parity = False if thresholdParity == "negative" else True
    threshold = afwDet.createThreshold(thresholdValue, thresholdType, parity)
    threshold.setIncludeMultiplier(extraThreshold)
    footprints = afwDet.makeFootprintSet(image, threshold, "DETECTED", minPixels)
    return footprints

def detectSources(exposure, psf, detectionConfig, extraThreshold=1.0):
    try:
        import lsstDebug
        display = lsstDebug.Info(__name__).display
    except ImportError, e:
        try:
            display
        except NameError:
            display = False
    
    if exposure is None:
        raise RuntimeException("No exposure for detection")
       
    #
    # Unpack variables
    #
    maskedImage = exposure.getMaskedImage()
    region = maskedImage.getBBox(afwImage.PARENT)

    mask = maskedImage.getMask()
    mask &= ~(mask.getPlaneBitMask("DETECTED") | mask.getPlaneBitMask("DETECTED_NEGATIVE"))
    del mask

    if psf is None:
        convolvedImage = maskedImage.Factory(maskedImage)
        middle = convolvedImage
    else:
        # We may have a proxy;  if so instantiate it
        if isinstance(psf, dafPersist.readProxy.ReadProxy):
            psf = psf.__subject__

        ##########
        # use a separable psf for convolution ... the psf width for the center of the image will do
        
        xCen = maskedImage.getX0() + maskedImage.getWidth()/2
        yCen = maskedImage.getY0() + maskedImage.getHeight()/2

        # measure the 'sigma' of the psf we were given
        psfAttrib = measAlg.PsfAttributes(psf, xCen, yCen)
        sigma = psfAttrib.computeGaussianWidth()

        # make a SingleGaussian (separable) kernel with the 'sigma'
        gaussFunc = afwMath.GaussianFunction1D(sigma)
        gaussKernel = afwMath.SeparableKernel(psf.getKernel().getWidth(), psf.getKernel().getHeight(),
                                              gaussFunc, gaussFunc)
        
        convolvedImage = maskedImage.Factory(maskedImage.getDimensions())
        convolvedImage.setXY0(maskedImage.getXY0())

        afwMath.convolve(convolvedImage, maskedImage, gaussKernel, afwMath.ConvolutionControl())
        #
        # Only search psf-smooth part of frame
        #
        goodBBox = gaussKernel.shrinkBBox(convolvedImage.getBBox(afwImage.PARENT))
        middle = convolvedImage.Factory(convolvedImage, goodBBox, afwImage.PARENT, False)
        #
        # Mark the parts of the image outside goodBBox as EDGE
        #
        setEdgeBits(maskedImage, goodBBox, maskedImage.getMask().getPlaneBitMask("EDGE"))

    dsPositive, dsNegative = None, None
    if detectionConfig.thresholdPolarity != "negative":
        dsPositive = thresholdImage(middle, detectionConfig.thresholdValue,
                                    detectionConfig.thresholdType,
                                    "positive", extraThreshold, detectionConfig.minPixels)
    if detectionConfig.thresholdPolarity != "positive":
        dsNegative = thresholdImage(middle, detectionConfig.thresholdValue,
                                    detectionConfig.thresholdType,
                                    "negative", extraThreshold, detectionConfig.minPixels)

    for footprints in (dsPositive, dsNegative):
        if footprints is None:
            continue
        footprints.setRegion(region)
        if detectionConfig.nGrow > 0:
            footprints = afwDet.FootprintSetF(footprints, detectionConfig.nGrow, False)
        footprints.setMask(maskedImage.getMask(), "DETECTED")

    if display:
        ds9.mtv(exposure, frame=0, title="detection")

        if convolvedImage and display and display > 1:
            ds9.mtv(convolvedImage, frame=1, title="PSF smoothed")

        if middle and display and display > 1:
            ds9.mtv(middle, frame=2, title="middle")

    return dsPositive, dsNegative
