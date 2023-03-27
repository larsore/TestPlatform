from flask import Flask, request
from flask_cors import cross_origin
import json
from pollingServer import PollingServer

app = Flask(__name__)

pollingServer = PollingServer()

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
    response = pollingServer.handleGETAuthenticator(body)
    return response

# Client API Route to POST registration attempts
@app.route("/client/register", methods=['POST'])
@cross_origin(origins=["http://localhost:3000"])
def clientRegister():
    body = request.json
    for key in body.keys():
        body[key] = str(body[key])
    requiredKeys = ["authenticator_id", "rp_id", "client_data"]
    if not checkKeys(requiredKeys, list(body.keys())):
        return json.dumps("The provided keys are not correct. The correct keys are " + ' '.join(requiredKeys))
    response = pollingServer.handlePOSTClientRegister(body)
    return response

# Client API Route to POST authentication attempts
@app.route("/client/authenticate", methods=['POST'])
@cross_origin(origins=["http://localhost:3000"])
def clientAuthenticate():
    body = request.json
    for key in body.keys():
        body[key] = str(body[key])
    requiredKeys = ["authenticator_id", "rp_id", "client_data", "credential_id"]
    if not checkKeys(requiredKeys, list(body.keys())):
        return json.dumps("The provided keys are not correct. The correct keys are " + ' '.join(requiredKeys))
    response = pollingServer.handlePOSTClientAuthenticate(body)
    return response

# Authenticator API Route to POST registration data
@app.route("/authenticator/register", methods=['POST'])
def authenticatorRegister():
    body = request.json

    if isinstance(body, list):
        response = PollingServer.handleDismissal(body, False)
        return response

    for key in body.keys():
        body[key] = str(body[key])
    requiredKeys = ["credential_id", "public_key_t", "public_key_seed", "client_data", "rp_id", "authenticator_id"]
    if not checkKeys(list(body.keys()), requiredKeys):
        return json.dumps("The provided keys are not correct. The correct keys are " + ' '.join(requiredKeys))
    response = pollingServer.handlePOSTAuthenticatorRegister(body)
    return response

# Authenticator API Route to POST authentication data
@app.route("/authenticator/authenticate", methods=['POST'])
def authenticatorAuthenticate():
    body = request.json

    if isinstance(body, list):
        response = PollingServer.handleDismissal(body, True)
        return response

    for key in body.keys():
        body[key] = str(body[key])
    requiredKeys = ["authenticator_data", "w", "z1", "z2", "c"]
    if not checkKeys(list(body.keys()), requiredKeys):
        return json.dumps("The provided keys are not correct. The correct keys are " + ' '.join(requiredKeys))
    response = pollingServer.handlePOSTAuthenticatorAuthenticate(body)
    return response
    

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')