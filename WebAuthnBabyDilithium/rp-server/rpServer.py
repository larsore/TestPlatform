from flask import Flask, request, Response
from flask_cors import cross_origin
import json
from rpHandler import Handler

app = Flask(__name__)

responseHandler = Handler(RPID="http://ntnumaster:5050")
clientUrl = "http://10.22.64.19:3000"

def checkKeys(requiredKeys, keys):
    if len(requiredKeys) > len(keys):
        return False
    for rKey in requiredKeys:
        if rKey in keys:
            keys.remove(rKey)
    if len(keys) == 0:
        return True
    return False

# API Route for register-attempts from client
@app.route("/register", methods=['POST'])
@cross_origin(origins=[clientUrl, "http://localhost:3000"])
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
        
# API Route for register-attempts from client
@app.route("/authenticate", methods=['POST'])
@cross_origin(origins=[clientUrl, "http://localhost:3000"])
def clientLogin():
    body = request.json
    for key in body.keys():
        body[key] = str(body[key])
    requiredKeys = ["username"]
    if not checkKeys(requiredKeys, list(body.keys())):
        return json.dumps("The provided key is not correct. The correct key is " + ' '.join(requiredKeys))
    response = responseHandler.handleLogin(body)
    return response 

# API Route for register-attempts from client
@app.route("/authenticator/register", methods=['POST'])
@cross_origin(origins=[clientUrl, "http://localhost:3000"])
def clientAuthenticatorRegisterResponse():
    body = request.json
    
    for key in body.keys():
        body[key] = str(body[key])

    requiredKeys = ["public_key_t", "public_key_seed", "credential_id", "client_data", "authenticator_id", "w", "c", "z1", "z2", "username"]
    if not checkKeys(requiredKeys, list(body.keys())):
        return json.dumps("The provided key is not correct. The correct key is " + ' '.join(requiredKeys))
    response = responseHandler.handleRegisterResponse(body)
    return response 

# API Route for register-attempts from client
@app.route("/authenticator/authenticate", methods=['POST'])
@cross_origin(origins=[clientUrl, "http://localhost:3000"])
def clientAuthenticatorAuthenticateResponse():
    body = request.json
    for key in body.keys():
        body[key] = str(body[key])
    requiredKeys = ["w", "c", "z1", "z2", "authenticator_data", "username", "rp_id", "challenge"]
    if not checkKeys(requiredKeys, list(body.keys())):
        return json.dumps("The provided key is not correct. The correct key is " + ' '.join(requiredKeys))
    response = responseHandler.handleLoginResponse(body)
    return response  

@app.route("/authenticator/register/failed", methods=['POST'])
@cross_origin(origins=[clientUrl, "http://localhost:3000"])
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
@cross_origin(origins=[clientUrl, "http://localhost:3000"])
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
    app.run(debug=True, host='0.0.0.0', port=5050)