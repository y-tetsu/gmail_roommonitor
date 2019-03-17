#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
picameraの操作
"""

import time
import picamera


class MyPiCamera():
    """
    picameraによる写真と動画の撮影
    """
    def __init__(self):
        self.camera = None

    def capture_photo(self, width, height, filename):
        """
        写真を撮影する
        """
        with picamera.PiCamera() as camera:
            camera.resolution = width, height  # 画像サイズ設定
            camera.hflip = True                # 水平反転
            camera.vflip = True                # 垂直反転

            time.sleep(2)                      # カメラ起動待ち
            camera.capture(filename)           # 静止画撮影

    def start_video(self, width, height, filename):
        """
        動画撮影を開始する
        """
        try:
            self.camera = picamera.PiCamera()

            self.camera.resolution = width, height  # 画像サイズ設定
            self.camera.hflip = True                # 水平反転
            self.camera.vflip = True                # 垂直反転

            time.sleep(2)                           # カメラ起動待ち
            self.camera.start_recording(filename)   # 動画撮影

        except:
            self.stop_video()

    def stop_video(self):
        """
        動画撮影を停止する
        """
        self.camera.stop_recording()  # 撮影停止
        self.camera.close()


if __name__ == '__main__':
    CAMERA = MyPiCamera()

    # 写真撮影
    CAMERA.capture_photo(720, 960, './photo.jpg')

    # ビデオ撮影
    CAMERA.start_video(240, 320, './video.h264')
    time.sleep(10)
    CAMERA.stop_video()
