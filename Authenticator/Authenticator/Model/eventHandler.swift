//
//  eventHandler.swift
//  Authenticator
//
//  Created by Lars Sørensen on 16/03/2023.
//

import Foundation
import PythonKit

class EventHandler {
    
    private var babyDilithium: BabyDilithium
    private var hashlib: PythonObject
    private var os: PythonObject
    
    private var hashedDeviceID: String
    
    init?(deviceID: String) {
        guard let ipAddrAndPara = EventHandler.readIpAndPara(filename: "ipAddrAndPara", fileEnding: "txt") else {
            print("Unable to extract data from file")
            return nil
        }
        CommunicateWithServer.SetUrl(url: ipAddrAndPara.pollingUrl+"/authenticator")
        self.babyDilithium = BabyDilithium(
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
    
    func handleRegistration(RP_ID: String, clientData: String) -> String? {
        let keyPair = babyDilithium.generateKeyPair()
        print("Keypair generated")
        let credential_ID = UUID().uuidString
        print("Generated credential_id: \(credential_ID)")
        let sig = babyDilithium.sign(sk: keyPair.secretKey, message: clientData)
        
        let encodedSecretKey = BabyDilithium.getSecretKeyAsData(secretKey: keyPair.secretKey)!
        
        do {
            try AccessKeychain.save(credentialID: credential_ID,
                                RPID: RP_ID,
                                secretKey: encodedSecretKey)
        } catch {
            print(error)
            return nil
        }
        print("Credentials saved to keychain")
        
        Task {
            do {
                try await CommunicateWithServer.postResponse(publicKey: keyPair.publicKey,
                                                             credential_ID: credential_ID,
                                                             clientData: clientData,
                                                             RP_ID: RP_ID,
                                                             hashedDeviceID: self.hashedDeviceID,
                                                             signature: sig)
            } catch {
                print("Unable to post registration response...")
                return
            }
        }
        print("Public key, credential_ID and client data sent to pollingServer")
        return credential_ID
    }
    
    func handleAuthentication(credential_ID: String, RP_ID: String, clientData: String) {
        guard let data = AccessKeychain.get(
            credentialID: credential_ID,
            RPID: RP_ID
        ) else {
            print("Failed to read secret key from keychain")
            return
        }
        print("Correct secret key retrieved from keychain")
        
        guard let secretKey = try? JSONDecoder().decode(BabyDilithium.SecretKey.self, from: data) else {
            print("Unable to decode secret key")
            return
        }
        
        let sig = babyDilithium.sign(sk: secretKey, message: clientData)
        
        guard let authenticatorData = String(hashlib.sha256(Python.str(RP_ID).encode()).hexdigest()) else {
            print("Unable to convert authenticatorData python hash to a SWIFT String")
            return
        }
        
        Task {
            do {
                try await CommunicateWithServer.postResponse(signature: sig,
                                                             authenticatorData: authenticatorData,
                                                             hashedDeviceID: self.hashedDeviceID
                )
            } catch {
                print("Unable to post authentication response...")
                return
            }
        }
        print("Signature and authenticator data sent to pollingServer")
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
    
    func testCrypto() {
        let keypair = babyDilithium.generateKeyPair()
        let credID = "id11"
        let rpID = "rp id"
        let encodedSecretKey = BabyDilithium.getSecretKeyAsData(secretKey: keypair.secretKey)!
        
        let sigBefore = babyDilithium.sign(sk: keypair.secretKey, message: "En random melding")
        
        
        do {
            try AccessKeychain.save(credentialID: credID,
                                RPID: rpID,
                                secretKey: encodedSecretKey)
        } catch {
            print(error)
            return
        }
        print("Credentials saved to keychain")
        
        guard let data = AccessKeychain.get(
            credentialID: credID,
            RPID: rpID
        ) else {
            print("Failed to read secret key from keychain")
            return
        }
        print("Correct secret key retrieved from keychain")
        
        guard let secretKey = try? JSONDecoder().decode(BabyDilithium.SecretKey.self, from: data) else {
            print("Unable to decode secret key")
            return
        }
        
        let sigAfter = babyDilithium.sign(sk: secretKey, message: "En random melding")
        
        print(sigBefore)
        print("------------------------------------------------------------------------------------")
        print(sigAfter)
        

    }
    
}
