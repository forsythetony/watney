from flask import Flask, send_file, request, send_from_directory, jsonify
import json
from rover import Driver
import signal
import sys
from rover import MotorController
from subprocess import call
import logging

app = Flask(__name__)
roverDriver = None


@app.route("/")
def getPageHTML():
    return send_file("index.html")


@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory('js', path)


@app.route("/sendCommand", methods=['POST'])
def setCommand():
    commandObj = json.loads(request.data.decode("utf-8"))
    newBearing = commandObj['bearing']
    newLook = commandObj['look']

    if newBearing in MotorController.validBearings:
        if newBearing == "0":
            roverDriver.stop()
        else:
            roverDriver.setBearing(newBearing)
    else:
        print("Invalid bearing {}".format(newBearing))
        return "Invalid", 400

    if newLook == 0:
        roverDriver.lookStop()
    elif newLook == -1:
        roverDriver.lookUp()
    elif newLook == 1:
        roverDriver.lookDown()
    else:
        print("Invalid look at {}".format(newLook))
        return "Invalid", 400

    return "OK"


@app.route("/shutDown", methods=['POST'])
def shutdown():
    call("halt", shell=True)

@app.route("/sendTTS", methods=['POST'])
def sendTTS():
    ttsObj = json.loads(request.data.decode("utf-8"))
    ttsString = ttsObj['str']
    roverDriver.sayTTS(ttsString)
    return "OK"

@app.route("/setVolume", methods=['POST'])
def setVolume():
    volumeObj = json.loads(request.data.decode("utf-8"))
    volume = int(volumeObj['volume'])
    roverDriver.setVolume(volume)
    return "OK"

@app.route("/heartbeat", methods=['POST'])
def onHeartbeat():
    stats = roverDriver.onHeartbeat()
    return jsonify(stats)


def signal_handler(signal, frame):
    roverDriver.cleanup()
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    roverDriver = Driver()
    #ssl_context=('cert.pem', 'key.pem')
    app.run(host='0.0.0.0', port=5000, debug=False)
