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
    private let approxBeta: Int
    
    private let f: PythonObject
        
    init(q: Int, beta: Int, d: Int, n: Int, m: Int, gamma: Int) {
        self.q = q
        self.beta = beta
        self.d = d
        self.n = n
        self.m = m
        self.gamma = gamma
        self.approxBeta = Int((q-1)/16)
        
        PythonSupport.initialize()
        NumPySupport.sitePackagesURL.insertPythonPath()
        np = Python.import("numpy")
        os = Python.import("os")
        hashlib = Python.import("hashlib")
        
        let fCoeffs = np.array([1] + Array(repeating: 0, count: (self.d - 2)) + [1])
        self.f = self.np.polynomial.Polynomial(fCoeffs)
    }
    
    struct SecretKey: Encodable, Decodable {
        var s1Coeffs: [[Int]]
        var s2Coeffs: [[Int]]
        var seed: Int
    }
    
    struct PublicKey: Codable {
        var seed: Int
        var tCoeffs: [[Int]]
    }
    
    struct KeyPair {
        var secretKey: SecretKey
        var publicKey: PublicKey
    }
    
    struct Signature: Encodable {
        var z1Coeffs: [[Int]]
        var z2Coeffs: [[Int]]
        var cCoeffs: [Int]
        var wCoeffs: [[Int]]
    }
    
    private func getA(seed: PythonObject) -> PythonObject {
        self.np.random.seed(seed)
        var startA: [PythonObject] = []
        for _ in 0..<self.n {
            var row: [PythonObject] = []
            for _ in 0..<self.m {
                row.append(self.np.polynomial.Polynomial(self.np.random.randint(0, self.q, self.d)))
            }
            startA.append(self.np.array(row))
        }
        return self.np.array(startA)
    }
    
    private func getRandomPolynomial(maxNorm: Int, size: Int) -> PythonObject {
        var randomVector: [PythonObject] = []
        let length = 4096
        let rand = os.urandom(length)
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
        var res: [[Int]] = [[]]
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
        
        let sk = SecretKey(
            s1Coeffs: self.getCoefficients(polyList: s1),
            s2Coeffs: self.getCoefficients(polyList: s2),
            seed: Int(Python.int(self.os.urandom(64).hex(), 16))!
        )
        let A = self.getA(seed: Python.int(sk.seed))
        var t = self.getLatticePoint(A: A, s: s1, e: s2)
        
        let pk = PublicKey(
            seed: sk.seed,
            tCoeffs: self.getCoefficients(polyList: t)
        )
        
        return KeyPair(secretKey: sk, publicKey: pk)
    }
    
    private func rejectionSampling(z: PythonObject) -> Bool {
        return self.getCoefficients(polyList: z).flatMap { $0 }.map { abs($0) }.max()! <= self.approxBeta
    }
    
    private static func convertToSwiftList(numpyArray: PythonObject) -> [Int] {
        var list: [Int] = []
        for i in 0..<Int(numpyArray.size)! {
            list.append(Int(numpyArray[i])!)
        }
        return list
    }
    
    private func getChallenge(A: PythonObject, t: PythonObject, w: PythonObject, message: PythonObject) -> PythonObject {
        let h = self.hashlib.sha256()
        h.update(A.tobytes())
        h.update(t.tobytes())
        h.update(w.tobytes())
        h.update(message)
        
        let bits = String(Int(Python.int(h.hexdigest(), 16))!, radix: 2).map { String($0) }
        
        return self.np.polynomial.Polynomial(np.array(bits))
    }
    
    private func coeffsToPolynomial(listOfCoeffs: [[Int]]) -> PythonObject {
        var poly: [PythonObject] = []
        
        for coeffs in listOfCoeffs {
            poly.append(self.np.polynomial.Polynomial(np.array(coeffs)))
        }
        
        return self.np.array(poly)
    }
    
    private func getLatticePoint(A: PythonObject, s: PythonObject, e: PythonObject) -> PythonObject {
        var res = self.np.inner(A, s)+e
        for i in 0..<Int(res.size)! {
            res[i] = self.np.polynomial.Polynomial(self.np.mod((self.np.polynomial.Polynomial.divmod(res[i], self.f)[1]).coef, self.q))
        }
        return res
    }
    
    func sign(sk: SecretKey, message: String) -> Signature {
        let s1 = self.coeffsToPolynomial(listOfCoeffs: sk.s1Coeffs)
        let s2 = self.coeffsToPolynomial(listOfCoeffs: sk.s2Coeffs)
        
        let A = self.getA(seed: Python.int(sk.seed))
        var t = self.getLatticePoint(A: A, s: s1, e: s2)
        var k = 1
        while true {
            let y1 = self.getRandomPolynomial(maxNorm: (self.gamma+self.approxBeta), size: self.m)
            let y2 = self.getRandomPolynomial(maxNorm: (self.gamma+self.approxBeta), size: self.n)
            
            var w = self.getLatticePoint(A: A, s: y1, e: y2)
        
            let c = self.getChallenge(A: A, t: t, w: w, message: Python.str(message).encode())
            
            var cs1: [PythonObject] = []
            for i in 0..<Int(s1.size)! {
                cs1.append(self.np.inner(c, s1[i]))
            }
            var z1 = self.np.array(cs1) + y1
            for i in 0..<Int(z1.size)! {
                z1[i] = self.np.polynomial.Polynomial((self.np.polynomial.Polynomial.divmod(z1[i], self.f)[1]).coef)
            }
            
            var cs2: [PythonObject] = []
            for i in 0..<Int(s2.size)! {
                cs2.append(self.np.inner(c, s2[i]))
            }
            var z2 = self.np.array(cs2) + y2
            for i in 0..<Int(z2.size)! {
                z2[i] = self.np.polynomial.Polynomial((self.np.polynomial.Polynomial.divmod(z2[i], self.f)[1]).coef)
            }
            
            if rejectionSampling(z: z1) && rejectionSampling(z: z2) {
                print("Success at attempt number "+String(k))
                
                var cCoeffs: [Int] = []
                for i in 0..<Int(c.coef.size)! {
                    cCoeffs.append(Int(c.coef[i])!)
                }
                
                return Signature(
                    z1Coeffs: self.getCoefficients(polyList: z1),
                    z2Coeffs: self.getCoefficients(polyList: z2),
                    cCoeffs: cCoeffs,
                    wCoeffs: self.getCoefficients(polyList: w))
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
