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
    private let subprocess: PythonObject
    
    private let q: Int
    private let beta: Int
    private let d: Int
    private let n: Int
    private let m: Int
    private let gamma: Int
    private let eta: Int
    private let approxBeta: Int
    
    private let f: PythonObject
        
    init(q: Int, beta: Int, d: Int, n: Int, m: Int, gamma: Int, eta: Int) {
        self.q = q
        self.beta = beta
        self.d = d
        self.n = n
        self.m = m
        self.gamma = gamma
        self.eta = eta
        self.approxBeta = Int((q-1)/16)
        
        PythonSupport.initialize()
        NumPySupport.sitePackagesURL.insertPythonPath()
        self.np = Python.import("numpy")
        self.os = Python.import("os")
        self.hashlib = Python.import("hashlib")
        self.subprocess = Python.import("subprocess")
        
        let fCoeffs = np.array([1] + Array(repeating: 0, count: (self.d - 2)) + [1])
        self.f = self.np.polynomial.Polynomial(fCoeffs)
    }
    
    struct SecretKey: Encodable, Decodable {
        var s1Coeffs: [[Int]]
        var s2Coeffs: [[Int]]
        var Aseed: String
    }
    
    struct PublicKey: Codable {
        var Aseed: String
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
    
    private func expandMask(seed: PythonObject, kappa: Int, noOfPoly: Int) -> PythonObject {
        let h = self.hashlib.shake_256(seed)
        h.update(Python.str(Python.int(kappa)).encode())
        var y: [PythonObject] = []
        var repr = 0
        for _ in 0..<noOfPoly {
            var coefs: [Int] = []
            while coefs.count < self.d {
                h.update(Python.str(repr).encode())
                let sample = h.digest(5)
                let b0 = Int(sample[0])!
                let b1 = Int(sample[1])!
                let b2mark = Int(sample[2])! & 15
                let b2markmark = Int(sample[2])! / 16
                let b3 = Int(sample[3])!
                let b4 = Int(sample[4])!
                
                let candids = [b2mark*NSDecimalNumber(decimal: pow(2, 16)).intValue + b1*NSDecimalNumber(decimal: pow(2, 8)).intValue + b0,
                               b4*NSDecimalNumber(decimal: pow(2, 12)).intValue + b3*NSDecimalNumber(decimal: pow(2, 4)).intValue + b2markmark]
                for candid in candids {
                    if candid < 2*(self.approxBeta+self.gamma)+1 {
                        coefs.append(candid - (self.approxBeta+self.gamma))
                    }
                }
                repr+=5
            }
            y.append(self.np.polynomial.Polynomial(Array(coefs[0..<self.d])))
        }
        return self.np.array(y)
    }
    
    private func expandS(seed: PythonObject, noOfPoly: Int) -> PythonObject {
        let h = self.hashlib.shake_256(seed)
        var s: [PythonObject] = []
        var repr = 0
        for _ in 0..<noOfPoly {
            var coefs: [Int] = []
            while coefs.count < self.d {
                h.update(Python.str(repr).encode())
                let sampleString = String(Python.bin(h.digest(1)[0]))!
                let index = sampleString.index(sampleString.startIndex, offsetBy: 2)
                var sampleArray = Array(sampleString[index..<sampleString.endIndex])
                if sampleArray.count < 4 {
                    for _ in 0..<4-sampleArray.count {
                        sampleArray.insert("0", at: 0)
                    }
                }
                var sampleInt = 0
                for i in 0..<4 {
                    sampleInt += Int(String(sampleArray[i]))! * NSDecimalNumber(decimal: pow(2, i)).intValue
                }
                if sampleInt < 2*self.beta+1 {
                    coefs.append(sampleInt-self.beta)
                }
                repr += 1
            }
            s.append(self.np.polynomial.Polynomial(coefs))
        }
        return self.np.array(s)
    }
    
    private func expandA(seed: PythonObject) -> PythonObject {
        let h = self.hashlib.shake_128(seed)
        var A: [[PythonObject]] = []
        var repr = 0
        for _ in 0..<self.n {
            var row: [PythonObject] = []
            for _ in 0..<self.m {
                var coefs: [Int] = []
                while coefs.count < self.d {
                    h.update(Python.str(repr).encode())
                    let sample = h.digest(3)
                    let b0 = Int(Python.int(Python.bin(sample[0]), 2))!
                    let b1 = Int(Python.int(Python.bin(sample[1]), 2))!
                    let b2string = String(Python.bin(sample[2]))!
                    let index = b2string.index(b2string.startIndex, offsetBy: 2)
                    var b2Array = Array(b2string[index..<b2string.endIndex])
                    if b2Array.count < 8 {
                        for _ in 0..<8-b2Array.count {
                            b2Array.insert("0", at: 0)
                        }
                    } else {
                        b2Array[0] = "0"
                    }
                    var b2Int = 0
                    for i in 0..<b2Array.count {
                        b2Int += Int(String(b2Array[i]))! * NSDecimalNumber(decimal: pow(2, b2Array.count - (i+1))).intValue
                    }
                    let candid = b2Int * NSDecimalNumber(decimal: pow(2, 16)).intValue + b1 * NSDecimalNumber(decimal: pow(2, 8)).intValue + b0
                    if candid < self.q {
                        coefs.append(candid)
                        
                    }
                    repr += 1
                }
                row.append(self.np.polynomial.Polynomial(coefs))
            }
            A.append(row)
        }
        return self.np.array(A)
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
    
    private func getRandomBytes(count: Int) -> [Int8]? {
        var bytes = [Int8](repeating: 0, count: count)
        let status = SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes)
        if status == errSecSuccess {
            return bytes
        } else {
            print("Unable to sample random bytes")
            return nil
        }
    }
    
    public func generateKeyPair() -> KeyPair? {
        guard let zeta = self.getRandomBytes(count: 32) else {
            print("Unable to sample zeta with getRandomBytes")
            return nil
        }
        let h = self.hashlib.shake_256(self.np.array(zeta).tobytes())
        let sample = h.hexdigest(96)
        var rho1 = ""
        for i in 0..<32 {
            rho1 += String(sample[i])!
        }
        var rho2 = ""
        for i in 32..<64 {
            rho2 += String(sample[i])!
        }
        var rhomark = ""
        for i in 64..<96 {
            rhomark += String(sample[i])!
        }
        let s1 = self.expandS(seed: Python.str(rho1).encode(), noOfPoly: self.m)
        let s2 = self.expandS(seed: Python.str(rho2).encode(), noOfPoly: self.n)
        
        let sk = SecretKey(
            s1Coeffs: self.getCoefficients(polyList: s1),
            s2Coeffs: self.getCoefficients(polyList: s2),
            Aseed: rhomark
        )
        let A = self.expandA(seed: Python.str(sk.Aseed).encode())
        let t = self.getLatticePoint(A: A, s: s1, e: s2)
        let pk = PublicKey(
            Aseed: sk.Aseed,
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
    
    private func hashToBall(seed: PythonObject) -> PythonObject {
        let cCoeffs = self.np.zeros(256)
        var k = 0
        var s: [Int] = []
        let shake = self.hashlib.shake_256(seed)
        while true {
            let byteString = String(Python.bin(Python.int(shake.digest(k+1)[k])))!
            let index = byteString.index(byteString.startIndex, offsetBy: 2)
            let byteArray = Array(byteString[index..<byteString.endIndex])
            for bit in byteArray {
                s.append(Int(String(bit))!)
            }
            k += 1
            if s.count >= self.eta {
                break
            }
        }
        
        var taken: [Int] = []
        let start = 196
        for i in start..<256 {
            var j = 257
            while j > i {
                if !taken.contains(Int(shake.digest(k+1)[k])!) {
                    j = Int(shake.digest(k+1)[k])!
                }
                k += 1
            }
            taken.append(j)
            cCoeffs[i] = cCoeffs[j]
            cCoeffs[j] = Python.int(pow(-1.0, Double(s[i-start])))
        }
        return cCoeffs
    }
    
    private func getChallenge(Aseed: PythonObject, t: PythonObject, omega: PythonObject, message: PythonObject) -> Challenge {
        let h = self.hashlib.shake_256()
        h.update(Aseed)
        var tCoeffs: [PythonObject] = []
        for i in 0..<self.n {
            tCoeffs.append(t[i].coef)
        }
        h.update(self.np.array(tCoeffs).tobytes())
        h.update(omega)
        h.update(message)
        
        let challengeHex = String(h.hexdigest(48))!
        
        return Challenge(
            challengeHex: challengeHex,
            challengePolynomial: self.np.polynomial.Polynomial(self.hashToBall(seed: h.hexdigest(48).encode()))
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

        let A = self.expandA(seed: Python.str(sk.Aseed).encode())
        let t = self.getLatticePoint(A: A, s: s1, e: s2)
        let rho1 = self.getRandomBytes(count: 32)
        let rho2 = self.getRandomBytes(count: 32)
        var k = 1
        var kappa = 0
        while true {
            let y1 = self.expandMask(seed: self.np.array(rho1).tobytes(), kappa: kappa, noOfPoly: self.m)
            let y2 = self.expandMask(seed: self.np.array(rho2).tobytes(), kappa: kappa, noOfPoly: self.n)
            
            let w = self.getLatticePoint(A: A, s: y1, e: y2)
            let omega = self.hashlib.shake_256()
            omega.update(self.np.array(self.getCoefficients(polyList: w)).tobytes())
            
            let c = self.getChallenge(Aseed: Python.str(sk.Aseed).encode(), t: t, omega: omega.hexdigest(48).encode(), message: Python.str(message).encode())

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
                    omega: String(omega.hexdigest(48))!
                )
            }
            k += 1
            kappa += self.n
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
