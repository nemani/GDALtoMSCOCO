# Author: Arjun Nemani (nemaniarjun@gmail.com)
# This script takes a GeoTIFF file and Polygon Shapefile
# Returns 300x300 sized PNGs with all bands seperated 
# and Polygon Annotations in MSCOCO format.

# Imports
import os
from os import path
import sys
import json
import numpy as np
from osgeo import gdal, ogr

# For Progress Bar
from tqdm import tqdm, trange

gdal.UseExceptions()

def GetBboxFromPolygon(polygon, gt):
	ulx, uly, lrx, lry = polygon.GetEnvelope()
	ulx, uly = convertMapCoords2PixelOffset(ulx, uly, gt)
	lrx, lry = convertMapCoords2PixelOffset(lrx, lry, gt)
	return [ulx, uly, lrx, lry]

def GetSegmentationFromPolygon(polygon, gt, offset):
	polygon_json = json.loads(polygon.ExportToJson())

	coords = []
	for coord_list in polygon_json['coordinates']:
		for coord in coord_list:
			if polygon_json['type'] == "MultiPolygon":
				coords.extend(coord)
			else:
				coords.append(coord)

	segmentation = []
	for coord in coords:
		segmentation.extend(convertMapCoords2PixelOffset(*coord, gt, offset))

	return [segmentation]

def convertPixelOffset2MapCoords(x, y, gt):
	# Takes gdalTransformMatrix and a pixel offset -> converts it to map coordinates 
	xOrigin = gt[0]
	yOrigin = gt[3]
	pixelWidth = gt[1]
	pixelHeight = gt[5]

	X = xOrigin + x * pixelWidth  
	Y = yOrigin + y * pixelHeight
	return X, Y


def convertMapCoords2PixelOffset(x, y, gt, offset=(0,0)):
	# Takes gdalTransformMatrix and a map coordinates -> converts it to pixel offset  
	xOrigin = gt[0]
	yOrigin = gt[3]
	pixelWidth = gt[1]
	pixelHeight = gt[5]

	col = ((x - xOrigin) / pixelWidth) - offset[0]
	row = ((y - yOrigin) / pixelHeight) - offset[1]
	return col, row


def GeneratePolyForWindow(Window, gt):
	a, b, c, d = Window

	# Create a new Polygon
	PolyTile = ogr.Geometry(ogr.wkbPolygon)

	# Create a new ring geometry for the polygon
	ring = ogr.Geometry(ogr.wkbLinearRing)

	'''
	Ring with following points
	(a,b)-----(a+c,b)
	|           |
	(a,b+d)---(a+c,b+d)
	'''
	points = [(a,b), (a+c, b), (a+c, b+d), (a, b+d), (a,b)]

	for point in points:
		ring.AddPoint_2D(*convertPixelOffset2MapCoords(*point, gt))	

	PolyTile.AddGeometry(ring)
	return PolyTile


