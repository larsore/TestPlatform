//
//  babyDilithium.swift
//  Authenticator
//
//  Created by Lars Sørensen on 13/03/2023.
//

import Foundation
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
    
    private let SHAKElength: Int
    
    init(n: Int, m: Int, q: Int, eta: Int, gamma: Int, SHAKElength: Int) {
        self.n = n
        self.m = m
        self.q = q
        self.eta = eta
        self.gamma = gamma
        
        self.SHAKElength = SHAKElength
        
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
            s1: BabyDilithium.convertToSwiftList(numpyArray: s1),
            s2: BabyDilithium.convertToSwiftList(numpyArray: s2),
            seed: Int.random(in: 1...100000) // Seed må ses nærmere på
        )
        let A = self.getA(seed: Python.int(sk.seed))
        let t = self.np.remainder(self.np.inner(A, np.array(sk.s1)) + np.array(sk.s2), self.q)
        let pk = PublicKey(seed: sk.seed, t: BabyDilithium.convertToSwiftList(numpyArray: t))
        
        return KeyPair(secretKey: sk, publicKey: pk)
    }
    
    private func rejectionSampling(z: PythonObject, beta: Int) -> Bool {
        let check = String(Python.str(self.np.all(self.np.isin(z, self.np.arange(-(self.gamma - beta), (self.gamma - beta)+1)))))!
        if check == "True" {
            return true
        }
        return false
    }
    
    private static func convertToSwiftList(numpyArray: PythonObject) -> [Int] {
        var list: [Int] = []
        for i in 0..<Int(numpyArray.size)! {
            list.append(Int(numpyArray[i])!)
        }
        return list
    }
    
    private func getChallenge(A: PythonObject, t: PythonObject, w: PythonObject, message: PythonObject, last: Bool) -> PythonObject {
        let shake = self.hashlib.shake_128()
        shake.update(A.tobytes())
        shake.update(t.tobytes())
        shake.update(w.tobytes())
        shake.update(message)
        let shakeInt = Int(Python.int(shake.hexdigest(2), 16))!
        let bits = String(shakeInt, radix: 2)
        var shortenedBits = ""
        var i = 0
        for bit in bits.reversed() {
            shortenedBits += String(bit)
            i+=1
            if i >= self.SHAKElength {
                break
            }
        }
        let binC = String(shortenedBits.reversed())
        let c = Python.int(strtoul(binC, nil, 2)) - Python.int(Int(pow(Double(2),Double(self.SHAKElength-1))))
        if last {
            print("ShakeInt = \(shakeInt)")
            print("bits = \(bits)")
            print("Shakelength amount of bits = \(binC)")
            print("Actual shake-value = \(Python.int(strtoul(binC, nil, 2)))")
            print("c = \(c)")
        }
        return c
    }
    
    func sign(sk: SecretKey, message: String) -> Signature {
        let A = self.getA(seed: Python.int(sk.seed))
        let t = self.np.remainder(self.np.inner(A, np.array(sk.s1)) + np.array(sk.s2), self.q)
        var k = 1
        while true {
            let y1 = self.getRandomVector(maxNorm: self.gamma, size: self.m)
            let y2 = self.getRandomVector(maxNorm: self.gamma, size: self.n)
            
            let w = self.np.remainder(self.np.inner(A, y1) + y2, self.q)
        
            let c = self.getChallenge(A: A, t: t, w: w, message: Python.str(message).encode(), last: false)
            
            let z1 = c*np.array(sk.s1) + y1
            let z2 = c*np.array(sk.s2) + y2
            let checkz1 = rejectionSampling(z: z1, beta: self.eta)
            let checkz2 = rejectionSampling(z: z2, beta: self.eta)
            if checkz1 && checkz2 {
                print("Success at attempt number "+String(k))
                let _ = self.getChallenge(A: A, t: t, w: w, message: Python.str(message).encode(), last: true)
                return Signature(
                    z1: BabyDilithium.convertToSwiftList(numpyArray: z1),
                    z2: BabyDilithium.convertToSwiftList(numpyArray: z2),
                    c: Int(c)!,
                    w: BabyDilithium.convertToSwiftList(numpyArray: w))
            }
            print("\(k) rejections")
            k += 1
        }
    }
    
    static func getSecretKeyAsData(secretKey: SecretKey) -> Data? {
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
