#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
サーボモータ(SG90)の操作
 -------------------------------------------------
 Support SG90-Specification
 -------------------------------------------------
 PWM Period : 20ms(50Hz)
 Duty Cycle : 1 - 2 ms (5.0% - 10.0%)(-90° - +90°)
 -------------------------------------------------
"""

import time
import RPi.GPIO as GPIO
import pigpio

FREQUENCY = 50      # Hz
ANGLE_MARGIN = 5    # °
MIN_DUTY_CYCLE = 1  # ms
MAX_DUTY_CYCLE = 2  # ms
MIN_ANGLE = -90     # °
MAX_ANGLE = 90      # °

PWM_PERIOD = float(1.0 / FREQUENCY) * 1000.0  # ms
MIN_DUTY_RATIO = MIN_DUTY_CYCLE / PWM_PERIOD
MAX_DUTY_RATIO = MAX_DUTY_CYCLE / PWM_PERIOD

STEP_WAIT = 0.005
INTERVAL = 0.5

PERCENT = 100
MEGA = 1000000


class MyServo():
    """
    ソフトウェアPWMによるサーボモータ(SG90)の操作
      -----------------------------
      input   : duty ratio
      -----------------------------
      100.00% : 1.000
       10.00% : 0.100(2.0ms : +90°)
        5.00% : 0.050(1.0ms : -90°)
      -----------------------------
    """
    def __init__(self, gpio, min_angle=-90, max_angle=90, resolution=0.25):
        self.gpio = gpio
        self.frequency = FREQUENCY
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.cnter_angle = (self.min_angle + self.max_angle) // 2
        self.resolution = resolution
        self.pwm = None

    def setup(self):
        """
        GPIOのセットアップ
        """
        try:
            # GPIO準備
            GPIO.setmode(GPIO.BCM)           # GPIOをラズパイのピン名で指定する
            GPIO.setup(self.gpio, GPIO.OUT)  # GPIOを出力に設定

            self.pwm = GPIO.PWM(self.gpio, self.frequency)                    # PWMオブジェクト取得
            self.pwm.start(self.angle2dutyratio(self.cnter_angle) * PERCENT)  # PWM出力を開始

        except:
            self.cleanup()

    def cleanup(self):
        """
        GPIOのクリーンアップ
        """
        GPIO.cleanup()

    def move(self, angle):
        """
        移動
        """
        self.pwm.ChangeDutyCycle(self.angle2dutyratio(angle) * PERCENT)

    def rotate(self, src_angle, dst_angle, step=1):
        """
        回転
        """
        start = int(src_angle / self.resolution)
        end = int(dst_angle / self.resolution) + 1

        for angle in range(start, end, step):
            self.pwm.ChangeDutyCycle(self.angle2dutyratio(angle * self.resolution) * PERCENT)
            time.sleep(STEP_WAIT)

    def center(self):
        """
        中央に移動
        """
        self.move(self.cnter_angle)
        time.sleep(INTERVAL)

    def swing(self):
        """
        振る
        """
        self.rotate(self.cnter_angle, self.max_angle)
        time.sleep(INTERVAL)
        self.rotate(self.max_angle, self.min_angle, -1)
        time.sleep(INTERVAL)
        self.rotate(self.min_angle, self.cnter_angle)
        time.sleep(INTERVAL)

    def angle2dutyratio(self, angle):
        """
        角度をDuty比に変換
        """
        if angle < self.min_angle + ANGLE_MARGIN:
            angle = self.min_angle + ANGLE_MARGIN
        elif angle > self.max_angle - ANGLE_MARGIN:
            angle = self.max_angle - ANGLE_MARGIN

        duty_ratio = (MIN_DUTY_RATIO + (MAX_DUTY_RATIO - MIN_DUTY_RATIO) * (angle + -MIN_ANGLE) / (MAX_ANGLE - MIN_ANGLE))

        return duty_ratio


class MyServoHW(MyServo):
    """
    ハードウェアPWMによるサーボモータ(SG90)の操作
      -----------------------------
      input   : duty ratio
      -----------------------------
      1000000 : 1.000
       100000 : 0.100(2.0ms : +90°)
        50000 : 0.050(1.0ms : -90°)
      -----------------------------
    """
    def setup(self):
        """
        GPIOのセットアップ
        """
        try:
            self.pwm = pigpio.pi()  # GPIOのセットアップ
            self.pwm.set_mode(self.gpio, pigpio.OUTPUT)

        except:
            self.cleanup()

    def cleanup(self):
        """
        GPIOのクリーンアップ
        """
        self.pwm.set_mode(self.gpio, pigpio.INPUT)  # 入力に戻す
        self.pwm.stop()

    def move(self, angle):
        """
        移動
        """
        self.pwm.hardware_PWM(self.gpio, self.frequency, int(self.angle2dutyratio(angle) * MEGA))

    def rotate(self, src_angle, dst_angle, step=1):
        """
        回転
        """
        start = int(src_angle / self.resolution)
        end = int(dst_angle / self.resolution) + 1

        for angle in range(start, end, step):
            self.pwm.hardware_PWM(self.gpio, self.frequency, int(self.angle2dutyratio(angle * self.resolution) * MEGA))
            time.sleep(STEP_WAIT)


def swing_servo(servo):
    """
    サーボをスイングする
    """
    servo.setup()

    try:
        servo.center()
        servo.swing()

    finally:
        servo.cleanup()


if __name__ == '__main__':
    swing_servo(MyServo(18))
    swing_servo(MyServo(19))
    swing_servo(MyServoHW(18))
    swing_servo(MyServoHW(19))
