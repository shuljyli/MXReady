# Security policy

MXReady reads untrusted public repositories, so its own boundaries are part of the product.
The design is documented in [docs/security.md](docs/security.md); this file covers how to report a
problem.

## Reporting a vulnerability

Report suspected vulnerabilities privately through GitHub Security Advisories — open the
**Security** tab and choose **Report a vulnerability**. Please do not open a public issue first.

Include the affected version, the command or endpoint you used, and what you expected instead.
A reproduction against a public repository is ideal. Do not attach private source code,
credentials or internal host details.

## What counts as a vulnerability

In scope:

- escaping the read-only scan boundary, for example getting code from a scanned repository to run;
- bypassing the repository host allowlist, URL normalization, clone limits or archive size limits;
- command injection through the verification manifest, the runner or an uploaded result;
- leaking credentials, local paths, user names or hostnames through reports, logs or runner output;
- a crafted repository that makes a scan hang or exhaust memory far beyond the documented budgets.

Out of scope:

- a static finding that turns out to be a false positive — open a regular issue with a fixture;
- the absence of a compatibility verdict, which is deliberate: MXReady does not score compatibility;
- vulnerabilities in the third-party projects that get scanned.

## Supported versions

Only the latest release receives fixes. This is a single-maintainer community prototype with no
formal response-time commitment.
