import React from 'react';
import loginImg from "../../login.svg";
import { sha256 } from 'js-sha256';
import raw from './baseUrl.txt';

export class Login extends React.Component {
    
    static username = "";
    static RPUrl = "";
    static pollingUrl = "";
    
    constructor(props) {
        super(props);
    }

    static changeLabel(id, text) {
        document.getElementById(id).innerHTML = text;
    }

    async handleLogin() {

        await fetch(raw)
            .then(r => r.text())
            .then(text => {
                Login.RPUrl = text+":5050";
                Login.pollingUrl = text+":5000";
            });

        document.getElementById('RPloginResponse').innerHTML = "";
        document.getElementById('authenticatorResponse').innerHTML = "";
        document.getElementById('RPfinalResponse').innerHTML = "";

        const username = Login.username;

        if (username === "") {
            console.log("Empty username");
            Login.changeLabel("RPloginResponse", "Please fill in a username");
            return
        }
        
        const RPrequestOptions = {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                "username": username
            })
        };
        const RPresponse = await fetch(Login.RPUrl+'/authenticate', RPrequestOptions);
        const RPdata = await RPresponse.json();
        console.log(RPdata)
        // TODO: Compare HTTP Origin with RP_ID
        //console.log(response.headers.get("Origin"));

        if (typeof RPdata === 'string') {
            Login.changeLabel("RPloginResponse", RPdata)
            return
        }
        Login.changeLabel("RPloginResponse", "Recieved challenge and other login information from RP-server")
        
        const rp_id = RPdata["rp_id"];
        const challenge = RPdata["challenge"];
        const credID = RPdata["credential_id"];
        const timeout = RPdata["timeout"];
        const authID = RPdata["authenticator_id"];
        
        var clientData = sha256.create();
        clientData.update(rp_id);
        clientData.update(challenge);

        const pollingRequestOptions = {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                "authenticator_id": authID,
                "rp_id": rp_id,
                "client_data": clientData.hex(),
                "timeout": timeout,
                "username": username,
                "credential_id": credID
            })
        };
        const pollingResponse = await fetch(Login.pollingUrl+'/client/authenticate', pollingRequestOptions);
        const pollingData = await pollingResponse.json();
        
        //Check response and act different based on response from polling server
        console.log(pollingData);

        
        if (typeof pollingData === 'string') {
            const loginFailedOptions = {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    "username": username
                })
            };
            const loginFailedResponse = await fetch(Login.RPUrl+'/authenticator/authenticate/failed', loginFailedOptions);
            const loginFailedData = await loginFailedResponse.json();
            console.log(loginFailedData)
            Login.changeLabel("authenticatorResponse", pollingData);
            return
        }
        Login.changeLabel("authenticatorResponse", "Recieved signature from authenticator")
        
        const RPresponseOptions = {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                "username": username,
                "authenticator_data": pollingData["authenticator_data"],
                "omega": pollingData["omega"],
                "c": pollingData["c"],
                "z1": pollingData["z1"],
                "z2": pollingData["z2"],
                "rp_id": rp_id,
                "challenge": challenge
            })
        };
        const RPresponseResponse = await fetch(Login.RPUrl+'/authenticator/authenticate', RPresponseOptions);
        const RPresponseData = await RPresponseResponse.json();
        console.log(RPresponseData)
        
        if (typeof RPresponseData !== 'string') {
            const pollingResultOptions = {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    "authenticator_id": authID,
                    "username": username
                })
            };
            const pollingResultResponse = await fetch(Login.pollingUrl+'/client/authenticate/failed', pollingResultOptions);
            const pollingResultData = await pollingResultResponse.json();
            console.log(pollingResultData);
            Login.changeLabel("RPfinalResponse", RPresponseData["reason"]+": "+RPresponseData["msg"]);
        } else {
            Login.changeLabel("RPfinalResponse", RPresponseData);
            //window.location.replace('https://www.youtube.com/watch?v=xvFZjo5PgG0?autoplay=1');
        }
    }

    render() {
        return (
            <div className="base-container" ref={this.props.containerRef}>
                <div className='header'>Login</div>
                <div className='content'>
                    <div className="image">
                        <img src={loginImg} />
                    </div>
                    <div className="form">
                        <div className="form-group">
                            <input type="text" name='username' onChange={(e) => Login.username=e.target.value} placeholder='Username'/>
                        </div>
                    </div>
                </div>
                <div className='informationLabels'>
                    <label id='RPloginResponse'></label>
                    <label id='authenticatorResponse'></label>
                    <label id='RPfinalResponse'></label>
                </div>
                <div className="footer">
                    <button type="button" className="btn" onClick={this.handleLogin}>
                        Login
                    </button>
                </div>
            </div>
        )
    }
}