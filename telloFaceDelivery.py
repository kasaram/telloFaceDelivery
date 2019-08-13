# Face Tracking Delivery Project
# Based on Jabrils TelloTV Project
# Extended / reworked by Luca Fluri & Dario Breitenstein

from djitellopy import Tello
import face_recognition
import cv2
import numpy as np
import time
import datetime
import os

# Speed of the drone
v_yaw_pitch = 100
v_for_back = 15

# Frames per second of the pygame window display
FPS = 25
dimensions = (960, 720)

# Face Recognition
dario_image = face_recognition.load_image_file("known_faces/dario.png")
dario_face_encoding = face_recognition.face_encodings(dario_image)[0]

# Create arrays of known face encodings and their names
known_face_encodings = [
    dario_face_encoding,
]
known_face_names = [
    "Dario",
]

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

        self.tello.get_battery()

        while not should_stop:
            self.update()

            if frame_read.stopped:
                frame_read.stop()
                break

            frame = cv2.cvtColor(frame_read.frame, cv2.COLOR_BGR2RGB)
            frameRet = frame_read.frame

            vid = self.tello.get_video_capture()

            frame = np.rot90(frame)
            time.sleep(1 / FPS)

            # Listen for key presses
            k = cv2.waitKey(20)

            # Press T to take off
            if k == ord('t'):
                if not args.debug:
                    print("Taking Off")
                    self.tello.takeoff()
                    self.tello.get_battery()

            # Press L to land
            if k == ord('l'):
                if not args.debug:
                    print("Landing")
                    self.tello.land()

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
                    self.for_back_velocity = v_for_back
                elif k == ord('w'):
                    self.for_back_velocity = -v_for_back
                else:
                    self.for_back_velocity = 0

                # e & q to pan right & left
                if k == ord('e'):
                    self.yaw_velocity = v_yaw_pitch
                elif k == ord('q'):
                    self.yaw_velocity = -v_yaw_pitch
                else:
                    self.yaw_velocity = 0

                # space & y to fly up & down
                if k == 32: #space
                    self.up_down_velocity = v_yaw_pitch
                elif k == ord('y'):
                    self.up_down_velocity = -v_yaw_pitch
                else:
                    self.up_down_velocity = 0

                # c & z to fly right & left
                if k == ord('d'):
                    self.left_right_velocity = v_for_back
                elif k == ord('a'):
                    self.left_right_velocity = -v_for_back
                else:
                    self.left_right_velocity = 0

            # Quit the software
            if k == 27: # escape key
                should_stop = True
                break

            # Resize the frame
            capture_divider = 0.5
            rgb_recognition_frame = cv2.resize(frameRet, (0, 0), fx=capture_divider, fy=capture_divider)
            
            face_locations = face_recognition.face_locations(rgb_recognition_frame)
            face_encodings = face_recognition.face_encodings(rgb_recognition_frame, face_locations)
            
            tolerance_x = 50
            tolerance_y = 50
            depth_box_size = 150
            depth_tolerance = 50

            if not OVERRIDE:
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
                    top = int(top * 1/capture_divider)
                    right = int(right * 1/capture_divider)
                    bottom = int(bottom * 1/capture_divider)
                    left = int(left * 1/capture_divider)
            
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

                        close_enough = (right-left) > depth_box_size * 2 - depth_tolerance \
                                        and (right-left) < depth_box_size * 2 + depth_tolerance \
                                        and (bottom-top) > depth_box_size * 2 - depth_tolerance \
                                        and (bottom-top) < depth_box_size * 2 + depth_tolerance

                        # Draw the target zone
                        cv2.rectangle(
                            frameRet,
                            (target_point_x - depth_box_size, target_point_y - depth_box_size),
                            (target_point_x + depth_box_size, target_point_y + depth_box_size),
                            (0, 255, 0) if close_enough else (255, 0, 0), 2)

                        
                        if not target_reached:
                            target_offset_x = target_point_x - heading_point_x
                            target_offset_y = target_point_y - heading_point_y
                            
                            self.yaw_velocity = round(v_yaw_pitch * map_values(target_offset_x, -dimensions[0], dimensions[0], -1, 1))
                            self.up_down_velocity = -round(v_yaw_pitch * map_values(target_offset_y, -dimensions[1], dimensions[1], -1, 1))
                            print("YAW SPEED {} UD SPEED {}".format(self.yaw_velocity, self.up_down_velocity))

                        if not close_enough:
                            depth_offset = (right - left) - depth_box_size * 2
                            if (right - left) > depth_box_size * 1.5 and not target_reached:
                                self.for_back_velocity = 0
                            else:
                                self.for_back_velocity = -round(v_for_back * map_values(depth_offset, -depth_box_size, depth_box_size, -1, 1))
                        else:
                            self.for_back_velocity = 0
  
                # No Faces
                if len(face_encodings) == 0:
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
        self.tello.send_rc_control(self.left_right_velocity, self.for_back_velocity, self.up_down_velocity,
                                    self.yaw_velocity)

def lerp(a,b,c):
    return a + c*(b-a)

def map_values(value, leftMin, leftMax, rightMin, rightMax):
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