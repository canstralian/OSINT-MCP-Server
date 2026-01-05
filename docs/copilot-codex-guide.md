# GitHub Copilot & Codex Configuration Guide for the Trading Bot Swarm

## Purpose and Scope
This guide standardizes how GitHub Copilot and Codex operate within the Trading Bot Swarm ecosystem. It defines strict behavioral rules, automation guardrails, and quality gates so AI assistance acts as a disciplined pair programmer. The goal is to ensure consistent code quality, secure automation, and predictable developer experience across services, agents, and shared libraries.

## Configuration Overview
- **Testing & Linting:** Every code change must run the relevant unit/integration tests and linters before merge. Documentation-only changes are exempt.
- **Code Style:** Follow the project formatter and linters (e.g., `ruff`, `black`, or project defaults). Enforce type hints where applicable and prefer small, composable functions.
- **Async Patterns:** Use async I/O for network-bound tasks; avoid blocking calls in event loops. Wrap external I/O with timeouts and cancellations.
- **Security Defaults:** Assume zero trust. Validate inputs, sanitize logs, and prefer least-privilege credentials. Never hardcode secrets; use the secrets manager and CI-provided environment variables.
- **Logging & Observability:** Emit structured logs with correlation/trace IDs. Surface critical events to the central APM. Avoid noisy logs; use rate limits for chatty components.
- **CI/CD Integration:** All branches open pull requests that trigger lint and test gates. Mainline merges require green checks. Release branches run semantic versioning/tagging workflows.
- **Version Control:** Keep changes small and atomic. Use meaningful commit messages. Rebase over merge commits for cleaner history where project policy allows.

## Custom Instruction Behavior
Copilot and Codex should behave predictably and defensively. Apply the following rules by default unless a file-specific policy overrides them.

### Example Rule Set
- Prefer explicit imports and deterministic behavior.
- Never bypass linters or tests; surface failures with actionable context.
- Default to secure primitives: parameterized queries, HTTPS/TLS verification, signed requests.
- Respect rate limits and API terms when generating integration code.
- Propose doc updates when APIs or behaviors change, but do not block code delivery if docs are unchanged.
- Treat infrastructure-as-code with the same rigor as application code (lint, policy checks).

### Conceptual Custom Instructions (YAML)
```yaml
copilot:
  role: "pair-programmer"
  priorities:
    - safety
    - correctness
    - clarity
  defaults:
    testing: "Run tests/linters for code changes; skip for docs-only diffs"
    style: "Follow project lint/format rules; keep functions small and typed"
    async: "Use async for I/O; avoid blocking event loops; add timeouts"
    security: "No secrets in code; validate inputs; prefer least privilege"
    logging: "Structured logs with trace IDs; avoid PII"
    observability: "Expose metrics/traces around critical paths"
  responses:
    - "Explain trade-offs when suggesting risky changes"
    - "Surface missing tests and propose coverage"
    - "Respect rate limits and legal boundaries for integrations"

codex:
  role: "automation-orchestrator"
  behaviors:
    - "Generate CI/CD and infrastructure snippets with secure defaults"
    - "Enforce quality gates: tests + lint required before merge"
    - "Skip test runs for pure documentation updates"
    - "Prompt for secrets to be injected via CI, not committed"
  outputs:
    - "Provide ready-to-run commands and file paths"
    - "Annotate steps that require credentials or approvals"
```

## GitHub Workflow: Lint & Test Automation
Trigger when code changes are proposed. Documentation-only changes (`docs/**`, `**/*.md`) bypass the workflow to save resources.

```yaml
name: quality-gate
on:
  pull_request:
    paths-ignore:
      - "docs/**"
      - "**/*.md"
  push:
    branches: [ main ]
    paths-ignore:
      - "docs/**"
      - "**/*.md"

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Lint
        run: |
          ruff check .
          black --check .
      - name: Test
        run: |
          pytest --maxfail=1 --disable-warnings -q
```

## Best Practices: Releases and Scanning

### Semantic Release & Version Tagging
```yaml
name: semantic-release
on:
  push:
    branches: [ main ]

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - name: Install semantic-release
        run: npm install -g semantic-release @semantic-release/git @semantic-release/changelog @semantic-release/github
      - name: Run semantic-release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: semantic-release
```

### Security & Dependency Scanning
```yaml
name: security-scan
on:
  schedule:
    - cron: "0 6 * * *"
  workflow_dispatch:

jobs:
  dependencies:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Dependency review
        uses: actions/dependency-review-action@v4

  codeql:
    uses: github/codeql-action/codeql-analysis.yml@v3
    with:
      languages: python
```

## Contributor Guidelines
- **Proposing Changes:** Open an issue describing scope, risks, and testing plan. For significant changes, include design docs.
- **Review Criteria:** Security posture, test coverage, performance impact, observability hooks, and adherence to style guides.
- **Validation:** All code changes must show passing lint and test checks. Documentation-only PRs should state "Docs-only; tests not required" in the description.

## Troubleshooting & Optimization
- **Flaky Tests:** Rerun with isolated seed and increased logging; quarantine flaky cases and open a ticket.
- **CI Failures from Linters:** Run the same commands locally (`ruff check .`, `black --check .`) and auto-format before pushing.
- **Dependency Conflicts:** Prefer upgrading minor versions with changelog review; avoid pinning unless required for stability.
- **Rate Limit Issues:** Implement exponential backoff and request coalescing. Cache benign responses when allowed.
- **Secrets & Tokens:** Use GitHub Actions secrets or the project vault. Rotate credentials regularly and audit access.

## Maintenance Schedule
- **Quarterly:** Review Copilot/Codex instruction sets for alignment with current standards.
- **Monthly:** Verify CI workflows, lint/test configurations, and scanning policies remain valid.
- **Release Cadence:** Update semantic-release rules when introducing new package types or breaking changes.

## Closing Note
Standardizing these practices strengthens reliability, performance, and safety across the trading ecosystem. Consistent automation ensures AI assistance remains trustworthy and reinforces excellence in every change.
