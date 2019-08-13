# Face Tracking Delivery Project
# Based on Jabrils TelloTV Project

from djitellopy import Tello
import face_recognition
import cv2
import numpy as np
import time
import datetime
import os
import argparse

# standard argparse stuff
parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter, add_help=False)
parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                    help='** = required')
parser.add_argument('-d', '--distance', type=int, default=3,
    help='use -d to change the distance of the drone. Range 0-6')
parser.add_argument('-sx', '--saftey_x', type=int, default=100,
    help='use -sx to change the saftey bound on the x axis . Range 0-480')
parser.add_argument('-sy', '--saftey_y', type=int, default=55,
    help='use -sy to change the saftey bound on the y axis . Range 0-360')
parser.add_argument('-os', '--override_speed', type=int, default=1,
    help='use -os to change override speed. Range 0-3')
parser.add_argument('-ss', "--save_session", action='store_true',
    help='add the -ss flag to save your session as an image sequence in the Sessions folder')
parser.add_argument('-D', "--debug", action='store_true',
    help='add the -D flag to enable debug mode. Everything works the same, but no commands will be sent to the drone')

args = parser.parse_args()

# Speed of the drone
S = 20


# this is just the bound box sizes that openCV spits out *shrug*
faceSizes = [1026, 684, 456, 304, 202, 136, 90]

# These are the values in which kicks in speed up mode, as of now, this hasn't been finalized or fine tuned so be careful
# Tested are 3, 4, 5
acc = [500,250,250,150,110,70,50]

# Frames per second of the pygame window display
FPS = 25
dimensions = (960, 720)

# 
# face_cascade = cv2.CascadeClassifier('cascades/data/haarcascade_frontalface_alt2.xml')
# recognizer = cv2.face.LBPHFaceRecognizer_create()

# Face Recognition

dario_image = face_recognition.load_image_file("known_faces/dario.png")
dario_face_encoding = face_recognition.face_encodings(dario_image)[0]

luca_image = face_recognition.load_image_file("known_faces/luca.png")
luca_face_encoding = face_recognition.face_encodings(dario_image)[0]


# Create arrays of known face encodings and their names
known_face_encodings = [
    dario_face_encoding,
    luca_face_encoding
]
known_face_names = [
    "Dario",
    "Luca"
]

# If we are to save our sessions, we need to make sure the proper directories exist
if args.save_session:
    ddir = "Sessions"

    if not os.path.isdir(ddir):
        os.mkdir(ddir)

    ddir = "Sessions/Session {}".format(str(datetime.datetime.now()).replace(':','-').replace('.','_'))
    os.mkdir(ddir)

