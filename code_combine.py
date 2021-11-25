# import the necessary packages
from scipy.spatial import distance as dist
from imutils.video import VideoStream
from imutils.video import FPS
from imutils import face_utils
import threading
import numpy as np
import RPi.GPIO as GPIO
# import playsound
import argparse
import imutils
import time
import dlib
import cv2

# def sound_alarm(path):
# 	# play an alarm sound
# 	playsound.playsound(path)

def eye_aspect_ratio(eye):
	# compute the euclidean distances between the two sets of
	# vertical eye landmarks (x, y)-coordinates
	A = dist.euclidean(eye[1], eye[5])
	B = dist.euclidean(eye[2], eye[4])
	# compute the euclidean distance between the horizontal
	# eye landmark (x, y)-coordinates
	C = dist.euclidean(eye[0], eye[3])
	# compute the eye aspect ratio
	ear = (A + B) / (2.0 * C)
	# return the eye aspect ratio
	return ear


# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-p", "--shape-predictor", required=True,
	help="path to facial landmark predictor")
# ap.add_argument("-a", "--alarm", type=str, default="",
# 	help="path alarm .WAV file")
ap.add_argument("-w", "--webcam", type=int, default=0,
	help="index of webcam on system")
args = vars(ap.parse_args())

# define two constants, one for the eye aspect ratio to indicate
# blink and then a second constant for the number of consecutive
# frames the eye must be below the threshold for to set off the
# alarm
EYE_AR_THRESH = 0.28
EYE_AR_CONSEC_FRAMES = 12 # utk Raspi
# EYE_AR_CONSEC_FRAMES = 48 # utk Laptop

# pertambahan 0.5 detik = 3 frames --> 12 + 3 = 15
EYE_AR_2ND_CONSEC_FRAMES = 15
# initialize the frame counter as well as a boolean used to
# indicate if the alarm is going off
COUNTER = 0
ALARM_ON = False
ALARM_L2 = False
threadCreated = False
threadRunning = False

# GPIO Buzzer
signal1PIN = 27
signal2PIN = 17
GreenLED = 22
# Set PIN to output
GPIO.setmode(GPIO.BCM)
GPIO.setup(signal1PIN,GPIO.OUT)
GPIO.setup(signal2PIN,GPIO.OUT)
GPIO.setup(GreenLED,GPIO.OUT)


# Functions
def beep_beep_buzzer(pin):
	global ALARM_L2
	while ALARM_L2:
		GPIO.output(pin,1)
		time.sleep(0.1)
		GPIO.output(pin,0)
		time.sleep(0.1)

def level_2_buzzer_active(signal):
	global threadCreated
	global threadRunning
	global ALARM_L2
	if signal == 0:
		GPIO.output(signal2PIN,0)
		ALARM_L2 = False
		threadCreated = False
		threadRunning = False
	if signal == 1:
		ALARM_L2 = True
		GPIO.output(signal1PIN,0)
		if not threadCreated:
			beep_thread = threading.Thread(target=beep_beep_buzzer, args=[signal2PIN])
			threadCreated = True
		if not threadRunning:
			beep_thread.start()
			threadRunning = True


# initialize dlib's face detector (HOG-based) and then create
# the facial landmark predictor
print("[INFO] loading facial landmark predictor...")
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(args["shape_predictor"])

# grab the indexes of the facial landmarks for the left and
# right eye, respectively
(lStart, lEnd) = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"]
(rStart, rEnd) = face_utils.FACIAL_LANDMARKS_IDXS["right_eye"]

# start the video stream thread
print("[INFO] starting video stream thread...")
vs = VideoStream(src=args["webcam"]).start()
print("[INFO] ok")
time.sleep(1.0)

# Penghitung FPS (Frame per Second)
fps = FPS().start()

