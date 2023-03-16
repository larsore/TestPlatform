.md

Authentication scheme following WebAuthn/FIDO architecture. Signing procedure uses Baby-Dilithium.

The following APIs are used in the communication between server, client, pollingServer and authenticator

##/newcredential 

###request (fra client -> pollingServer):
{
    "credential_id": 3456,
    "rp_id": 1,
    "client_data": "dummy data"
}

###response (fra pollingServer -> client):
"Credential '3456' added to dict"


##/polling

###request (fra authenticator -> pollingServer):
{
    "credential_id": 35
}

###response (fra pollingServer -> authenticator):
{
    "credential_id": 35,
    "rp_id": 1,
    "client_data": "dummy data"
}


##/register

###request (fra client -> server):

{
    "username":"vegard",
    "authenticator_nickname":"myYubiKey1"
}

###response (fra server -> client):

{
    "publicKey": {
        "attestation": "none",
        "authenticatorSelection": {
            "authenticatorAttachment": "platform",
            "requireResidentKey": true,
            "userVerification": "required"
        },
        "challenge": 328,
        "excludeCredentials": [],
        "pubKeyCredParams": [
            {
                "alg": "baby-dilithium",
                "type": "public-key"
            }
        ],
        "rp": {
            "id": 1,
            "name": "Master Thesis"
        },
        "timeout": 30000,
        "user": {
            "displayName": "julenissen3",
            "id": "julenissen3"
        }
    }
}

##/register/verification

###request (fra client -> server):

{
    "public_key": {
        "matrix_a":[1,2,3,4],
        "vector_t":[1,2,3,4]
        },
    "credential_id": "credID",
    "client_data": "226f76b55acb49701e06ded1d95165d179458f6fc37f5c6fc760ae30dec1c378",
    "signature": "signature"
}


###response (fra server -> client):

"Verifikasjon OK. Du kan naa logge inn"

##/auth

###request (fra client -> server):

{
    "username": "vegard"
}

###response (fra server -> client):

{
    "rpID": 1,
    "credential_id": "credID",
    "challenge": 377
}

##/auth/verification

###request (fra client -> server):

{
    "client_data": "dummy",
    "authenticator_data": "dummy",
    "signature": "dummy"
}

###response (fra server -> client):

"SUCCESS! You are now logged in as user 'vegard'"
