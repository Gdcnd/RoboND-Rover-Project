
# coding: utf-8

# ## Rover Project Test Notebook
# This notebook contains the functions from the lesson and provides the scaffolding you need to test out your mapping methods.  The steps you need to complete in this notebook for the project are the following:
# 
# * First just run each of the cells in the notebook, examine the code and the results of each.
# * Run the simulator in "Training Mode" and record some data. Note: the simulator may crash if you try to record a large (longer than a few minutes) dataset, but you don't need a ton of data, just some example images to work with.   
# * Change the data directory path (2 cells below) to be the directory where you saved data
# * Test out the functions provided on your data
# * Write new functions (or modify existing ones) to report and map out detections of obstacles and rock samples (yellow rocks)
# * Populate the `process_image()` function with the appropriate steps/functions to go from a raw image to a worldmap.
# * Run the cell that calls `process_image()` using `moviepy` functions to create video output
# * Once you have mapping working, move on to modifying `perception.py` and `decision.py` to allow your rover to navigate and map in autonomous mode!
# 
# **Note: If, at any point, you encounter frozen display windows or other confounding issues, you can always start again with a clean slate by going to the "Kernel" menu above and selecting "Restart & Clear Output".**
# 
# **Run the next cell to get code highlighting in the markdown cells.**

# In[1]:

#get_ipython().run_cell_magic('HTML', '', '<style> code {background-color : orange !important;} </style>')


# In[2]:

#get_ipython().magic('matplotlib inline')
#%matplotlib qt # Choose %matplotlib qt to plot to an interactive window (note it may show up behind your browser)
# Make some of the relevant imports
import cv2 # OpenCV for perspective transform
import numpy as np
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import scipy.misc # For saving images as needed
import glob  # For reading in a list of images from a folder

import imageio


# ## Quick Look at the Data
# There's some example data provided in the `test_dataset` folder.  This basic dataset is enough to get you up and running but if you want to hone your methods more carefully you should record some data of your own to sample various scenarios in the simulator.  
# 
# Next, read in and display a random image from the `test_dataset` folder

# In[3]:

path = '../test_dataset/IMG/*'
img_list = glob.glob(path)
# Grab a random image and display it
idx = np.random.randint(0, len(img_list)-1)
image = mpimg.imread(img_list[idx])
plt.imshow(image)
plt.show()


# ## Calibration Data
# Read in and display example grid and rock sample calibration images.  You'll use the grid for perspective transform and the rock image for creating a new color selection that identifies these samples of interest. 

# In[4]:

# In the simulator you can toggle on a grid on the ground for calibration
# You can also toggle on the rock samples with the 0 (zero) key.  
# Here's an example of the grid and one of the rocks
example_grid = '../calibration_images/example_grid1.jpg'
example_rock = '../calibration_images/example_rock1.jpg'
grid_img = mpimg.imread(example_grid)
rock_img = mpimg.imread(example_rock)

fig = plt.figure(figsize=(12,3))
plt.subplot(121)
plt.imshow(grid_img)
plt.subplot(122)
plt.imshow(rock_img)
plt.show()


# ## Perspective Transform
# 
# Define the perspective transform function from the lesson and test it on an image.

# In[5]:

# Define a function to perform a perspective transform
# I've used the example grid image above to choose source points for the
# grid cell in front of the rover (each grid cell is 1 square meter in the sim)
# Define a function to perform a perspective transform
def perspect_transform(img, src, dst):
    
    M = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(img, M, (img.shape[1], img.shape[0]))# keep same size as input image
    
    return warped


