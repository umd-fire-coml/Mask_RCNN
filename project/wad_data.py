import math
import matplotlib.pyplot as plt
import numpy as np
import os
import pickle
import re
import skimage.io

from mrcnn import config, utils
from os.path import join, isfile
from time import time

from sklearn.model_selection import train_test_split
import copy


###############################################################################
#                              CLASS DICTIONARIES                             #
###############################################################################

classes = {
    33: 'car',
    34: 'motorcycle',
    35: 'bicycle',
    36: 'person',
    37: 'rider',
    38: 'truck',
    39: 'bus',
    40: 'tricycle',
    0: 'others',
    1: 'rover',
    17: 'sky',
    161: 'car_groups',
    162: 'motorcycle_group',
    163: 'bicycle_group',
    164: 'person_group',
    165: 'rider_group',
    166: 'truck_group',
    167: 'bus_group',
    168: 'tricycle_group',
    49: 'road',
    50: 'sidewalk',
    65: 'traffic_cone',
    66: 'road_pile',
    67: 'fence',
    81: 'traffic_light',
    82: 'pole',
    83: 'traffic_sign',
    84: 'wall',
    85: 'dustbin',
    86: 'billboard',
    97: 'building',
    98: 'bridge',
    99: 'tunnel',
    100: 'overpass',
    113: 'vegetation'
}

classes_to_index = dict([(e, i + 1) for i, e in enumerate(classes.keys())])
index_to_classes = {v: k for k, v in classes_to_index.items()}

###############################################################################
#                                CONFIGURATION                                #
###############################################################################


class WADConfig(config.Config):
    NAME = 'WAD'

    NUM_CLASSES = len(classes) + 1

###############################################################################
#                                   DATASET                                   #
###############################################################################


class WADDataset(utils.Dataset):
    image_height = 2710
    image_width = 3384

    def __init__(self, random_state=42):
        super(self.__class__, self).__init__(self)

        # Add classes (35)
        for class_id, class_name in classes.items():
            self.add_class('WAD', classes_to_index[class_id], class_name)

        self.random_state = random_state

    def _load_video(self, video_list_filename, img_dir, mask_dir=None, assume_match=False):
        """Loads all the images from a particular video list into the dataset.
        video_list_filename: path of the file containing the list of images
        img_dir: directory of the images
        mask_dir: directory of the mask images, if available
        assume_match: Whether to assume all images have ground-truth masks (ignored if mask_dir
        is None)
        """

        # Get list of images for this video
        video_file = open(video_list_filename, 'r')
        image_filenames = video_file.readlines()
        video_file.close()

        if image_filenames is None:
            print('No video list found at {}.'.format(video_list_filename))
            return

        # Generate images and masks
        for img_mask_paths in image_filenames:
            # Set paths and img_id
            if mask_dir is not None:
                matches = re.search('^.*\\\\(.*\\.jpg).*\\\\(.*\\.png)', img_mask_paths)
                img_file, mask_file = matches.group(1, 2)
                img_id = img_file[:-4]
            else:
                matches = re.search('^([0-9a-zA-z]+)', img_mask_paths)
                img_id = matches.group(1)
                img_file = img_id + '.jpg'

            # Paths
            img_path = join(img_dir, img_file)
            mask_path = join(mask_dir, mask_file) if mask_dir is not None else None

            # Check if files exist
            if not assume_match:
                if not isfile(img_path):
                    continue
                elif not isfile(mask_path):
                    mask_path = None

            # Add the image to the dataset
            self.add_image("WAD", image_id=img_id, path=img_path, mask_path=mask_path)

    def _load_all_images(self, img_dir, mask_dir=None, assume_match=False, val_size=0):
        """Load all images from the img_dir directory, with corresponding masks
        if doing training.
        img_dir: directory of the images
        mask_dir: directory of the corresponding masks, if available
        assume_match: Whether to assume all images have ground-truth masks (ignored if mask_dir
        is None)
        val_size: only applicable if we are labeled data
        """

        # Retrieve list of all images in directory
        for _, _, images in os.walk(img_dir):
            break
        
        if val_size != 0:
          imgs_train, imgs_val = train_test_split(images, test_size=val_size, random_state=self.random_state)
          #print(imgs_train)
          #print(imgs_val)

          val_part = WADDataset()

          # Iterate through images and add to dataset
          for img_filename in imgs_train:
              img_id = img_filename[:-4]
              img_path = join(img_dir, img_filename)

              # If using masks, only add images to dataset that also have a mask
              if mask_dir is not None:
                  mask_path = join(mask_dir, img_id + '_instanceIds.png')

                  # Ignores the image (doesn't add) if no mask exists
                  if not assume_match and not isfile(mask_path):
                      continue
              else:
                  mask_path = None

              # Adds the image to the dataset
              self.add_image('WAD', img_id, img_path, mask_path=mask_path)

          for img_filename in imgs_val:
              img_id = img_filename[:-4]
              img_path = join(img_dir, img_filename)

              # If using masks, only add images to dataset that also have a mask
              if mask_dir is not None:
                  mask_path = join(mask_dir, img_id + '_instanceIds.png')

                  # Ignores the image (doesn't add) if no mask exists
                  if not assume_match and not isfile(mask_path):
                      continue
              else:
                  mask_path = None

              # Adds the image to the dataset
              val_part.add_image('WAD', img_id, img_path, mask_path=mask_path)

          return val_part
      
        #otherwise val not 0 do the normal process
        
        # Iterate through images and add to dataset
        for img_filename in images:
            img_id = img_filename[:-4]
            img_path = join(img_dir, img_filename)

            # If using masks, only add images to dataset that also have a mask
            if mask_dir is not None:
                mask_path = join(mask_dir, img_id + '_instanceIds.png')

                # Ignores the image (doesn't add) if no mask exists
                if not assume_match and not isfile(mask_path):
                    continue
            else:
                mask_path = None

            # Adds the image to the dataset
            self.add_image('WAD', img_id, img_path, mask_path=mask_path)

        return None

    def load_data(self, root_dir, subset, val_size=0, labeled=True, assume_match=False):
        """Load a subset of the WAD image segmentation dataset.
        root_dir: Root directory of the data
        subset: Which subset to load: images will be looked for in 'subset_color' and masks will
        be looked for in 'subset_label'
        labeled: Whether the images have ground-truth masks
        assume_match: Whether to assume all images have ground-truth masks (ignored if labeled
        is False)
        val_size: applicable only when labeled = True. it is how much to split training for validation
        """

        # Set up directories
        img_dir = join(root_dir, subset + '_color')
        mask_dir = join(root_dir, subset + '_label')

        if labeled:
            assert os.path.exists(img_dir) and os.path.exists(mask_dir)
            return self._load_all_images(img_dir, mask_dir, assume_match=assume_match, val_size=val_size)
        else:
            assert os.path.exists(img_dir)
            self._load_all_images(img_dir, assume_match=assume_match)
            return None

    def load_mask(self, image_id):
        """Generate instance masks for an image.
        image_id: integer id of the image
        Returns:
        masks: A bool array of shape [height, width, instance count] with
            one mask per instance.
        class_ids: a 1D array of class IDs of the instance masks.
        """

        info = self.image_info[image_id]

        # If not a WAD dataset image, delegate to parent class
        if info["source"] != "WAD":
            return super(self.__class__, self).load_mask(image_id)

        # Read the original mask image
        raw_mask = skimage.io.imread(info["mask_path"])

        # unique is a sorted array of unique instances (including background)
        unique = np.unique(raw_mask)

        # section that removes/involves background
        index = np.searchsorted(unique, 255)
        unique = np.delete(unique, index, axis=0)

        # tensors!
        raw_mask = raw_mask.reshape(2710, 3384, 1)

        # broadcast!!!!
        # k = instance_count
        # (h, w, 1) x (k,) => (h, w, k) : bool array
        masks = raw_mask == unique

        # get the actually class id
        # int(PixelValue / 1000) is the label (class of object)
        unique = np.floor_divide(unique, 1000)
        class_ids = np.array([classes_to_index[e] for e in unique])

        # Return mask, and array of class IDs of each instance.
        return masks, class_ids

    def load_images_from_file(self, filename):
        """Load images from pickled file.
        filename: name of the pickle file
        """
        with open(filename, 'rb') as f:
            self.image_info = pickle.load(f)

    def save_images_to_file(self, filename):
        """Save loaded images to pickle file.
        filename: name of the pickle file"""
        with open(filename, 'wb') as f:
            pickle.dump(self.image_info, f)

    def image_reference(self, image_id):
        """Return the path to the image."""

        info = self.image_info[image_id]
        if info["source"] == "balloon":
            return info["path"]
        else:
            super(self.__class__, self).image_reference(image_id)

