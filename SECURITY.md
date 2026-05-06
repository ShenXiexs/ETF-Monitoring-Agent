# Security Policy

This project is designed for local demos and controlled challenge environments.

## Defaults

- The server binds to `127.0.0.1` by default.
- The frontend uses one product endpoint: `POST /workspace`.
- The app does not require external document permissions for v1.
- The seeded PRD knowledge pack is local JSON and should not contain secrets.
- Exported PRD Markdown is generated from the current editor content and deterministic review output.

## Guidance

- Do not commit real company PRDs, credentials, private tokens, or customer data.
- Use synthetic or sanitized PRD/MRD samples for demos.
- If you set `HOST=0.0.0.0`, add your own network controls, authentication, and TLS.
- Treat generated PRD content as a draft. Human review remains required before delivery.

## Reporting

If you find a security issue, include:

1. Affected interface or file
2. Reproduction steps
3. Expected impact
4. Suggested remediation
