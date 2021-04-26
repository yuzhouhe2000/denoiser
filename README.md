# EE434 Project Updating 

A software that receive audio & video input and enhance them in real time. Possible application: meeting (using feedback loop in apps like Zoom) and speech/lecture recording/streaming. The software will denoise the received audio, adjust EQ and enhance the audio performance based on video infomation.

Team: Michael Pozzi, Matt Baseheart, Yuzhou He

![Flask App](example.jpeg)

How it works:

    After Audio Client collects Input Frames 
    
    [16k Hz for speech detection + single channel for speed]
    
        1. If Voice Activity Detected: Client send the audio data to Server through UDP

        2. Another thread waits for server output and play the output

    When Audio Server receives Input:

        1. To Denoiser 
        
        2. To EQ

        3. To video based enhancement 

        4. Send processed audio back to Client through UDP

Note: [two denoisers are included, one based on Demucs network ("DL"), one based on OMLSA + IMCRA algorithm ("DSP")] The Demucs network is trained on the entire valentini dataset + DNS dataset with hidden size = 48, plus some office/room noises downloaded from youtube and Audioset. The Demucs Network runs slow on CPU, so DSP denoiser is prefered. Demucs can run in real time on 4 i-5 cpu cores, add VAD module can help reduce the computation when no speech is detected.]

    Video Module (works separately from flask app):

        1. Detect and mark face 

        2. Detect Eyes and measure eye separations (support glasses). Using moving average filter for stable output.

        3. Estimate distance using eye separation and focal length

        4. Send distance information to Audio Server

        5. Send position information to Pan-Tilt Camera / digital zoom

To run the flask server (linux/mac):

    0. Download "denoiser.th" from drive. Move "[denoiser.th](https://drive.google.com/file/d/17WuFlrUMJZdYiYEqvBfq4hmAd3x_NwDm/view?usp=sharing)" to 434-project/Processor/Audio_Server/denoiser/denoiser.th

    1. pip3 install -r requirements.txt

    2. on Jetson or on any device for server (need to run server first to allow UDP binding):

        cd 434-project/Processor/Audio_Server

        python3 main.py

    3. on PC or any device for client (needs to have sounddevice):
    
        cd 434-project/Processor/Audio_Client

        flask run

    4. connect the video processor to the audio chain:

        cd 434-project/Processor/Video
        
        python3 eye_detect.py

    5. open flask site in chrome "http://127.0.0.1:5000/")

    [Notes: The default IP configuration allows you to run both client and server on the same device. (127.0.0.1) You need to reconfigure the ip and port if you are running them on separate devices.]
    

Notes:

if OSX limits the maximum UDP-package to be 9216, input the following command in terminal to remove the restriction:

    sudo sysctl -w net.inet.udp.maxdgram=65535





