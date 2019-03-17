#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
サーボモータ(SG90)の操作
"""

import time
import RPi.GPIO as GPIO
import pigpio

#GPIO_SERVO_PIN = 18                       # ハードウェアPWMに対応
#FREQUENCY = 100                           # PWMの周波数
#MIN_DUTY, MAX_DUTY = 130000, 190000       # Duty比最小, Duty比最大
#CENTER_DUTY = (MIN_DUTY + MAX_DUTY) // 2  # 真ん中
#STEP = 100                                # Duty比の変化量


class MyServo():
    """
    PWMによるサーボモータ(SG90)の操作
    """
    def __init__(self, gpio, frequency, min_duty, max_duty, step):
        self.gpio = gpio
        self.frequency = frequency
        self.min_duty = min_duty
        self.max_duty = max_duty
        self.center_duty = (min_duty + max_duty) // 2
        self.step = step

    def setup(self):
        """
        ソフトPWMの設定
        """
        try:
            # GPIO準備
            GPIO.setmode(GPIO.BCM)           # GPIOをラズパイのピン名で指定する
            GPIO.setup(self.gpio, GPIO.OUT)  # GPIOを出力に設定

            self.pwm = GPIO.PWM(self.gpio, self.frequency)      # PWMオブジェクト取得
            self.pwm.start(float(self.center_duty)/10.0 + 2.5)  # PWM出力を開始

        except:
            GPIO.cleanup()

    def cleanup(self):
        """
        PWMのクリーンアップ
        """
        GPIO.cleanup()

    def point_move(self):
        """
        ポイント移動
        """
        pass

    def lenear_move(self):
        """
        直線移動
        """
        pass


#def move(pi, src_duty, dst_duty, step, gpio, frequency):
#    for duty in range(src_duty, dst_duty, step):
#        pi.hardware_PWM(gpio, frequency, duty)
#        time.sleep(0.005)
#    time.sleep(0.3)
#
#if __name__ == '__main__':
#    try:
#        pi = pigpio.pi()  # GPIOのセットアップ
#        pi.set_mode(GPIO_SERVO_PIN, pigpio.OUTPUT)
#        time.sleep(0.3)
#        pi.hardware_PWM(GPIO_SERVO_PIN, FREQUENCY, CENTER_DUTY)  # サーボを初期位置に移動
#        time.sleep(0.3)
#        move(pi, CENTER_DUTY, MAX_DUTY, STEP, GPIO_SERVO_PIN, FREQUENCY)  # 真ん中→左
#        move(pi, MAX_DUTY, MIN_DUTY, -STEP, GPIO_SERVO_PIN, FREQUENCY)    # 左→右
#        move(pi, MIN_DUTY, CENTER_DUTY, STEP, GPIO_SERVO_PIN, FREQUENCY)  # 右→真ん中
#    
#    finally:
#        pi.set_mode(GPIO_SERVO_PIN, pigpio.INPUT)  # 入力に戻す
#        pi.stop()
