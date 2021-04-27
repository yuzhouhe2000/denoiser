from flask import Flask, render_template, request, redirect,url_for, json, render_template_string, jsonify, Response
from flask_socketio import SocketIO, emit,send
import sys
import time
import sounddevice as sd
import cv2
from npsocket import SocketNumpyArray
import numpy as np
import socket
from equalizer import *
from VAD import denoiser_VAD
from scipy import signal


# Initilize flask app and socketio
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

MIX = 40
COUNT = 0
LIVE = 0
VAD_RESULT = 0
volume = 1
EQ_curve = 0
Denoiser = "DSP"
buffer = []
outport_denoiser = 9999
inport_denoiser = 9998
outport_parameter = 9997
video_port = 9996
CONNECTED = 0
client_denoiser_receiver = SocketNumpyArray()
client_denoiser_sender = SocketNumpyArray()
client_denoiser_sender.initialize_sender('127.0.0.1', outport_denoiser)
client_parameter_sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_video_receiver = socket.socket(socket.AF_INET,socket.SOCK_DGRAM) 
server_video_receiver.bind(("127.0.0.1",video_port))

@app.route("/", methods=['GET', 'POST'])
def index():
    return render_template("index.html")

@app.route('/param', methods=['POST'])
def parameter():
    global Denoiser
    Q = 3
    A = 1
    EQ_LP = request.form.get("EQ_LP")
    EQ_LS = request.form.get("EQ_LS")
    EQ_PK = request.form.get("EQ_PK")
    EQ_HS = request.form.get("EQ_HS")
    EQ_HP = request.form.get("EQ_HP")
    Denoiser = request.form.get("Denoiser")
    h_list = []

    if EQ_LP != "":
        EQ_LP = int(EQ_LP)
        if EQ_LP >= 1 and EQ_LP <= 16000:
            sos1 = lowpass(EQ_LP, Q)
            w, h1 = signal.sosfreqz(sos1)
            h_list.append(h1)

    if EQ_LS != "":
        EQ_LS = int(EQ_LS)
        if EQ_LS >= 1 and EQ_LS <= 16000:
            sos2 = lowShelf(EQ_LS, Q,A)
            w, h2 = signal.sosfreqz(sos2)
            h_list.append(h2)

    if EQ_PK != "":
        EQ_PK = int(EQ_PK)
        if EQ_PK >= 1 and EQ_PK <= 16000:
            sos3 = peaking(EQ_PK, Q,A)
            w, h3 = signal.sosfreqz(sos3)
            h_list.append(h3)
    
    if EQ_HS != "":
        EQ_HS = int(EQ_HS)
        if EQ_HS >= 1 and EQ_HS <= 16000:
            sos4 = highShelf(EQ_HS, Q,A)
            w, h4 = signal.sosfreqz(sos4)
            h_list.append(h4)

    if EQ_HP != "":
        EQ_HP = int(EQ_HP)
        if EQ_HP >= 1 and EQ_HP <= 16000:
            sos5 = highpass(EQ_HP, Q)
            w, h5 = signal.sosfreqz(sos5)
            h_list.append(h5)
    
    h_all = 1
    for i in h_list:
        h_all = h_all * i
    db = 20 * np.log10(np.maximum(np.abs(h_all), 1e-5))
    print(w/np.pi)
    EQ_curve = {}
    for i in range(0,512):
        EQ_curve[w[i]] = db[i]

    socketio.emit('plot',{'data': EQ_curve})
    # return SOS expression
    parameters = {"EQ_LP":EQ_LP,"EQ_LS":EQ_LS,"EQ_PK":EQ_PK,"EQ_HS":EQ_HS,"EQ_HP":EQ_HP, "Denoiser": Denoiser, "MIX": MIX}
    parameters_json = json.dumps(parameters).encode('utf-8')
    client_parameter_sender.sendto(parameters_json, ("127.0.0.1", outport_parameter))
    # print(parameters_json)
    return ('', 204)

# sound_device
def query_devices(device, kind):
    try:
        caps = sd.query_devices(device, kind=kind)
    except ValueError:
        sys.exit(1)
    return caps

# denoiser_live
@app.route("/live", methods=['POST'])
def denoiser_live():
    global VAD_RESULT
    global LIVE
    global Denoiser
    global buffer
    
    LIVE = 1
    print("live request")

    sample_rate = 16000
    caps = query_devices(None, "input")
    channels_in = min(caps['max_input_channels'], 1)
    stream_in = sd.InputStream(
        device=None,
        samplerate=sample_rate,
        channels=channels_in)
    stream_in.start()
    while (LIVE == 1):
        # if Denoiser == "DL":
        #     frame, overflow = stream_in.read(2)
        #     client_denoiser_sender.send_numpy_array(frame)
        # elif Denoiser == "DSP":
        frame, overflow = stream_in.read(128)
        buffer.append(frame)
        # print(len(buffer))
        # print(Denoiser)
        if "VAD" in Denoiser:
            # print(result)
            if VAD_RESULT == 1:
                client_denoiser_sender.send_numpy_array(frame)
            
        else:
            client_denoiser_sender.send_numpy_array(frame)

    stream_in.stop()
    return ('', 204)

@app.route("/output_audio", methods=["POST"])
def output_audio():
    global CONNECTED
    global client_denoiser_receiver
    global volume
    sample_rate = 16000
    device_out = "Soundflower (2ch)"
    caps = query_devices(device_out, "output")
    channels_out = min(caps['max_output_channels'], 1)
    stream_out = sd.OutputStream(
        device=None,
        samplerate=sample_rate,
        channels=channels_out)
    stream_out.start()

    while True:
        if CONNECTED == 0:
            client_denoiser_receiver.initialize_receiver(inport_denoiser)
            print("INITIALIZED") 
            CONNECTED = 1  
        else:
            out = client_denoiser_receiver.receive_array()
            stream_out.write(out*volume)
    stream_out.stop()
    return ('', 204)


@app.route("/endlive", methods=['POST'])
def end_live():
    global LIVE
    LIVE = 0
    socketio.emit('my_response',{'data': ""})
    return ('', 204)

@app.route("/volume", methods=['POST'])
def receive_video_parameter():
    global volume
    time.sleep(1)
    while LIVE == 1:
        print("connecting to video server")
        recieved = server_video_receiver.recvfrom(1024)
        json_obj = json.loads(recieved[0].decode('utf-8'))
        volume = json_obj.get("volume")
    return ('', 204)

@app.route("/VAD", methods=['POST'])
def VAD():
    global VAD_RESULT
    global buffer
    global Denoiser
    global LIVE
    time.sleep(1)

    while LIVE == 1:
        if "VAD" in Denoiser:
            # print(len(buffer))
            # print(len(buffer))
            while len(buffer) >= 20:
                del(buffer[0])            
            if len(buffer) > 0:
                frame = buffer[0] 
                # print(frame)
                del(buffer[0])
                VAD_RESULT = denoiser_VAD(frame)
            # print(VAD_RESULT)
        else:
            time.sleep(1)
    return ('', 204)

@app.route('/slide', methods=['GET', 'POST'])
def control_panel():
    global MIX
    if request.method == 'POST':
        MIX = request.form.get('slide')
        print('MIX changed to:', MIX)
    return ('', 204)


if __name__ == '__main__':
    socketio.run(app)