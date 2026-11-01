# Agent rules for homeassistant-south-west-water

Home Assistant custom integration (domain: south_west_water), distributed via HACS.

## Workflow
1. Use Git and GitHub throughout. Work on short-lived branches
   (feat/, fix/, ci/, docs/) and open a pull request into main for each phase.
2. Commit small and often, one logical change per commit, using Conventional
   Commits (feat:, fix:, test:, ci:, docs:, refactor:, chore:). Subject under
   72 chars; explain WHY in the body when not obvious. No vague messages.
3. After every push, check GitHub Actions. If it fails, read the logs, fix the
   cause and push again. Do not start the next task until CI is green. Never
   disable or skip tests to get green.
4. Write tests alongside code.
5. SECURITY: never commit credentials, tokens, meter references, IPs or real
   API responses. Use obvious fakes. Check every diff for secrets.
6. Async only (aiohttp), full type hints, follow current Home Assistant
   developer docs, lint/format with ruff.
7. End each phase with a summary: changes, commits, CI status, proposed next step.

## Target platform
- Home Assistant 2026.10 (minimum 2026.10.0), which requires Python 3.14.
- Check CI uses Python 3.14 and ruff target py314; bump together when HA bumps.
