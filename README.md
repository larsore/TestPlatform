# FIDO-Inspired Authentication System

This authentication system is developed as part of a master thesis and is inspired by the FIDO protocol specifications defined by the FIDO Alliance. The system consists of four key components: an authenticator iOS application, a client application, a polling server serving as the authenticator back-end, and a relying party server. A lattice-based digital signature scheme facilitates authentication.

## Features

- Implements FIDO-inspired authentication protocol.
- Integration with iOS devices for the authenticator application.
- Provides seamless authentication experience for users.

## System Components

1. **Authenticator iOS Application**:
   - Developed using Swift programming language and iOS frameworks.
   - Enables secure authentication using a lattice-based digital signature scheme.
   - Provides user-friendly authentication interfaces.
   - Respponsible for generat8ing key pairs during registration and producing signatures during authentication.

2. **Client Application**:
   - Interacts with the authenticator (via the polling server) and the relying party server.
   - Initiates authentication and registration requests.

3. **Polling Server**:
   - Serves as the back-end for the authenticators.
   - Handles queueing of authentication requests and responses.
   - Maintains communication with authenticators and relying party server.

4. **Relying Party Server**:
   - Receives authentication requests from the client application.
   - Validates authentication responses received from the authenticator via the client application.
   - Manages user accounts and authentication data.
   - Integrates with the client application for seamless authentication flow.
   - Receives and verifies signatures received from the authenticator.

## Repository Structure

- `Authenticator/`: Contains the source code and documentation for the authenticator iOS application.
- `client/`: Contains the source code and documentation for the client application.
- `polling-server/`: Contains the source code and documentation for the polling server.
- `rp-server/`: Contains the source code and documentation for the relying party server.

## Installation and Usage

1. Clone the repository using the following command: ```git clone https://github.com/larsore/TestPlatform.git```

2. Start the system by running the relying party server, followed by the polling server, client application, and authenticator iOS application.

## Contributing

We welcome contributions to enhance the system's functionality, security, and usability.

## License

This authentication system is open-source and released under the [MIT License](https://opensource.org/license/mit/).



