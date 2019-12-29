#!/usr/bin/python
# -*- coding: utf-8 -*-
#==========================================================
# gmailで操作するルームモニターシステム
#==========================================================
import subprocess
import sys
import re
import time
import datetime
import picamera
import os
import shutil

import RPi.GPIO as GPIO

import email
from email import encoders
from email.header import Header
from email.header import decode_header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import utils
from imaplib import IMAP4_SSL
from smtplib import SMTP_SSL

import base64

import pandas as pd
import matplotlib
matplotlib.use('Agg') # not use the Xwindows backend
import matplotlib.pyplot as plt

import sqlite3


#------#
# 引数 #
#------#
argv = sys.argv
argc = len(argv)
direct_address = ""
graph = ""

if argc == 2:
    direct_address = argv[1]

if argc == 3:
    if argv[1] == "-day-graph" or argv[1] == "-month-graph" or argv[1] == "-year-graph":
        graph = argv[1]
    direct_address = argv[2]

#--------#
# 設定値 #
#--------#
d       = datetime.datetime.today()
year    = d.strftime("%Y")
month   = d.strftime("%m")
day     = d.strftime("%d")
now     = d.strftime("%Y%m%d%H%M%S")

LOGIN_USERNAME = "*** gmail-address ***"            # gmailアドレス
LOGIN_PASSWORD = "*** application-password ***"     # アプリパスワード

USER_ADDRESS = ["*** controler-mail-address1 ***", "*** controler-mail-address2 ***"] #操作対象の送信元アドレス

MIME_IMAGE      =  {'type':'image', 'subtype':'jpeg'}
MIME_VIDEO      =  {'type':'video', 'subtype':'mp4'}
ATTACH_PICTURE  =  {'name':now + '.jpg', 'path':'***gmail_camera***/picture/picture.jpg'}
ATTACH_GRAPH    =  {'name':now + '.jpg', 'path':'***gmail_camera***/graph/sensor.jpg'}
ATTACH_VIDEO    =  {'name':now + '.mp4', 'path':'***gmail_camera***/video/video.mp4'}

EMAIL_SUBJECT1  = u"gmail_camera@xxx"
EMAIL_SUBJECT2  = u"gmail_sensor@xxx"
EMAIL_BODY      = u""

TRIGGER_KEYWORD = r'カメラロ'

PICTURE_WIDTH   = 720
PICTURE_HEIGHT  = 960

VIDEO_WIDTH     = 240
VIDEO_HEIGHT    = 320

CAMERA_MIN_TILT     = 50
CAMERA_MAX_TILT     = 110
CAMERA_INIT_TILT    = int((CAMERA_MIN_TILT + CAMERA_MAX_TILT)/2)
CAMERA_MIN_PAN      = 30
CAMERA_MAX_PAN      = 100
CAMERA_INIT_PAN     = int((CAMERA_MIN_PAN + CAMERA_MAX_PAN)/2)

GPIO_T_SERVO_PIN = 18
GPIO_P_SERVO_PIN = 23

DBNAME = './record/db/info.db'

VIDEO_STORE = 'xxx'