class FrontEnd(object):
    
    def __init__(self):
        # Init Tello object that interacts with the Tello drone
        self.tello = Tello()

        # Drone velocities between -100~100
        self.for_back_velocity = 0
        self.left_right_velocity = 0
        self.up_down_velocity = 0
        self.yaw_velocity = 0
        self.speed = 10

        self.send_rc_control = True

    def run(self):

        if not self.tello.connect():
            print("Tello not connected")
            return

        if not self.tello.set_speed(self.speed):
            print("Not set speed to lowest possible")
            return

        # In case streaming is on. This happens when we quit this program without the escape key.
        if not self.tello.streamoff():
            print("Could not stop video stream")
            return

        if not self.tello.streamon():
            print("Could not start video stream")
            return

        frame_read = self.tello.get_frame_read()

        should_stop = False
        imgCount = 0
        OVERRIDE = False
        oSpeed = args.override_speed
        tDistance = args.distance
        self.tello.get_battery()
        
        # Safety Zone X
        szX = args.saftey_x

        # Safety Zone Y
        szY = args.saftey_y
        
        if args.debug:
            print("DEBUG MODE ENABLED!")

        while not should_stop:
            self.update()

            if frame_read.stopped:
                frame_read.stop()
                break

            theTime = str(datetime.datetime.now()).replace(':','-').replace('.','_')

            frame = cv2.cvtColor(frame_read.frame, cv2.COLOR_BGR2RGB)
            frameRet = frame_read.frame

            vid = self.tello.get_video_capture()

            if args.save_session:
                cv2.imwrite("{}/tellocap{}.jpg".format(ddir,imgCount),frameRet)
            
            frame = np.rot90(frame)
            imgCount+=1

            time.sleep(1 / FPS)

            # Listen for key presses
            k = cv2.waitKey(20)

            # Press 0 to set distance to 0
            if k == ord('0'):
                if not OVERRIDE:
                    print("Distance = 0")
                    tDistance = 0

            # Press 1 to set distance to 1
            if k == ord('1'):
                if OVERRIDE:
                    oSpeed = 1
                else:
                    print("Distance = 1")
                    tDistance = 1

            # Press 2 to set distance to 2
            if k == ord('2'):
                if OVERRIDE:
                    oSpeed = 2
                else:
                    print("Distance = 2")
                    tDistance = 2
                    
            # Press 3 to set distance to 3
            if k == ord('3'):
                if OVERRIDE:
                    oSpeed = 3
                else:
                    print("Distance = 3")
                    tDistance = 3
            
            # Press 4 to set distance to 4
            if k == ord('4'):
                if not OVERRIDE:
                    print("Distance = 4")
                    tDistance = 4
                    
            # Press 5 to set distance to 5
            if k == ord('5'):
                if not OVERRIDE:
                    print("Distance = 5")
                    tDistance = 5
                    
            # Press 6 to set distance to 6
            if k == ord('6'):
                if not OVERRIDE:
                    print("Distance = 6")
                    tDistance = 6

            # Press T to take off
            if k == ord('t'):
                if not args.debug:
                    print("Taking Off")
                    self.tello.takeoff()
                    self.tello.get_battery()
                self.send_rc_control = True

            # Press L to land
            if k == ord('l'):
                if not args.debug:
                    print("Landing")
                    self.tello.land()
                self.send_rc_control = False

            # Press Backspace for controls override
            if k == 8:
                if not OVERRIDE:
                    OVERRIDE = True
                    print("OVERRIDE ENABLED")
                else:
                    OVERRIDE = False
                    print("OVERRIDE DISABLED")

            if OVERRIDE:
                # W & S to fly forward & back
                if k == ord('s'):
                    self.for_back_velocity = int(S * oSpeed)
                elif k == ord('w'):
                    self.for_back_velocity = -int(S * oSpeed)
                else:
                    self.for_back_velocity = 0

                # e & q to pan right & left
                if k == ord('e'):
                    self.yaw_velocity = int(S * oSpeed)
                elif k == ord('q'):
                    self.yaw_velocity = -int(S * oSpeed)
                else:
                    self.yaw_velocity = 0

                # space & y to fly up & down
                if k == 32: #space
                    self.up_down_velocity = int(S * oSpeed)
                elif k == ord('y'):
                    self.up_down_velocity = -int(S * oSpeed)
                else:
                    self.up_down_velocity = 0

                # c & z to fly right & left
                if k == ord('d'):
                    self.left_right_velocity = int(S * oSpeed)
                elif k == ord('a'):
                    self.left_right_velocity = -int(S * oSpeed)
                else:
                    self.left_right_velocity = 0

            # Quit the software
            if k == 27: #escape key
                should_stop = True
                break

            #gray  = cv2.cvtColor(frameRet, cv2.COLOR_BGR2GRAY)
            #faces = face_cascade.detectMultiScale(gray, scaleFactor=1.5, minNeighbors=2)
            
            # Resize the frame to 1/4 the size
            recognition_frame = cv2.resize(frameRet, (0, 0), fx=0.25, fy=0.25)
            # Convert the video frame from GRB (opencv) to RGB (face_recognition) color
            rgb_recognition_frame = recognition_frame[:, :, ::-1] 
            
            face_locations = face_recognition.face_locations(rgb_recognition_frame)
            face_encodings = face_recognition.face_encodings(rgb_recognition_frame, face_locations)
            
            tolerance_x = 100
            tolerance_y = 100

            noFaces = len(face_encodings) == 0

            if self.send_rc_control and not OVERRIDE:
                face_names = []
                for face_encoding in face_encodings:
                    # See if the face is a match for the known face(s)
                    matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                    name = "Who dis?"
        
                    # Use the known face with the smallest distance to the new face
                    face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        name = known_face_names[best_match_index]
        
                    face_names.append(name)
                
                face_locked = False
                for (top, right, bottom, left), name in zip(face_locations, face_names):
                    # Scale back up face locations since the frame we detected in was scaled to 1/4 size
                    top *= 4
                    right *= 4
                    bottom *= 4
                    left *= 4
            
                    # Draw a box around the face
                    cv2.rectangle(frameRet, (left, top), (right, bottom), (0, 0, 255), 2)
            
                    # Draw a label with a name below the face
                    cv2.rectangle(frameRet, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
                    font = cv2.FONT_HERSHEY_DUPLEX
                    cv2.putText(frameRet, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

                    if name is not "Who dis?" and not face_locked:
                        face_locked = True

                        # Track the face
                        # top, right, bottom, left, name
                        
                        x = left
                        y = top
                        w = right - left
                        h = bottom - top

                        target_point_x = int(left + (w/2))
                        target_point_y = int(top  + (h/2))

                        # Draw the target point
                        cv2.circle(frameRet,
                            (target_point_x, target_point_y),
                            10, (0, 255, 0), 2)

                        heading_point_x = int(dimensions[0] / 2)
                        heading_point_y = int(dimensions[1] / 2)
                        
                        # Draw the heading point
                        cv2.circle(
                            frameRet,
                            (heading_point_x, heading_point_y),
                            5, (0, 0, 255), 2)
                        
                        target_reached = heading_point_x >= (target_point_x - tolerance_x) \
                                            and heading_point_x <= (target_point_x + tolerance_x) \
                                            and heading_point_y >= (target_point_y - tolerance_y) \
                                            and heading_point_y <= (target_point_y + tolerance_y)

                        # Draw the target zone
                        cv2.rectangle(
                            frameRet,
                            (target_point_x - tolerance_x, target_point_y - tolerance_y),
                            (target_point_x + tolerance_x, target_point_y + tolerance_y),
                            (0, 255, 0) if target_reached else (0, 255, 255), 2)
                        
                        if not target_reached:
                            target_offset_x = target_point_x - heading_point_x
                            target_offset_y = target_point_y - heading_point_y
                            
                            self.yaw_velocity = round(S * translate(target_offset_x, -dimensions[0]/2, dimensions[0] / 2, -1, 1))
                            self.up_down_velocity = -round(S * translate(target_offset_y, -dimensions[1]/2, dimensions[1] / 2, -1, 1))
                            
                            print("YAW SPEED {} UD SPEED {}".format(self.yaw_velocity, self.up_down_velocity))
                        else:
                            self.yaw_velocity = 0
                            self.up_down_velocity = 0

                if noFaces:
                    self.yaw_velocity = 0
                    self.up_down_velocity = 0
                    self.for_back_velocity = 0
                    print("NO TARGET")

            # Display the resulting frame
            cv2.imshow(f'Tello Tracking...',frameRet)

        # On exit, print the battery
        self.tello.get_battery()

        # When everything done, release the capture
        cv2.destroyAllWindows()
        
        # Call it always before finishing. I deallocate resources.
        self.tello.end()


    def battery(self):
        return self.tello.get_battery()[:2]

    def update(self):
        """ Update routine. Send velocities to Tello."""
        if self.send_rc_control:
            self.tello.send_rc_control(self.left_right_velocity, self.for_back_velocity, self.up_down_velocity,
                                       self.yaw_velocity)

def lerp(a,b,c):
    return a + c*(b-a)

def translate(value, leftMin, leftMax, rightMin, rightMax):
    # Figure out how 'wide' each range is
    leftSpan = leftMax - leftMin
    rightSpan = rightMax - rightMin

    # Convert the left range into a 0-1 range (float)
    valueScaled = float(value - leftMin) / float(leftSpan)

    # Convert the 0-1 range into a value in the right range.
    return rightMin + (valueScaled * rightSpan)

def main():
    frontend = FrontEnd()

    # run frontend
    frontend.run()


if __name__ == '__main__':
    main()
