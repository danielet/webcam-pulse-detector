from lib.device import Camera
from lib.processors_noopenmdao import findFaceGetPulse
from lib.interface import plotXY, imshow, waitKey, destroyWindow
from cv2 import moveWindow
import argparse
import numpy as np
import datetime
from serial import Serial
import socket
import sys
import time 

import csv

class getPulseApp(object):

    """
    Python application that finds a face in a webcam stream, then isolates the
    forehead.

    Then the average green-light intensity in the forehead region is gathered
    over time, and the detected person's pulse is estimated.
    """

    def __init__(self, args):
        # Imaging device - must be a connected camera (not an ip camera or mjpeg
        # stream)

                
        serial = args.serial
        baud = args.baud
        name = args.name
        self.send_serial = False
        self.send_udp = False
        self.name = name

        self.videoinput = args.videoInput

        self.fileName = []
        
        self.cameras = []
        self.selected_cam = 0
        print(args.videoInput)
        for i in xrange(3):
            
            camera = Camera(camera=i, videoPass = args.videoInput)  # first camera by default
            if camera.valid or not len(self.cameras):
                self.cameras.append(camera)
            else:
                break

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
        self.processor = findFaceGetPulse(bpm_limits=[50, 160],
                                          data_spike_limit=2500.,
                                          face_detector_smoothness=10.)

        # Init parameters for the cardiac data plot
        self.bpm_plot = False
        self.plot_title = "Data display - raw signal (top) and PSD (bottom)"

        # Maps keystrokes to specified methods
        #(A GUI window must have focus for these to work)
        self.key_controls = {"s": self.toggle_search,
                             "d": self.toggle_display_plot,
                             "c": self.toggle_cam,
                             "f": self.write_csv}

    def toggle_cam(self):
        if len(self.cameras) > 1:
            self.processor.find_faces = True
            self.bpm_plot = False
            destroyWindow(self.plot_title)
            self.selected_cam += 1
            self.selected_cam = self.selected_cam % len(self.cameras)

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
        
        print "face detection lock =", not state

    def toggle_display_plot(self):
        """
        Toggles the data display.
        """
        if self.bpm_plot:
            print "bpm plot disabled"
            self.bpm_plot = False
            destroyWindow(self.plot_title)
        else:
            print "bpm plot enabled"
            if self.processor.find_faces:
                self.toggle_search()
            self.bpm_plot = True
            self.make_bpm_plot()
            moveWindow(self.plot_title, self.w, 0)

    def make_bpm_plot(self):
        """
        Creates and/or updates the data display
        """
        plotXY([[self.processor.times,
                 self.processor.samples],
                [self.processor.freqs,
                 self.processor.fft]],
               labels=[False, True],
               showmax=[False, "bpm"],
               label_ndigits=[0, 0],
               showmax_digits=[0, 1],
               skip=[3, 3],
               name=self.plot_title,
               bg=self.processor.slices[0])

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
            if self.send_serial:
                self.serial.close()
            sys.exit()

        for key in self.key_controls.keys():
            if chr(self.pressed) == key:
                print('enter')
                self.key_controls[key]()

    def main_loop(self):
        """
        Single iteration of the application's main loop.
        """

        # Get current image frame from the camera
        frame = self.cameras[self.selected_cam].get_frame()
        if frame != None:
            self.h, self.w, _c = frame.shape

            # display unaltered frame
            # imshow("Original",frame)

            # set current image frame to the processor's input
            self.processor.frame_in = frame
            # process the image frame to perform all needed analysis
            
            self.processor.run(self.selected_cam)
            
            # collect the output frame for display
            output_frame = self.processor.frame_out

            # show the processed/annotated output frame
            imshow("Processed", output_frame)

            # create and/or update the raw data display if needed
            if self.bpm_plot:
                self.make_bpm_plot()

            if self.writeCSV:
                data = np.array([self.processor.actualTime, 
                             self.processor.bpm, 
                             self.processor.RRvalue]).T
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
            print "Exiting"
            for cam in self.cameras:
                cam.cam.release()
            if self.send_serial:
                self.serial.close()
            sys.exit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Webcam pulse detector.')
    parser.add_argument('--serial', default=None,
                        help='serial port destination for bpm data')
    parser.add_argument('--baud', default=None,
                        help='Baud rate for serial transmission')
    parser.add_argument('--udp', default=None,
                        help='udp address:port destination for bpm data')
    parser.add_argument('--name', default='unknown',
                        help='first name is going to do the experiment')

    parser.add_argument('--videoInput', default=None,
                        help='first name is going to do the experiment')

    args = parser.parse_args()
    App = getPulseApp(args)
    while True:
        App.main_loop()
