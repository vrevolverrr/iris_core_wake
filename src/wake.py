import os
import queue
import sys
import time
import threading
import numpy as np
import sounddevice as sd
import tensorflow as tf
from tensorflow.lite.python.interpreter import Interpreter

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
np.set_printoptions(precision=6, suppress=True)

class Speech:
    def __init__(self, model_path):
        self.model_path = model_path
        
        self.__interpreter: Interpreter = tf.lite.Interpreter(model_path=self.model_path)
        self.__interpreter.allocate_tensors()

        self.input_details: dict = self.__interpreter.get_input_details()[0]
        self.output_details: dict = self.__interpreter.get_output_details()[0]
        self.input_tensor: int = self.input_details["index"]
        self.output_tensor: int = self.output_details["index"]
        self.input_shape: np.ndarray = self.input_details["shape"]
        self.output_shape: np.ndarray = self.output_details["shape"]

        self.RATE: int = self.input_shape[1]
        self.MODELNUMCLASSES: int = self.output_shape[1]
        self.BLOCKSIZE: int = 1376 # 2752
        self.OVERLAPFACTOR: int = 0.4
        self.TRIGGERPROBABILITY = 0.85

        try:
            assert self.RATE % self.BLOCKSIZE == 0
        except AssertionError:
            raise ValueError("Block size must be a factor of the sampling rate")

        self.NUMBLOCKS: int = int(self.RATE / self.BLOCKSIZE)
        self.NUMOVERLAPS: int = round(self.OVERLAPFACTOR * self.NUMBLOCKS)
        self.REMAINBLOCKS: int = self.NUMBLOCKS - self.NUMOVERLAPS
        self.LASTBUFFERSIZE: int = self.NUMOVERLAPS * self.BLOCKSIZE

        self.bufferqueue = queue.Queue()
        self.recognitionqueue = queue.Queue()
        self.lastBuffer: np.ndarray = None

        self.isRecording = False
        self.pendingHotword = False

    def __recordingCallback(self, chunk, _, __, ___):
        self.bufferqueue.put(chunk)

    def __recognitionThread(self):
        while self.recognitionqueue.not_empty:
            if not self.isRecording: return

            input = self.recognitionqueue.get()
            self.__interpreter.set_tensor(self.input_tensor, input)
            self.__interpreter.invoke()

            output = np.squeeze(self.__interpreter.get_tensor(self.output_tensor))

            if output[1] > self.TRIGGERPROBABILITY:
                if self.pendingHotword: self.pendingHotword = False
                print("Hotword")

    def __bufferprocessThread(self):
        time.sleep(1)

        while self.isRecording:
            buffer = np.empty((1, self.RATE), dtype=np.float32)

            if self.lastBuffer is None:
                for i in range(self.NUMBLOCKS):
                    buffer[0][i * self.BLOCKSIZE:(i + 1) * self.BLOCKSIZE] = np.frombuffer(self.bufferqueue.get(), dtype=np.float32)
            else:
                buffer[0][:self.LASTBUFFERSIZE] = self.lastBuffer

                for i in range(self.REMAINBLOCKS):
                    buffer[0][i * self.BLOCKSIZE + self.LASTBUFFERSIZE:(i + 1) * self.BLOCKSIZE + self.LASTBUFFERSIZE] = np.frombuffer(self.bufferqueue.get(), dtype=np.float32)

            self.recognitionqueue.put(buffer)
            self.lastBuffer = np.array(buffer[0][-(self.LASTBUFFERSIZE):], copy=True)
    
    def __recordingThread(self):
        with sd.RawInputStream(samplerate=self.RATE, blocksize=self.BLOCKSIZE, channels=1, dtype='float32', callback=self.__recordingCallback):
            while True:
                if self.isRecording:
                    sd.sleep(1000)
                else: break

    def start(self):
        self.isRecording = True
        threading.Thread(target=self.__recognitionThread).start()
        threading.Thread(target=self.__bufferprocessThread).start()
        threading.Thread(target=self.__recordingThread).start()

        input()
        self.stop()
    
    def stop(self):
        self.isRecording = False
        self.bufferqueue = queue.Queue()
        self.recognitionqueue = queue.Queue()

s = Speech("D:\PersonalProjects\iris-core-wake\model\irishotword.tflite")
s.start()