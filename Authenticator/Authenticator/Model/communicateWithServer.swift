//
//  polling.swift
//  Authenticator
//
//  Created by Lars Sørensen on 08/03/2023.
//

import Foundation

class CommunicateWithServer {
    
    private static var baseURL: String?
    
    struct GetMessage: Decodable {
        let credential_id: String
        let rp_id: String
        let client_data: String
        let username: String
        let random_int: String
    }
    
    static func SetUrl(url: String) {
        CommunicateWithServer.baseURL = url
    }
    
    struct SuccessInfo: Decodable {
        let success: String
    }
    
    enum CommunicationError: Error {
        case InvalidURL
        case ResponseCodeNot200
    }
    
    static func pollServer(hashedDeviceID: String) async throws -> GetMessage? {
        guard let baseUrl = CommunicateWithServer.baseURL else {
            print("BaseUrl not set")
            return nil
        }
        guard let url = URL(string: baseUrl + "/poll") else {
            throw CommunicationError.InvalidURL
        }
        let body: [String: Any] = [
            "authenticator_id":hashedDeviceID
        ]
        guard let data = try await CommunicateWithServer.post(url: url, body: body) else {
            print("Unable to get response from server")
            return nil
        }
        return try JSONDecoder().decode(GetMessage.self, from: data)
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
    static func postResponse(publicKey: DilithiumLite.PublicKey, credential_ID: String, clientData: String, RP_ID: String, hashedDeviceID: String) async throws {
        guard let baseUrl = CommunicateWithServer.baseURL else {
            print("BaseUrl not set")
            return
        }
        guard let url = URL(string: baseUrl+"/register") else {
            throw CommunicationError.InvalidURL
        }
        let body: [String: Any] = [
            "credential_id":credential_ID,
            "public_key_t":publicKey.tCoeffs,
            "public_key_seed":publicKey.Aseed,
            "client_data":clientData,
            "rp_id":RP_ID,
            "authenticator_id":hashedDeviceID
        ]
        guard let data = try await CommunicateWithServer.post(url: url, body: body) else {
            print("Unable to get response from server")
            return
        }
        let _ = try JSONDecoder().decode(SuccessInfo.self, from: data)
    }
    
    
    //AUTHENTICATION POST
    static func postResponse(signature: DilithiumLite.Signature, authenticatorData: String, hashedDeviceID: String, clientData: String, randomInt: String) async throws {
        guard let baseUrl = CommunicateWithServer.baseURL else {
            print("BaseUrl not set")
            return
        }
        guard let url = URL(string: baseUrl+"/authenticate") else {
            throw CommunicationError.InvalidURL
        }
        let body: [String: Any] = [
            "authenticator_data":authenticatorData,
            "omega":signature.omega,
            "z1":signature.z1Coeffs,
            "z2":signature.z2Coeffs,
            "c":signature.cHex,
            "authenticator_id": hashedDeviceID,
            "client_data": clientData,
            "random_int": randomInt
        ]
        guard let data = try await CommunicateWithServer.post(url: url, body: body) else {
            print("Unable to get response from server")
            return
        }
        let _ = try JSONDecoder().decode(SuccessInfo.self, from: data)
    }
    
    //DISMISSAL
    static func postResponse(dismissMessage: String, action: String, hashedDeviceID: String) async throws {
        guard let baseUrl = CommunicateWithServer.baseURL else {
            print("BaseUrl not set")
            return
        }
        guard let url = URL(string: baseUrl+"/dismiss") else {
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
                guard let data = try await CommunicateWithServer.post(url: url, body: body) else {
                    print("Unable to get dismissal response from server")
                    return
                }
                let _ = try JSONDecoder().decode(SuccessInfo.self, from: data)
            }
        }
    }
    
    static func updateOtp(oldOtp: Int, currentOtp: Int, authID: String) async throws {
        guard let baseUrl = CommunicateWithServer.baseURL else {
            print("BaseUrl not set")
            return
        }
        guard let url = URL(string: baseUrl+"/update") else {
            throw CommunicationError.InvalidURL
        }
        let body: [String: Any] = [
            "old_otp": oldOtp,
            "current_otp": currentOtp,
            "authenticator_id": authID
        ]
        Task {
            guard let data = try await CommunicateWithServer.post(url: url, body: body) else {
                print("Unable to get update response from server")
                return
            }
            let _ = try JSONDecoder().decode(SuccessInfo.self, from: data)
        }
    }
    
}
