from flask import Flask, request
from flask_cors import cross_origin
import json
from pollingHandler import Handler

app = Flask(__name__)

pollingHandler = Handler()
macClientUrl = ""
iPhoneClientUrl = ""

def loadIp():
    file = open("/Users/larsore/Documents/Master/TestPlatform/Authenticator/Authenticator/Model/ipAddrAndPara.txt", "r")
    for line in file:
        words = line.split("=")
        if words[0] == "url":
            macClientUrl = words[1]+":3000"
            return True
    return False
    

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
def authenticatorGet():
    body = request.json
    for key in body.keys():
        body[key] = str(body[key])
    requiredKeys = ["authenticator_id"]
    if not checkKeys(requiredKeys, list(body.keys())):
        return json.dumps("The provided key is not correct. The correct key is " + ' '.join(requiredKeys))
    response = pollingHandler.handleGETAuthenticator(body)
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
    requiredKeys = ["credential_id", "public_key_t", "public_key_seed", "client_data", "rp_id", "authenticator_id", "w", "z1", "z2", "c"]
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
    requiredKeys = ["authenticator_data", "w", "z1", "z2", "c", "authenticator_id"]
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