# Wake Word Detection For Project Iris

This is a component of Project Iris, a Windows based personal assistant written in Python, Dart and NodeJS.
The model is trained in Tensorflow and the Tensorflow Lite model is used for inference locally. The model uses binary classification to determine whether the sample buffer is a hotword or not. The model is trained with 1 second clips of the hotword and 1 seconds clips of background noise and not hotword audio.

### About

A recording thread creates monochannel raw audio input stream with a sampling rate of 44032Hz. Data blocks of size 2752 and dtype of float32 are put() into a thread-safe First In First Out (FIFO) Queue through a callback function every (RATE / BLOCKSIZE) * 60 seconds and each block is get() by a seperate processing thread. The processing thread broadcasts the (RATE / BLOCKSIZE) blocks of data into an array with shape (1, 44032). The last OVERLAP_FACTOR * (RATE / BLOCKSIZE) is copied into another array and stored as the previous buffer and filled with remaining blocks. Each buffer is put() into a recognition Queue and is get() by a recognition thread where each buffer is fed into the Tensorflow Lite model for inference. The ouput has a shape of (1, 2) where 2 is the number of classes