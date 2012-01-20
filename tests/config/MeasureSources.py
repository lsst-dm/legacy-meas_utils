import lsst.meas.algorithms as measAlg

root = measAlg.MeasureSourcesConfig()
root.source.astrom = "SDSS"
root.source.apFlux = "NAIVE"
root.source.psfFlux = "PSF"
root.source.shape = "SDSS"
root.source.modelFlux = None
root.source.instFlux = None
root.astrometry.names = ["GAUSSIAN", "SDSS"]
root.shape.names = ["SDSS"]
root.photometry.names = ["NAIVE", "PSF", "SINC"]
root.photometry["NAIVE"].radius = 3.0
root.photometry["SINC"].radius = 3.0