# Define calibration box in source (actual) and destination (desired) coordinates
# These source and destination points are defined to warp the image
# to a grid where each 10x10 pixel square represents 1 square meter
# The destination box will be 2*dst_size on each side
dst_size = 5 
# Set a bottom offset to account for the fact that the bottom of the image 
# is not the position of the rover but a bit in front of it
# this is just a rough guess, feel free to change it!
bottom_offset = 6
source = np.float32([[14, 140], [301 ,140],[200, 96], [118, 96]])
print(image.shape)
destination = np.float32([[image.shape[1]/2 - dst_size, image.shape[0] - bottom_offset],
                  [image.shape[1]/2 + dst_size, image.shape[0] - bottom_offset],
                  [image.shape[1]/2 + dst_size, image.shape[0] - 2*dst_size - bottom_offset], 
                  [image.shape[1]/2 - dst_size, image.shape[0] - 2*dst_size - bottom_offset],
                  ])
warped = perspect_transform(grid_img, source, destination)
plt.imshow(warped)
#scipy.misc.imsave('../output/warped_example.jpg', warped)
plt.show()


# ## Color Thresholding
# Define the color thresholding function from the lesson and apply it to the warped image
# 
# **TODO:** Ultimately, you want your map to not just include navigable terrain but also obstacles and the positions of the rock samples you're searching for.  Modify this function or write a new function that returns the pixel locations of obstacles (areas below the threshold) and rock samples (yellow rocks in calibration images), such that you can map these areas into world coordinates as well.  
# **Suggestion:** Think about imposing a lower and upper boundary in your color selection to be more specific about choosing colors.  Feel free to get creative and even bring in functions from other libraries.  Here's an example of [color selection](http://opencv-python-tutroals.readthedocs.io/en/latest/py_tutorials/py_imgproc/py_colorspaces/py_colorspaces.html) using OpenCV.  
# **Beware:** if you start manipulating images with OpenCV, keep in mind that it defaults to `BGR` instead of `RGB` color space when reading/writing images, so things can get confusing.

# In[6]:

# Identify pixels above the threshold
# Threshold of RGB > 160 does a nice job of identifying ground pixels only
def color_thresh(img, roll, pitch, rgb_thresh=(160, 160, 160)):
    # Create an array of zeros same xy size as img, but single channel
    color_select = np.zeros_like(img[:,:,0])
    
    if float(roll) > 10:
        #rgb_thresh=(190,190,190)
        print('ignoring frame as to much roll')
    # Require that each pixel be above all three threshold values in RGB
    # above_thresh will now contain a boolean array with "True"
    # where threshold was met
    above_thresh = (img[:,:,0] > rgb_thresh[0]) & (img[:,:,1] > rgb_thresh[1]) & (img[:,:,2] > rgb_thresh[2])
    # Index the array of zeros with the boolean array and set to 1
    color_select[above_thresh] = 1
    # Return the binary image
    return color_select

def obstacles(img, rgb_thresh=(70, 70, 70)):
    obstacles = np.zeros_like(img[:,:,0])
    below_thresh = (img[:,:,0] < rgb_thresh[0]) & (img[:,:,1] < rgb_thresh[1])  & (img[:,:,2] < rgb_thresh[2])
    obstacles[below_thresh] = 1
    return obstacles

def rocks(img):
    low_yellow = np.array([20, 100, 100], dtype = "uint8")
    high_yellow = np.array([255, 255, 255], dtype = "uint8")
    
    # convert to HSV space
    img_hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV,3)
    # mask yellow values
    mask_rock = cv2.inRange(img_hsv, low_yellow, high_yellow)
    return mask_rock


img_road = color_thresh(warped, '9', '2')
img_obstacles = obstacles(grid_img)
img_rocks = rocks(rock_img)

fig = plt.figure(figsize=(12,5))
plt.subplot(231)
plt.imshow(warped)
plt.subplot(232)
plt.imshow(grid_img)
plt.subplot(233)
plt.imshow(rock_img)
plt.subplot(234)
plt.imshow(img_road, cmap='gray')
plt.subplot(235)
plt.imshow(img_obstacles, cmap='gray')
plt.subplot(236)
plt.imshow(img_rocks, cmap='gray')
plt.show()

#scipy.misc.imsave('../output/warped_threshed.jpg', threshed*255)


# ## Coordinate Transformations
# Define the functions used to do coordinate transforms and apply them to an image.

# In[7]:

