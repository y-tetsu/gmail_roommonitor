#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
サーボモータ(SG90)の操作
"""

import time
import RPi.GPIO as GPIO
import pigpio

STEP_WAIT = 0.005
INTERVAL = 0.5


class MyServo():
    """
    ソフトウェアPWMによるサーボモータ(SG90)の操作
    """
    def __init__(self, gpio, frequency=50, min_duty=1300, max_duty=1900, step=1):
        self.gpio = gpio
        self.frequency = frequency
        self.min_duty = min_duty
        self.max_duty = max_duty
        self.center_duty = (self.min_duty + self.max_duty) // 2
        self.step = step
        self.pwm = None

    def setup(self):
        """
        GPIOのセットアップ
        """
        try:
            # GPIO準備
            GPIO.setmode(GPIO.BCM)           # GPIOをラズパイのピン名で指定する
            GPIO.setup(self.gpio, GPIO.OUT)  # GPIOを出力に設定

            self.pwm = GPIO.PWM(self.gpio, self.frequency)  # PWMオブジェクト取得
            self.pwm.start(float(self.center_duty) / 200)   # PWM出力を開始

        except:
            self.cleanup()

    def cleanup(self):
        """
        GPIOのクリーンアップ
        """
        GPIO.cleanup()

    def move(self, duty):
        """
        移動
        """
        duty = self.guard_duty(duty)
        self.pwm.ChangeDutyCycle(float(duty) / 200)

    def rotate(self, src_duty, dst_duty, step):
        """
        回転
        """
        src_duty = self.guard_duty(src_duty)
        dst_duty = self.guard_duty(dst_duty)

        for duty in range(src_duty, dst_duty, step):
            self.pwm.ChangeDutyCycle(float(duty) / 200)
            time.sleep(STEP_WAIT)

    def center(self):
        """
        中央に移動
        """
        self.move(self.center_duty)
        time.sleep(INTERVAL)

    def swing(self):
        """
        振る
        """
        self.rotate(self.center_duty, self.max_duty, self.step)
        time.sleep(INTERVAL)
        self.rotate(self.max_duty, self.min_duty, -self.step)
        time.sleep(INTERVAL)
        self.rotate(self.min_duty, self.center_duty, self.step)
        time.sleep(INTERVAL)

    def guard_duty(self, duty):
        """
        デューティーの上下限ガード
        """
        if duty < self.min_duty:
            duty = self.min_duty
        elif duty > self.max_duty:
            duty = self.max_duty

        return duty


class MyServoHW(MyServo):
    """
    ハードウェアPWMによるサーボモータ(SG90)の操作
    """
    def __init__(self, gpio, frequency=100, min_duty=1300, max_duty=1900, step=1):
        super().__init__(gpio, frequency, min_duty, max_duty, step)

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

    def move(self, duty):
        """
        ポイント移動
        """
        duty = self.guard_duty(duty)
        self.pwm.hardware_PWM(self.gpio, self.frequency, duty * 100)

    def rotate(self, src_duty, dst_duty, step):
        """
        直線移動
        """
        src_duty = self.guard_duty(src_duty)
        dst_duty = self.guard_duty(dst_duty)

        for duty in range(src_duty, dst_duty, step):
            self.pwm.hardware_PWM(self.gpio, self.frequency, duty * 100)
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
