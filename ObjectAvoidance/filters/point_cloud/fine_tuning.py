# Copyright (C) 2019 Eugene Pomazov, <stereopi.com>, virt2real team
#
# This file is a variation of a part of StereoPi tutorial scripts.
#

import json

import av
import cv2
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.widgets import Slider, Button
from stereovision.calibration import StereoCalibration

# create a PyAV input stream from the raw H264 video stream
container = av.open("udp://192.168.0.191:3001?overrun_nonfatal=1&fifo_size=50000&pkt_size=30000")
stream = container.streams.video[0]

pair_img = None
for packet in container.demux(stream):
    for frame in packet.decode():
        print(frame)
        # convert the frame to a numpy array
        pair_img = np.array(frame.to_image())
        if pair_img is not None:
            break
    if pair_img is not None:
        break

pair_img = cv2.cvtColor(pair_img, cv2.COLOR_BGR2GRAY)
photo_height, photo_width = pair_img.shape[:2]
image_width = photo_width // 2

# Read image and split it in a stereo pair
print('Read and split image...')
imgLeft = pair_img[0:photo_height, 0:image_width]  # Y+H and X+W
imgRight = pair_img[0:photo_height, image_width:photo_width]  # Y+H and X+W
cv2.imshow('Left CALIBRATED', imgLeft)
cv2.imshow('Right CALIBRATED', imgRight)
cv2.waitKey(0)

# Implementing calibration data
print('Read calibration data and rectifying stereo pair...')
calibration = StereoCalibration(input_folder='calib_result')
rectified_pair = calibration.rectify((imgLeft, imgRight))
cv2.imshow('Left CALIBRATED', rectified_pair[0])
cv2.imshow('Right CALIBRATED', rectified_pair[1])
cv2.waitKey(0)

# Depth map function
SWS = 5
PFS = 5
PFC = 29
MDS = -25
NOD = 128
TTH = 100
UR = 10
SR = 15
SPWS = 100


def stereo_depth_map(rectified_pair):
    print('SWS=' + str(SWS) + ' PFS=' + str(PFS) + ' PFC=' + str(PFC) + ' MDS=' + \
          str(MDS) + ' NOD=' + str(NOD) + ' TTH=' + str(TTH))
    print(' UR=' + str(UR) + ' SR=' + str(SR) + ' SPWS=' + str(SPWS))
    c, r = rectified_pair[0].shape
    disparity = np.zeros((c, r), np.uint8)
    sbm = cv2.StereoBM_create(numDisparities=16, blockSize=15)
    # sbm.SADWindowSize = SWS
    sbm.setPreFilterType(1)
    sbm.setPreFilterSize(PFS)
    sbm.setPreFilterCap(PFC)
    sbm.setMinDisparity(MDS)
    sbm.setNumDisparities(NOD)
    sbm.setTextureThreshold(TTH)
    sbm.setUniquenessRatio(UR)
    sbm.setSpeckleRange(SR)
    sbm.setSpeckleWindowSize(SPWS)
    dmLeft = rectified_pair[0]
    dmRight = rectified_pair[1]
    # cv2.FindStereoCorrespondenceBM(dmLeft, dmRight, disparity, sbm)
    disparity = sbm.compute(dmLeft, dmRight)
    # disparity_visual = cv.CreateMat(c, r, cv.CV_8U)
    local_max = disparity.max()
    local_min = disparity.min()
    print("MAX " + str(local_max))
    print("MIN " + str(local_min))
    disparity_visual = (disparity - local_min) * (1.0 / (local_max - local_min))
    local_max = disparity_visual.max()
    local_min = disparity_visual.min()
    print("MAX " + str(local_max))
    print("MIN " + str(local_min))
    # cv.Normalize(disparity, disparity_visual, 0, 255, cv.CV_MINMAX)
    # disparity_visual = np.array(disparity_visual)
    return disparity_visual


disparity = stereo_depth_map(rectified_pair)

# Set up and draw interface
# Draw left image and depth map
axcolor = 'lightgoldenrodyellow'
fig = plt.subplots(1, 2)
plt.subplots_adjust(left=0.15, bottom=0.5)
plt.subplot(1, 2, 1)
dmObject = plt.imshow(rectified_pair[0], 'gray')

saveax = plt.axes([0.3, 0.38, 0.15, 0.04])  # stepX stepY width height
buttons = Button(saveax, 'Save settings', color=axcolor, hovercolor='0.975')


def save_map_settings(event):
    buttons.label.set_text("Saving...")
    print('Saving to file...')
    result = json.dumps({'SADWindowSize': SWS, 'preFilterSize': PFS, 'preFilterCap': PFC, \
                         'minDisparity': MDS, 'numberOfDisparities': NOD, 'textureThreshold': TTH, \
                         'uniquenessRatio': UR, 'speckleRange': SR, 'speckleWindowSize': SPWS}, \
                        sort_keys=True, indent=4, separators=(',', ':'))
    fName = '3dmap_set.txt'
    f = open(str(fName), 'w')
    f.write(result)
    f.close()
    buttons.label.set_text("Save to file")
    print('Settings saved to file ' + fName)


