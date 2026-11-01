<p align="center">
  <img src="https://raw.githubusercontent.com/kieran-tanner-9/homeassistant-south-west-water/main/custom_components/south_west_water/brand/icon.png" alt="South West Water" width="128">
</p>

<h1 align="center">South West Water for Home Assistant</h1>

<p align="center">
  Smart meter water usage in Home Assistant, ready for the Energy dashboard.
</p>

<p align="center">
  <a href="https://github.com/kieran-tanner-9/homeassistant-south-west-water/releases"><img alt="Release" src="https://img.shields.io/github/v/release/kieran-tanner-9/homeassistant-south-west-water?style=flat-square"></a>
  <a href="https://hacs.xyz"><img alt="HACS" src="https://img.shields.io/badge/HACS-Custom-orange?style=flat-square"></a>
  <a href="https://github.com/kieran-tanner-9/homeassistant-south-west-water/actions/workflows/validate.yml"><img alt="Validate" src="https://img.shields.io/github/actions/workflow/status/kieran-tanner-9/homeassistant-south-west-water/validate.yml?branch=main&label=validate&style=flat-square"></a>
  <a href="https://github.com/kieran-tanner-9/homeassistant-south-west-water/actions/workflows/lint.yml"><img alt="Lint" src="https://img.shields.io/github/actions/workflow/status/kieran-tanner-9/homeassistant-south-west-water/lint.yml?branch=main&label=lint&style=flat-square"></a>
  <a href="https://github.com/kieran-tanner-9/homeassistant-south-west-water/actions/workflows/tests.yml"><img alt="Tests" src="https://img.shields.io/github/actions/workflow/status/kieran-tanner-9/homeassistant-south-west-water/tests.yml?branch=main&label=tests&style=flat-square"></a>
  <a href="LICENSE"><img alt="Licence" src="https://img.shields.io/github/license/kieran-tanner-9/homeassistant-south-west-water?style=flat-square"></a>
</p>

<p align="center">
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=kieran-tanner-9&repository=homeassistant-south-west-water&category=integration"><img alt="Open in HACS" src="https://my.home-assistant.io/badges/hacs_repository.svg"></a>
  <a href="https://my.home-assistant.io/redirect/config_flow_start/?domain=south_west_water"><img alt="Add integration" src="https://my.home-assistant.io/badges/config_flow_start.svg"></a>
</p>

> [!WARNING]
> **Unofficial.** Not affiliated with South West Water. It uses an undocumented
> web API that may change or stop working without notice.

## Features

- 💧 **Water usage sensor** in m³ (`water` device class, `total_increasing`), usable in the Energy dashboard.
- 🔌 **One device** per meter, set up entirely from the UI.
- 🔁 **Re-authentication prompt** if your password stops working.
- 🕒 Polls every 6 hours, with a `last_reading` attribute showing when the utility last read the meter.
- 🔒 Credentials and meter reference are redacted from diagnostics.

## Requirements

- Home Assistant 2026.10 or later
- A South West Water **My Account** login with a smart meter

## Installation (HACS)

1. Click **Open in HACS** above, or in HACS open the menu → **Custom repositories** and add
   `https://github.com/kieran-tanner-9/homeassistant-south-west-water` as type **Integration**.
2. Download **South West Water** and restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration** and choose **South West Water**.

## Configuration

| Field | What to enter |
| --- | --- |
| Username or email address | Whatever you type into the sign-in box on My Account |
| Password | Your My Account password |
| Meter reference | Your smart meter reference number |

> [!NOTE]
> The usage total is **year-to-date** and restarts each 1 January. Home Assistant
> treats that drop as a meter reset, so long-term statistics keep adding up.

## Troubleshooting

If the integration fails to set up, enable debug logging and check the log:

```yaml
logger:
  logs:
    custom_components.south_west_water: debug
```

The log shows the HTTP status and reply for failed requests, never your credentials.

## Disclaimer

This project is not endorsed by or connected to South West Water. Use at your own risk.
