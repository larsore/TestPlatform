//
//  eventHandler.swift
//  Authenticator
//
//  Created by Lars Sørensen on 16/03/2023.
//

import Foundation
import PythonKit
import Accelerate

class EventHandler {
    
    private var dilithiumLite: DilithiumLite
    private var hashlib: PythonObject
    private var os: PythonObject
    
    private var hashedDeviceID: String
    
    init?(deviceID: String) {
        guard let ipAddrAndPara = EventHandler.readIpAndPara(filename: "para", fileEnding: "txt") else {
            print("Unable to extract data from file")
            return nil
        }
        CommunicateWithServer.SetUrl(url: ipAddrAndPara.pollingUrl+"/authenticator")
        self.dilithiumLite = DilithiumLite(
            q: ipAddrAndPara.q,
            beta: ipAddrAndPara.beta,
            d: ipAddrAndPara.d,
            n: ipAddrAndPara.n,
            m: ipAddrAndPara.m,
            gamma: ipAddrAndPara.gamma,
            eta: ipAddrAndPara.eta
        )
        
        self.hashlib = Python.import("hashlib")
        self.os = Python.import("os")
        
        guard let hashedDeviceID = String(hashlib.sha256(Python.str(deviceID).encode()).hexdigest()) else {
            print("Unable to hash device-ID and convert it to a SWIFT String")
            return nil
        }
        self.hashedDeviceID = hashedDeviceID
    
    }
    
    private struct PollingAddressAndParameters {
        var q: Int
        var beta: Int
        var d: Int
        var n: Int
        var m: Int
        var gamma: Int
        var eta: Int
        var pollingUrl: String
    }
    
    private static func readIpAndPara(filename: String, fileEnding: String) -> PollingAddressAndParameters? {
    
        var pollingAddressAndParameters = PollingAddressAndParameters(q: 0, beta: 0, d: 0, n: 0, m: 0, gamma: 0, eta: 0, pollingUrl: "")
        
        var lines = [String]()
        if let fileUrl = Bundle.main.url(forResource: filename, withExtension: fileEnding) {
            if let contents = try? String(contentsOf: fileUrl) {
                lines = contents.components(separatedBy: "\n")
            }
        }
        if lines.isEmpty {
            print("Unable to localize file or load the contents of it")
            return nil
        }
        for line in lines {
            let words = line.components(separatedBy: "=")
            if words[0] == "url" {
                pollingAddressAndParameters.pollingUrl = words[1]+":5000"
            } else if words[0] == "q" {
                pollingAddressAndParameters.q = Int(words[1])!
            } else if words[0] == "beta" {
                pollingAddressAndParameters.beta = Int(words[1])!
            } else if words[0] == "d" {
                pollingAddressAndParameters.d = Int(words[1])!
            } else if words[0] == "n" {
                pollingAddressAndParameters.n = Int(words[1])!
            } else if words[0] == "m" {
                pollingAddressAndParameters.m = Int(words[1])!
            } else if words[0] == "gamma" {
                pollingAddressAndParameters.gamma = Int(words[1])!
            } else if words[0] == "eta" {
                pollingAddressAndParameters.eta = Int(words[1])!
            }
        }
        if pollingAddressAndParameters.q == 0 || pollingAddressAndParameters.beta == 0 || pollingAddressAndParameters.d == 0 || pollingAddressAndParameters.n == 0 || pollingAddressAndParameters.m == 0 || pollingAddressAndParameters.gamma == 0 || pollingAddressAndParameters.eta == 0 || pollingAddressAndParameters.pollingUrl == "" {
            print("Not all values read correctly from text-file...")
            return nil
        }
        return pollingAddressAndParameters
    }
    
    func handleRegistration(RP_ID: String, clientData: String) {
        guard let keyPair = dilithiumLite.generateKeyPair() else {
            print("Unable to generate keypair...")
            return
        }
        let credential_ID = UUID().uuidString
        
        let encodedSecretKey = DilithiumLite.getSecretKeyAsData(secretKey: keyPair.secretKey)!
        
        do {
            try AccessKeychain.saveItem(account: credential_ID,
                                service: RP_ID,
                                item: encodedSecretKey)
        } catch {
            print(error)
            return
        }
        Task {
            do {
                try await CommunicateWithServer.postResponse(publicKey: keyPair.publicKey,
                                                             credential_ID: credential_ID,
                                                             clientData: clientData,
                                                             RP_ID: RP_ID,
                                                             hashedDeviceID: self.hashedDeviceID)
            } catch {
                print("Unable to post registration response...")
                return
            }
        }
    }
    
    func handleAuthentication(credential_ID: String, RP_ID: String, clientData: String, randomInt: String) {
        guard let data = AccessKeychain.getItem(
            account: credential_ID,
            service: RP_ID
        ) else {
            print("Failed to read secret key from keychain")
            return
        }
        guard let secretKey = try? JSONDecoder().decode(DilithiumLite.SecretKey.self, from: data) else {
            print("Unable to decode secret key")
            return
        }
        let sig = dilithiumLite.sign(sk: secretKey, message: clientData)
        
        guard let authenticatorData = String(hashlib.sha256(Python.str(RP_ID).encode()).hexdigest()) else {
            print("Unable to convert authenticatorData python hash to a SWIFT String")
            return
        }
        Task {
            do {
                try await CommunicateWithServer.postResponse(signature: sig,
                                                             authenticatorData: authenticatorData,
                                                             hashedDeviceID: self.hashedDeviceID,
                                                             clientData: clientData,
                                                             randomInt: randomInt
                )
            } catch {
                print("Unable to post authentication response...")
                return
            }
        }
    }
    
    
    
    func handleDismiss(message: String, action: String) {
        Task {
            do {
                try await CommunicateWithServer.postResponse(dismissMessage: message, action: action, hashedDeviceID: self.hashedDeviceID)
            }
        }
    }
    
    func handlePolling() async -> CommunicateWithServer.GetMessage? {
        let message = try? await CommunicateWithServer.pollServer(hashedDeviceID: self.hashedDeviceID)
        return message
    }
    
    func updateOtp(oldOtp: Int, currentOtp: Int) async {
        try? await CommunicateWithServer.updateOtp(oldOtp: oldOtp, currentOtp: currentOtp, authID: self.hashedDeviceID)
    }
    
}