buttons.on_clicked(save_map_settings)

loadax = plt.axes([0.5, 0.38, 0.15, 0.04])  # stepX stepY width height
buttonl = Button(loadax, 'Load settings', color=axcolor, hovercolor='0.975')


def load_map_settings(event):
    global SWS, PFS, PFC, MDS, NOD, TTH, UR, SR, SPWS, loading_settings
    loading_settings = 1
    fName = '3dmap_set.txt'
    print('Loading parameters from file...')
    buttonl.label.set_text("Loading...")
    f = open(fName, 'r')
    data = json.load(f)
    sSWS.set_val(data['SADWindowSize'])
    sPFS.set_val(data['preFilterSize'])
    sPFC.set_val(data['preFilterCap'])
    sMDS.set_val(data['minDisparity'])
    sNOD.set_val(data['numberOfDisparities'])
    sTTH.set_val(data['textureThreshold'])
    sUR.set_val(data['uniquenessRatio'])
    sSR.set_val(data['speckleRange'])
    sSPWS.set_val(data['speckleWindowSize'])
    f.close()
    buttonl.label.set_text("Load settings")
    print('Parameters loaded from file ' + fName)
    print('Redrawing depth map with loaded parameters...')
    loading_settings = 0
    update(0)
    print('Done!')


buttonl.on_clicked(load_map_settings)

plt.subplot(1, 2, 2)
dmObject = plt.imshow(disparity, aspect='equal', cmap='jet')

# Draw interface for adjusting parameters
print('Start interface creation (it takes up to 30 seconds)...')

SWSaxe = plt.axes([0.15, 0.01, 0.7, 0.025])  # stepX stepY width height
PFSaxe = plt.axes([0.15, 0.05, 0.7, 0.025])  # stepX stepY width height
PFCaxe = plt.axes([0.15, 0.09, 0.7, 0.025])  # stepX stepY width height
MDSaxe = plt.axes([0.15, 0.13, 0.7, 0.025])  # stepX stepY width height
NODaxe = plt.axes([0.15, 0.17, 0.7, 0.025])  # stepX stepY width height
TTHaxe = plt.axes([0.15, 0.21, 0.7, 0.025])  # stepX stepY width height
URaxe = plt.axes([0.15, 0.25, 0.7, 0.025])  # stepX stepY width height
SRaxe = plt.axes([0.15, 0.29, 0.7, 0.025])  # stepX stepY width height
SPWSaxe = plt.axes([0.15, 0.33, 0.7, 0.025])  # stepX stepY width height

sSWS = Slider(SWSaxe, 'SWS', 5.0, 255.0, valinit=5)
sPFS = Slider(PFSaxe, 'PFS', 5.0, 255.0, valinit=5)
sPFC = Slider(PFCaxe, 'PreFiltCap', 5.0, 63.0, valinit=29)
sMDS = Slider(MDSaxe, 'MinDISP', -100.0, 100.0, valinit=-25)
sNOD = Slider(NODaxe, 'NumOfDisp', 16.0, 256.0, valinit=128)
sTTH = Slider(TTHaxe, 'TxtrThrshld', 0.0, 1000.0, valinit=100)
sUR = Slider(URaxe, 'UnicRatio', 1.0, 20.0, valinit=10)
sSR = Slider(SRaxe, 'SpcklRng', 0.0, 40.0, valinit=15)
sSPWS = Slider(SPWSaxe, 'SpklWinSze', 0.0, 300.0, valinit=100)


# Update depth map parameters and redraw
def update(val):
    global SWS, PFS, PFC, MDS, NOD, TTH, UR, SR, SPWS
    SWS = int(sSWS.val / 2) * 2 + 1  # convert to ODD
    PFS = int(sPFS.val / 2) * 2 + 1
    PFC = int(sPFC.val / 2) * 2 + 1
    MDS = int(sMDS.val)
    NOD = int(sNOD.val / 16) * 16
    TTH = int(sTTH.val)
    UR = int(sUR.val)
    SR = int(sSR.val)
    SPWS = int(sSPWS.val)

    print('Rebuilding depth map')
    disparity = stereo_depth_map(rectified_pair)
    dmObject.set_data(disparity)
    print('Redraw depth map')
    plt.draw()


# Connect update actions to control elements
sSWS.on_changed(update)
sPFS.on_changed(update)
sPFC.on_changed(update)
sMDS.on_changed(update)
sNOD.on_changed(update)
sTTH.on_changed(update)
sUR.on_changed(update)
sSR.on_changed(update)
sSPWS.on_changed(update)

print('Show interface to user')
plt.show()
