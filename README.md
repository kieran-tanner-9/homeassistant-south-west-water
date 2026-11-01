# South West Water for Home Assistant

[![Validate](../../actions/workflows/validate.yml/badge.svg)](../../actions/workflows/validate.yml)
[![Lint](../../actions/workflows/lint.yml/badge.svg)](../../actions/workflows/lint.yml)
[![Tests](../../actions/workflows/tests.yml/badge.svg)](../../actions/workflows/tests.yml)

Custom integration exposing South West Water smart meter usage to Home Assistant,
for use with the Energy dashboard.

> **Unofficial.** Not affiliated with South West Water. It uses an undocumented
> web API that may change or stop working without notice.

Requires Home Assistant 2026.10 or later.

## Installation (HACS)

1. In HACS, open the menu → **Custom repositories**.
2. Add `https://github.com/kieran-tanner-9/homeassistant-south-west-water` as type **Integration**.
3. Download **South West Water** and restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration**, choose
   **South West Water** and enter your My Account **username or email address**
   (whichever you use to sign in on the South West Water website), your password
   and your smart meter reference.

## What you get

One device with a **Water usage** sensor (m³, `water` device class,
`total_increasing`), usable in the Energy dashboard. Data is polled every
6 hours. Note the total is year-to-date and restarts each 1 January.
Credentials and meter reference are redacted from diagnostics.
