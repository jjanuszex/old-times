# Security Policy

## Supported Versions

We release patches for security vulnerabilities. Which versions are eligible for receiving such patches depends on the CVSS v3.0 Rating:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

Please report (suspected) security vulnerabilities to **[jjanuszex@gmail.com]**. You will receive a response from us within 48 hours. If the issue is confirmed, we will release a patch as soon as possible depending on complexity but historically within a few days.

## Security Considerations

### Asset Pipeline Security

The asset pipeline processes external assets and configurations. Please be aware:

- **TOML Configuration**: Validate all TOML files before processing
- **External Assets**: Assets from external sources (Kenney.nl, AI providers) are processed locally
- **File System Access**: The pipeline writes to the assets directory - ensure proper permissions
- **API Keys**: Store API keys securely using environment variables

### Game Security

- **Save Files**: Game save files use RON format and should be validated on load
- **Mod Loading**: Mods can execute code - only load trusted mods
- **Network**: Currently single-player only, but future multiplayer features will need security review

### Development Security

- **Dependencies**: Regularly update Rust and Python dependencies
- **CI/CD**: GitHub Actions workflows are configured with minimal permissions
- **Secrets**: API keys and tokens are stored as GitHub secrets

## Best Practices

When contributing to this project:

1. **Input Validation**: Always validate external input (files, network data, user input)
2. **Error Handling**: Don't expose sensitive information in error messages
3. **Dependencies**: Keep dependencies up to date and review new ones
4. **Permissions**: Use minimal required permissions for file operations
5. **Logging**: Don't log sensitive information (API keys, personal data)

## Vulnerability Response

1. **Assessment**: We will assess the vulnerability within 48 hours
2. **Fix Development**: Critical vulnerabilities will be patched within 7 days
3. **Release**: Security patches will be released as soon as possible
4. **Disclosure**: We will coordinate disclosure with the reporter
5. **Credit**: Security researchers will be credited (if desired) in release notes

## Contact

For security-related questions or concerns, please contact:
- Email: jjanuszex@gmail.com
- GitHub: Create a private security advisory

Thank you for helping keep Old Times RTS secure!