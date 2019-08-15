# Face Tracking Delivery Project
# Based on Jabrils TelloTV Project
# Extended / reworked by Luca Fluri & Dario Breitenstein

from djitellopy import Tello
import face_recognition
import cv2
import numpy as np
import datetime
import os
import shutil
import uuid

# Speed of the drone
v_yaw_pitch = 100
v_for_back = 15
v_override = 50

# Tracking tolerances
tolerance_x = 50
tolerance_y = 50
depth_box_size = 150
depth_tolerance = 50

detection_wait_interval = 10

# Frames per second of the window display
FPS = 25
dimensions = (960, 720)

# Face Recognition
unknown_face_name = "unknown"
target_name = ""

class DroneControl(object):
    def __init__(self):
        # Init Tello object that interacts with the Tello drone
        self.tello = Tello()

        # Drone velocities between -100~100
        self.for_back_velocity = 0
        self.left_right_velocity = 0
        self.up_down_velocity = 0
        self.yaw_velocity = 0
        self.speed = 10

        # Autonomous mode: Navigate autonomously
        self.autonomous = True

        # Enroll mode: Try to find new faces
        self.enroll_mode = False

        # Create arrays of known face encodings and their names
        self.known_face_encodings = []
        self.known_face_names = []

        # Logic used for navigation
        self.face_locations = None
        self.face_encodings = None    
        self.target_name = ""
        self.has_face = False    
        self.detect_faces = True
        self.wait = 0

        self.load_all_faces()

        if not self.tello.connect():
            print("Tello not connected")
            raise Exception("Tello not connected")

        if not self.tello.set_speed(self.speed):
            print("Not set speed to lowest possible")
            raise Exception("Not set speed to lowest possible")

        # In case streaming is on. This happens when we quit this program without the escape key.
        if not self.tello.streamoff():
            print("Could not stop video stream")
            raise Exception("Could not stop video stream")

        if not self.tello.streamon():
            print("Could not start video stream")
            raise Exception("Could not start video stream")
    
    def loop(self):
        self.update_rc_control()

        if self.tello.get_frame_read().stopped:
            self.tello.get_frame_read().stop()
            self.shutdown()

        video_frame = self.tello.get_frame_read().frame

        # Resize the frame
        capture_divider = 0.5
        recognition_frame = cv2.resize(video_frame, (0, 0), fx=capture_divider, fy=capture_divider) #BGR is used, not RGB
        
        # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
        # recognition_frame = bgr_recognition_frame[:, :, ::-1]

        # Copy of the frame for capturing faces
        if self.enroll_mode:
            capture_frame = video_frame.copy()

        # Only detect faces every other frame
        if self.detect_faces:
            self.face_locations = face_recognition.face_locations(recognition_frame)
            self.face_encodings = face_recognition.face_encodings(recognition_frame, self.face_locations)
            self.detect_faces = False
        else:
            self.detect_faces = True

        # Navigate Autonomously
        if self.autonomous:
            # Loop through detected faces
            for (top, right, bottom, left), name in self.identify_faces(self.face_locations, self.face_encodings):
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
                    cv2.rectangle(video_frame, (left, top), (right, bottom), (0, 0, 255), 2)

                    if name is not unknown_face_name:
                        # Draw a label with a name below the face
                        font = cv2.FONT_HERSHEY_DUPLEX
                        cv2.rectangle(video_frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
                        cv2.putText(video_frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

                    if self.enroll_mode:
                        if name is unknown_face_name:
                            target_reached = self.approach_target(video_frame, top,right, bottom, left)

                            if target_reached:
                                newUUID = uuid.uuid4()
                                newFacePath = "new_faces/{}.png".format(newUUID)
                                roi = capture_frame[y:y+h, x:x+w]
                                cv2.imwrite(newFacePath, roi)
        
                                if self.load_face(newFacePath, str(newUUID)):
                                    shutil.copy2(newFacePath, "known_faces/{}.png".format(newUUID))
                            break
                    elif (self.target_name and name is self.target_name) or (name is not unknown_face_name):
                        target_reached = self.approach_target(video_frame, top,right, bottom, left)
                        break

            # No Faces / Face lost
            if len(self.face_encodings) == 0:
                # Wait for a bit if the stream has collapsed
                if self.wait >= detection_wait_interval:
                    self.wait = 0
                    
                    if self.has_face:
                        # Go back and down to try to find the face again
                        self.has_face = False
                        self.up_down_velocity = -30
                        self.for_back_velocity = -20
                    else:
                        # Turn to find any face
                        self.yaw_velocity = 25
                        self.up_down_velocity = 0
                        self.for_back_velocity = 0
                else:
                    self.wait += 1

        # Show video stream
        cv2.imshow("Tello Drone Delivery", video_frame)
            
    def shutdown(self):
        # On exit, print the battery
        print(self.get_battery())

        # When everything done, release the capture
        cv2.destroyAllWindows()
        
        # Call it always before finishing. I deallocate resources.
        self.tello.end()
    
    def update_rc_control(self):
        """ Update routine. Send velocities to Tello."""
        self.tello.send_rc_control(
            self.left_right_velocity,
            self.for_back_velocity,
            self.up_down_velocity,
            self.yaw_velocity)

    def get_battery(self):
        """ Get Tello battery state """
        return self.tello.get_battery()[:2]

    def load_face(self, file, name):
        """ Load and enroll a face from the File System """
        face_img = face_recognition.load_image_file(file)
        face_encodings = face_recognition.face_encodings(face_img)

        if len(face_encodings) > 0:
            self.known_face_encodings.append(face_encodings[0])   
            self.known_face_names.append(name)
            return True
        return False

    def load_all_faces(self):
        """ Load and enroll all faces from the known_faces folder, then clear out the new_faces folder """
        for face in os.listdir("known_faces/"):
            print(face[:-4])
            self.load_face("known_faces/" + face, face[:-4])
        
        for file in os.listdir("new_faces/"):
            os.remove("new_faces/" + file)

    def identify_faces(self, face_locations, face_encodings):
        """ Identify known faces from face encodings """
        face_names = []
        for face_encoding in face_encodings:
            # See if the face is a match for the known face(s)
            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
            name = unknown_face_name

            # Use the known face with the smallest distance to the new face
            face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = self.known_face_names[best_match_index] 
            
            face_names.append(name)
        
        return zip(face_locations, face_names)

    def approach_target(self, video_frame, top, right, bottom, left):
        """ The main navigation algorithm """
        x = left
        y = top
        w = right - left
        h = bottom - top
        
        self.has_face = True

        # The Center point of our Target
        target_point_x = int(left + (w/2))
        target_point_y = int(top  + (h/2))
    
        # Draw the target point
        cv2.circle(video_frame,
            (target_point_x, target_point_y),
            10, (0, 255, 0), 2)
    
        # The Center Point of the drone's view
        heading_point_x = int(dimensions[0] / 2)
        heading_point_y = int(dimensions[1] / 2)
    
        # Draw the heading point
        cv2.circle(
            video_frame,
            (heading_point_x, heading_point_y),
            5, (0, 0, 255), 2)
    
        target_reached = heading_point_x >= (target_point_x - tolerance_x) \
                        and heading_point_x <= (target_point_x + tolerance_x) \
                        and heading_point_y >= (target_point_y - tolerance_y) \
                        and heading_point_y <= (target_point_y + tolerance_y)
    
        # Draw the target zone
        cv2.rectangle(
            video_frame,
            (target_point_x - tolerance_x, target_point_y - tolerance_y),
            (target_point_x + tolerance_x, target_point_y + tolerance_y),
            (0, 255, 0) if target_reached else (0, 255, 255), 2)
    
        close_enough = (right-left) > depth_box_size * 2 - depth_tolerance \
                        and (right-left) < depth_box_size * 2 + depth_tolerance \
                        and (bottom-top) > depth_box_size * 2 - depth_tolerance \
                        and (bottom-top) < depth_box_size * 2 + depth_tolerance
    
        # Draw the target zone
        cv2.rectangle(
        video_frame,
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

    def take_off(self):
        self.tello.takeoff()
    
    def land(self):
        self.tello.land()

    def set_autonomous(self, autonomous): self.autonomous = autonomous
    def set_enroll_mode(self, enroll_mode): self.enroll_mode = enroll_mode
    def set_target_name(self, target_name): self.target_name = target_name
    def set_for_back_velocity(self, for_back_velocity): self.for_back_velocity = for_back_velocity
    def set_left_right_velocity(self, left_right_velocity): self.left_right_velocity = left_right_velocity
    def set_up_down_velocity(self, up_down_velocity): self.up_down_velocity = up_down_velocity
    def set_yaw_velocity(self, yaw_velocity): self.yaw_velocity = yaw_velocity

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
    try:
        drone = DroneControl()
        
        should_exit = False
        manual_override = False
        while not should_exit:
            drone.loop()

            k = cv2.waitKey(20)
            
            # Press T to take off
            if k == ord('t'):
                print("Taking Off")
                drone.take_off()
                print(drone.get_battery())

            # Press L to land
            if k == ord('l'):
                print("Landing")
                drone.land()

            # Press o for controls override
            if k == ord('o'):
                if not manual_override:
                    manual_override = True
                    drone.set_autonomous(False)
                    
                    print("OVERRIDE ENABLED")
                else:
                    manual_override = False
                    drone.set_autonomous(True)

                    print("OVERRIDE DISABLED")
            
            # g to toggle to enroll mode
            if k == ord('v'):
                if drone.enroll_mode:
                    drone.set_enroll_mode(False)
                    print("ENROLL MODE OFF")
                else:
                    drone.set_enroll_mode(True)
                    print("ENROLL MODE ON")
            
            # esc to exit
            if k == 27:
                should_exit = True

            if manual_override:
                if k == ord('w'):
                    drone.set_for_back_velocity(v_override)
                elif k == ord('s'):
                    drone.set_for_back_velocity(-v_override)
                else:
                    drone.set_for_back_velocity(0)

                if k == ord('d'):
                    drone.set_left_right_velocity(v_override)
                elif k == ord('a'):
                    drone.set_left_right_velocity(-v_override)
                else:
                    drone.set_left_right_velocity(0)

                if k == ord('r'):
                    drone.set_up_down_velocity(v_override)
                elif k == ord('f'):
                    drone.set_up_down_velocity(-v_override)
                else:
                    drone.set_up_down_velocity(0)
                
                if k == ord('e'):
                    drone.set_yaw_velocity(v_yaw_pitch)
                elif k == ord('q'):
                    drone.set_yaw_velocity(-v_yaw_pitch)
                else:
                    drone.set_yaw_velocity(0)

        drone.shutdown()
    except Exception as e:
        print(e)

if __name__ == '__main__':
    main()
