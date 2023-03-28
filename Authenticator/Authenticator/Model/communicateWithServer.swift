//
//  polling.swift
//  Authenticator
//
//  Created by Lars Sørensen on 08/03/2023.
//

import Foundation


class CommunicateWithServer {
    
    private let eventHandler = EventHandler()
    private static let baseURL = "http://10.52.194.117:5000/authenticator"
    
    struct GetMessage: Decodable {
        let credential_id: String
        let rp_id: String
        let client_data: String
    }
    
    struct SuccessInfo: Decodable {
        let success: String
    }
    
    enum CommunicationError: Error {
        case InvalidURL
        case ResponseCodeNot200
    }
    
    static func pollServer(deviceID: String) async throws -> GetMessage? {
        guard let url = URL(string: CommunicateWithServer.baseURL + "/poll") else {
            throw CommunicationError.InvalidURL
        }
        
        let body: [String: Any] = [
            "authenticator_id":deviceID
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
    
    private static func post(url: URL, body: [String]) async throws {
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        guard let payload = try? JSONSerialization.data(withJSONObject: body, options: .fragmentsAllowed) else {
            print("Unable to JSON serialize HTTP body into a payload")
            return
        }
        let (data, response) = try await URLSession.shared.upload(for: request, from: payload)
            
        guard (response as? HTTPURLResponse)?.statusCode == 200 else { fatalError("Error while fetching data") }
            
        let successInfo = try JSONDecoder().decode(SuccessInfo.self, from: data)
        print("Success with the following response: \(successInfo.success)")
    }
    
    //REGISTRATION POST
    static func postResponse(publicKey: BabyDilithium.PublicKey, credential_ID: String, clientData: String, RP_ID: String, deviceID: String) async throws {
        guard let url = URL(string: CommunicateWithServer.baseURL+"/register") else {
            throw CommunicationError.InvalidURL
        }
        let body: [String: Any] = [
            "credential_id":credential_ID,
            "public_key_t":publicKey.t,
            "public_key_seed":publicKey.seed,
            "client_data":clientData,
            "rp_id":RP_ID,
            "authenticator_id":deviceID
        ]
        guard let data = try await CommunicateWithServer.post(url: url, body: body) else {
            print("Unable to get response from server")
            return
        }
        let successInfo = try JSONDecoder().decode(SuccessInfo.self, from: data)
        print("Success with the following response: \(successInfo.success)")
        
    }
    
    
    //AUTHENTICATION POST
    static func postResponse(signature: BabyDilithium.Signature, authenticatorData: String) async throws {
        guard let url = URL(string: CommunicateWithServer.baseURL+"/authenticate") else {
            throw CommunicationError.InvalidURL
        }
        let body: [String: Any] = [
            "authenticator_data":authenticatorData,
            "w":signature.w,
            "z1":signature.z1,
            "z2":signature.z2,
            "c":signature.z2
        ]
        guard let data = try await CommunicateWithServer.post(url: url, body: body) else {
            print("Unable to get response from server")
            return
        }
        let successInfo = try JSONDecoder().decode(SuccessInfo.self, from: data)
        print("Success with the following response: \(successInfo.success)")
        
    }
    
    static func postResponse(dismissMessage: String, action: String) async throws {
        if action == "reg" {
            guard let url = URL(string: CommunicateWithServer.baseURL+"/register") else {
                throw CommunicationError.InvalidURL
            }
            let body: [String] = [dismissMessage]
            Task {
                try await CommunicateWithServer.post(url: url, body: body)
            }
        } else {
            guard let url = URL(string: CommunicateWithServer.baseURL+"/authenticate") else {
                throw CommunicationError.InvalidURL
            }
            let body: [String] = [dismissMessage]
            Task {
                try await CommunicateWithServer.post(url: url, body: body)
            }
        }
    }
    
}
