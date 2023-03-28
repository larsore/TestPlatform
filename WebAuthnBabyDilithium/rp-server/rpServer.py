from flask import Flask, request
from flask_cors import cross_origin
import json
from rpHandler import Handler

app = Flask(__name__)

responseHandler = Handler()

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
def authenticatorGet():
    body = request.json
    for key in body.keys():
        body[key] = str(body[key])
    requiredKeys = ["username", "authenticator_nickname"]
    if not checkKeys(requiredKeys, list(body.keys())):
        return json.dumps("The provided key is not correct. The correct key is " + ' '.join(requiredKeys))
    response = responseHandler.handleRegister(body)
    return response  

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')