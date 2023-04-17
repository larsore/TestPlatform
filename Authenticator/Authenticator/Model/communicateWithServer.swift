//
//  polling.swift
//  Authenticator
//
//  Created by Lars Sørensen on 08/03/2023.
//

import Foundation


class CommunicateWithServer {
    
    private static let baseURL = "http://192.168.39.177:5000/authenticator"
    
    
    struct GetMessage: Decodable {
        let credential_id: String
        let rp_id: String
        let client_data: String
        let username: String
    }
    
    struct SuccessInfo: Decodable {
        let success: String
    }
    
    enum CommunicationError: Error {
        case InvalidURL
        case ResponseCodeNot200
    }
    
    
    static func pollServer(hashedDeviceID: String) async throws -> GetMessage? {
        guard let url = URL(string: CommunicateWithServer.baseURL + "/poll") else {
            throw CommunicationError.InvalidURL
        }
        let body: [String: Any] = [
            "authenticator_id":hashedDeviceID
        ]
        
        guard let data = try await CommunicateWithServer.post(url: url, body: body) else {
            print("Unable to get response from server")
            return nil
        }
            
        let message = try JSONDecoder().decode(GetMessage.self, from: data)
        print("Response when polling server: \(message)")
        return message
    }
    
    private static func post(url: URL, body: [String: Any]) async throws -> Data? {
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        guard let payload = try? JSONSerialization.data(withJSONObject: body, options: .fragmentsAllowed) else {
            print("Unable to JSON serialize HTTP body into a payload")
            return nil
        }
        
        let (data, response) = try await URLSession.shared.upload(for: request, from: payload)
        
        guard (response as? HTTPURLResponse)?.statusCode == 200 else { fatalError("Error while fetching data") }
        
        return data
    }
    
    //REGISTRATION POST
    static func postResponse(publicKey: BabyDilithium.PublicKey, credential_ID: String, clientData: String, RP_ID: String, hashedDeviceID: String, signature: BabyDilithium.Signature) async throws {
        guard let url = URL(string: CommunicateWithServer.baseURL+"/register") else {
            throw CommunicationError.InvalidURL
        }
        let body: [String: Any] = [
            "credential_id":credential_ID,
            "public_key_t":publicKey.t,
            "public_key_seed":publicKey.seed,
            "client_data":clientData,
            "rp_id":RP_ID,
            "authenticator_id":hashedDeviceID,
            "w":signature.w,
            "z1":signature.z1,
            "z2":signature.z2,
            "c":signature.c
        ]
        guard let data = try await CommunicateWithServer.post(url: url, body: body) else {
            print("Unable to get response from server")
            return
        }
        let successInfo = try JSONDecoder().decode(SuccessInfo.self, from: data)
        print("Success with the following response: \(successInfo.success)")
        
    }
    
    
    //AUTHENTICATION POST
    static func postResponse(signature: BabyDilithium.Signature, authenticatorData: String, hashedDeviceID: String) async throws {
        guard let url = URL(string: CommunicateWithServer.baseURL+"/authenticate") else {
            throw CommunicationError.InvalidURL
        }
        let body: [String: Any] = [
            "authenticator_data":authenticatorData,
            "w":signature.w,
            "z1":signature.z1,
            "z2":signature.z2,
            "c":signature.c,
            "authenticator_id": hashedDeviceID
        ]
        guard let data = try await CommunicateWithServer.post(url: url, body: body) else {
            print("Unable to get response from server")
            return
        }
        let successInfo = try JSONDecoder().decode(SuccessInfo.self, from: data)
        print("Success with the following response: \(successInfo.success)")
        
    }
    
    //DISMISSAL
    static func postResponse(dismissMessage: String, action: String, hashedDeviceID: String) async throws {
        guard let url = URL(string: CommunicateWithServer.baseURL+"/dismiss") else {
            throw CommunicationError.InvalidURL
        }
        if action == "reg" {
            let body: [String: Any] = [
                "msg": dismissMessage,
                "authenticator_id": hashedDeviceID,
                "action": "reg"
            ]
            Task {
                try await CommunicateWithServer.post(url: url, body: body)
            }
        } else {
            let body: [String: Any] = [
                "msg": dismissMessage,
                "authenticator_id": hashedDeviceID,
                "action": "auth"
            ]
            Task {
                try await CommunicateWithServer.post(url: url, body: body)
            }
        }
    }
    
}
