from pycocotools.coco import COCO
import skimage.io as io
import matplotlib.pyplot as plt
import random
import os

data_directory = "output/"

TRAIN_IMAGES_DIRECTORY = "output/Band1"
TRAIN_ANNOTATIONS_SMALL_PATH = "annotations-small.json"

coco = COCO(TRAIN_ANNOTATIONS_SMALL_PATH)

category_ids = coco.loadCats(coco.getCatIds())
print(category_ids)

image_ids = coco.getImgIds()

for image in image_ids:
	img = coco.loadImgs(image)[0]

	image_path = os.path.join(TRAIN_IMAGES_DIRECTORY, img["filename"])
	I = io.imread(image_path)
	plt.imshow(I)

	annotation_ids = coco.getAnnIds(imgIds=img['id'])
	annotations = coco.loadAnns(annotation_ids)

	# load and render the image
	plt.imshow(I); plt.axis('off')
	# Render annotations on top of the image
	
	for annotation in annotations:
		try:
			coco.showAnns([annotation])
		except IndexError:
			print(annotation)
			continue

	plt.show()