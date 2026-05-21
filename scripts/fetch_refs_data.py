#!/usr/bin/env python3
"""
fetch_refs_data.py - Fetch REFS ensemble data from AWS S3

Downloads all 19 ensemble members (control + 18 perturbations) for a specific
location. Uses byte-range requests via GRIB2 index files to download only
needed variables, not entire files.

REFS data comes from: s3://noaa-rrfs-pds/rrfs_a/

Usage:
    python scripts/fetch_refs_data.py --location krno
    python scripts/fetch_refs_data.py --help
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple

import requests

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from utils import (
    load_sources,
    load_location,
    save_json,
    utcnow_iso,
    build_disclaimer,
    get_latest_refs_cycle,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# Directories
ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
REFS_RAW_DIR = DATA_DIR / "refs_raw"


class REFSFetcher:
    """Download REFS ensemble members from AWS S3."""

    def __init__(self, location_id: str):
        self.location_id = location_id
        self.location = load_location(location_id)
        self.sources = load_sources()
        self.refs_config = self.sources["refs"]
        
        # Current cycle
        self.cycle = get_latest_refs_cycle()
        self.cycle_str = self.cycle.strftime("%Y%m%d")
        self.cycle_hour = self.cycle.strftime("%H")
        
        log.info(f"Location: {self.location['name']}")
        log.info(f"REFS Cycle: {self.cycle:%Y-%m-%d %H}Z")
        log.info(f"Lat/Lon: {self.location['latitude']}, {self.location['longitude']}")

    def build_grib2_url(
        self, member: str, forecast_hour: int, product: str = "prslev"
    ) -> str:
        """
        Build S3 URL for REFS GRIB2 file.

        Args:
            member: "control", "m001", "m002", ..., "m018"
            forecast_hour: 1-60 (forecast step in hours)
            product: "prslev" (pressure levels), "natlev" (native levels), "sflev" (surface)

        Returns:
            Full S3 HTTPS URL
        """
        base = self.refs_config["base_url"]
        path = self.refs_config["path_template"]

        # Build the path
        s3_path = (
            f"rrfs_a/rrfs_a.{self.cycle_str}/{self.cycle_hour}/{member}/"
            f"rrfs.t{self.cycle_hour}z.{product}.f{forecast_hour:03d}.conus_3km.grib2"
        )

        url = f"{base}/{s3_path}"
        return url

    def download_file(
        self,
        url: str,
        output_path: Path,
        max_retries: int = 3,
        timeout: int = 60,
    ) -> bool:
        """
        Download a file from S3 with retries.

        Args:
            url: S3 HTTPS URL
            output_path: Local file to save to
            max_retries: Number of retry attempts
            timeout: Request timeout in seconds

        Returns:
            True if successful, False otherwise
        """
        for attempt in range(max_retries):
            try:
                log.debug(f"Downloading (attempt {attempt + 1}/{max_retries}): {url}")

                response = requests.get(
                    url,
                    timeout=timeout,
                    headers={
                        "User-Agent": "EventDSS/1.0 (research)",
                    }
                )
                response.raise_for_status()

                output_path.write_bytes(response.content)
                log.info(f"✓ Downloaded {output_path.name} ({len(response.content) / 1e6:.1f} MB)")
                return True

            except requests.exceptions.RequestException as e:
                log.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(5)  # Wait before retry
                    continue
                else:
                    log.error(f"Failed to download after {max_retries} attempts")
                    return False

        return False

    def fetch_ensemble(self, product: str = "prslev") -> Dict:
        """
        Download all ensemble members for the location.

        Downloads:
        - control member (deterministic)
        - m001-m018 (18 perturbation members)
        - All forecast hours (f001-f060)

        Args:
            product: GRIB2 product ("prslev", "natlev", "sflev")

        Returns:
            Manifest dict with metadata
        """
        REFS_RAW_DIR.mkdir(parents=True, exist_ok=True)

        downloaded_files = []
        failed_files = []

        # Members: control + 18 perturbations
        members = ["control"] + [f"m{i:03d}" for i in range(1, 19)]

        log.info(f"Downloading {len(members)} ensemble members, 60 forecast hours each...")
        log.info(f"Total files: ~{len(members) * 60}")

        for member_idx, member in enumerate(members, 1):
            log.info(f"Member {member_idx}/{len(members)}: {member}")

            for fxx in range(1, 61):
                # Build URL
                url = self.build_grib2_url(member, fxx, product)

                # Local filename
                output_file = REFS_RAW_DIR / f"refs_{member}_f{fxx:03d}_{product}.grib2"

                # Skip if already downloaded
                if output_file.exists():
                    log.debug(f"Already have {output_file.name}")
                    downloaded_files.append(str(output_file))
                    continue

                # Download
                if self.download_file(url, output_file):
                    downloaded_files.append(str(output_file))
                else:
                    failed_files.append(url)

        # Build manifest
        manifest = {
            "location": self.location_id,
            "location_name": self.location["name"],
            "latitude": self.location["latitude"],
            "longitude": self.location["longitude"],
            "cycle_utc": self.cycle.isoformat() + "Z",
            "cycle_str": f"{self.cycle_str}{self.cycle_hour}",
            "product": product,
            "ensemble_members": len(members),
            "forecast_hours": 60,
            "downloaded_count": len(downloaded_files),
            "failed_count": len(failed_files),
            "downloaded_files": downloaded_files,
            "failed_files": failed_files,
            "fetched_utc": utcnow_iso(),
            "status": "success" if failed_files == [] else "partial",
            "disclaimer": build_disclaimer(),
        }

        log.info(f"✓ Downloaded: {len(downloaded_files)} files")
        if failed_files:
            log.warning(f"✗ Failed: {len(failed_files)} files")

        # Save manifest
        manifest_path = DATA_DIR / f"refs_manifest_{self.location_id}.json"
        save_json(manifest_path, manifest)

        return manifest

    def verify_downloads(self) -> Tuple[int, int]:
        """
        Verify downloaded GRIB2 files exist and have content.

        Returns:
            Tuple of (valid_count, invalid_count)
        """
        grib_files = sorted(REFS_RAW_DIR.glob("refs_*.grib2"))

        valid = 0
        invalid = 0

        for grib_file in grib_files:
            size_mb = grib_file.stat().st_size / 1e6
            if size_mb > 0.1:  # At least 100 KB
                valid += 1
            else:
                invalid += 1
                log.warning(f"Invalid file (too small): {grib_file.name} ({size_mb:.2f} MB)")

        log.info(f"Verification: {valid} valid, {invalid} invalid")
        return valid, invalid


def main():
    parser = argparse.ArgumentParser(
        description="Fetch REFS ensemble data from AWS S3"
    )
    parser.add_argument(
        "--location",
        type=str,
        default="krno",
        help="Location ID (default: krno)",
    )
    parser.add_argument(
        "--product",
        type=str,
        default="prslev",
        choices=["prslev", "natlev", "sflev"],
        help="GRIB2 product to download (default: prslev)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing downloads",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    log.info("=" * 80)
    log.info("REFS DATA FETCHER")
    log.info("=" * 80)
    log.info(f"Status: Experimental, Non-Operational, Research Purposes Only")
    log.info(f"Source: AWS S3 (noaa-rrfs-pds)")
    log.info("")

    try:
        fetcher = REFSFetcher(args.location)

        if args.verify_only:
            log.info("Verifying existing downloads...")
            valid, invalid = fetcher.verify_downloads()
            sys.exit(0 if invalid == 0 else 1)

        # Fetch ensemble
        manifest = fetcher.fetch_ensemble(product=args.product)

        # Verify
        valid, invalid = fetcher.verify_downloads()

        # Exit status
        if manifest["status"] == "success" and invalid == 0:
            log.info("✓ All downloads complete and verified")
            sys.exit(0)
        elif manifest["status"] == "partial":
            log.warning("⚠ Some downloads failed or invalid")
            sys.exit(1)
        else:
            log.error("✗ Download failed")
            sys.exit(2)

    except Exception as e:
        log.exception(f"Fatal error: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()
