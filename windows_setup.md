# Windows setup (TUNERSX)

## Recommended baseline
- Windows 10/11
- Python 3.10+ (3.11 preferred)
- Git

## Install

```powershell
python -m venv .venv
./.venv/Scripts/Activate.ps1
pip install --upgrade pip
pip install -e .[can]
```

## Run the CLI

```powershell
python -m tunersx.cli catalog load docs/command_catalog.sample.json
python -m tunersx.cli run can.passive_log --risk PASSIVE
```

## Safety gates

- Anything beyond PASSIVE/READ_ONLY requires:
  - a permitted command catalog entry, and
  - explicit arming (`python -m tunersx.cli policy arm ...`).

Keep your development hardware disconnected from the car until you verify:
- the correct interface/channel/bitrate
- your DBC decode pipeline
- artifact logging paths
