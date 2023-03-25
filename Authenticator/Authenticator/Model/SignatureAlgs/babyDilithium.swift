//
//  babyDilithium.swift
//  Authenticator
//
//  Created by Lars Sørensen on 13/03/2023.
//

import Foundation
import Accelerate
import NumPySupport
import PythonSupport
import PythonKit

class BabyDilithium {
    
    private let np: PythonObject
    private let os: PythonObject
    private let sys: PythonObject
    private let hashlib: PythonObject
    
    private let n: Int
    private let m: Int
    private let q: Int
    private let eta: Int
    private let gamma: Int
    
    init(n: Int, m: Int, q: Int, eta: Int, gamma: Int) {
        self.n = n
        self.m = m
        self.q = q
        self.eta = eta
        self.gamma = gamma
        
        PythonSupport.initialize()
        NumPySupport.sitePackagesURL.insertPythonPath()
        np = Python.import("numpy")
        os = Python.import("os")
        sys = Python.import("sys")
        hashlib = Python.import("hashlib")
    }
    
    struct SecretKey: Encodable, Decodable {
        var s1: [Int]
        var s2: [Int]
        var seed: Int
    }
    
    struct PublicKey: Codable {
        var seed: Int
        var t: [Int]
    }
    
    struct KeyPair {
        var secretKey: SecretKey
        var publicKey: PublicKey
    }
    
    struct Signature: Encodable {
        var z1: [Int]
        var z2: [Int]
        var c: Int
        var w: [Int]
    }
    
    private func getA(seed: PythonObject) -> PythonObject {
        self.np.random.seed(seed)
        var startA: [PythonObject] = []
        for _ in 0..<self.n {
            startA.append(self.np.random.randint(0, self.q, self.m))
        }
        return self.np.array(startA)
    }
    
    private func getRandomVector(maxNorm: Int, size: Int) -> PythonObject {
        var randomVector: [PythonObject] = []
        let length = 4096 // Dette må ses nærmere på
        let rand = os.urandom(length)
        for i in 0..<length {
            randomVector.append(rand[i])
        }
        let rng = self.np.random.default_rng(randomVector)
        return rng.integers(-maxNorm, maxNorm+1, size)
    }
    
    public func generateKeyPair() -> KeyPair {
        let s1 = self.getRandomVector(maxNorm: self.eta, size: self.m)
        let s2 = self.getRandomVector(maxNorm: self.eta, size: self.n)
        let sk = SecretKey(
            s1: self.convertToSwiftList(numpyArray: s1),
            s2: self.convertToSwiftList(numpyArray: s2),
            seed: Int.random(in: 1...100000) // Seed må ses nærmere på
        )
        let A = self.getA(seed: Python.int(sk.seed))
        let t = self.np.remainder(self.np.inner(A, np.array(sk.s1)) + np.array(sk.s2), self.q)
        let pk = PublicKey(seed: sk.seed, t: self.convertToSwiftList(numpyArray: t))
        
        return KeyPair(secretKey: sk, publicKey: pk)
    }
    
    private func rejectionSampling(z: PythonObject, beta: Int) -> Bool {
        let check = String(Python.str(self.np.all(self.np.isin(z, self.np.arange(-(self.gamma - beta), (self.gamma - beta)+1)))))!
        if check == "True" {
            return true
        }
        return false
    }
    
    private func convertToSwiftList(numpyArray: PythonObject) -> [Int] {
        var list: [Int] = []
        for i in 0..<Int(numpyArray.size)! {
            list.append(Int(numpyArray[i])!)
        }
        return list
    }
    
    func sign(sk: SecretKey, message: String) -> Signature {
        let A = self.getA(seed: Python.int(sk.seed))
        let t = self.np.remainder(self.np.inner(A, np.array(sk.s1)) + np.array(sk.s2), self.q)
        var i = 1
        while true {
            let y1 = self.getRandomVector(maxNorm: self.gamma, size: self.m)
            let y2 = self.getRandomVector(maxNorm: self.gamma, size: self.n)
            
            let w = self.np.remainder(self.np.inner(A, y1) + y2, self.q)
            
            let shake = self.hashlib.shake_128()
            shake.update(A.tobytes())
            shake.update(t.tobytes())
            shake.update(w.tobytes())
            shake.update(Python.str(message).encode())
            let c = Python.int(shake.hexdigest(1), 16)
            let z1 = c*np.array(sk.s1) + y1
            let z2 = c*np.array(sk.s2) + y2
            let checkz1 = rejectionSampling(z: z1, beta: self.eta)
            let checkz2 = rejectionSampling(z: z2, beta: self.eta)
            if checkz1 && checkz2 {
                return Signature(
                    z1: self.convertToSwiftList(numpyArray: z1),
                    z2: self.convertToSwiftList(numpyArray: z2),
                    c: Int(c)!,
                    w: self.convertToSwiftList(numpyArray: w))
            }
            print(String(i) + " rejected")
            i += 1
        }
    }
    
    func getSecretKeyAsData(secretKey: SecretKey) -> Data? {
        do {
            let encoded = try JSONEncoder().encode(secretKey)
            guard let keyAsUTF8 = String(data: encoded, encoding: .utf8) else {
                print("Unable to encode json-encoded secret key to utf-8")
                return nil
            }
            guard let keyAsData = keyAsUTF8.data(using: .utf8) else {
                print("Unable to convert utf-8 encoded secret key to object of type 'Data'")
                return nil
            }
            return keyAsData
        } catch {
            print("Unable to encode secret key as json")
            return nil
        }
        
        
        
    }
    
}
