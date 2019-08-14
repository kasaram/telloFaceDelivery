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
import shutil
import uuid

# Speed of the drone
v_yaw_pitch = 100
v_for_back = 15

# Tracking tolerances
tolerance_x = 50
tolerance_y = 50
depth_box_size = 150
depth_tolerance = 50

# Frames per second of the pygame window display
FPS = 25
dimensions = (960, 720)



# Face Recognition
unknown_face_name = "unknown"

# Create arrays of known face encodings and their names

known_face_encodings = []
known_face_names = []

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

        # Enroll mode: Try to find new faces
        self.enroll_mode = False

    def run(self):
        addAllFaces()

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
                print("Taking Off")
                self.tello.takeoff()
                self.tello.get_battery()

            # Press L to land
            if k == ord('l'):
                print("Landing")
                self.tello.land()

            # Press o for controls override
            if k == ord('o'):
                if not OVERRIDE:
                    OVERRIDE = True
                    print("OVERRIDE ENABLED")
                else:
                    OVERRIDE = False
                    print("OVERRIDE DISABLED")
            
            # g to toggle to enroll mode
            if k == ord('v'):
                if self.enroll_mode:
                    print("ENROLL MODE OFF")
                    self.enroll_mode = False
                else:
                    print("ENROLL MODE ON")
                    self.enroll_mode = True

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

                # d & a to fly right & left
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
            recognition_frame = cv2.resize(frameRet, (0, 0), fx=capture_divider, fy=capture_divider) #BGR is used, not RGB
            
            if self.enroll_mode: capture_frame = frameRet.copy()

            # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
            # recognition_frame = bgr_recognition_frame[:, :, ::-1]
            
            face_locations = face_recognition.face_locations(recognition_frame)
            face_encodings = face_recognition.face_encodings(recognition_frame, face_locations)

            if not OVERRIDE:
                face_locked = False

        
                for (top, right, bottom, left), name in detect_faces(face_locations, face_encodings):
                    # Scale back up face locations since the frame we detected in was scaled to 1/4 size
                    top = int(top * 1/capture_divider)
                    right = int(right * 1/capture_divider)
                    bottom = int(bottom * 1/capture_divider)
                    left = int(left * 1/capture_divider)
                    
                    x = left
                    y = top
                    w = right - left
                    h = bottom - top

                    # Draw a box around the face
                    cv2.rectangle(frameRet, (left, top), (right, bottom), (0, 0, 255), 2)

                    if name is not unknown_face_name:
                        # Draw a label with a name below the face
                        cv2.rectangle(frameRet, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
                        font = cv2.FONT_HERSHEY_DUPLEX
                        cv2.putText(frameRet, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

                    if self.enroll_mode:
                        if name is unknown_face_name:
                            target_reached = self.approach_target(frameRet, top,right, bottom, left)

                            if target_reached:
                                newUUID = uuid.uuid4()
                                newFacePath = "new_faces/{}.png".format(newUUID)
                                roi = capture_frame[y:y+h, x:x+w]
                                cv2.imwrite(newFacePath, roi)
        
                                if addFace(newFacePath, str(newUUID)):
                                    shutil.copy2(newFacePath, "known_faces/{}.png".format(newUUID))
                            break
                    else:
                        if name is not unknown_face_name:
                            target_reached = self.approach_target(frameRet, top,right, bottom, left)
                            break

                # No Faces
                
                if len(face_encodings) == 0:
                    print("no faces")
                    #turn while no face detected
                                
                    self.yaw_velocity = 10
                    self.up_down_velocity = 0
                    self.for_back_velocity = 0

            # Display the resulting frame
            cv2.imshow(f'Tello Tracking...',frameRet)

        # On exit, print the battery
        self.tello.get_battery()

        # When everything done, release the capture
        cv2.destroyAllWindows()
        
        # Call it always before finishing. I deallocate resources.
        self.tello.end()
    
    
    def approach_target(self, frameRet, top, right, bottom, left):
        x = left
        y = top
        w = right - left
        h = bottom - top
    
        # The Center point of our Target
        target_point_x = int(left + (w/2))
        target_point_y = int(top  + (h/2))
    
        # Draw the target point
        cv2.circle(frameRet,
            (target_point_x, target_point_y),
            10, (0, 255, 0), 2)
    
        # The Center Point of the drone's view
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
        
        return target_reached and close_enough
    
    def battery(self):
        return self.tello.get_battery()[:2]

    def update(self):
        """ Update routine. Send velocities to Tello."""
        self.tello.send_rc_control(self.left_right_velocity, self.for_back_velocity, self.up_down_velocity,
                                    self.yaw_velocity)

def detect_faces(face_locations, face_encodings):
    face_names = []
    for face_encoding in face_encodings:
        # See if the face is a match for the known face(s)
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
        name = unknown_face_name


        # Use the known face with the smallest distance to the new face
        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
        best_match_index = np.argmin(face_distances)
        if matches[best_match_index]:
            name = known_face_names[best_match_index] 
        
        face_names.append(name)
    
    return zip(face_locations, face_names)

def lerp(a,b,c):
    return a + c*(b-a)

def addFace(file, name):
    face_img = face_recognition.load_image_file(file)
    face_encodings = face_recognition.face_encodings(face_img)

    if len(face_encodings) > 0:
        known_face_encodings.append(face_encodings[0])   
        known_face_names.append(name)
        return True
    return False

def addAllFaces():
    for face in os.listdir("known_faces/"):
        print(face[:-4])
        addFace("known_faces/" + face, face[:-4])
    
    for file in os.listdir("new_faces/"):
        os.remove("new_faces/" + file)

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