def rover_coords(binary_img):
    # Identify nonzero pixels
    ypos, xpos = binary_img.nonzero()
    # Calculate pixel positions with reference to the rover position being at the 
    # center bottom of the image.  
    x_pixel = np.absolute(ypos - binary_img.shape[0]).astype(np.float)
    y_pixel = -(xpos - binary_img.shape[0]).astype(np.float)
    return x_pixel, y_pixel

# Define a function to convert to radial coords in rover space
def to_polar_coords(x_pixel, y_pixel):
    # Convert (x_pixel, y_pixel) to (distance, angle) 
    # in polar coordinates in rover space
    # Calculate distance to each pixel
    dist = np.sqrt(x_pixel**2 + y_pixel**2)
    # Calculate angle away from vertical for each pixel
    angles = np.arctan2(y_pixel, x_pixel)
    return dist, angles

# Define a function to apply a rotation to pixel positions
def rotate_pix(xpix, ypix, yaw):
    # Convert yaw to radians
    yaw_rad = yaw * np.pi / 180
    xpix_rotated = (xpix * np.cos(yaw_rad)) - (ypix * np.sin(yaw_rad))
                            
    ypix_rotated = (xpix * np.sin(yaw_rad)) + (ypix * np.cos(yaw_rad))
    # Return the result  
    return xpix_rotated, ypix_rotated

# Define a function to perform a translation
def translate_pix(xpix_rot, ypix_rot, xpos, ypos, scale): 
    # Apply a scaling and a translation
    xpix_translated = (xpix_rot / scale) + xpos
    ypix_translated = (ypix_rot / scale) + ypos
    # Return the result  
    return xpix_translated, ypix_translated

# Define a function to apply rotation and translation (and clipping)
# Once you define the two functions above this function should work
def pix_to_world(xpix, ypix, xpos, ypos, yaw, world_size, scale):
    # Apply rotation
    xpix_rot, ypix_rot = rotate_pix(xpix, ypix, yaw)
    # Apply translation
    xpix_tran, ypix_tran = translate_pix(xpix_rot, ypix_rot, xpos, ypos, scale)
    # Perform rotation, translation and clipping all at once
    x_pix_world = np.clip(np.int_(xpix_tran), 0, world_size - 1)
    y_pix_world = np.clip(np.int_(ypix_tran), 0, world_size - 1)
    # Return the result
    return x_pix_world, y_pix_world

# Grab another random image
idx = np.random.randint(0, len(img_list)-1)
image = mpimg.imread(img_list[idx])
warped = perspect_transform(image, source, destination)
threshed = color_thresh(warped, '11', '2')

# Calculate pixel values in rover-centric coords and distance/angle to all pixels
xpix, ypix = rover_coords(threshed)
dist, angles = to_polar_coords(xpix, ypix)
mean_dir = np.mean(angles)

# Do some plotting
fig = plt.figure(figsize=(12,6))
plt.subplot(221)
plt.imshow(image)
plt.subplot(222)
plt.imshow(warped)
plt.subplot(223)
plt.imshow(threshed, cmap='gray')
plt.subplot(224)
plt.plot(xpix, ypix, '.')
plt.ylim(-160, 160)
plt.xlim(0, 160)
arrow_length = 100
x_arrow = arrow_length * np.cos(mean_dir)
y_arrow = arrow_length * np.sin(mean_dir)
plt.arrow(0, 0, x_arrow, y_arrow, color='red', zorder=2, head_width=10, width=2)
plt.show()


# Extra Stuff

# # Read in saved data and ground truth map of the world
# The next cell is all setup to read your saved data into a `pandas` dataframe.  Here you'll also read in a "ground truth" map of the world, where white pixels (pixel value = 1) represent navigable terrain.  
# 
# After that, we'll define a class to store telemetry data and pathnames to images.  When you instantiate this class (`data = Databucket()`) you'll have a global variable called `data` that you can refer to for telemetry and map data within the `process_image()` function in the following cell.  
# 

# In[8]:

