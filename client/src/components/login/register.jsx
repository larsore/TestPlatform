import React from 'react';
import loginImg from "../../login.svg";
import { sha256 } from 'js-sha256';
import raw from './baseUrl.txt';

export class Register extends React.Component {

    static username = ""
    static authID = ""
    static RPUrl = "";
    static pollingUrl = "";
    
    constructor(props) {
        super(props);
    }

    static changeLabel(id, text) {
        document.getElementById(id).innerHTML = text;
    }

    async handleRegister() {

        await fetch(raw) //raw is the contents of 'baseUrl.txt'
            .then(r => r.text())
            .then(text => {
                Register.RPUrl = text+":5050";
                Register.pollingUrl = text+":5000";
            });

        document.getElementById('RPregResponse').innerHTML = "";
        document.getElementById('authenticatorResponse').innerHTML = "";
        document.getElementById('RPfinalResponse').innerHTML = "";

        const username = Register.username;
        const authID = Register.authID;

        if (username === "" || authID === "") {
            console.log("Empty username and/or authID...");
            Register.changeLabel("RPregResponse", "Please fill in both a username and an authenticator ID");
            return
        }

        var hashedAuthID = sha256.create();
        hashedAuthID.update(authID);

        const RPrequestOptions = {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                "username": username,
                "otp": authID
            })
        };
        const RPresponse = await fetch(Register.RPUrl+'/register', RPrequestOptions);
        const RPdata = await RPresponse.json();

        if (typeof RPdata === 'string') {
            Register.changeLabel("RPregResponse", RPdata)
            return
        }
        Register.changeLabel("RPregResponse", "Register information recieved from RP server")
        
        const rp_id = RPdata["rp_id"];
        const challenge = RPdata["challenge"];
        const timeout = RPdata["timeout"];
        
        var clientData = sha256.create();
        clientData.update(rp_id);
        clientData.update(challenge);
        clientData = clientData.hex()

        const pollingRequestOptions = {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                "otp": authID,
                "rp_id": rp_id,
                "client_data": clientData,
                "timeout": timeout,
                "username": username
            })
        };
        const pollingResponse = await fetch(Register.pollingUrl+'/client/register', pollingRequestOptions);
        const pollingData = await pollingResponse.json();
        
        if (typeof pollingData === 'string') {
            const registerFailedOptions = {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    "username": username
                })
            };
            await fetch(Register.RPUrl+'/authenticator/register/failed', registerFailedOptions);
            
            Register.changeLabel("authenticatorResponse", pollingData);
            return
        }
        Register.changeLabel("authenticatorResponse", "Response from authenticator recieved");
        
        const RPresponseOptions = {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                "username": username,
                "credential_id": pollingData["credential_id"],
                "public_key_t": pollingData["public_key_t"],
                "public_key_seed": pollingData["public_key_seed"],
                "client_data": pollingData["client_data"],
                "authenticator_id": pollingData["authenticator_id"]
            })
        };
        const RPresponseResponse = await fetch(Register.RPUrl+'/authenticator/register', RPresponseOptions);
        const RPresponseData = await RPresponseResponse.json();
        
        if (typeof RPresponseData !== 'string') {
            const pollingResultOptions = {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    "authenticator_id": hashedAuthID.hex(),
                    "username": username
                })
            };
            await fetch(Register.pollingUrl+'/client/register/failed', pollingResultOptions);
            
            Register.changeLabel("RPfinalResponse", RPresponseData["reason"]+": "+RPresponseData["msg"]);
        } else {
            Register.changeLabel("RPfinalResponse", RPresponseData);
        }
        
    }

    render() {
        return (
            <div className="base-container" ref={this.props.containerRef}>
                <div className='header'>Register</div>
                <div className='content'>
                    <div className="image">
                        <img src={loginImg} />
                    </div>
                    <div className="form">
                        <div className="form-group">
                            <input type="text" name='username' onChange={(e) => Register.username=e.target.value} placeholder='Username'/>
                        </div>
                        <div className="form-group">
                            <input type="text" name='auth-id' onChange={(e) => Register.authID=e.target.value} placeholder='One time code'/>
                        </div>
                    </div>
                </div>
                <div className='informationLabels'>
                    <label id='RPregResponse'></label>
                    <label id='authenticatorResponse'></label>
                    <label id='RPfinalResponse'></label>
                </div>
                <div className="footer">
                    <button type="button" className="btn" onClick={this.handleRegister}>
                        Register
                    </button>
                </div>
            </div>
        )
    }
}