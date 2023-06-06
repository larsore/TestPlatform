from flask import Flask, request, Response
from flask_cors import cross_origin
import json
from rpHandler import Handler
import socket

app = Flask(__name__)

responseHandler = Handler(RPID="http://ntnumaster:5050")
macClientUrl = ""
iPhoneClientUrl = ""
baseUrl = ""

def loadIpAndPara():

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    baseUrl = "http://"+s.getsockname()[0]
    f = open("/Users/larsore/Documents/Master/TestPlatform/WebAuthnBabyDilithium/client/src/components/login/baseUrl.txt", "w")
    f.write(baseUrl)
    f.close()
    macClientUrl = baseUrl+":3000"
    s.close() 

    file = open("/Users/larsore/Documents/Master/TestPlatform/Authenticator/Authenticator/Model/para.txt", "r")
    parameters = {
        "q": None,
        "beta": None,
        "d": None,
        "n": None,
        "m": None,
        "gamma": None,
        "eta": None
    }
    for line in file:
        words = line.split("=")   
        if words[0] == "q":
            parameters["q"] = int(words[1])
        elif words[0] == "beta":
            parameters["beta"] = int(words[1])
        elif words[0] == "d":
            parameters["d"] = int(words[1])
        elif words[0] == "n":
            parameters["n"] = int(words[1])
        elif words[0] == "m":
            parameters["m"] = int(words[1])
        elif words[0] == "gamma":
            parameters["gamma"] = int(words[1])
        elif words[0] == "eta":
            parameters["eta"] = int(words[1])
    file.close()
    for key in parameters.keys():
        if parameters[key] == None:
            return False
    if macClientUrl == "":
        return False
    responseHandler.setParameters(
        q=parameters["q"], 
        beta=parameters["beta"], 
        d=parameters["d"], 
        n=parameters["n"], 
        m=parameters["m"], 
        gamma=parameters["gamma"],
        eta=parameters["eta"]
        )
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

# API Route for register-attempts from Client Application
@app.route("/register", methods=['POST'])
@cross_origin(origins=[macClientUrl, iPhoneClientUrl, "http://localhost:3000"])
def clientRegister():
    body = request.json
    for key in body.keys():
        body[key] = str(body[key])
    requiredKeys = ["username", "authenticator_id"]
    if not checkKeys(requiredKeys, list(body.keys())):
        return json.dumps("The provided key is not correct. The correct key is " + ' '.join(requiredKeys))
    responseBody = responseHandler.handleRegister(body)
    response = Response(responseBody)
    response.headers['Origin'] = responseHandler.getRPID()
    return response
        
# API Route for register-attempts from Client Application
@app.route("/authenticate", methods=['POST'])
@cross_origin(origins=[macClientUrl, iPhoneClientUrl, "http://localhost:3000"])
def clientLogin():
    body = request.json
    for key in body.keys():
        body[key] = str(body[key])
    requiredKeys = ["username"]
    if not checkKeys(requiredKeys, list(body.keys())):
        return json.dumps("The provided key is not correct. The correct key is " + ' '.join(requiredKeys))
    response = responseHandler.handleLogin(body)
    return response 

# API Route for register-attempts from Client Application
@app.route("/authenticator/register", methods=['POST'])
@cross_origin(origins=[macClientUrl, iPhoneClientUrl, "http://localhost:3000"])
def clientAuthenticatorRegisterResponse():
    body = request.json
    
    for key in body.keys():
        body[key] = str(body[key])

    requiredKeys = ["public_key_t", "public_key_seed", "credential_id", "client_data", "username"]
    if not checkKeys(requiredKeys, list(body.keys())):
        return json.dumps("The provided key is not correct. The correct key is " + ' '.join(requiredKeys))
    response = responseHandler.handleRegisterResponse(body)
    return response 

# API Route for register-attempts from Client Application
@app.route("/authenticator/authenticate", methods=['POST'])
@cross_origin(origins=[macClientUrl, iPhoneClientUrl, "http://localhost:3000"])
def clientAuthenticatorAuthenticateResponse():
    body = request.json
    for key in body.keys():
        body[key] = str(body[key])
    requiredKeys = ["omega", "c", "z1", "z2", "authenticator_data", "username", "client_data"]
    if not checkKeys(requiredKeys, list(body.keys())):
        return json.dumps("The provided key is not correct. The correct key is " + ' '.join(requiredKeys))
    response = responseHandler.handleLoginResponse(body)
    return response  

@app.route("/authenticator/register/failed", methods=['POST'])
@cross_origin(origins=[macClientUrl, iPhoneClientUrl, "http://localhost:3000"])
def clientAuthenticatorRegistrationFailed():
    body = request.json
    for key in body.keys():
        body[key] = str(body[key])
    requiredKeys = ["username"]
    if not checkKeys(requiredKeys, list(body.keys())):
        return json.dumps("The provided key is not correct. The correct key is " + ' '.join(requiredKeys))
    response = responseHandler.handleRegisterFailed(body)
    return response  

@app.route("/authenticator/authenticate/failed", methods=['POST'])
@cross_origin(origins=[macClientUrl, iPhoneClientUrl, "http://localhost:3000"])
def clientAuthenticatorAuthenticateFailed():
    body = request.json
    for key in body.keys():
        body[key] = str(body[key])
    requiredKeys = ["username"]
    if not checkKeys(requiredKeys, list(body.keys())):
        return json.dumps("The provided key is not correct. The correct key is " + ' '.join(requiredKeys))
    response = responseHandler.handleLoginFailed(body)
    return response  


if __name__ == "__main__":
    isLoaded = loadIpAndPara()
    if isLoaded:
        app.run(debug=True, host='0.0.0.0', port=5050)
    else:
        print("Unable to load parameters and IP-address of client")