#------------------#
# 監視カメラクラス #
#------------------#
class gmail_camera(object):

    #--------------------------#
    # クライアント処理の初期化 #
    #--------------------------#
    def __init__(self, user, password):
        self.user = user
        self.password = password
        self.smtp_host = 'smtp.gmail.com'
        self.smtp_port = 465
        self.imap_host = 'imap.gmail.com'
        self.imap_port = 993
        self.email_default_encoding = 'iso-2022-jp'
        self.email = ""
        self.camera = 0

    #------#
    # 監視 #
    #------#
    def monitor(self, address):
        print("")
        print("[%s]" % address)

        # ユーザからのメールを検索
        if argc != 2:
            self.search_email(address)

            print("from_address  = %s" % self.email['from_address'])
            print("to_addresses  = %s" % self.email['to_addresses'])
            print("cc_addresses  = %s" % self.email['cc_addresses'])
            print("bcc_addresses = %s" % self.email['bcc_addresses'])
            print("date          = %s" % self.email['date'])
            print("subject       = %s" % self.email['subject'])
            print("body          = %s" % self.email['body'])
            print("enable_camera = %s" % self.enable_camera)
        else:
            self.enable_camera = 1

        # カメラ起動命令を本文に含む場合
        if self.enable_camera:
            command = {
                    'control'   : 'pan',
                    'up'        : 0,
                    'down'      : 0,
                    'left'      : 0,
                    'right'     : 0,
                    'option'    : 0,
            }

            # コマンド解析
            if argc != 2:
                command = self.parse_command()

            print("control       = %s" % command['control'])
            print("up            = %s" % command['up'])
            print("down          = %s" % command['down'])
            print("left          = %s" % command['left'])
            print("right         = %s" % command['right'])
            print("option        = %s" % command['option'])

            mode = ""

            # カメラ撮影
            if command['control'] == 'none':
                # 写真
                self.picamera_picture(
                        command['up'],
                        command['down'],
                        command['left'],
                        command['right'],
                )
                mode = "picture"

            else:
                # ビデオ
                self.picamera_video(
                        command['up'],
                        command['down'],
                        command['left'],
                        command['right'],
                        command['control'],
                )
                mode = "video"

            # DB取得
            conn = sqlite3.connect(DBNAME)
            c = conn.cursor()

            rows = c.execute("SELECT * FROM info ORDER BY datetime DESC LIMIT 1;")

            dtime   = ''
            temp    = ''
            humi    = ''
            part    = ''
            cpu_r   = ''
            cpu_t   = ''
            mem_u   = ''
            mem_f   = ''
            disk_u  = ''
            disk_f  = ''

            for row in rows:
                dtime   = row[0]
                temp    = "{:.1f}".format(row[1])
                humi    = "{:.1f}".format(row[2])
                part    = "{:.1f}".format(row[3])
                cpu_r   = "{:.1f}".format(row[4])
                cpu_t   = "{:.1f}".format(row[5])
                mem_u   = "{:.1f}".format(row[6])
                mem_f   = "{:.1f}".format(row[7])
                disk_u  = "{:.1f}".format(row[8])
                disk_f  = "{:.1f}".format(row[9])

                print("datetiem=", dtime, " temp=", temp, "'C humi=", humi, "%")

            conn.close()

            # メール送信
            email_body = EMAIL_BODY

            if argc == 2:
                email_body = email_body + u"定期送信\n"

            if command['option'] != 1:
                email_body = email_body + u"温度 : " + str(temp) + u"'C\n"
                email_body = email_body + u"湿度 : " + str(humi) + u"%\n"
                email_body = email_body + u"粒子 : " + str(part)   + u"ug/m^3\n"
            else:
                email_body = email_body + u"温度 : " + str(temp)   + u"'C\n"
                email_body = email_body + u"湿度 : " + str(humi)   + u"%\n"
                email_body = email_body + u"粒子 : " + str(part)   + u"ug/m^3\n"
                email_body = email_body + u"\n"
                email_body = email_body + u"CPU使用 : " + str(cpu_r)  + u"%\n"
                email_body = email_body + u"CPU温度 : " + str(cpu_t)  + u"'C\n"
                email_body = email_body + u"\n"
                email_body = email_body + u"Mem使用 : " + str(mem_u)  + u"M\n"
                email_body = email_body + u"Mem空き : " + str(mem_f)  + u"M\n"
                email_body = email_body + u"\n"
                email_body = email_body + u"Disk使用 : " + str(disk_u) + u"G\n"
                email_body = email_body + u"Disk空き : " + str(disk_f) + u"G\n"

            print("send_email")
            self.send_email(
                    LOGIN_USERNAME,
                    [address],
                    None,
                    None,
                    EMAIL_SUBJECT1,
                    email_body,
                    mode,
            )

    #----------------------------------#
    # ユーザからの受信メールをチェック #
    #----------------------------------#
    def search_email(self, from_address):
        try:
            # 受信サーバアクセス
            conn = IMAP4_SSL(self.imap_host, self.imap_port)
            conn.login(self.user, self.password)

            # 受信トレイ検索
            conn.list()
            conn.select('inbox')

            # 特定の送信者アドレスのメールを取得
            typ, data = conn.search(None, '(ALL HEADER FROM "%s")' % from_address)

            ids = data[0].split()
            self.enable_camera = 0
            print("ids=%s" % ids)

            # 受信メール格納内容を初期化
            self.email =  {
                'from_address': "",
                'to_addresses': "",
                'cc_addresses': "",
                'bcc_addresses': "",
                'date': "",
                'subject': "",
                'body': "",
            }

            if ids:
                # 新しいものから順に確認
                for id in ids[::-1]:
                    typ, data = conn.fetch(id, '(RFC822)')
                    raw_email = data[0][1]

                    msg = email.message_from_string(raw_email.decode('utf-8'))
                    msg_encoding = decode_header(msg.get('Subject'))[0][1] or self.email_default_encoding
                    msg = email.message_from_string(raw_email.decode(msg_encoding))

                    date    = msg.get('Date')
                    subject = ""

                    body    = ""
                    try:
                        tmp_str = msg.get_payload()
                        body    = base64.standard_b64decode(tmp_str + '=' * (-len(tmp_str) % 4)).decode(encoding='utf-8')
                    except:
                        body    = msg.get_payload()
                        print("Warning : probabry ascii only message.")

                    print("date    : %s" % date)
                    print("body    : %s" % body)

                    # 本文にキーワードが含まれる
                    k = 0
                    try:
                        k = re.search(TRIGGER_KEYWORD, body)
                    except:
                        print("Warning : probabry email has attach file. this message ignored.")

                    if k:
                        # 解析したメールは削除
                        conn.store(id, '+FLAGS', '\\Deleted')

                        # カメラ撮影を許可する
                        self.enable_camera = 1

                        self.email =  {
                            'from_address': msg.get('From'),
                            'to_addresses': msg.get('To'),
                            'cc_addresses': msg.get('CC'),
                            'bcc_addresses': msg.get('BCC'),
                            'date': date,
                            'subject': subject,
                            'body': body,
                        }
                        break

        except:
            raise

        finally:
            conn.close()
            conn.logout()

    #------------------------------#
    # 受信メール本文のコマンド解析 #
    #------------------------------#
    def parse_command(self):
        control = 'none'
        up      = 0
        down    = 0
        left    = 0
        right   = 0
        option  = 0

        t = re.search(r"チ", self.email['body'])
        if t:
            control = 'tilt'

        p = re.search(r"パ", self.email['body'])
        if p:
            control = 'pan'

        u = re.search(r'上\s*(\d+)', self.email['body'])
        if u:
            up = u.group(1)

        d = re.search(r'下\s*(\d+)', self.email['body'])
        if d:
            down = d.group(1)

        l = re.search(r'左\s*(\d+)', self.email['body'])
        if l:
            left = l.group(1)

        r = re.search(r'右\s*(\d+)', self.email['body'])
        if r:
            right = r.group(1)

        o = re.search(r"オ", self.email['body'])
        if o:
            option = 1

        command = {
                'control'   : control,
                'up'        : up,
                'down'      : down,
                'left'      : left,
                'right'     : right,
                'option'    : option,
        }

        return command

    #----------#
    # 写真撮影 #
    #----------#
    def picamera_picture(self, up, down, left, right):
        try:
            with picamera.PiCamera() as camera:
                # カメラ開始
                pwm = self.picamera_start(camera, PICTURE_WIDTH, PICTURE_HEIGHT, up, down, left, right)

                # プレビュー開始
                #camera.start_preview()
                time.sleep(2)

                # 静止画撮影
                camera.capture('picture/picture.jpg')

                # プレビュー停止
                #camera.stop_preview()

        finally:
            # カメラ停止
            self.picamera_off()


    #------------#
    # ビデオ撮影 #
    #------------#
    def picamera_video(self, up, down, left, right, mode):
        try:
            with picamera.PiCamera() as camera:
                # カメラ開始
                pwm = self.picamera_start(camera, VIDEO_WIDTH, VIDEO_HEIGHT, up, down, left, right)

                # プレビュー開始
                #camera.start_preview()
                time.sleep(2)

                # 動画撮影開始
                camera.start_recording('video/video.h264')

                # カメラ操作
                if mode == 'tilt':
                    self.picamera_tilt(pwm, up, down, left, right)
                else:
                    self.picamera_pan(pwm, up, down, left, right)

                # カメラ撮影停止
                camera.stop_recording()

                # プレビュー停止
                #camera.stop_preview()

                # 動画フォーマットをH.264からMP4に変換
                cmd = "MP4Box -fps 30 -add ***gmail_camera***/video/video.h264 -new ***gmail_camera***/video/video.mp4"
                returncode = subprocess.call(cmd, shell=True)
                time.sleep(1)

        finally:
            # カメラ停止
            self.picamera_off()

    #------------#
    # カメラ開始 #
    #------------#
    def picamera_start(self, camera, width, height, up, down, left, right):
        # カメラ設定
        camera.resolution = (width, height)
        camera.hflip = True
        camera.vflip = True

        # GPIO準備
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(GPIO_T_SERVO_PIN, GPIO.OUT)
        GPIO.setup(GPIO_P_SERVO_PIN, GPIO.OUT)

        # カメラ初期化
        tpwm = GPIO.PWM(GPIO_T_SERVO_PIN, 100)
        ppwm = GPIO.PWM(GPIO_P_SERVO_PIN, 100)

        tpwm.start(float(CAMERA_INIT_TILT)/10.0 + 2.5)
        ppwm.start(float(CAMERA_INIT_PAN)/10.0 + 2.5)

        # カメラ位置決定
        tilt    = self.get_tilt(up, down)
        pan     = self.get_pan(left, right)

        # カメラ移動
        for i in range(5):
            tpwm.ChangeDutyCycle(float(tilt) / 10.0 + 2.5)
            ppwm.ChangeDutyCycle(float(pan) / 10.0 + 2.5)
            time.sleep(0.1)

        return [tpwm, ppwm]

    #------------------#
    # チルト位置の取得 #
    #------------------#
    def get_tilt(self, up, down):
        tilt = CAMERA_INIT_TILT + int(down) - int(up)

        if tilt < CAMERA_MIN_TILT:
            tilt = CAMERA_MIN_TILT
        if tilt > CAMERA_MAX_TILT:
            tilt = CAMERA_MAX_TILT

        return tilt

    #----------------#
    # パン位置の取得 #
    #----------------#
    def get_pan(self, left, right):
        pan = CAMERA_INIT_PAN + int(left) - int(right)

        if pan < CAMERA_MIN_PAN:
            pan = CAMERA_MIN_PAN
        if pan > CAMERA_MAX_PAN:
            pan = CAMERA_MAX_PAN

        return pan

    #--------------------#
    # カメラをチルトする #
    #--------------------#
    def picamera_tilt(self, pwm, up, down, left, right):
        tilt    = self.get_tilt(up, down)
        pan     = self.get_pan(left, right)

        # 上
        for i in range((tilt - CAMERA_MIN_TILT) * 10):
            pwm[0].ChangeDutyCycle(float(tilt*10 - i) / 100.0 + 2.5)
            pwm[1].ChangeDutyCycle(float(pan) / 10.0 + 2.5)
            time.sleep(0.005)
        time.sleep(0.5)

        # 下
        for i in range((CAMERA_MAX_TILT - CAMERA_MIN_TILT) * 10):
            pwm[0].ChangeDutyCycle(float(CAMERA_MIN_TILT*10 + i) / 100.0 + 2.5)
            pwm[1].ChangeDutyCycle(float(pan) / 10.0 + 2.5)
            time.sleep(0.005)
        time.sleep(0.5)

        # 上
        for i in range((CAMERA_MAX_TILT - tilt) * 10):
            pwm[0].ChangeDutyCycle(float(CAMERA_MAX_TILT*10 - i) / 100.0 + 2.5)
            pwm[1].ChangeDutyCycle(float(pan) / 10.0 + 2.5)
            time.sleep(0.005)

    #------------------#
    # カメラをパンする #
    #------------------#
    def picamera_pan(self, pwm, up, down, left, right):
        tilt    = self.get_tilt(up, down)
        pan     = self.get_pan(left, right)

        # 右
        for i in range((pan - CAMERA_MIN_PAN) * 10):
            pwm[0].ChangeDutyCycle(float(tilt) / 10.0 + 2.5)
            pwm[1].ChangeDutyCycle(float(pan*10 - i) / 100.0 + 2.5)
            time.sleep(0.005)
        time.sleep(0.5)

        # 左
        for i in range((CAMERA_MAX_PAN - CAMERA_MIN_PAN) * 10):
            pwm[0].ChangeDutyCycle(float(tilt) / 10.0 + 2.5)
            pwm[1].ChangeDutyCycle(float(CAMERA_MIN_PAN*10 + i) / 100.0 + 2.5)
            time.sleep(0.005)
        time.sleep(0.5)

        # 右
        for i in range((CAMERA_MAX_PAN - pan) * 10):
            pwm[0].ChangeDutyCycle(float(tilt) / 10.0 + 2.5)
            pwm[1].ChangeDutyCycle(float(CAMERA_MAX_PAN*10 - i) / 100.0 + 2.5)
            time.sleep(0.005)

    #--------------#
    # カメラを停止 #
    #--------------#
    def picamera_off(self):
        GPIO.cleanup()

    #------------#
    # メール送信 #
    #------------#
    def send_email(self, from_address, to_addresses, cc_addresses, bcc_addresses, subject, body, mode):
        try:
            # 送信メールサーバアクセス
            conn = SMTP_SSL(self.smtp_host, self.smtp_port)
            conn.login(self.user, self.password)

            # メール作成
            msg = MIMEMultipart()

            msg['Subject']  = Header(subject, self.email_default_encoding)
            msg['From']     = from_address
            msg['To']       = ', '.join(to_addresses)

            if cc_addresses:
                msg['CC']   = ', '.join(cc_addresses)
            if bcc_addresses:
                msg['BCC']  = ', '.join(bcc_addresses)

            msg['Date'] = utils.formatdate(localtime=True)

            body = MIMEText(body, 'plain', self.email_default_encoding)
            msg.attach(body)

            # 添付ファイル
            attachment  = MIMEBase(MIME_IMAGE['type'], MIME_IMAGE['subtype'])
            attach_file = ATTACH_PICTURE

            if mode == "video":
                attachment  = MIMEBase(MIME_VIDEO['type'], MIME_VIDEO['subtype'])
                attach_file = ATTACH_VIDEO

                # フォルダ作成
                if not os.path.isdir(VIDEO_STORE + year):
                    os.mkdir(VIDEO_STORE + year)

                if not os.path.isdir(VIDEO_STORE + year + "/" + month):
                    os.mkdir(VIDEO_STORE + year + "/" + month)

                # ファイルコピー
                shutil.copyfile(attach_file['path'], VIDEO_STORE + year + "/" + month + "/" + now + ".mp4")

            elif mode == "graph":
                attach_file = ATTACH_GRAPH

            file = open(attach_file['path'], 'rb')
            attachment.set_payload(file.read())
            file.close()

            encoders.encode_base64(attachment)
            msg.attach(attachment)

            attachment.add_header('Content-Disposition', 'attachment', filename=attach_file['name'])

            conn.sendmail(from_address, to_addresses, msg.as_string())

        except:
            raise

        finally:
            conn.close()

    #------------#
    # DB読み出し #
    #------------#
    def load_db(self, year, month, day):
        conn = sqlite3.connect(DBNAME)
        c = conn.cursor()
        command = "SELECT * FROM info where datetime like '" + year + "-" + month + "-" + day + " %';"
        rows = c.execute(command)

        datetime    = []
        temp        = []
        humi        = []
        part        = []

        for row in rows:
            datetime    += [row[0]]
            temp        += ["{:.1f}".format(row[1])]
            humi        += ["{:.1f}".format(row[2])]
            part        += ["{:.1f}".format(row[3])]

        return datetime, temp, humi, part

    #------------#
    # グラフ作成 #
    #------------#
    def create_graph(self, year, month, day):
        # DBからセンサーデータ取得
        datetime, temp, humi, part = self.load_db(year, month, day)

        x = pd.to_datetime(datetime)

        # ------------ #
        # センサー情報 #
        # ------------ #
        plt.title("Sensor Information")

        # 湿度
        plt.plot(x, humi, label="humidity[%]")

        # 温度
        plt.plot(x, temp, label="temperature['C]")

        # 粒子
        plt.plot(x, part, label="particle[ug/m^3]")

        # 画像生成
        plt.legend(bbox_to_anchor=(0.8, 0.8, 0.3, 0.3))
        plt.xticks(rotation=20)
        plt.savefig("./graph/sensor.jpg")
        plt.close('all')

