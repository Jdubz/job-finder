# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in Job Finder, please report it responsibly:

1. **DO NOT** open a public issue
2. Email the maintainers with details about the vulnerability
3. Include steps to reproduce if possible
4. Allow reasonable time for a fix before public disclosure

## Security Considerations

### Credential Storage

This application may store credentials in environment variables or configuration files:

- **Never commit `.env` files** to version control
- Use strong, unique passwords
- Regularly rotate credentials
- Be aware that storing credentials for automated access may violate service Terms of Service

### Web Scraping Risks

**IMPORTANT**: Web scraping carries inherent risks:

- **Legal Risk**: Automated scraping may violate website Terms of Service
- **Account Risk**: Using authenticated scraping may result in account suspension
- **IP Blocking**: Aggressive scraping may result in IP blocks
- **Data Privacy**: Ensure compliance with data protection regulations (GDPR, CCPA, etc.)

### Best Practices

When using this tool:

1. **Review Terms of Service**: Check each website's ToS before scraping
2. **Respect robots.txt**: Configure scrapers to honor robots.txt directives
3. **Rate Limiting**: Use appropriate delays between requests
4. **User-Agent**: Use honest User-Agent strings
5. **Personal Use Only**: This tool is intended for personal job searching, not commercial data harvesting
6. **Credential Protection**: Store credentials securely and never share them

### Dependency Security

- Regularly update dependencies: `pip install --upgrade -r requirements.txt`
- Monitor security advisories for dependencies
- Review `pip audit` or similar tools for known vulnerabilities

## Disclaimer

**USE AT YOUR OWN RISK**: This software is provided "as is" without warranty. Users are solely responsible for:

- Ensuring their use complies with applicable laws and regulations
- Respecting website Terms of Service
- Any consequences resulting from use of this software
- Protecting their credentials and data

The maintainers are not responsible for any misuse of this software or any consequences thereof.

## Responsible Use

This tool is designed for **personal, non-commercial job searching only**. Do not use it for:

- Commercial data harvesting or resale
- Bulk credential testing or unauthorized access
- Circumventing access controls or rate limits
- Any activity that violates website Terms of Service
- Any malicious or unethical purposes

If you're unsure whether your intended use is appropriate, consult with a legal professional.
