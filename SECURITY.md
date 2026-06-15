# Security Policy

## Supported Versions

This project is pre-1.0 alpha software. Security fixes are applied to the latest `main` branch until release
branches exist.

## Reporting a Vulnerability

Do not open a public issue for vulnerabilities involving credentials, cookies, login state, or local file
exposure. Report privately through the repository owner's preferred GitHub security contact once the public
repository is configured.

## Sensitive Data

Never commit:

- cookies or exported browser cookie files
- API keys or platform tokens
- browser profiles or login state
- raw media downloads
- generated bundles, reports, or screenshots that may contain private source material

The repository `.gitignore` excludes the expected local output and secret paths, but contributors remain
responsible for checking staged files before committing.