# Import pandas and read in csv file as a dataframe
import pandas as pd
# Change this path to your data directory
df = pd.read_csv('../../telemetry/robot_log.csv', delimiter=',', decimal='.')
csv_img_list = df["Path"].tolist() # Create list of image pathnames
# Read in ground truth map and create a 3-channel image with it
ground_truth = mpimg.imread('../calibration_images/map_bw.png')
ground_truth_3d = np.dstack((ground_truth*0, ground_truth*255, ground_truth*0)).astype(np.float)

# Creating a class to be the data container
# Will read in saved data from csv file and populate this object
# Worldmap is instantiated as 200 x 200 grids corresponding 
# to a 200m x 200m space (same size as the ground truth map: 200 x 200 pixels)
# This encompasses the full range of output position values in x and y from the sim
class Databucket():
    def __init__(self):
        self.images = csv_img_list  
        self.xpos = df["X_Position"].values
        self.ypos = df["Y_Position"].values
        self.yaw = df["Yaw"].values
        self.roll = df["Roll"].values
        self.pitch = df["Pitch"].values
        self.count = -1 # This will be a running index, setting to -1 is a hack
                        # because moviepy (below) seems to run one extra iteration
        self.worldmap = np.zeros((200, 200, 3)).astype(np.float)
        self.ground_truth = ground_truth_3d # Ground truth worldmap

# Instantiate a Databucket().. this will be a global variable/object
# that you can refer to in the process_image() function below
data = Databucket()


# ## Write a function to process stored images
# 
# Modify the `process_image()` function below by adding in the perception step processes (functions defined above) to perform image analysis and mapping.  The following cell is all set up to use this `process_image()` function in conjunction with the `moviepy` video processing package to create a video from the images you saved taking data in the simulator.  
# 
# In short, you will be passing individual images into `process_image()` and building up an image called `output_image` that will be stored as one frame of video.  You can make a mosaic of the various steps of your analysis process and add text as you like (example provided below).  
# 
# 
# 
# To start with, you can simply run the next three cells to see what happens, but then go ahead and modify them such that the output video demonstrates your mapping process.  Feel free to get creative!

# In[9]:

