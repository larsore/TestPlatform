//
//  polling.swift
//  Authenticator
//
//  Created by Lars Sørensen on 08/03/2023.
//

import Foundation


class CommunicateWithServer {
    
    private let eventHandler = EventHandler()
    private static let baseURL = "http://192.168.39.177:8000/authenticator/"
    private static let myID = "69"//Dette skal egt være hashen av device-ID
    
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
    
    static func pollServer() async throws -> GetMessage? {
        
        guard let url = URL(string: CommunicateWithServer.baseURL + "poll/" + CommunicateWithServer.myID) else {
            throw CommunicationError.InvalidURL
        }
                
        let (data, _) = try await URLSession.shared.data(from: url)
        guard let message = try? JSONDecoder().decode(GetMessage.self, from: data) else {
            return nil
        }
        print("Response when polling server: \(message)")
        return message
    }
    
    private static func post(url: URL, body: [String: Any]) async throws {
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
    static func postResponse(publicKey: BabyDilithium.PublicKey, credential_ID: String, clientData: String, RP_ID: String) async throws {
        guard let url = URL(string: baseURL+"register") else {
            throw CommunicationError.InvalidURL
        }
        let body: [String: Any] = [
            "credential_id":credential_ID,
            "public_key_t":publicKey.t,
            "public_key_seed":publicKey.seed,
            "client_data":clientData,
            "rp_id":RP_ID,
            "authenticator_id":CommunicateWithServer.myID
        ]
        try await CommunicateWithServer.post(url: url, body: body)
    }
    
    
    //AUTHENTICATION POST
    static func postResponse(signature: BabyDilithium.Signature, authenticatorData: String) async throws {
        guard let url = URL(string: baseURL+"authenticate") else {
            throw CommunicationError.InvalidURL
        }
        let body: [String: Any] = [
            "authenticator_data":authenticatorData,
            "w":signature.w,
            "z1":signature.z1,
            "z2":signature.z2,
            "c":signature.z2
        ]
        Task {
            try await CommunicateWithServer.post(url: url, body: body)
        }
        
    }
    
    static func postResponse(dismissMessage: String, action: String) async throws {
        if action == "reg" {
            guard let url = URL(string: baseURL+"register") else {
                throw CommunicationError.InvalidURL
            }
            let body: [String] = [dismissMessage]
            Task {
                try await CommunicateWithServer.post(url: url, body: body)
            }
        } else {
            guard let url = URL(string: baseURL+"authenticate") else {
                throw CommunicationError.InvalidURL
            }
            let body: [String] = [dismissMessage]
            Task {
                try await CommunicateWithServer.post(url: url, body: body)
            }
        }
    }
    
}
