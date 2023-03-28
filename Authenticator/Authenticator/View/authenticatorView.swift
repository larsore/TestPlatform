//
//  ContentView.swift
//  Authenticator
//
//  Created by Lars Sørensen on 06/03/2023.
//

import SwiftUI
import LocalAuthentication
import Foundation

let backgroundGradient = LinearGradient(
    colors: [Color.mint, Color.clear],
    startPoint: .topLeading, endPoint: .bottom)

struct authenticatorView: View {
    
    @State private var showRegisterAlert = false
    @State private var showAuthAlert = false
    @State private var isDeciding = false
    @State private var deviceID = UIDevice.current.identifierForVendor!.uuidString
    @State private var lastMessage: CommunicateWithServer.GetMessage? = nil
    let keychain = AccessKeychain()
    let eventHandler = EventHandler()
    
    var body: some View {
        VStack {
            ScrollView {
                Text("Baby Dilithium\nAuthenticator")
                    .font(.largeTitle)
                    .fontWeight(.semibold)
                    .foregroundColor(Color.black)
                    .multilineTextAlignment(.leading)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(25)
                
            }
            .refreshable {
                Task {
                    lastMessage = await pollServerFromView()
                }
            }
            .alert("Register??", isPresented: $showRegisterAlert) {
                Button("Register") {
                    guard let message: CommunicateWithServer.GetMessage = lastMessage else {
                        print("lastMessage not updated, still nil")
                        return
                    }
                    eventHandler.handleRegistration(RP_ID: message.rp_id, clientData: message.client_data, deviceID: deviceID)
                    isDeciding = false
                }
                Button("Dismiss", role: .cancel){
                    eventHandler.handleDismiss(message: "Authenticator chose to dismiss registration", action: "reg")
                    isDeciding = false
                }
            }
            .alert("Authenticate??", isPresented: $showAuthAlert) {
                Button("Authenticate") {
                    guard let message: CommunicateWithServer.GetMessage = lastMessage else {
                        print("lastMessage not updated, still nil")
                        return
                    }
                    eventHandler.handleAuthentication(credential_ID: message.credential_id, RP_ID: message.rp_id, clientData: message.client_data)
                    isDeciding = false
                }
                Button("Dismiss", role: .cancel){
                    eventHandler.handleDismiss(message: "Authenticator chose to dismiss authentication", action: "auth")
                    isDeciding = false
                }
            }

            Spacer()
            
            Text("Powered by Lars and Vegard")
                .font(.callout)
                .foregroundColor(Color.white)
        }
        .background(backgroundGradient)
        .onAppear(perform: startTimer)
    }
    
    func startTimer() {
        Timer.scheduledTimer(withTimeInterval: 3.0, repeats: true, block: {timer in
            Task {
                if !isDeciding {
                    lastMessage = await pollServerFromView()
                }
            }
            
        })
    }
    
    func pollServerFromView() async -> CommunicateWithServer.GetMessage? {
        let message = try? await CommunicateWithServer.pollServer(deviceID: deviceID)
        if message != nil {
            isDeciding = true
            if message?.credential_id == "" {
                showRegisterAlert = true
            } else {
                showAuthAlert = true
            }
            return message
        } else {
            print("Server has no messages for the specific ID")
            return nil
        }
    }
}


struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        authenticatorView()
    }
}
