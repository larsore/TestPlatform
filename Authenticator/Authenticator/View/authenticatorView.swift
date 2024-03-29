//
//  ContentView.swift
//  Authenticator
//
//  Created by Lars Sørensen on 06/03/2023.
//

import SwiftUI
import Foundation


let backgroundGradient = LinearGradient(
    colors: [Color.mint, Color.clear],
    startPoint: .topLeading, endPoint: .bottom)

struct authenticatorView: View {
    
    struct GrowingButton: ButtonStyle {
        func makeBody(configuration: Configuration) -> some View {
            configuration.label
                .padding()
                .background(.blue)
                .foregroundColor(.white)
                .clipShape(Capsule())
                .scaleEffect(configuration.isPressed ? 1.2 : 1)
                .animation(.easeOut(duration: 0.2), value: configuration.isPressed)
        }
    }
    
    @State private var showRegisterAlert = false
    @State private var showAuthAlert = false
    @State private var isDeciding = false
    @State var isSigning = false
    @State var doneSigning = false
    @State var registerAlertText = ""
    @State var authAlertText = ""
    @State private var lastMessage: CommunicateWithServer.GetMessage? = nil
    @State private var seconds = 1
    @State private var oldOtp = Int.random(in: 1...999999)
    @State private var currentOtp = Int.random(in: 1...999999)
    let eventHandler = EventHandler(deviceID: UIDevice.current.identifierForVendor!.uuidString)
    
    var body: some View {
        VStack {
            ScrollView {
                Text("Authenticator")
                    .font(.largeTitle)
                    .fontWeight(.semibold)
                    .foregroundColor(Color.black)
                    .multilineTextAlignment(.leading)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(25)
                HStack {
                    Text("Current one-time code:")
                        .font(.headline)
                        .foregroundColor(Color.black)
                        .padding(1)
                    Text("\(currentOtp)")
                        .font(.headline)
                        .foregroundColor(Color.black)
                        .padding(1)
                        .bold()
                }
            }
            .alert(registerAlertText, isPresented: $showRegisterAlert) {
                Button("Register") {
                    guard let message: CommunicateWithServer.GetMessage = lastMessage else {
                        print("lastMessage not updated, still nil")
                        return
                    }
                    eventHandler?.handleRegistration(RP_ID: message.rp_id, clientData: message.client_data)
                    isSigning = false
                    doneSigning = true
                    isDeciding = false
                }
                Button("Dismiss", role: .cancel){
                    eventHandler?.handleDismiss(message: "Authenticator chose to dismiss registration", action: "reg")
                    isDeciding = false
                    isSigning = false
                }
            }
            .alert(authAlertText, isPresented: $showAuthAlert) {
                Button("Authenticate") {
                    guard let message: CommunicateWithServer.GetMessage = lastMessage else {
                        print("lastMessage not updated, still nil")
                        return
                    }
                    eventHandler?.handleAuthentication(credential_ID: message.credential_id, RP_ID: message.rp_id, clientData: message.client_data, randomInt: message.random_int)
                    isSigning = false
                    doneSigning = true
                    isDeciding = false
                }
                Button("Dismiss", role: .cancel){
                    eventHandler?.handleDismiss(message: "Authenticator chose to dismiss authentication", action: "auth")
                    isDeciding = false
                    isSigning = false
                }
            }
            Spacer()
            if doneSigning {
                Text("Completed")
                    .foregroundColor(Color.white)
            }
            if isSigning {
                ProgressView()
                    .scaleEffect(2, anchor: .center)
            }
            HStack {
                Text("New OTP in")
                    .font(.headline)
                    .foregroundColor(Color.white)
                    .padding(1)
                Text("\(seconds)")
                    .font(.headline)
                    .foregroundColor(Color.white)
                    .padding(1)
                Text("seconds")
                    .font(.headline)
                    .foregroundColor(Color.white)
                    .padding(1)
            }
            Text("Powered by Lars and Vegard")
                .font(.callout)
                .foregroundColor(Color.white)
                .padding(50)
        }
        .background(backgroundGradient)
        .onAppear(perform: startTimer)
    }
    
    func startTimer() {
        Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true, block: {timer in
            seconds -= 1
            Task {
                if seconds == 0 {
                    seconds = 60
                    await updateOtp()
                }
            }
            Task {
                if !isDeciding {
                    lastMessage = await pollServerFromView()
                }
            }
        })
    }
    
    func updateOtp() async {
        oldOtp = currentOtp
        currentOtp = Int.random(in: 1...999999)
        await eventHandler?.updateOtp(oldOtp: oldOtp, currentOtp: currentOtp)
    }
    
    func pollServerFromView() async -> CommunicateWithServer.GetMessage? {
        let message = await eventHandler?.handlePolling()
        if message != nil {
            isDeciding = true
            isSigning = true
            doneSigning = false
            if message?.credential_id == "" {
                registerAlertText = "Register \(message!.username) to \(message!.rp_id)?"
                showRegisterAlert = true
            } else {
                authAlertText = "Authenticate \(message!.username) to \(message!.rp_id)?\nVerify code: \(message!.random_int)"
                showAuthAlert = true
            }
            return message
        } else {
            return nil
        }
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        authenticatorView()
    }
}