# Define a function to pass stored images to
# reading rover position and yaw angle from csv file
# This function will be used by moviepy to create an output video
def process_image(img):
    # Example of how to use the Databucket() object defined above
    # to print the current x, y and yaw values 
    # print(data.xpos[data.count], data.ypos[data.count], data.yaw[data.count])
    
    # TODO: 
    # 1) Define source and destination points for perspective transform
    dst_size = 5 
    bottom_offset = 6
    source = np.float32([[14, 140], [301 ,140],[200, 96], [118, 96]])
    destination = np.float32([[img.shape[1]/2 - dst_size, img.shape[0] - bottom_offset],
                  [img.shape[1]/2 + dst_size, img.shape[0] - bottom_offset],
                  [img.shape[1]/2 + dst_size, img.shape[0] - 2*dst_size - bottom_offset], 
                  [img.shape[1]/2 - dst_size, img.shape[0] - 2*dst_size - bottom_offset],
                  ])
    
    # 2) Apply perspective transform
    warped = perspect_transform(img, source, destination)
    
    # 3) Apply color threshold to identify navigable terrain/obstacles/rock samples

    threshed_terrain = color_thresh(warped, "1", "1")
    threshed_obstacles = obstacles(warped)
    threshed_rocks = rocks(warped)
    
    # 4) Convert thresholded image pixel values to rover-centric coords
        
    terrain_x_pix, terrain_y_pix = rover_coords(threshed_terrain)
    obstacles_x_pix, obstacles_y_pix = rover_coords(threshed_obstacles)
    rocks_x_pix, rocks_y_pix = rover_coords(threshed_rocks)

    
    # 5) Convert rover-centric pixel values to world coords
    dist, angles = to_polar_coords(terrain_x_pix, terrain_y_pix)
    
    # 6) Update worldmap (to be displayed on right side of screen)

    scale = 10
    x_world, y_world = pix_to_world(terrain_x_pix, terrain_y_pix, data.xpos[data.count], data.ypos[data.count], data.yaw[data.count], data.worldmap.shape[0], scale)
    obstacles_x_world, obstacles_y_world = pix_to_world(obstacles_x_pix, obstacles_y_pix, data.xpos[data.count], data.ypos[data.count], data.yaw[data.count], data.worldmap.shape[0], scale)
    rock_x_world, rock_y_world = pix_to_world(rocks_x_pix, rocks_y_pix, data.xpos[data.count], data.ypos[data.count], data.yaw[data.count], data.worldmap.shape[0], scale) 

    data.worldmap[y_world, x_world, 2] += 255
    data.worldmap[rock_y_world, rock_x_world, 1] += 255
    data.worldmap[obstacles_y_world, obstacles_x_world, 0] += 255
    
    # 7) Make a mosaic image, below is some example code
        # First create a blank image (can be whatever shape you like)
    output_image = np.zeros((img.shape[0] + data.worldmap.shape[0], img.shape[1]*2, 3))
        # Next you can populate regions of the image with various output
        # Here I'm putting the original image in the upper left hand corner
        
    output_image[0:img.shape[0], 0:img.shape[1]] = img

        # Let's create more images to add to the mosaic, first a warped image
    output_image[0:img.shape[0], img.shape[1]:] = warped    
    output_image[img.shape[0]:, 0:data.worldmap.shape[1]] = data.ground_truth 

        # Overlay worldmap with ground truth map
    map_add = cv2.addWeighted(data.worldmap, 1, data.ground_truth, 0.5, 0)
        # Flip map overlay so y-axis points upward and add to output_image 
    output_image[img.shape[0]:, img.shape[1]:img.shape[1]+ data.worldmap.shape[1],:] = np.flipud(map_add)       

    cv2.putText(output_image, "Camera View", (20, 20), cv2.FONT_HERSHEY_COMPLEX, 0.4, (255, 255, 255), 1)
    cv2.putText(output_image, "perspective", (350, 20), cv2.FONT_HERSHEY_COMPLEX, 0.4, (255, 255, 255), 1)
    cv2.putText(output_image, "World Map", (20, 180), cv2.FONT_HERSHEY_COMPLEX, 0.4, (255, 255, 255), 1)
    cv2.putText(output_image, "Navigate ", (350, 180), cv2.FONT_HERSHEY_COMPLEX, 0.4, (255, 255, 255), 1)
    
    data.count += 1 # Keep track of the index in the Databucket()
    
    if data.count == 5000:  # to overcome some error for index out of bounds
        data.count =0
   
    return output_image


# ## Make a video from processed image data
# Use the [moviepy](https://zulko.github.io/moviepy/) library to process images and create a video.
#   

# In[10]:

# Import everything needed to edit/save/watch video clips
from moviepy.editor import VideoFileClip
from moviepy.editor import ImageSequenceClip


# Define pathname to save the output video
output = '../../telemetry/test_mapping.mp4'
data = Databucket() # Re-initialize data in case you're running this cell multiple times
clip = ImageSequenceClip(data.images, fps=60) # Note: output video will be sped up because 
                                          # recording rate in simulator is fps=25
new_clip = clip.fl_image(process_image) #NOTE: this function expects color images!!
#get_ipython().magic('time new_clip.write_videofile(output, audio=False)')
new_clip.write_videofile(output, audio=False)

# ### This next cell should function as an inline video player
# If this fails to render the video, try running the following cell (alternative video rendering method).  You can also simply have a look at the saved mp4 in your `/output` folder

# ### Below is an alternative way to create a video in case the above cell did not work.

# In[12]:

import io
import base64
from IPython.display import HTML
video = io.open(output, 'r+b').read()
encoded_video = base64.b64encode(video)
HTML(data='''<video alt="test" controls>
                <source src="data:video/mp4;base64,{0}" type="video/mp4" />
             </video>'''.format(encoded_video.decode('ascii')))


# In[ ]:



