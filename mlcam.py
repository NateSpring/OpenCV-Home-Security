import cv2
import os
import imutils
import datetime
import time
import asyncio
import smtplib, ssl
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from os.path import basename
from threading import Thread
import queue
q=queue.Queue()


firstFrame = None
motion = 0
rec = False
frame_no = 0
start = 0

def Rec():
    global frame_no, out, width, height, fourcc
    cap = cv2.VideoCapture("rtsp://192.168.0.22/ch0_1.h264")
    width  = int(cap.get(3))
    height = int(cap.get(4))
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter('saved-images/output.avi', fourcc, 20, (width, height))

    while True:
        if not os.path.exists('saved-images/output.avi'):
            out = cv2.VideoWriter('saved-images/output.avi', fourcc, 20, (width, height))
        status, img = cap.read()
        if not status:
            print('Img Error:{}'.format(datetime.datetime.now().strftime("%I:%M:%S%p")))
            cap = cv2.VideoCapture("rtsp://192.168.0.22/ch0_1.h264")
            continue
        q.put(img)
                

def Dis():
    print('**Running OCV**')
    print('Stream: Start')
    global firstFrame, motion, rec, imgHUD
    while True:
        try:
            if q.empty() != True:
                img = q.get()
                img = imutils.resize(img, width=640, height=480)
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                gray = cv2.GaussianBlur(gray, (7, 7), 0)
                if firstFrame is None:
                    firstFrame = gray
                    continue
                frameDelta = cv2.absdiff(firstFrame, gray)
                thresh = cv2.threshold(frameDelta, 50, 255, cv2.THRESH_BINARY)[1]
                thresh = cv2.dilate(thresh, None, iterations=2)
                cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cnts = imutils.grab_contours(cnts)

                for c in cnts:
                    if cv2.contourArea(c) < 2000:
                        continue
                    (x, y, w, h) = cv2.boundingRect(c)
                    text = "Motion Detected"
                    cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(
                            img,
                            "Status: {}".format(text),
                            (10, 20),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            .75,
                            (0, 255,0),
                            2,
                        )
                    cv2.putText(
                            img,
                            datetime.datetime.now().strftime("%A %d %B %Y %I:%M:%S%p"),
                            (10, img.shape[0] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            .75,
                            (0, 255, 0),
                            2,
                        )
                    # Movement Timer / Recorder 
                    motion +=1
                    out.write(img)
                
                cv2.putText(
                            img,
                            "Status: None",
                            (10, 20),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            .75,
                            (0, 255,0),
                            2,
                        )
                cv2.putText(
                            img,
                            datetime.datetime.now().strftime("%A %d %B %Y %I:%M:%S%p"),
                            (10, img.shape[0] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            .75,
                            (0, 255, 0),
                            2,
                        )
                imgHUD = img
                if motion >= 500:
                        out.release()
                        email_alert()
                        # record()
                        rec = True
                        firstFrame = None
                        motion = 0

                # cv2.imshow("Security Feed", img)
                cv2.waitKey(1)
        except AttributeError as e:
            print('{} @ {}'.format(e, datetime.datetime.now().strftime("%I:%M:%S%p")
))


def record():
    global out, rec, fourcc, width, height, imgHUD
    print('Recording: Start')
    start_time = time.time()
    while True:
        out.write(imgHUD)
        # print('Recording:{}'.format(int(time.time() - start_time)))
        if (int(time.time() - start_time) > 10):
            print('Recording: Stop')
            out.release()
            rec = False
            email_alert()
            break


def email_alert():
    global filename
    msg = MIMEMultipart()
    msg['Subject'] = 'Motion Detected'
    msg['From'] = "CV Cam"
    msg['To'] = 'natespring92@gmail.com'
    msg.attach(MIMEText('Motion Detected - {}'.format(datetime.datetime.now().strftime("%I:%M:%S%p"))))
    with open('saved-images/output.avi', "rb") as fil: 
        ext = 'saved-images/output.avi'.split('.')[-1:]
        attachedfile = MIMEApplication(fil.read(), _subtype = ext)
        attachedfile.add_header(
                'content-disposition', 'attachment', filename=basename('saved-images/output.avi') )
        msg.attach(attachedfile)
    # Send the message via our own SMTP server.
    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.login("email@gmail.com", "pass")
    server.send_message(msg)
    server.quit()
    print('Email: Sent')
    # os.remove('saved_images/image.jpg')
    os.remove('saved-images/output.avi')
    print('Stored Images/Video: Removed')


# Search email inbox
def search_boxes():
    global start, img, rec
    mail = imaplib.IMAP4_SSL(host='smtp.gmail.com')
    mail.login("email@gmail.com", "pass")
    mail.select()  # Default is `INBOX`
    n=0
    (retcode, messages) = mail.search(None, '(UNSEEN)')
    if retcode == 'OK':
        for num in messages[0].split() :
            print('Email: Processing...')
            n=n+1
            typ, data = mail.fetch(num,'(RFC822)')
            for response_part in data:
                if isinstance(response_part, tuple):
                    message = email.message_from_bytes(data[0][1])
                    if message['Subject'] == 'See':
                        print('Email: Read!')
                        record()
                        
                    typ, data = mail.store(num,'+FLAGS','\\Seen')
        # print('Unseen Emails:',n)


# Loop to read emails
def read_email():
    while True:
        search_boxes()
        time.sleep(10)


# Threading
if __name__ == '__main__':
    print('***** Starting Cam @ {})'.format(datetime.datetime.now().strftime("%I:%M:%S%p")))

    p1=Thread(target=Rec)
    p2=Thread(target=Dis)
    p3=Thread(target=read_email)

    p1.start()
    p2.start()
    p3.start()
