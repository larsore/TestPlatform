from flask import Flask, request
from flask_cors import cross_origin
import json
from pollingHandler import Handler
import socket

app = Flask(__name__)

pollingHandler = Handler()
macClientUrl = ""
iPhoneClientUrl = ""
baseUrl = ""

def loadIp():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    baseUrl = "http://"+s.getsockname()[0]
    f = open("/Users/larsore/Documents/Master/TestPlatform/WebAuthnBabyDilithium/client/src/components/login/baseUrl.txt", "w")
    f.write(baseUrl)
    f.close()

    fRead = open("/Users/larsore/Documents/Master/TestPlatform/Authenticator/Authenticator/Model/para.txt", "r")
    lines = []
    for line in fRead:
        if line.startswith('url'):
            lines.append("url="+baseUrl+"\n")
        else:
            lines.append(line)
    fRead.close()
    fWrite = open("/Users/larsore/Documents/Master/TestPlatform/Authenticator/Authenticator/Model/para.txt", "w")
    for line in lines:
        fWrite.write(line)
    fWrite.close()

    

    macClientUrl = baseUrl+":3000"
    s.close()

    if macClientUrl == "":
        return False
    return True
    

def checkKeys(requiredKeys, keys):
    if len(requiredKeys) > len(keys):
        return False
    for rKey in requiredKeys:
        if rKey in keys:
            keys.remove(rKey)
    if len(keys) == 0:
        return True
    return False

# Authenticator API Route to check for incoming registration or authentication attempts
@app.route("/authenticator/poll", methods=['POST'])
def authenticatorPost():
    body = request.json
    for key in body.keys():
        body[key] = str(body[key])
    requiredKeys = ["authenticator_id"]
    if not checkKeys(requiredKeys, list(body.keys())):
        return json.dumps("The provided key is not correct. The correct key is " + ' '.join(requiredKeys))
    response = pollingHandler.handlePOSTAuthenticator(body)
    return response

# Client API Route to POST registration attempts
@app.route("/client/register", methods=['POST'])
@cross_origin(origins=[macClientUrl, iPhoneClientUrl, "http://localhost:3000"])
def clientRegister():
    body = request.json

    for key in body.keys():
        body[key] = str(body[key])
    requiredKeys = ["authenticator_id", "rp_id", "username", "client_data", "timeout"]

    if not checkKeys(requiredKeys, list(body.keys())):
        return json.dumps("The provided keys are not correct. The correct keys are " + ' '.join(requiredKeys))
    
    response = pollingHandler.handlePOSTClientRegister(body)
    return response

# Client API Route to POST authentication attempts
@app.route("/client/authenticate", methods=['POST'])
@cross_origin(origins=[macClientUrl, iPhoneClientUrl, "http://localhost:3000"])
def clientAuthenticate():
    body = request.json
    for key in body.keys():
        body[key] = str(body[key])
    requiredKeys = ["authenticator_id", "rp_id", "client_data", "credential_id", "timeout", "username"]
    if not checkKeys(requiredKeys, list(body.keys())):
        return json.dumps("The provided keys are not correct. The correct keys are " + ' '.join(requiredKeys))
    response = pollingHandler.handlePOSTClientAuthenticate(body)
    return response

# Authenticator API Route to POST registration data
@app.route("/authenticator/register", methods=['POST'])
def authenticatorRegister():
    body = request.json
    for key in body.keys():
        body[key] = str(body[key])
    requiredKeys = ["credential_id", "public_key_t", "public_key_seed", "client_data", "rp_id", "authenticator_id"]
    if not checkKeys(list(body.keys()), requiredKeys):
        return json.dumps("The provided keys are not correct. The correct keys are " + ' '.join(requiredKeys))
    response = pollingHandler.handlePOSTAuthenticatorRegister(body)
    return response

@app.route("/authenticator/dismiss", methods=['POST'])
def authenticatorDismiss():
    body = request.json
    for key in body.keys():
        body[key] = str(body[key])
    requiredKeys = ["msg", "authenticator_id", "action"]
    if not checkKeys(list(body.keys()), requiredKeys):
        return json.dumps("The provided keys are not correct. The correct keys are " + ' '.join(requiredKeys))
    response = pollingHandler.handleDismissal(body)
    return response

# Authenticator API Route to POST authentication data
@app.route("/authenticator/authenticate", methods=['POST'])
def authenticatorAuthenticate():
    body = request.json
    for key in body.keys():
        body[key] = str(body[key])
    requiredKeys = ["authenticator_data", "omega", "z1", "z2", "c", "authenticator_id", "client_data"]
    if not checkKeys(list(body.keys()), requiredKeys):
        return json.dumps("The provided keys are not correct. The correct keys are " + ' '.join(requiredKeys))
    response = pollingHandler.handlePOSTAuthenticatorAuthenticate(body)
    return response
    
@app.route("/client/register/failed", methods=['POST'])
@cross_origin(origins=[macClientUrl, iPhoneClientUrl, "http://localhost:3000"])
def clientFailedReg():
    body = request.json
    for key in body.keys():
        body[key] = str(body[key])
    requiredKeys = ["authenticator_id", "username"]
    if not checkKeys(list(body.keys()), requiredKeys):
        return json.dumps("The provided keys are not correct. The correct keys are " + ' '.join(requiredKeys))
    response = pollingHandler.handleClientRegisterFailed(body)
    return response

@app.route("/client/authenticate/failed", methods=['POST'])
@cross_origin(origins=[macClientUrl, iPhoneClientUrl, "http://localhost:3000"])
def clientFailedAuth():
    body = request.json
    for key in body.keys():
        body[key] = str(body[key])
    requiredKeys = ["authenticator_id", "username"]
    if not checkKeys(list(body.keys()), requiredKeys):
        return json.dumps("The provided keys are not correct. The correct keys are " + ' '.join(requiredKeys))
    response = pollingHandler.handleClientLoginFailed(body)
    return response

if __name__ == "__main__":
    isLoaded = loadIp()
    if isLoaded:
        app.run(debug=True, host='0.0.0.0')
    else:
        print("IP address not set")