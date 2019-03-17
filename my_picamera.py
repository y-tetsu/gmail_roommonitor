#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
picameraの操作
"""

import time
import picamera


def photo(width, height, filename):
    """
    写真を撮影する
    """
    with picamera.PiCamera() as camera:
        camera.resolution = width, height  # 画像サイズ設定
        camera.hflip = True                # 水平反転
        camera.vflip = True                # 垂直反転
        time.sleep(3)                      # カメラ初期化
        camera.capture(filename)           # 静止画撮影


if __name__ == '__main__':
    photo(720, 960, './photo.jpg')
