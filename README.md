[README.md](https://github.com/user-attachments/files/28110557/README.md)
# Event Decision Support System (DSS)

**Status:** Experimental, Non-Operational, Research Purposes Only

A real-time weather decision support system for large events using experimental REFS (Regional Ensemble Forecast System) ensemble forecast data from AWS.

## Overview

Event DSS provides 60-hour probabilistic weather forecasts optimized for event operations and ground safety. It combines:

- **REFS Ensemble Data** (18 members, 3 km resolution) from AWS S3
- **NWS Alerts** (Watches/Warnings/Advisories, updated every minute)
- **Airport Weather Warnings** (AWW) for KRNO from NWS Reno
- **ASOS Observations** (5-minute updates from Synoptic API)
- **Risk Matrix Analysis** (probability × impact for decision support)

## Features

### Risk Cards (60-Hour Maximum)
Top-left panel shows worst-case values across the entire 60-hour window for each hazard:
- **WIND**: 60-hr max gust (ensemble mean of member maxes)
- **HEAT**: 60-hr max temperature
- **COLD**: 60-hr min temperature  
- **SNOW/RAIN/FZRA/LIGHTNING**: 60-hr max probability
- **VISIBILITY**: 60-hr min visibility
- **FLASH FREEZE**: Joint probability (wet surface + cold wet bulb)

Each shows impact level 1-5 and corresponding risk (0-5).

### 48-Hour Timeline (20 Blocks × 3 Hours)
Top-right panel shows hourly risk progression:
- 20 blocks covering all 60 hours (f001-f060)
- Each block shows highest-probability hour within that 3-hour window
- Color-coded by risk level (green/yellow/orange/red/purple)
- Quick visual of weather evolution

### Current Observations
Bottom-left panel displays real-time ASOS data from KRNO:
- Wind speed/direction/gust
- Temperature/dewpoint/RH
- Visibility, sky condition
- 1-hour precipitation
- Altimeter setting
- Updated every 60 seconds

### Active Alerts
Bottom-right panel shows:
- NWS Watches, Warnings, Advisories (excluding Lake Wind)
- Airport Weather Warnings (AWW) from NWS Reno
- Current status: "NO ACTIVE WATCHES, WARNINGS, OR ADVISORIES" or alert list
- Updated every 60 seconds

## Supported Locations

- **KRNO** — Reno-Tahoe International Airport
- **Burning Man** — Black Rock Playa, Gerlach NV
- **Reno Rodeo** — Reno-Sparks Livestock Events Center
- **Nevada State Fair** — Reno-Sparks Convention Center
- **Night in the Country** — Yerington, NV

Add new locations by creating a new JSON file in `config/locations/`.

## Hazards & Thresholds

| Hazard | Level 1 | Level 2 | Level 3 | Level 4 | Level 5 | Reason |
|--------|---------|---------|---------|---------|---------|--------|
| **WIND** | < 30 mph | 30-45 | 45-58 | 58-65 | > 65 | Debris/high-profile vehicles |
| **SNOW** | Trace | T-0.5"/hr | 0.5-1"/hr | 1-2"/hr | > 2"/hr | Plow operations |
| **RAIN** | < 0.10"/hr | 0.10-0.25 | 0.25-0.50 | 0.50-1.00 | > 1.00 | Drainage capacity |
| **TEMPERATURE COLD** | ≥ 40°F | 32-40 | 20-32 | 10-20 | < 10 | Frostbite/safety |
| **TEMPERATURE HEAT** | < 90°F | 90-95 | 95-100 | 100-105 | > 105 | Heatstroke/safety |
| **FZRA** | None | Trace | Trace-0.01" | 0.01-0.10" | > 0.10" | Chemical treatment |
| **VISIBILITY** | > 5 SM | 3-5 | 1-3 | 0.50-1 | < 0.50 | Driver disorientation |
| **LIGHTNING** | < 5% | 5-25% | 25-50% | 50-75% | > 75% | Ramp/safety closure |
| **FLASH FREEZE** | Dry | Wet + < 36°F Tw | Wet + ≤ 32°F Tw | Wet + ≤ 28°F Tw | Wet + ≤ 25°F Tw | Chemical treatment efficacy |

## Risk Matrix

Combines probability (1-5 likelihood) × impact level (1-5) → risk (0-5 severity)

```
                Impact Level
              1  2  3  4  5
Likelihood 1  1  1  1  2  2
          2  1  1  2  2  3
          3  1  2  2  3  4
          4  1  2  3  4  4
          5  1  2  3  4  5

Risk Levels:
  0 = None
  1 = Little to None
  2 = Minor
  3 = Moderate
  4 = Major
  5 = Extreme
```

## Data Sources

### REFS (Regional Ensemble Forecast System)
- **Status**: Experimental, Non-Operational, Research Purposes Only
- **Source**: AWS S3 bucket `noaa-rrfs-pds` (no credentials needed)
- **Resolution**: 3 km over North America
- **Ensemble Members**: 19 (control + 18 perturbations)
- **Forecast Range**: 60 hours
- **Update Frequency**: 4 cycles per day (00Z, 06Z, 12Z, 18Z)
- **Grid**: Covers CONUS (Continental US), Alaska, Hawaii
- **Variables**: Wind, temperature, precipitation, visibility, wet bulb, lightning probability

### NWS Watches/Warnings/Advisories
- **Source**: `api.weather.gov/alerts/active`
- **Update Frequency**: Every 60 seconds
- **Excluded**: Lake Wind Advisories
- **Coverage**: All alert types (tornado, flood, winter weather, etc.)

### Airport Weather Warnings (AWW)
- **Source**: NWS Reno (AWIPS ID: `AWWRNO`, WMO: `WWUS85 KREV`)
- **Update Frequency**: Every 60 seconds
- **Coverage**: Ground operations hazards specific to KRNO

### ASOS Observations
- **Source**: Synoptic Data API (requires token)
- **Update Frequency**: Every 60 seconds
- **Station**: KRNO
- **Variables**: Wind, temperature, dew point, humidity, visibility, weather, clouds, precipitation, pressure

## System Architecture

```
event-dss/
├── config/                    # All configuration
│   ├── hazards.json          # Hazard definitions (thresholds, units, calculations)
│   ├── locations.json        # Event locations (lat/lon, enabled hazards)
│   ├── data-sources.json     # API endpoints and REFS bucket config
│   └── risk-matrix.json      # Risk calculation matrix
│
├── scripts/                   # Python backend
│   ├── utils.py              # Shared utilities (risk calc, conversions)
│   ├── fetch_refs_data.py    # Download REFS from AWS S3 (Hour 1-2)
│   ├── extract_hazards.py    # Extract hazard values from GRIB2 (Hour 2-4)
│   ├── risk_engine.py        # Calculate risks and build timeline (Hour 4-5)
│   ├── fetch_alerts.py       # NWS alerts + AWW (every minute)
│   └── audit.py              # Validation and debugging
│
├── frontend/                  # React + Vite
│   ├── src/
│   │   ├── App.jsx           # Main dashboard
│   │   ├── App.css
│   │   ├── components/
│   │   │   ├── RiskCards.jsx
│   │   │   ├── Timeline.jsx
│   │   │   ├── Observations.jsx
│   │   │   └── Alerts.jsx
│   │   └── index.js
│   ├── public/index.html
│   ├── package.json
│   └── vite.config.js
│
├── docs/                      # JSON outputs (served by GitHub Pages)
│   ├── risk_cards.json       # 60-hr max/min values + impact levels
│   ├── timeline.json         # 20 blocks × 3 hours with hazard risks
│   ├── alerts.json           # NWS alerts + AWW
│   ├── obs.json              # ASOS observations
│   └── metadata.json         # Last update times, cycle info
│
├── data/                      # Temporary GRIB2 files (git ignored)
│   └── refs_raw/
│
├── .github/workflows/         # GitHub Actions
│   ├── fetch-refs.yml        # Every 6 hours at REFS cycle times
│   ├── fetch-alerts.yml      # Every minute for alerts/obs
│   └── deploy-frontend.yml   # On push to main
│
├── .gitignore
├── README.md                  (this file)
├── DISCLAIMER.md
├── requirements.txt
└── .env.example
```

## Update Schedule

| Component | Frequency | Trigger |
|-----------|-----------|---------|
| REFS forecast | Every 6 hours | 00Z, 06Z, 12Z, 18Z UTC |
| Risk cards | Every 6 hours | After REFS fetch |
| Timeline | Every 6 hours | After REFS extraction |
| NWS alerts | Every 60 seconds | GitHub Actions cron |
| AWW | Every 60 seconds | GitHub Actions cron |
| ASOS obs | Every 60 seconds | GitHub Actions cron |
| Frontend | Every 30 seconds | Polls JSON files |

## Deployment

### GitHub Actions Workflows

**1. Fetch REFS Data** (`fetch-refs.yml`)
- Runs at 02Z, 08Z, 14Z, 20Z UTC (2 hrs after each cycle)
- Downloads ensemble members from AWS S3
- Extracts hazard values
- Calculates 60-hr max/min for risk cards
- Builds timeline (20 blocks)
- Commits `docs/` JSON files to repo

**2. Fetch Alerts & Observations** (`fetch-alerts.yml`)
- Runs every minute
- Fetches NWS alerts (api.weather.gov)
- Fetches AWW from NWS Reno
- Fetches ASOS from Synoptic API
- Commits `docs/alerts.json` and `docs/obs.json`

**3. Deploy Frontend** (`deploy-frontend.yml`)
- Runs on push to `main`
- Builds React app with Vite
- Deploys to GitHub Pages
- Serves at `https://your-org.github.io/event-dss/`

### GitHub Pages Configuration

1. Go to repo **Settings** → **Pages**
2. Set source to: **GitHub Actions**
3. Builds and deploys automatically on push

### Environment Variables

Create `.env` file (not committed):

```bash
# Synoptic API token for ASOS observations
SYNOPTIC_TOKEN=your_token_here

# Optional: NWS API User-Agent
NWS_USER_AGENT=EventDSS/1.0 (research; your-email@example.com)

# Optional: Local development
DEBUG=false
LOCATION=krno
```

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/your-org/event-dss.git
cd event-dss

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..

# Copy environment template
cp .env.example .env
# Edit .env with your Synoptic API token
```

### 2. Test Locally (Requires REFS Data)

```bash
# Fetch REFS ensemble from AWS S3
python scripts/fetch_refs_data.py

# Extract hazards and build timeline
python scripts/extract_hazards.py
python scripts/risk_engine.py

# Verify output
cat docs/risk_cards.json | jq '.hazards | keys'
cat docs/timeline.json | jq '.blocks[0]'

# Run alerts fetcher
python scripts/fetch_alerts.py
```

### 3. Run Frontend

```bash
cd frontend
npm run dev
# Opens http://localhost:5173
```

### 4. Deploy

```bash
# Push to main branch
git add .
git commit -m "Initial Event DSS deployment"
git push origin main

# GitHub Actions runs automatically
# Frontend available at: https://your-org.github.io/event-dss/
```

## Adding New Locations

1. Create `config/locations/my-event.json`:

```json
{
  "id": "my-event",
  "name": "My Event Name",
  "latitude": 39.5,
  "longitude": -119.5,
  "elevation_ft": 4400,
  "timezone": "America/Los_Angeles",
  "nws_zone": "NVZ003",
  "nws_county": "NVC031",
  "hazards": {
    "WIND": true,
    "SNOW": false,
    "RAIN": true,
    "TEMPERATURE": true,
    "FZRA": false,
    "VISIBILITY": true,
    "LIGHTNING": true,
    "FLASH_FREEZE": false
  }
}
```

2. Update `config/locations.json` to include it

3. Restart app or re-run scripts

## Changing Thresholds

Edit `config/hazards.json` for a specific hazard:

```json
{
  "WIND": {
    "thresholds": [25, 40, 55, 65],  // Customize here
    "labels": ["< 25 mph", "25-40", "40-55", "55-65", "> 65"]
  }
}
```

Re-run `risk_engine.py` to recalculate.

## Troubleshooting

### REFS Download Fails
- Check AWS bucket is accessible: `aws s3 ls noaa-rrfs-pds/ --no-sign-request`
- Verify cycle exists (typically available 2-3 hours after cycle time)
- Check network connectivity

### Timeline Empty
- Ensure `fetch_refs_data.py` ran successfully
- Verify GRIB2 files in `data/refs_raw/`
- Run `extract_hazards.py` and `risk_engine.py`

### Frontend Shows No Data
- Check `docs/risk_cards.json` and `docs/timeline.json` exist and are valid
- Verify GitHub Pages is enabled in repo settings
- Check browser console for errors

### Alerts Not Updating
- Verify NWS API is accessible: `curl https://api.weather.gov/alerts/active?point=39.4991,-119.7681`
- Check Synoptic token is valid in `.env`

## License & Attribution

This system uses experimental REFS forecast data from NOAA. NOAA data is public domain. Attribution to NOAA is requested but not required.

## References

- **REFS**: https://vlab.noaa.gov/web/rrfs/
- **NWS API**: https://www.weather.gov/documentation/services-web-api
- **NOAA RRFS AWS**: https://registry.opendata.aws/noaa-rrfs/
- **Synoptic API**: https://synopticdata.com/

## Disclaimer

⚠️ **EXPERIMENTAL, NON-OPERATIONAL, RESEARCH PURPOSES ONLY**

This system uses experimental, non-operational REFS forecast data from AWS. It is NOT suitable for official operational decision-making. For official forecasts, consult the National Weather Service at weather.gov.

Use at your own risk. The authors and NOAA make no warranty of accuracy or suitability for any purpose.
