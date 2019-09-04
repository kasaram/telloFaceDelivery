# Tello Face Tracking Delivery System

### Project for the ws2C Workshop @ FHNW 2019

Initially based on Jabrils [TelloTV](https://github.com/Jabrils/TelloTV) Project, but then completely reworked.

The Drone recognises faces with the [face_recognition](https://github.com/ageitgey/face_recognition) python module. Known Faces are saved in the known_faces folder. These are loaded on startup.

Via a flask webserver, the drone can be controlled via an interface on localhost:5000.

#### Modes

**Enroll Mode**: Targets the first face the program does not know and positions itself in front of it to take a picture and add it the known_faces folder

**Autonomous Mode**: The drone follows the first face it knows and positions itself in front of it. When a target face is selected in the interface, the drone ignores all other known faces and targets only the target.

