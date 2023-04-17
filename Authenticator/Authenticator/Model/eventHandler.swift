//
//  eventHandler.swift
//  Authenticator
//
//  Created by Lars Sørensen on 16/03/2023.
//

import Foundation
import PythonKit

class EventHandler {
    
    private let babyDilithium = BabyDilithium(n: 1280, m: 1690, q: 8380417, eta: 5, gamma: 523776, SHAKElength: 13)
    private let hashlib: PythonObject = Python.import("hashlib")
    private let os: PythonObject = Python.import("os")
    
    private var hashedDeviceID: String
    
    init?(deviceID: String) {
        guard let hashedDeviceID = String(hashlib.sha256(Python.str(deviceID).encode()).hexdigest()) else {
            print("Unable to hash device-ID and convert it to a SWIFT String")
            return nil
        }
        self.hashedDeviceID = hashedDeviceID
    }
    
    enum HashError: Error {
        case unableToGenerateHash
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
                                                             authenticatorData: authenticatorData, hashedDeviceID: self.hashedDeviceID)
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
    
}