# loop over frames from the video stream
while True:
	# grab the frame from the threaded video file stream, resize
	# it, and convert it to grayscale
	# channels)
	GPIO.output(GreenLED,1)
	frame = vs.read()
	# cv2.normalize(frame, frame, 0, 255, cv2.NORM_MINMAX)
	frame = imutils.resize(frame, width=450)
	frame = cv2.rotate(frame, cv2.ROTATE_180)
	gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
	# detect faces in the grayscale frame
	rects = detector(gray, 0)

	# check if there's face detected/not
	if (len(rects) == 0):
		ALARM_ON = False
		if ALARM_ON == False :
			GPIO.output(signal1PIN,0)
			level_2_buzzer_active(0)
			# GPIO.output(signal2PIN,0)

  # loop over the face detections
	for rect in rects:
		# determine the facial landmarks for the face region, then
		# convert the facial landmark (x, y)-coordinates to a NumPy
		# array
		shape = predictor(gray, rect)
		shape = face_utils.shape_to_np(shape)
		# extract the left and right eye coordinates, then use the
		# coordinates to compute the eye aspect ratio for both eyes
		leftEye = shape[lStart:lEnd]
		rightEye = shape[rStart:rEnd]
		leftEAR = eye_aspect_ratio(leftEye)
		rightEAR = eye_aspect_ratio(rightEye)
		# average the eye aspect ratio together for both eyes
		ear = (leftEAR + rightEAR) / 2.0



    # compute the convex hull for the left and right eye, then
		# visualize each of the eyes
		leftEyeHull = cv2.convexHull(leftEye)
		rightEyeHull = cv2.convexHull(rightEye)
		cv2.drawContours(frame, [leftEyeHull], -1, (0, 255, 0), 1)
		cv2.drawContours(frame, [rightEyeHull], -1, (0, 255, 0), 1)

    # check to see if the eye aspect ratio is below the blink
		# threshold, and if so, increment the blink frame counter
		# if (ear) :
			# print(ear)
		if ear < EYE_AR_THRESH:
			COUNTER += 1
			# if the eyes were closed for a sufficient number of
			# then sound the alarm
			if COUNTER >= EYE_AR_CONSEC_FRAMES:
				# if the alarm is not on, turn it on
				if not ALARM_ON:
					ALARM_ON = True
					if ALARM_ON == True :
						print('ALARM ON LEVEL 1!!!!!!!!!')
						GPIO.output(signal1PIN,1)
						level_2_buzzer_active(0)
						# GPIO.output(signal2PIN,0)
					
					
				# draw an alarm on the frame
				cv2.putText(frame, "DROWNSINESS ALERT!", (10, 30),
					cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
				
				if COUNTER >= EYE_AR_2ND_CONSEC_FRAMES:
					print('ALARM ON~~~~~~~~~~~~~LEVEL 2')
					level_2_buzzer_active(1)
					# GPIO.output(signal2PIN,1)
				
		# otherwise, the eye aspect ratio is not below the blink
		# threshold, so reset the counter and alarm
		else:
			COUNTER = 0
			ALARM_ON = False
			print('ALARM OFF.')
			if ALARM_ON == False :
				GPIO.output(signal1PIN,0)
				level_2_buzzer_active(0)
				# GPIO.output(signal2PIN,0)





    # draw the computed eye aspect ratio on the frame to help
		# with debugging and setting the correct eye aspect ratio
		# thresholds and frame counters
		cv2.putText(frame, "EAR: {:.3f}".format(ear), (300, 30),
			cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)


	# show the frame
	cv2.imshow("Frame", frame) # comment if debugging is finish
	key = cv2.waitKey(1) & 0xFF

	# if the `q` key was pressed, break from the loop
	if key == 27 or key == ord("q"):
		print("[INFO] exiting...")
		break

	# update FPS
	fps.update()

# tampilkan info FPS
fps.stop()
print("[INFO] elasped time: {:.2f}".format(fps.elapsed()))
print("[INFO] approx. FPS: {:.2f}".format(fps.fps()))

# do a bit of cleanup
GPIO.output(GreenLED,0)
cv2.destroyAllWindows()
GPIO.cleanup()
vs.stop()