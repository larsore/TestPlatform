//
//  accessKeychain.swift
//  Authenticator
//
//  Created by Lars Sørensen on 10/03/2023.
//

import Foundation

class AccessKeychain {
    
    
    private static let access = SecAccessControlCreateWithFlags(nil, // Use the default allocator.
                                                 kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly,
                                                 .userPresence,
                                                 nil) // Ignore any error.
    
    enum KeychainError: Error {
        case duplicateEntry
        case unknown(OSStatus)
    }
    
    static func save(credentialID: String, RPID: String, secretKey: Data) throws {
        let query: [String: AnyObject] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: credentialID as AnyObject,
            kSecAttrAccount as String: RPID as AnyObject,
            kSecAttrAccessControl as String: AccessKeychain.access as AnyObject,
            kSecValueData as String: secretKey as AnyObject,
        ]
        
        let status = SecItemAdd(query as CFDictionary, nil)
        
        guard status != errSecDuplicateItem else {
            throw KeychainError.duplicateEntry
        }
        
        guard status == errSecSuccess else {
            throw KeychainError.unknown(status)
        }
        
        print("saved")
        
    }
    
    static func get(credentialID: String, RPID: String) -> Data? {
        let query: [String: AnyObject] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: credentialID as AnyObject,
            kSecAttrAccount as String: RPID as AnyObject,
            kSecAttrAccessControl as String: AccessKeychain.access as AnyObject,
            kSecReturnData as String: kCFBooleanTrue,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        
        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        
        print("Read status: \(status)")
        
        return result as? Data
        
    }
    
    
    
    
}