# This is a demo of running face recognition on a Raspberry Pi.
# This program will print out the names of anyone it recognizes to the console.

# To run this, you need a Raspberry Pi 2 (or greater) with face_recognition and
# the picamera[array] module installed.
# You can follow this installation instructions to get your RPi set up:
# https://gist.github.com/ageitgey/1ac8dbe8572f3f533df6269dab35df65

import face_recognition
import picamera
import numpy as np
from pirc522 import RFID
import signal
import time
import os
import telepot
from PIL import Image
import RPi.GPIO as GPIO

# Get a reference to the Raspberry Pi camera.
# If this fails, make sure you have a camera connected to the RPi and that you
# enabled your camera in raspi-config and rebooted first.
camera = picamera.PiCamera()
camera.resolution = (320, 240)
output = np.empty((240, 320, 3), dtype=np.uint8)

rdr = RFID()

# to use Raspberry Pi board pin numbers
GPIO.setmode(GPIO.BOARD)
# set up GPIO output channel
GPIO.setup(11, GPIO.OUT)
GPIO.setup(12,GPIO.OUT)
GPIO.setup(13,GPIO.OUT)
GPIO.setup(15,GPIO.OUT)

bot = telepot.Bot('495441198:AAGzOjNR6sVG58xcdfWL2uZ56unCJ77ZHl8')

path = '/home/pi/dlib/face_recognition/examples/facerec/'

try:
    # Load a sample picture and learn how to recognize it.
    print("Loading known face image(s)")
    encodings = list()
    names = list()
    for file in os.listdir(path + 'photos'):
        if file.endswith('.jpg'):
            image = face_recognition.load_image_file(path + 'photos/' + file)
            encodings.append(face_recognition.face_encodings(image)[0])
            names.append(file.split('.')[0])

    # Initialize some variables
    face_locations = []
    face_encodings = []
    bot.sendMessage(451158714, "System is ready.")
    while True:
        id_file = open(path + 'id.txt','r+')
        lines = id_file.readlines()
        print("Tag is being waited...")
        rdr.wait_for_tag()
        (error, data) = rdr.request()
        check = True
        while error==True:
            if check:
                print("Bring the tag closer.")
                check = False
            rdr.wait_for_tag()
            (error, data) = rdr.request()
        if not error:
            print("Tag detected!")
            (error, uid) = rdr.anticoll()
            check = True
            while error==True:
                if check:
                    print("Bring the tag closer.")
                    check = False
                (error, uid) = rdr.anticoll()
            if not error:
                person_uid = uid
                print(uid)
                if not rdr.select_tag(uid):
                    if not rdr.card_auth(rdr.auth_a, 10, [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF], uid):
                        rdr.stop_crypto()
                        
        count = 0
        for line in lines:
            if str(person_uid) in line:
                count = 1
                uid_name = line.split('] ')[1]
                uid_name = uid_name.split('\n')[0]
                index = names.index(uid_name)
                break
        
        if count==0:
            print("Unauthorized card!")
            GPIO.output(11,True)
            cond2 = True
            while cond2:
                print("Capturing image.")
                camera.capture(output, format="rgb")
                face_locations = face_recognition.face_locations(output)
                face_encodings = face_recognition.face_encodings(output, face_locations)
                print("Found {} faces in image.".format(len(face_locations)))
                if len(face_encodings)>1:
                    print("There are more than one person!")
                    cond2 = True
                elif len(face_encodings)==0:
                    print("No faces detected!")
                    cond2 = True
                else:
                    GPIO.output(15,True)
                    im = Image.fromarray(output)
                    im.save("/home/pi/new.jpg")
                    response = bot.getUpdates()
                    length = len(response)
                    f = open('/home/pi/new.jpg', 'rb')
                    bot.sendPhoto(451158714, f)
                    f.close()
                    bot.sendMessage(451158714, 'Do you want to add this to database? Yes or No?')
                    c = ""
                    while (len(response)==length)or((c!="Yes")and(c!="No")):
                        response = bot.getUpdates()
                        if (len(response)!=0):
                            newLength = len(response)
                            a = response[newLength-1]
                            b = a["message"]
                            c = b["text"]
                    print(c)
                    if c=="Yes":
                        response = bot.getUpdates()
                        length = len(response)
                        bot.sendMessage(451158714,"What's his/her name?")
                        while (len(response)==length):
                            response = bot.getUpdates()
                            if (len(response)!=0):
                                newLength = len(response)
                                a = response[newLength-1]
                                b = a["message"]
                                c = b["text"]
                        print(c)
                        os.rename('/home/pi/new.jpg', path +'photos/{}.jpg'.format(c))
                        encodings.append(face_encodings[0])
                        names.append(c)
                        id_file.write(str(person_uid) + ' ' + c + '\n')
                        id_file.close()
                    else:
                        GPIO.output(15,False)
                        GPIO.output(13,True)
                    cond2 = False
            cond = False
        else:
            GPIO.output(12,True)
            cond = True
        
        while cond:
            print("Capturing image.")
            # Grab a single frame of video from the RPi camera as a numpy array
            camera.capture(output, format="rgb")

            # Find all the faces and face encodings in the current frame of video
            face_locations = face_recognition.face_locations(output)
            print("Found {} faces in image.".format(len(face_locations)))
            face_encodings = face_recognition.face_encodings(output, face_locations)
                
            if len(face_encodings)>1:
                print("There are more than one person!")
                cond = True
            elif len(face_encodings)==0:
                print("No faces detected!")
                cond = True
            else:
                cond = False
                match = face_recognition.compare_faces([encodings[index]], face_encodings[0])
                if match[0]:
                    GPIO.output(15,True)
                    print("Access granted, welcome {}".format(uid_name))
                    localtime = time.asctime(time.localtime(time.time()))
                    min = localtime.split(':')[1]
                    x = localtime.split(':')[0]
                    x_len = len(x)
                    hour = x[x_len-2]+x[x_len-1]
                    clock = hour + ':' + min
                    bot.sendMessage(451158714, "{} came at {}.".format(uid_name,clock))
                else:
                    GPIO.output(13,True)
                    print("Access denied!")
                    im = Image.fromarray(output)
                    im.save("/home/pi/new.jpg")
                    f = open('/home/pi/new.jpg', 'rb')
                    bot.sendPhoto(451158714, f)
                    f.close()
                    bot.sendMessage(451158714, "This person tried to enter with {}'s card.".format(uid_name))
        time.sleep(3)
        GPIO.output(11,False)
        GPIO.output(12,False)
        GPIO.output(13,False)
        GPIO.output(15,False)
except:
    GPIO.output(11,False)
    GPIO.output(12,False)
    GPIO.output(13,False)
    GPIO.output(15,False)
    bot.sendMessage(451158714, "The system has been shutted down.")
finally:
    GPIO.cleanup()
    rdr.cleanup()