from osgeo import gdal
import os

gdal_path = os.path.dirname(gdal.__file__)
print(gdal_path)
