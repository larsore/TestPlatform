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
    
    let pasteboard = UIPasteboard.general
    
    @State private var showRegisterAlert = false
    @State private var showAuthAlert = false
    @State private var isDeciding = false
    @State private var showCheckMark = false
    @State private var showDeviceID = false
    @State var isSigning = false
    @State var doneSigning = false
    @State var registerAlertText = ""
    @State var authAlertText = ""
    @State private var deviceID = UIDevice.current.identifierForVendor!.uuidString
    @State private var lastMessage: CommunicateWithServer.GetMessage? = nil
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
                
                Button("Authenticator ID") {
                    showDeviceID = true
                    showCheckMark = false
                    //eventHandler?.testCrypto()
                }
                .buttonStyle(GrowingButton())
                .padding(20)
                
                if showDeviceID {
                    VStack {
                        Text(deviceID)
                            .font(.subheadline)
                            .foregroundColor(Color.black)
                            .padding(10)
                        if !showCheckMark {
                            Button("Copy to clipboard") {
                                pasteboard.string = deviceID
                                showCheckMark = true
                            }
                            .buttonStyle(.bordered)
                            .tint(Color(white: 0.3745))
                        } else {
                            let startX = 200
                            let startY = 18
                            Path() { path in
                            path.move(to: CGPoint(x: startX, y: startY))
                            path.addLine(to: CGPoint(x: startX+10, y: startY+15))
                            path.addLine(to: CGPoint(x: startX+25, y: startY-10))
                            }
                            .stroke(Color.green, lineWidth: 3)
                        }
                    }
                }
            }
            .refreshable {
                Task {
                    lastMessage = await pollServerFromView()
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
                    eventHandler?.handleAuthentication(credential_ID: message.credential_id, RP_ID: message.rp_id, clientData: message.client_data)
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
            
            
            Text("Powered by Lars and Vegard")
                .font(.callout)
                .foregroundColor(Color.white)
                .padding(50)
        }
        .background(backgroundGradient)
        .onAppear(perform: eventHandler?.test)
        //.onAppear(perform: startTimer)
    }
    
    func startTimer() {
        Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true, block: {timer in
            Task {
                if !isDeciding {
                    lastMessage = await pollServerFromView()
                }
            }
            
        })
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
                authAlertText = "Authenticate \(message!.username) to \(message!.rp_id)?"
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
