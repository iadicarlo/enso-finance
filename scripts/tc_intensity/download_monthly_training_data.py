"""
Download Monthly Training Data: ERA5 + ORAS5

Downloads monthly ERA5 pressure-level and ORAS5 ocean data for TC intensity training.
Following UQAM-TCW approach with monthly grids.

Enhanced with detailed logging and debugging output.
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime
from typing import List, Optional
import warnings
import argparse

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.data_loaders.cds_era5_monthly_loader import (
    download_era5_monthly_pressure_levels,
    download_era5_monthly_single_level,
    initialize_cds_client
)
from src.data_loaders.cds_oras5_monthly_loader import (
    download_oras5_monthly,
    initialize_cds_client as init_oras5_client
)

# Import pressure levels constants for comprehensive PI calculation
from scripts.tc_intensity._pressure_levels_constants import ERA5_PI_PRESSURE_LEVELS
from scripts.tc_intensity.verify_downloaded_files import verify_era5_pressure_level_file

# Data directories
DATA_DIR = project_root / 'data' / 'tc_intensity' / 'monthly'
ERA5_DIR = DATA_DIR / 'era5'
ORAS5_DIR = DATA_DIR / 'oras5'

ERA5_DIR.mkdir(parents=True, exist_ok=True)
ORAS5_DIR.mkdir(parents=True, exist_ok=True)

warnings.filterwarnings('ignore')


def log_message(message: str, level: str = "INFO"):
    """Log message with timestamp."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    msg = f"[{timestamp}] [{level}] {message}"
    print(msg, flush=True)
    sys.stdout.flush()
    sys.stderr.flush()