###############################################################################
#                               TESTING SCRIPTS                               #
###############################################################################


def test_loading():
    # SET THESE AS APPROPRIATE FOR YOUR TEST PLATFORM
    root_dir = 'G:\\Team Drives\\COML-Summer-2018\\Data\\CVPR-WAD-2018'
    subset = 'train'

    # Load and prepare dataset
    start_time = time()

    wad = WADDataset()
    wad.load_data(root_dir, subset)
    wad.prepare()

    print('[TIME] Time to Load and Prepare Dataset = {} seconds'.format(time() - start_time))

    # Check number of classes and images
    image_count = len(wad.image_info)
    print('No. Images:\t\t{}'.format(image_count))
    print('No. Classes:\t{}'.format(len(wad.class_info)))

    # Choose a random image to display
    which_image = np.random.randint(0, image_count)

    # Display original image
    plt.figure(0)
    plt.title('Image No. {}'.format(which_image))
    plt.imshow(wad.load_image(which_image))

    # Display masks if available
    if wad.image_info[which_image]['mask_path'] is not None:
        # Generate masks from file
        start = time()

        masks, labels = wad.load_mask(which_image)
        num_masks = masks.shape[2]

        print('[TIME] Time to Generate Masks = {} seconds'.format(time() - start))

        # Set up grid of plots for the masks
        rows, cols = math.ceil(math.sqrt(num_masks)), math.ceil(math.sqrt(num_masks))
        plt.figure(1)

        # Plot each mask
        for i in range(num_masks):
            instance_class = classes[index_to_classes[labels[i]]]

            frame = plt.subplot(rows, cols, i+1)
            frame.axes.get_xaxis().set_visible(False)
            frame.axes.get_yaxis().set_visible(False)
            plt.title('Mask No. {0} of class {1}'.format(i, instance_class))
            plt.imshow(np.uint8(masks[:, :, i]))

    print('Showing Image No. {}'.format(which_image))
    plt.show()
