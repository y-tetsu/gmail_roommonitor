#!/usr/bin/python
# -*- coding: utf-8 -*-
#==========================================================
# 色々記録する
#==========================================================
import smbus
import time
from datetime import datetime
import sqlite3
from contextlib import closing
import subprocess
import RPi.GPIO as GPIO

#--------#
# 設定値 #
#--------#
DBNAME = 'db/info.db'

AM2320_ADDR = 0x5c  # AM2320のI2Cアドレス

DUST_SENSOR_PIN = 17
SAMPLING_CYCLE  = 0.0001    # 100us
SAMPLING_TIME   = 50        # 50秒

#--------------#
# recordクラス #
#--------------#
class record(object):

    #--------#
    # 初期化 #
    #--------#
    def __init__(self, addr, pin):
        self.addr       = addr
        self.pin        = pin
        self.i2c        = smbus.SMBus(1)
        self.datetime   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.temp       = 0
        self.humi       = 0
        self.part       = 0
        self.cpu_r      = 0
        self.cpu_t      = 0
        self.mem_u      = 0
        self.mem_f      = 0
        self.disk_u     = 0
        self.disk_f     = 0

    #--------------------------#
    # 温湿度センサーの値を取得 #
    #--------------------------#
    def get_temphumi(self):
        # 5度読みの平均値
        count = 5

        tmp_temp = [0, 0, 0, 0, 0]
        tmp_humi = [0, 0, 0, 0, 0]

        for i in range(count):
            # スリープ状態を解除
            try:
                self.i2c.write_i2c_block_data( self.addr, 0x00, [] )
            except:
                pass

            # センサーに計測を要求
            time.sleep(0.003)

            self.i2c.write_i2c_block_data( self.addr, 0x03, [ 0x00, 0x04 ] )

            # センサーの計測結果を表示
            time.sleep(0.015)

            data = self.i2c.read_i2c_block_data( self.addr, 0x00, 6 )

            tmp_temp[i] = float( data[4] << 8 | data[5] ) / 10
            tmp_humi[i] = float( data[2] << 8 | data[3] ) / 10

            print("Temperature:", tmp_temp[i], "C Humidity:", tmp_humi[i], "%")

            time.sleep(1)

        self.temp   = 0
        self.humi   = 0

        for i in range(count):
            self.temp   += tmp_temp[i]
            self.humi   += tmp_humi[i]

        self.temp = self.temp / count
        self.humi = self.humi / count

        print(self.datetime, " Ave.Temperature:", "{:.1f}".format(self.temp), "C Ave.Humidity:", "{:.1f}".format(self.humi), "%")

    #----------------------------#
    # ダストセンサーの情報を取得 #
    #----------------------------#
    def get_dust(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.IN)
        GPIO.setwarnings(False)

        self.part = self.get_pm25()

        GPIO.cleanup()

        print("粒子 : " + "{:.1f}".format(self.part) + "ug/m^3")

    # PM2.5の計測
    def get_pm25(self):
        t0      = time.time()
        t       = 0
        ts      = SAMPLING_TIME
        sample  = 0
        high    = 0

        # サンプリング回数とHith出力の回数を取得
        while(1):
            sample += 1
            high += GPIO.input(self.pin)

            if ((time.time() - t0) > ts):
                break

            time.sleep(SAMPLING_CYCLE) # 1 sampling / 100 us

        # LOWの割合[%]を算出
        low     = sample - high
        ratio   = low / sample * 100

        # ほこりの濃度を算出
        pcs  = 1.1 * pow(ratio, 3) - 3.8 * pow(ratio, 2) + 520 * ratio + 0.62
        ugm3 = self.pcs2ugm3(pcs)

        print("> sample : ", sample)
        print("> low    : ", low)
        print("> ratio  : ", ratio, "[%]")

        return ugm3

    # 単位をug/m^3に変換
    def pcs2ugm3(self, pcs):
        pi = 3.141592

        density = 1.65 * pow(10, 12)

        r25     = 0.44 * pow(10, -6)
        vol25   = (4/3) * pi * pow(r25, 3)
        mass25  = density * vol25

        K = 3531.5

        return pcs * K * mass25

    #----------------------------#
    # ラズベリーパイの情報を取得 #
    #----------------------------#
    def get_raspberrypi(self):
        # CPU使用率
        try:
            result = subprocess.Popen('top -b -n 3 | grep Cpu', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        except:
            print("Can not get CPU-ratio!")

        rstdout, rstderr = result.communicate()
        linelist = rstdout.splitlines()

        tcklist = []

        for line in linelist:
            itemlist = line.split()
            cpu_ratio = float(100.0 - float(itemlist[7]))

        tcklist.append(cpu_ratio)

        self.cpu_r = tcklist[0]

        print("CPU使用率        : " + "{:.1f}".format(self.cpu_r) + "%")

        # CPU温度
        try:
            result = subprocess.Popen('vcgencmd measure_temp', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        except:
            print("Can not get CPU-temperature!")

        rstdout, rstderr = result.communicate()

        tmp_cpu_t = rstdout.split()[0].split('=')

        self.cpu_t = float(str(tmp_cpu_t[1]).replace("'C", ""))

        print("CPU温度          : " + "{:.1f}".format(self.cpu_t) + "'C")

        # メモリ使用量とメモリ空き容量
        try:
            result = subprocess.Popen('free | grep Mem', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        except:
            print("Can not get Memory-info!")

        rstdout, rstderr = result.communicate()
        linelist = rstdout.splitlines()

        tcklist = []

        for line in linelist:
            itemlist = line.split()
            used = int(itemlist[2])
            avei = int(itemlist[6])
            tcklist.append(used)
            tcklist.append(avei)

        self.mem_u = float(tcklist[0]/1000)
        self.mem_f = float(tcklist[1]/1000)

        print("メモリ使用量     : " + "{:.1f}".format(self.mem_u) + "M")
        print("メモリ空き容量   : " + "{:.1f}".format(self.mem_f) + "M")

        # ディスク使用量とディスク空き容量
        try:
            result = subprocess.Popen('df -h | grep root', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        except:
            print("Can not get Disk-info!")

        rstdout, rstderr = result.communicate()
        linelist = rstdout.splitlines()

        tcklist = []

        for line in linelist:
            itemlist = line.split()
            used = itemlist[2]
            avei = itemlist[3]
            tcklist.append(used)
            tcklist.append(avei)

        self.disk_u = float(str(tcklist[0]).replace('G', ''))
        self.disk_f = float(str(tcklist[1]).replace('G', ''))

        print("ディスク使用量   : " + "{:.1f}".format(self.disk_u) + "G")
        print("ディスク空き容量 : " + "{:.1f}".format(self.disk_f) + "G")

    #----------#
    # DBに登録 #
    #----------#
    def set_sqlite3(self):
        conn = sqlite3.connect(DBNAME)

        c = conn.cursor()

        # executeメソッドでSQL文を実行する
        sql = 'insert into info (datetime, temperature, humidity, particle, cpu_ratio, cpu_temp, memory_used, memory_free, disk_used, disk_free) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        val = (self.datetime, self.temp, self.humi, self.part, self.cpu_r, self.cpu_t, self.mem_u, self.mem_f, self.disk_u, self.disk_f)

        c.execute(sql, val)

        conn.commit()

        conn.close()

#------------#
# メイン処理 #
#------------#
if __name__ == "__main__":
    # インスタンス生成
    rec = record(AM2320_ADDR, DUST_SENSOR_PIN)

    # 温度と湿度を表示
    rec.get_temphumi()

    # ダストを表示
    rec.get_dust()

    # ラズパイ情報
    rec.get_raspberrypi()

    # データベースに記録
    rec.set_sqlite3()

# END
