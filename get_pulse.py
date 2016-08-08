from lib.device import Camera
from lib.processors_noopenmdao import findFaceGetPulse
from lib.interface import plotXY, imshow, waitKey, destroyWindow
import numpy as np
import datetime
from cv2 import moveWindow

import argparse
from serial import Serial
import socket
import sys
import time

#modules required for the picamera attrbute of the raspberry pi
from picamera.array import PiRGBArray
from picamera import PiCamera
import cv2
import csv


class getPulseApp(object):
    """
    Python application that finds a face in a webcam stream, then isolates the
    forehead.

     Then the average green-light intensity in the forehead region is gathered
     over time, and the detected person's pulse is estimated.
    """
    def __init__(self):
        # Imaging device - must be a connected camera (not an ip camera or mjpeg
        # stream)
        # self.videoinput = args.videoInput

         self.fileName = []
         self.cameras = []
         self.selected_cam = 0

         self.w, self.h = 0, 0
         self.pressed = 0
         self.writeCSV = False
         # Containerized analysis of recieved image frames (an openMDAO assembly)
         # is defined next.

         # This assembly is designed to handle all image & signal analysis,
         # such as face detection, forehead isolation, time series collection,
         # heart-beat detection, etc.

         # Basically, everything that isn't communication
         # to the camera device or part of the GUI
         self.processor = findFaceGetPulse(bpm_limits=[50, 160], data_spike_limit=2500.,face_detector_smoothness=10.)

         # Init parameters for the cardiac data plot
         self.bpm_plot = False
         self.plot_title = "Data display - raw signal (top) and PSD (bottom)"

         # Maps keystrokes to specified methods
         #(A GUI window must have focus for these to work)
         self.key_controls = {"s": lambda: None, #self.toggle_search,
                              "d": self.toggle_display_plot,
                              "f": self.write_csv}

    def write_csv(self):
         """
         Writes current data to a csv file
         """
         today = datetime.datetime.today()
         format = "%b %d %H:%M:%S"
         s = today.strftime(format)
         d = datetime.datetime.strptime(s, format)

         fn = "./OUTPUT_FILES/" + self.name +"_ICC2015_RR_" + d.strftime(format)
         # fn2 = self.name +"_ICC2015_HR_" + d.strftime(format)
         fn = fn.replace(":", "_").replace(" ", "_")
         # self.fileName = fn
         # with open(fn, 'a') as fp:
         self.fileName = open(fn , 'a')

         self.writeCSV = True


    def toggle_search(self):
         """
         Toggles a motion lock on the processor's face detection component.

         Locking the forehead location in place significantly improves
         data quality, once a forehead has been sucessfully isolated.
         """
         state = self.processor.find_faces_toggle()
         print ("face detection lock =", not state)

    def toggle_display_plot(self):
         """
         Toggles the data display.
         """
         if self.bpm_plot:
             print ("bpm plot disabled")
             self.bpm_plot = False
             destroyWindow(self.plot_title)
         else:
             print ("bpm plot enabled")
             if self.processor.find_faces:
                 self.toggle_search()
             self.bpm_plot = True
             self.make_bpm_plot()
             moveWindow(self.plot_title, self.w, 0)

    def make_bpm_plot(self):
         """
         Creates and/or updates the data display
         """
         plotXY([[self.processor.times,self.processor.samples],[self.processor.freqs,self.processor.fft]],
                labels=[False, True],
                showmax=[False, "bpm"],
                label_ndigits=[0, 0],
                showmax_digits=[0, 1],
                skip=[3, 3],
                name=self.plot_title,
                bg=self.processor.slices[0])


    def main_loop(self , frame):
        """
        Single iteration of the application's main loop.
        """

        if frame != None:
            self.h, self.w, _c = frame.shape

            # set current image frame to the processor's input
            self.processor.frame_in = frame
            # process the image frame to perform all needed analysis
            self.processor.run()

            # collect the output frame for display
            output_frame = self.processor.frame_out

            # show the processed/annotated output frame
            imshow("Processed", output_frame)

            # create and/or update the raw data display if needed
            if self.bpm_plot:
                self.make_bpm_plot()

            if self.writeCSV:
                data = np.array([self.processor.actualTime, self.processor.bpm, self.processor.RRvalue]).T
                print(data)
    # , self.processor.bpm , self.processor.RRvalue
                self.fileName.write("%s" % self.processor.actualTime + " ")
                self.fileName.write("%s" % self.processor.bpm + " ")
                self.fileName.write("%s" % self.processor.RRvalue + "\n")
                # np.savetxt("./CSV_FILE/"+ self.fileName + ".csv", data , delimiter=',')
            # data = np.array([self.processor.bpms , self.processor.RR]).T
            # print(data)
            # handle any key presses
            self.key_handler()
        else:
            print ("Exiting")
            sys.exit()


    def key_handler(self):
        """
        Handle keystrokes, as set at the bottom of __init__()

        A plotting or camera frame window must have focus for keypresses to be
        detected.
        """

        self.pressed = waitKey(10) & 255  # wait for keypress for 10 ms
        if self.pressed == 27:  # exit program on 'esc'
            print "Exiting"
            for cam in self.cameras:
                cam.cam.release()
            # if self.send_serial:
                # self.serial.close()
            sys.exit()

        for key in self.key_controls.keys():
            if chr(self.pressed) == key:
                print('enter')
                self.key_controls[key]()

if __name__ == "__main__":

    camera = PiCamera()
    camera.resolution = (640, 480)
    camera.framerate = 32
    camera.rotation = 180
    rawCapture = PiRGBArray(camera, size=(640, 480))
    time.sleep(0.1)
    parser = argparse.ArgumentParser(description='Webcam pulse detector.')

    App = getPulseApp()
    for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
    # # grab the raw NumPy array representing the image, then initialize the timestamp
    # # and occupied/unoccupied text
        image = frame.array
        key = cv2.waitKey(1) & 0xFF
        App.main_loop(image)
        rawCapture.truncate(0)
        # if the `q` key was pressed, break from the loop
        if key == ord("q"):
            break

