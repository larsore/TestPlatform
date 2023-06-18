# FIDO-Inspired Authentication System

This authentication system is developed as part of a master thesis and is inspired by the FIDO protocol specifications defined by the FIDO Alliance. The system consists of four key components: an authenticator iOS application, a client application, a polling server serving as the authenticator back-end, and a relying party server. The system source code is hosted on GitHub.

## Features

- Implements FIDO-inspired authentication protocol.
- Secure communication between client, authenticator, polling server, and relying party server.
- Integration with iOS devices for the authenticator application.
- Provides seamless authentication experience for users.

## System Components

1. **Authenticator iOS Application**:
   - Developed using Swift programming language and iOS frameworks.
   - Enables secure authentication using FIDO-inspired protocols.
   - Provides user-friendly authentication interfaces.
   - Implements secure communication with the polling server.

2. **Client Application**:
   - Interacts with the authenticator and the relying party server.
   - Initiates authentication requests.
   - Receives and verifies authentication responses.

3. **Polling Server**:
   - Serves as the back-end for the authenticators.
   - Handles authentication requests and responses.
   - Maintains secure communication with authenticators and relying party server.
   - Implements necessary security measures to protect sensitive data.

4. **Relying Party Server**:
   - Receives authentication requests from the client application.
   - Validates authentication responses received from the authenticator and polling server.
   - Manages user accounts and authentication data.
   - Integrates with the client application for seamless authentication flow.

## Repository Structure

- `authenticator-ios/`: Contains the source code and documentation for the authenticator iOS application.
- `client-app/`: Contains the source code and documentation for the client application.
- `polling-server/`: Contains the source code and documentation for the polling server.
- `relying-party-server/`: Contains the source code and documentation for the relying party server.

## Installation and Usage

1. Clone the repository using the following command: ```git clone https://github.com/your-username/repo-name.git```



2. Follow the instructions in each component's respective directory to set up and configure the required dependencies.

3. Start by running the relying party server, followed by the polling server, client application, and authenticator iOS application.

4. Refer to the documentation provided in each component directory for detailed instructions on usage and configuration.

## Contributing

We welcome contributions to enhance the system's functionality, security, and usability. If you would like to contribute, please follow the guidelines outlined in the `CONTRIBUTING.md` file.

## License

This authentication system is open-source and released under the [MIT License](LICENSE).

## Contact

For any inquiries or feedback, please contact the project team at [email address].