def print_header(title: str):
    """Print formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def download_era5_monthly_for_period(
    start_year: int = 1980,
    end_year: int = 2020,
    variables_pressure: Optional[List[str]] = None,
    variables_single: Optional[List[str]] = None,
    pressure_levels: Optional[List[int]] = None,
    force_download: bool = False
):
    """
    Download ERA5 monthly data for a time period with detailed logging.
    """
    if variables_pressure is None:
        variables_pressure = [
            'temperature',
            'u_component_of_wind',
            'v_component_of_wind',
            'relative_humidity',
            'specific_humidity'
        ]
    
    if variables_single is None:
        variables_single = [
            'sea_surface_temperature',
            'surface_pressure'
        ]
    
    if pressure_levels is None:
        # Use comprehensive pressure levels for accurate PI calculation (29 levels: 1000-50 hPa)
        # This replaces the previous 3-level default [850, 600, 200]
        pressure_levels = ERA5_PI_PRESSURE_LEVELS
    
    # Check CDS API availability
    log_message("Initializing CDS API client...")
    client = initialize_cds_client()
    if client is None:
        log_message("CDS API client not available.", "ERROR")
        log_message("Set up credentials: https://cds.climate.copernicus.eu/api-how-to", "ERROR")
        return
    
    log_message("✅ CDS API client initialized successfully")
    
    print_header("Downloading ERA5 Monthly Data")
    log_message(f"Period: {start_year}-{end_year}")
    log_message(f"Pressure-level variables: {variables_pressure}")
    log_message(f"Single-level variables: {variables_single}")
    log_message(f"Pressure levels: {pressure_levels} hPa")
    
    total_files = (end_year - start_year + 1) * 12
    files_downloaded = 0
    files_skipped = 0
    files_failed = 0
    
    start_time = datetime.now()
    
    # Download pressure-level data
    log_message("Starting ERA5 pressure-level downloads...")
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            output_file = ERA5_DIR / 'pressure_levels' / f'era5_monthly_plev_{year}_{month:02d}.nc'
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if file exists and is valid
            if output_file.exists():
                if not force_download:
                    # Verify file is good before skipping
                    is_valid, message = verify_era5_pressure_level_file(output_file, ERA5_PI_PRESSURE_LEVELS)
                    if is_valid:
                        files_skipped += 1
                        if files_skipped <= 5 or files_skipped % 12 == 0:
                            log_message(f"Skipping {year}/{month:02d} (valid file exists)")
                        continue
                    else:
                        # File exists but is corrupted/wrong, delete and re-download
                        log_message(f"⚠️  {year}/{month:02d}: File exists but invalid ({message}), will re-download")
                        output_file.unlink()
                else:
                    # Force download: delete existing file
                    if output_file.exists():
                        output_file.unlink()
            
            try:
                log_message(f"Downloading {year}/{month:02d} pressure-level data...")
                result = download_era5_monthly_pressure_levels(
                    variables=variables_pressure,
                    pressure_levels=pressure_levels,
                    year=year,
                    month=month,
                    output_file=output_file,
                    force_download=force_download
                )
                
                if result and result.exists():
                    files_downloaded += 1
                    file_size_mb = result.stat().st_size / (1024**2)
                    log_message(f"✅ Downloaded {year}/{month:02d}: {output_file.name} ({file_size_mb:.1f} MB)")
                else:
                    files_failed += 1
                    log_message(f"❌ Failed {year}/{month:02d}", "ERROR")
                    
            except Exception as e:
                files_failed += 1
                log_message(f"❌ Error downloading {year}/{month:02d}: {e}", "ERROR")
                import traceback
                traceback.print_exc()
            
            # Progress update every 12 files (1 year)
            if (files_downloaded + files_failed) % 12 == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = (files_downloaded + files_failed) / elapsed if elapsed > 0 else 0
                remaining = total_files - (files_downloaded + files_failed)
                eta_seconds = remaining / rate if rate > 0 else 0
                log_message(f"Progress: {files_downloaded + files_failed}/{total_files} files processed (rate: {rate*60:.1f} files/min, ETA: {eta_seconds/60:.1f} min)")
    
    # Download single-level data
    log_message("Starting ERA5 single-level downloads...")
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            output_file = ERA5_DIR / 'single_level' / f'era5_monthly_sl_{year}_{month:02d}.nc'
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            if output_file.exists() and not force_download:
                continue
            
            try:
                log_message(f"Downloading {year}/{month:02d} single-level data...")
                result = download_era5_monthly_single_level(
                    variables=variables_single,
                    year=year,
                    month=month,
                    output_file=output_file,
                    force_download=force_download
                )
                
                if result and result.exists():
                    file_size_mb = result.stat().st_size / (1024**2)
                    log_message(f"✅ Downloaded single-level {year}/{month:02d} ({file_size_mb:.1f} MB)")
                    
            except Exception as e:
                log_message(f"❌ Error downloading single-level {year}/{month:02d}: {e}", "ERROR")
    
    elapsed = (datetime.now() - start_time).total_seconds()
    log_message("")
    log_message("📊 ERA5 Download Summary:")
    log_message(f"   Downloaded: {files_downloaded} files")
    log_message(f"   Skipped: {files_skipped} files")
    log_message(f"   Failed: {files_failed} files")
    log_message(f"   Total time: {elapsed/60:.1f} minutes")


def download_oras5_monthly_for_period(
    start_year: int = 1980,
    end_year: int = 2020,
    variables: Optional[List[str]] = None,
    force_download: bool = False
):
    """
    Download ORAS5 monthly ocean data for a time period with detailed logging.
    """
    if variables is None:
        variables = ['potential_temperature']
    
    log_message("Initializing CDS API client for ORAS5...")
    client = init_oras5_client()
    if client is None:
        log_message("CDS API client not available.", "ERROR")
        return
    
    log_message("✅ CDS API client initialized")
    
    print_header("Downloading ORAS5 Monthly Ocean Data")
    log_message(f"Period: {start_year}-{end_year}")
    log_message(f"Variables: {variables}")
    
    total_files = (end_year - start_year + 1) * 12
    files_downloaded = 0
    files_skipped = 0
    files_failed = 0
    
    start_time = datetime.now()
    
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            output_file = ORAS5_DIR / f'oras5_monthly_{year}_{month:02d}.nc'
            
            if output_file.exists() and not force_download:
                files_skipped += 1
                if files_skipped <= 5 or files_skipped % 12 == 0:
                    log_message(f"Skipping {year}/{month:02d} (already exists)")
                continue
            
            try:
                log_message(f"Downloading {year}/{month:02d} ORAS5 data...")
                result = download_oras5_monthly(
                    variables=variables,
                    year=year,
                    month=month,
                    output_file=output_file,
                    force_download=force_download
                )
                
                if result and result.exists():
                    files_downloaded += 1
                    file_size_mb = result.stat().st_size / (1024**2)
                    log_message(f"✅ Downloaded {year}/{month:02d}: {output_file.name} ({file_size_mb:.1f} MB)")
                else:
                    files_failed += 1
                    log_message(f"❌ Failed {year}/{month:02d}", "ERROR")
                    
            except Exception as e:
                files_failed += 1
                log_message(f"❌ Error downloading {year}/{month:02d}: {e}", "ERROR")
                import traceback
                traceback.print_exc()
            
            # Progress update
            if (files_downloaded + files_failed) % 12 == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = (files_downloaded + files_failed) / elapsed if elapsed > 0 else 0
                remaining = total_files - (files_downloaded + files_failed)
                eta_seconds = remaining / rate if rate > 0 else 0
                log_message(f"Progress: {files_downloaded + files_failed}/{total_files} files processed (rate: {rate*60:.1f} files/min)")
    
    elapsed = (datetime.now() - start_time).total_seconds()
    log_message("")
    log_message("📊 ORAS5 Download Summary:")
    log_message(f"   Downloaded: {files_downloaded} files")
    log_message(f"   Skipped: {files_skipped} files")
    log_message(f"   Failed: {files_failed} files")
    log_message(f"   Total time: {elapsed/60:.1f} minutes")


def create_monthly_data_catalog():
    """
    Create a catalog of all downloaded monthly files.
    """
    print_header("Creating Monthly Data Catalog")
    
    catalog = {
        'era5_pressure_levels': [],
        'era5_single_level': [],
        'oras5': []
    }
    
    # Scan ERA5 pressure-level files
    era5_plev_dir = ERA5_DIR / 'pressure_levels'
    if era5_plev_dir.exists():
        for file in sorted(era5_plev_dir.glob('era5_monthly_plev_*.nc')):
            try:
                parts = file.stem.split('_')
                year = int(parts[-2])
                month = int(parts[-1])
                catalog['era5_pressure_levels'].append({
                    'file': str(file),
                    'year': year,
                    'month': month,
                    'size_bytes': file.stat().st_size
                })
            except Exception as e:
                log_message(f"Error processing {file.name}: {e}", "WARNING")
    
    # Scan ERA5 single-level files
    era5_sl_dir = ERA5_DIR / 'single_level'
    if era5_sl_dir.exists():
        for file in sorted(era5_sl_dir.glob('era5_monthly_sl_*.nc')):
            try:
                parts = file.stem.split('_')
                year = int(parts[-2])
                month = int(parts[-1])
                catalog['era5_single_level'].append({
                    'file': str(file),
                    'year': year,
                    'month': month,
                    'size_bytes': file.stat().st_size
                })
            except Exception as e:
                log_message(f"Error processing {file.name}: {e}", "WARNING")
    
    # Scan ORAS5 files
    if ORAS5_DIR.exists():
        for file in sorted(ORAS5_DIR.glob('oras5_monthly_*.nc')):
            try:
                parts = file.stem.split('_')
                year = int(parts[-2])
                month = int(parts[-1])
                catalog['oras5'].append({
                    'file': str(file),
                    'year': year,
                    'month': month,
                    'size_bytes': file.stat().st_size
                })
            except Exception as e:
                log_message(f"Error processing {file.name}: {e}", "WARNING")
    
    # Save catalog
    import json
    catalog_file = DATA_DIR / 'monthly_data_catalog.json'
    with open(catalog_file, 'w') as f:
        json.dump(catalog, f, indent=2)
    
    log_message(f"✅ Catalog created: {catalog_file}")
    log_message("")
    log_message("📊 Catalog Summary:")
    log_message(f"   ERA5 pressure-level files: {len(catalog['era5_pressure_levels'])}")
    log_message(f"   ERA5 single-level files: {len(catalog['era5_single_level'])}")
    log_message(f"   ORAS5 files: {len(catalog['oras5'])}")
    
    return catalog


def main():
    """Main download workflow with argument parsing."""
    parser = argparse.ArgumentParser(
        description='Download monthly ERA5 and ORAS5 data',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--start-year', type=int, default=1980, help='Start year (default: 1980)')
    parser.add_argument('--end-year', type=int, default=2020, help='End year (default: 2020)')
    parser.add_argument('--era5-only', action='store_true', help='Download ERA5 only')
    parser.add_argument('--oras5-only', action='store_true', help='Download ORAS5 only')
    parser.add_argument('--force', action='store_true', help='Force re-download existing files')
    parser.add_argument('--test', action='store_true', help='Test with single month (2020-09)')
    parser.add_argument('--catalog-only', action='store_true', help='Only create catalog, no download')
    
    args = parser.parse_args()
    
    log_message("=" * 70)
    log_message("MONTHLY TRAINING DATA DOWNLOAD WORKFLOW")
    log_message("=" * 70)
    log_message(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_message(f"Working directory: {project_root}")
    log_message("")
    
    if args.catalog_only:
        create_monthly_data_catalog()
        return
    
    if args.test:
        log_message("🧪 TEST MODE: Downloading single month (2020-09) only")
        if not args.oras5_only:
            download_era5_monthly_for_period(
                start_year=2020,
                end_year=2020,
                force_download=args.force
            )
        if not args.era5_only:
            download_oras5_monthly_for_period(
                start_year=2020,
                end_year=2020,
                force_download=args.force
            )
    else:
        # Full period download
        log_message("")
        log_message("=" * 70)
        log_message("STARTING FULL PERIOD DOWNLOAD")
        log_message("=" * 70)
        log_message(f"era5_only: {args.era5_only}")
        log_message(f"oras5_only: {args.oras5_only}")
        log_message("")
        
        if not args.era5_only:
            log_message("[1] Starting ORAS5 download...")
            try:
                download_oras5_monthly_for_period(
                    start_year=args.start_year,
                    end_year=args.end_year,
                    force_download=args.force
                )
                log_message("✅ ORAS5 download completed")
            except Exception as e:
                log_message(f"❌ ORAS5 download failed: {e}", "ERROR")
                import traceback
                traceback.print_exc()
        else:
            log_message("⏭️  Skipping ORAS5 (--era5-only specified)")
        
        if not args.oras5_only:
            log_message("[2] Starting ERA5 download...")
            try:
                download_era5_monthly_for_period(
                    start_year=args.start_year,
                    end_year=args.end_year,
                    force_download=args.force
                )
                log_message("✅ ERA5 download completed")
            except Exception as e:
                log_message(f"❌ ERA5 download failed: {e}", "ERROR")
                import traceback
                traceback.print_exc()
        else:
            log_message("⏭️  Skipping ERA5 (--oras5-only specified)")
    
    # Create catalog
    log_message("")
    log_message("Creating data catalog...")
    catalog = create_monthly_data_catalog()
    
    log_message("")
    log_message("=" * 70)
    log_message("Download Workflow Complete")
    log_message("=" * 70)
    log_message(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_message("")
    log_message("Next steps:")
    log_message("  1. Extract variables at TC locations:")
    log_message("     python3 scripts/tc_intensity/extract_tc_variables_by_basin.py --basin NA")
    log_message("  2. Train physics-informed ML model")
    log_message("  3. Apply to CMIP6 projections")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"FATAL ERROR in main(): {e}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        sys.exit(1)