#------------#
# メイン処理 #
#------------#
if __name__ == "__main__":
    # インスタンス生成
    camera = gmail_camera(LOGIN_USERNAME, LOGIN_PASSWORD)

    # 今日のグラフを直接送信
    if graph == "-day-graph":
        print("create_graph", year, month, day)
        camera.create_graph(year, month, day)

        print("send_email")
        camera.send_email(
                LOGIN_USERNAME,
                [direct_address],
                None,
                None,
                EMAIL_SUBJECT2,
                u"日単位",
                "graph",
        )

    # 先月のグラフを直接送信
    elif graph == "-month-graph":
        month = int(month) - 1

        if month <= 0:
            year    = str(int(year) - 1)
            month   = 12

        month = format(month, '02d')

        print("create_graph", year, month, "%")
        camera.create_graph(year, month, "%")

        print("send_email")
        camera.send_email(
                LOGIN_USERNAME,
                [direct_address],
                None,
                None,
                EMAIL_SUBJECT2,
                u"月単位",
                "graph",
        )

    # 去年のグラフを直接送信
    elif graph == "-year-graph":
        year = str(int(year) - 1)

        print("create_graph", year, "%", "%")
        camera.create_graph(year, "%", "%")

        print("send_email")
        camera.send_email(
                LOGIN_USERNAME,
                [direct_address],
                None,
                None,
                EMAIL_SUBJECT2,
                u"年単位",
                "graph",
        )

    # 受信メールをチェック
    else:
        if direct_address == "":
            print("normal %s" % direct_address)
            for addr in USER_ADDRESS:
                camera.monitor(addr)
        # 直接送信
        else:
            print("direct %s" % direct_address)
            camera.monitor(direct_address)

# END
