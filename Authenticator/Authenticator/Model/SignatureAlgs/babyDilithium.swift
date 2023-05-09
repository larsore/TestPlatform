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
    private let hashlib: PythonObject
    
    private let q: Int
    private let beta: Int
    private let d: Int
    private let n: Int
    private let m: Int
    private let gamma: Int
    private let hashSize: Int
    private let ballSize: Int
    private let approxBeta: Int
    
    private let f: PythonObject
        
    init(q: Int, beta: Int, d: Int, n: Int, m: Int, gamma: Int, hashSize: Int, ballSize: Int) {
        self.q = q
        self.beta = beta
        self.d = d
        self.n = n
        self.m = m
        self.gamma = gamma
        self.hashSize = hashSize
        self.ballSize = ballSize
        self.approxBeta = Int((q-1)/16)
        
        PythonSupport.initialize()
        NumPySupport.sitePackagesURL.insertPythonPath()
        self.np = Python.import("numpy")
        self.os = Python.import("os")
        self.hashlib = Python.import("hashlib")
        
        let fCoeffs = np.array([1] + Array(repeating: 0, count: (self.d - 2)) + [1])
        self.f = self.np.polynomial.Polynomial(fCoeffs)
    }
    
    struct SecretKey: Encodable, Decodable {
        var s1Coeffs: [[Int]]
        var s2Coeffs: [[Int]]
        var seedVector: [Int]
    }
    
    struct PublicKey: Codable {
        var seedVector: [Int]
        var tCoeffs: [[Int]]
    }
    
    struct KeyPair {
        var secretKey: SecretKey
        var publicKey: PublicKey
    }
    
    struct Signature: Encodable {
        var z1Coeffs: [[Int]]
        var z2Coeffs: [[Int]]
        var cHex: String
        var omega: String
    }
    
    struct Challenge {
        var challengeHex: String
        var challengePolynomial: PythonObject
    }
    
    private func getA(seedVector: [Int]) -> PythonObject {
        let rng = self.np.random.default_rng(seedVector)
        var startA: [PythonObject] = []
        for _ in 0..<self.n {
            var row: [PythonObject] = []
            for _ in 0..<self.m {
                row.append(self.np.polynomial.Polynomial(rng.integers(0, self.q, self.d)))
            }
            startA.append(self.np.array(row))
        }
        return self.np.array(startA)
    }
    
    private func getRandomPolynomial(maxNorm: Int, size: Int) -> PythonObject {
        var randomVector: [PythonObject] = []
        let length = 4096
        let rand = self.os.urandom(length)
        for i in 0..<length {
            randomVector.append(rand[i])
        }
        let rng = self.np.random.default_rng(randomVector)

        var poly: [PythonObject] = []
        for _ in 0..<size {
            let coef = rng.integers(-maxNorm, maxNorm+1, self.d)
            poly.append(self.np.polynomial.Polynomial(coef))
        }
        return np.array(poly)
    }
    
    private func getCoefficients(polyList: PythonObject) -> [[Int]] {
        var res: [[Int]] = []
        for i in 0..<Int(polyList.size)! {
            var coeffList: [Int] = []
            for k in 0..<Int(polyList[i].coef.size)! {
                coeffList.append(Int(polyList[i].coef[k])!)
            }
            res.append(coeffList)
        }
        return res
    }
    
    public func generateKeyPair() -> KeyPair {
        let s1 = self.getRandomPolynomial(maxNorm: self.beta, size: self.m)
        let s2 = self.getRandomPolynomial(maxNorm: self.beta, size: self.n)
        
        var seedVector: [Int] = []
        let length = 4096
        let rand = os.urandom(length)
        for i in 0..<length {
            seedVector.append(Int(rand[i])!)
        }
        let sk = SecretKey(
            s1Coeffs: self.getCoefficients(polyList: s1),
            s2Coeffs: self.getCoefficients(polyList: s2),
            seedVector: seedVector
        )
        let A = self.getA(seedVector: sk.seedVector)
        let t = self.getLatticePoint(A: A, s: s1, e: s2)
        let pk = PublicKey(
            seedVector: sk.seedVector,
            tCoeffs: self.getCoefficients(polyList: t)
        )
        return KeyPair(secretKey: sk, publicKey: pk)
    }
    
    private func rejectionSampling(z1: PythonObject, z2: PythonObject) -> Bool {
        var max = self.approxBeta
        var min = -self.approxBeta
        
        let concatenatedList = self.getCoefficients(polyList: z1) + self.getCoefficients(polyList: z2)
        for l in concatenatedList {
            if l.max()! > max {
                max = l.max()!
            }
            if l.min()! < min {
                min = l.min()!
            }
        }
        
        if max <= self.approxBeta && min >= -self.approxBeta {
            return true
        }
        return false
        
    }
    
    private func hashToBall(shake: PythonObject) -> PythonObject {
        let cCoeffs = self.np.zeros(256)
        let h = shake.digest(self.hashSize)
        var k = 0
        var s: [Int] = []
        while true {
            let byteString = String(Python.bin(Python.int(h[k])))!
            let index = byteString.index(byteString.startIndex, offsetBy: 2)
            let byteArray = Array(byteString[index..<byteString.endIndex])
            for bit in byteArray {
                s.append(Int(String(bit))!)
            }
            k += 1
            if s.count >= self.ballSize {
                break
            }
        }
        
        var taken: [Int] = []
        let start = 196
        for i in start..<256 {
            var j = 257
            while j > i {
                if !taken.contains(Int(h[k])!) {
                    j = Int(h[k])!
                }
                k += 1
            }
            taken.append(j)
            cCoeffs[i] = cCoeffs[j]
            cCoeffs[j] = Python.int(pow(-1.0, Double(s[i-start])))
        }
        return cCoeffs
    }
    
    private func getChallenge(A: PythonObject, t: PythonObject, omega: PythonObject, message: PythonObject) -> Challenge {
        let h = self.hashlib.shake_256()
        var ACoeffs: [PythonObject] = []
        for i in 0..<self.n {
            for p in 0..<self.m {
                ACoeffs.append(A[i][p].coef)
            }
        }
        h.update(self.np.array(ACoeffs).tobytes())
        var tCoeffs: [PythonObject] = []
        for i in 0..<self.n {
            tCoeffs.append(t[i].coef)
        }
        h.update(self.np.array(tCoeffs).tobytes())
        h.update(omega)
        h.update(message)
        
        let challengeHex = String(h.hexdigest(17))!
        
        return Challenge(
            challengeHex: challengeHex,
            challengePolynomial: self.np.polynomial.Polynomial(self.hashToBall(shake: h))
        )
    }
    
    private func coeffsToPolynomial(listOfCoeffs: [[Int]]) -> PythonObject {
        var poly: [PythonObject] = []
        
        for coeffs in listOfCoeffs {
            poly.append(self.np.polynomial.Polynomial(np.array(coeffs)))
        }
        
        return self.np.array(poly)
    }
    
    private func getLatticePoint(A: PythonObject, s: PythonObject, e: PythonObject) -> PythonObject {
        let res = self.np.inner(A, s)+e
        
        for i in 0..<Int(res.size)! {
            let divmodRes = self.np.polynomial.polynomial.polydiv(res[i].coef, self.f.coef)[1]
            res[i] = self.np.polynomial.Polynomial(self.np.mod(divmodRes, self.q))
        }
        return res
    }
    
    func sign(sk: SecretKey, message: String) -> Signature {
        let s1 = self.coeffsToPolynomial(listOfCoeffs: sk.s1Coeffs)
        let s2 = self.coeffsToPolynomial(listOfCoeffs: sk.s2Coeffs)

        let A = self.getA(seedVector: sk.seedVector)
        let t = self.getLatticePoint(A: A, s: s1, e: s2)
        
        var k = 1
        while true {
            let y1 = self.getRandomPolynomial(maxNorm: (self.gamma+self.approxBeta), size: self.m)
            let y2 = self.getRandomPolynomial(maxNorm: (self.gamma+self.approxBeta), size: self.n)
            
            let w = self.getLatticePoint(A: A, s: y1, e: y2)
            let omega = self.hashlib.sha256()
            omega.update(self.np.array(self.getCoefficients(polyList: w)).tobytes())
            
            let c = self.getChallenge(A: A, t: t, omega: omega.hexdigest().encode(), message: Python.str(message).encode())

            var cs1: [PythonObject] = []
            for i in 0..<Int(s1.size)! {
                cs1.append(self.np.inner(c.challengePolynomial, s1[i]))
            }
            let z1 = self.np.array(cs1) + y1
            for i in 0..<Int(z1.size)! {
                let divmodRes = self.np.polynomial.polynomial.polydiv(z1[i].coef, self.f.coef)[1]
                z1[i] = self.np.polynomial.Polynomial(divmodRes)
            }
            
            var cs2: [PythonObject] = []
            for i in 0..<Int(s2.size)! {
                cs2.append(self.np.inner(c.challengePolynomial, s2[i]))
            }
            let z2 = self.np.array(cs2) + y2
            for i in 0..<Int(z2.size)! {
                let divmodRes = self.np.polynomial.polynomial.polydiv(z2[i].coef, self.f.coef)[1]
                z2[i] = self.np.polynomial.Polynomial(divmodRes)
            }
            if rejectionSampling(z1: z1, z2: z2) {
                print("Success at attempt number "+String(k))
                return Signature(
                    z1Coeffs: self.getCoefficients(polyList: z1),
                    z2Coeffs: self.getCoefficients(polyList: z2),
                    cHex: c.challengeHex,
                    omega: String(omega.hexdigest())!
                )
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