if __name__ == '__main__':

	# Config Params
	tiff_input_path  = path.abspath("data/S1B_IW_GRDH_1SDV_20180507T151605_20180507T151630_010817_013C63_C906_TC.tif")
	filename = path.basename(tiff_input_path)
	shp_filename = path.abspath("data/Somalia1_20180507_ST1.shp")
	output_dir_path = path.abspath("output")
	train_percent = 0.8 # 80%

	# Set to array of bands to process
	# If empty then all bands are processed
	bands = []

	# Output size of PNGs
	output_size  = (300, 300)

	# Create Output DIR
	if not path.isdir(output_dir_path):
		os.makedirs(output_dir_path, exist_ok=True)

	# Open the GeoTiff using GDAL
	tiff = gdal.Open(tiff_input_path, gdal.GA_ReadOnly)
	
	# Get the Transform matrix
	gt = tiff.GetGeoTransform()

	# Size of the TIFF
	input_size  = (tiff.RasterXSize, tiff.RasterYSize)

	# Open the Polygon Shapefile using OGR
	shapefile = ogr.Open(shp_filename)

	# Get Layers from Shapefile
	lyrCount = shapefile.GetLayerCount()
	lyrs = [shapefile.GetLayer(i) for i in range(lyrCount)]

	if not bands:
		# NOTE: Band Index starts from 1
		bands = range(1, tiff.RasterCount+1)

	# Create a new dict for MSCOCO format
	MSCOCO_Dict_train = dict()
	MSCOCO_Dict_test = dict()

	# Add Info Data
	MSCOCO_Dict_test['info'] = {
						'about': 'Test Dataset for GeoTIFF and Polygon Annotations',
						'contributor': '',
						'date_created': '',
						'description': '',
						'url': '',
						'version': '',
						'year': 2018
						}

	MSCOCO_Dict_train['info'] = {
						'about': 'Train Dataset for GeoTIFF and Polygon Annotations',
						'contributor': '',
						'date_created': '',
						'description': '',
						'url': '',
						'version': '',
						'year': 2018
						}

	# Add Categories Data
	MSCOCO_Dict_test['categories'] = [{'id': 100, 'name': 'Object of Interest', 'supercategory': 'Object of Interest'}]
	MSCOCO_Dict_train['categories'] = [{'id': 100, 'name': 'Object of Interest', 'supercategory': 'Object of Interest'}]

	# Create List for Images
	MSCOCO_Dict_test['images'] = []
	MSCOCO_Dict_train['images'] = []

	# Create List for Annotations
	MSCOCO_Dict_test['annotations'] = []
	MSCOCO_Dict_train['annotations'] = []
	
	# Calculate number of loops
	loops = tuple(map(int, map(np.ceil, (input_size[0] / output_size[0], input_size[1] / output_size[1]))))
		
	# trange === range + progressbar
	for i in trange(loops[0], desc="X Offset"):
		for j in trange(loops[1], desc="Y Offset"):

			if np.random.random() > train_percent:
				test_or_train = "Test"
			else:
				test_or_train = "Train"

			# Create Image dict
			img_dict = dict({})

			# Calculate Photo ID
			if test_or_train == "Test":
				img_dict['id'] = len(MSCOCO_Dict_test['images']) + 1
			else:
				img_dict['id'] = len(MSCOCO_Dict_train['images']) + 1

			# filename_band = name of that bands file
			img_dict['filename'] = "{}.jpg".format(img_dict['id'])

			#  X -> Width, Y -> Height
			img_dict['width'], img_dict['height'] = output_size

			# Append it to MSCOCO
			if test_or_train == "Test":
				MSCOCO_Dict_test['images'].append(img_dict)
			else:
				MSCOCO_Dict_train['images'].append(img_dict)


			# Calculate Current Offset
			offset = (i * output_size[0], j * output_size[1])
			
			# Calculate Window from offset and output size
			Window = [offset[0], offset[1], output_size[0], output_size[1]]
			
			# Generates a polygon for this Tile
			PolyTile = GeneratePolyForWindow(Window, gt) 

			for lyr in lyrs:
				for feature in lyr:
					geometry = feature.GetGeometryRef()

					if PolyTile.Intersects(geometry):
						intersection = PolyTile.Intersection(geometry)
						
						# Create Annotations Object
						annotations_dict = {}

						if test_or_train == "Test":
							annotations_dict['id'] = len(MSCOCO_Dict_test['annotations']) + 1
						else:
							annotations_dict['id'] = len(MSCOCO_Dict_train['annotations']) + 1

						annotations_dict['image_id'] = img_dict['id']
						annotations_dict['category_id'] = 100
						annotations_dict['area'] = float(intersection.GetArea())
						annotations_dict['iscrowd'] = 0
						annotations_dict['bbox'] = GetBboxFromPolygon(intersection, gt)
						annotations_dict['segmentation'] = GetSegmentationFromPolygon(intersection, gt, offset)
						
						# Append it to MSCOCO
						if test_or_train == "Test":
							MSCOCO_Dict_test['annotations'].append(annotations_dict)
						else:
							MSCOCO_Dict_train['annotations'].append(annotations_dict)

				# Layer gets exhausted on reading. Need to reset it
				lyr.ResetReading()


			for band in bands:
				dir_path = "{}/{}/Band{}".format(output_dir_path, test_or_train, band)

				if not path.isdir(dir_path):
					os.makedirs(dir_path, exist_ok=True)

				# Calculate Filename
				filename = '{}/{}'.format(dir_path, img_dict['filename'])

				# Get gdalTranslateOptions Object
				options = gdal.TranslateOptions(format='JPEG', scaleParams=[[]], bandList=[band], srcWin=Window, outputType=1)

				# Do the actual Translate
				output = gdal.Translate(filename, tiff, options=options)

				# Close the output 
				output = None


	tiff = None

	# Dump the dict to a JSON file
	json.dump(MSCOCO_Dict_test, open("{}/annotations-test.json".format(output_dir_path), 'w'))
	json.dump(MSCOCO_Dict_train, open("{}/annotations-train.json".format(output_dir_path), 'w'))
