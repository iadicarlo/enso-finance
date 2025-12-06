"""
Extract Environmental Variables at TC Locations by Basin (Parallelized)

Parallelized version using ThreadPoolExecutor for faster processing.
Groups observations by year/month to efficiently load monthly data grids.

This script:
1. Loads IBTrACS TC tracks filtered by basin
2. Loads monthly ERA5 and ORAS5 data (cached per month)
3. Extracts environmental variables in parallel
4. Creates training dataset per basin

Usage:
    # Test mode with parallel processing
    python scripts/tc_intensity/extract_tc_variables_by_basin_parallel.py \
        --basin NA --test --max-workers 4
"""

import sys
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import xarray as xr
from datetime import datetime
from typing import Dict, Optional, List, Tuple
import json
import warnings
from tqdm import tqdm
# Sequential processing (no threading needed for thread safety)
# from concurrent.futures import ThreadPoolExecutor, as_completed  # Disabled - using sequential processing
import threading
from functools import partial

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import our modules
from src.tc_intensity import (
    interpolate_monthly_to_trajectory,
    calculate_mixed_layer_depth,
    calculate_thermal_stratification,
    calculate_translation_speed,
    extract_bathymetry_at_location,
    apply_all_physics_constraints
)
# Import tcpyPI wrapper for PI calculation (Bister & Emanuel 2002 with true reversible adiabatic CAPE)
from src.tc_intensity.physics.potential_intensity_tcpyPI import calculate_pi_tcpyPI

# Import pressure levels constants for comprehensive PI calculation
from scripts.tc_intensity._pressure_levels_constants import ERA5_PI_PRESSURE_LEVELS

# Import data loaders
from scripts.preprocessing.load_ibtracs_tracks import load_ibtracs_tracks, BASIN_CODES
from src.data_loaders.cds_era5_monthly_loader import (
    load_era5_monthly_pressure_levels,
    get_era5_monthly_variables_at_location
)
from src.data_loaders.cds_oras5_monthly_loader import (
    load_oras5_monthly,
    get_ocean_temperature_profile,
    get_oras5_sst
)

# Directories
DATA_DIR = project_root / 'data' / 'tc_intensity' / 'monthly'
OUTPUT_DIR = project_root / 'outputs' / 'tc_intensity' / 'training_data'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

warnings.filterwarnings('ignore')

# All available basins
ALL_BASINS = list(BASIN_CODES.keys())

# Thread-safe logging
_log_lock = threading.Lock()
_stats_lock = threading.Lock()

def log_message(message: str, level: str = "INFO"):
    """Thread-safe log message with timestamp."""
    with _log_lock:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        msg = f"[{timestamp}] [{level}] {message}"
        print(msg, flush=True)
        sys.stdout.flush()

def print_header(title: str):
    """Print formatted header."""
    log_message("\n" + "=" * 70)
    log_message(f"  {title}")
    log_message("=" * 70)

# Global statistics tracking
_extraction_stats = {
    'total': 0,
    'success': 0,
    'failed': 0,
    'start_time': None
}

# Data caching per year/month (thread-safe)
# DISABLED CACHING to prevent OOM - datasets loaded fresh each time
# Cache was causing memory accumulation even with limits
_monthly_data_cache = {}
_cache_lock = threading.Lock()
ENABLE_CACHE = False  # Disabled to prevent OOM - load datasets fresh each time
MAX_CACHE_SIZE = 1  # Minimal cache (effectively no cache)

# Pre-computed coordinate arrays (thread-safe, read-only)
_coordinate_cache = {}
_coord_cache_lock = threading.Lock()
MAX_COORD_CACHE_SIZE = 50  # Coordinates are small, can keep more

def load_monthly_data_catalog() -> Dict:
    """Load the monthly data catalog."""
    catalog_file = DATA_DIR / 'monthly_data_catalog.json'
    
    if not catalog_file.exists():
        raise FileNotFoundError(f"Monthly data catalog not found: {catalog_file}")
    
    with open(catalog_file, 'r') as f:
        catalog = json.load(f)
    
    return catalog

def load_monthly_era5_grids(year: int, month: int) -> Optional[Dict[str, xr.Dataset]]:
    """Load monthly ERA5 grids for a specific year/month (no caching to prevent OOM)."""
    cache_key = (year, month, 'era5')
    
    # Check cache only if enabled (currently disabled to prevent OOM)
    if ENABLE_CACHE:
        with _cache_lock:
            if cache_key in _monthly_data_cache:
                cached = _monthly_data_cache.pop(cache_key)
                _monthly_data_cache[cache_key] = cached
                return cached
    
    # Serialize file opening to avoid NetCDF threading issues
    era5_plev_file = DATA_DIR / 'era5' / 'pressure_levels' / f'era5_monthly_plev_{year}_{month:02d}.nc'
    era5_sl_file = DATA_DIR / 'era5' / 'single_level' / f'era5_monthly_sl_{year}_{month:02d}.nc'
    
    datasets = {}
    
    # Load files with proper error handling
    try:
        if era5_plev_file.exists():
            # Load and keep dataset open (don't close immediately)
            ds_plev = load_era5_monthly_pressure_levels(era5_plev_file)
            if ds_plev is not None:
                datasets['pressure_levels'] = ds_plev
    except Exception as e:
        log_message(f"Error loading ERA5 pressure-level {year}-{month:02d}: {e}", "WARNING")
    
    try:
        if era5_sl_file.exists():
            # Use chunks to avoid memory issues, but don't close
            ds_sl = xr.open_dataset(era5_sl_file, chunks={'latitude': 100, 'longitude': 100})
            datasets['single_level'] = ds_sl
    except Exception as e:
        log_message(f"Error loading ERA5 single-level {year}-{month:02d}: {e}", "WARNING")
    
    result = datasets if datasets else None
    
    # No caching - return datasets directly (they'll be closed after use)
    # Caching was causing OOM even with limits
    return result

def load_monthly_oras5_grid(year: int, month: int) -> Optional[xr.Dataset]:
    """Load monthly ORAS5 ocean data for a specific year/month (no caching to prevent OOM)."""
    cache_key = (year, month, 'oras5')
    
    # Check cache only if enabled (currently disabled to prevent OOM)
    if ENABLE_CACHE:
        with _cache_lock:
            if cache_key in _monthly_data_cache:
                cached = _monthly_data_cache.pop(cache_key)
                _monthly_data_cache[cache_key] = cached
                return cached
    
    # Serialize file opening
    oras5_file = DATA_DIR / 'oras5' / f'oras5_monthly_{year}_{month:02d}.nc'
    
    result = None
    try:
        if oras5_file.exists():
            result = load_oras5_monthly(oras5_file)
    except Exception as e:
        log_message(f"Error loading ORAS5 {year}-{month:02d}: {e}", "WARNING")
    
    # No caching - return dataset directly (will be closed after use)
    # Caching was causing OOM even with limits
    return result

def extract_all_environmental_variables_at_tc_location(
    lat: float,
    lon: float,
    time: pd.Timestamp,
    era5_datasets: Dict[str, xr.Dataset],
    oras5_dataset: Optional[xr.Dataset] = None,
    trajectory_df: Optional[pd.DataFrame] = None
) -> Dict[str, float]:
    """Extract all environmental variables at a TC location."""
    variables = {}
    
    # Basic location info
    variables['lat'] = lat
    variables['lon'] = lon
    variables['time'] = time
    
    # 1. Extract from ERA5 pressure-level data
    if 'pressure_levels' in era5_datasets:
        ds_plev = era5_datasets['pressure_levels']
        
        # Use pre-computed coordinate arrays (thread-safe, already in cache)
        cache_key_plev = (time.year, time.month, 'plev_coords')
        with _coord_cache_lock:
            if cache_key_plev not in _coordinate_cache:
                # Fallback: compute on-the-fly if not pre-computed
                _coordinate_cache[cache_key_plev] = {
                    'lat': np.array(ds_plev.latitude.values).copy(),
                    'lon': np.array(ds_plev.longitude.values).copy(),
                    'plev': np.array(ds_plev.pressure_level.values).copy()
                }
            coords = _coordinate_cache[cache_key_plev]
        
        # Access cached coordinates (read-only, thread-safe)
        lat_vals = coords['lat']
        lon_vals = coords['lon']
        plev_vals = coords['plev']
        
        # Find nearest indices manually (thread-safe)
        lat_idx = int(np.abs(lat_vals - lat).argmin())
        lon_idx = int(np.abs(lon_vals - lon).argmin())
        
        # Temperature at pressure levels
        # ERA5 uses 'pressure_level' dimension and 'latitude'/'longitude' coordinates
        if 't' in ds_plev.data_vars or 'temperature' in ds_plev.data_vars:
            temp_var = 't' if 't' in ds_plev.data_vars else 'temperature'
            for plev in [850, 600, 250, 200]:
                if 'pressure_level' in ds_plev[temp_var].dims:
                    plev_idx = int(np.abs(plev_vals - plev).argmin())
                    temp_at_plev = ds_plev[temp_var].isel(valid_time=0, pressure_level=plev_idx, latitude=lat_idx, longitude=lon_idx)
                    variables[f'temperature_{plev}'] = float(temp_at_plev.values)
        
        # Wind components
        if 'u' in ds_plev.data_vars or 'u_component_of_wind' in ds_plev.data_vars:
            u_var = 'u' if 'u' in ds_plev.data_vars else 'u_component_of_wind'
            v_var = 'v' if 'v' in ds_plev.data_vars else 'v_component_of_wind'
            
            for plev in [850, 250, 200]:
                if 'pressure_level' in ds_plev[u_var].dims:
                    plev_idx = int(np.abs(plev_vals - plev).argmin())
                    u = ds_plev[u_var].isel(valid_time=0, pressure_level=plev_idx, latitude=lat_idx, longitude=lon_idx)
                    v = ds_plev[v_var].isel(valid_time=0, pressure_level=plev_idx, latitude=lat_idx, longitude=lon_idx)
                    variables[f'u_{plev}'] = float(u.values)
                    variables[f'v_{plev}'] = float(v.values)
                    
                    wind_speed = np.sqrt(float(u.values)**2 + float(v.values)**2)
                    variables[f'wind_speed_{plev}'] = wind_speed
        
        # Calculate wind shear (850-250 hPa) - Emanuel 2017 requirement
        if 'u_850' in variables and 'v_850' in variables and 'u_250' in variables and 'v_250' in variables:
            u850 = variables['u_850']
            v850 = variables['v_850']
            u250 = variables['u_250']
            v250 = variables['v_250']
            
            wind_shear = np.sqrt((u250 - u850)**2 + (v250 - v850)**2)
            variables['wind_shear'] = wind_shear
        
        # Specific humidity at pressure levels (for full PI calculation)
        # ERA5 uses 'q' for specific humidity
        if 'q' in ds_plev.data_vars or 'specific_humidity' in ds_plev.data_vars:
            q_var = 'q' if 'q' in ds_plev.data_vars else 'specific_humidity'
            if 'pressure_level' in ds_plev[q_var].dims:
                for plev in [850, 600, 200]:
                    plev_idx = int(np.abs(plev_vals - plev).argmin())
                    q_at_plev = ds_plev[q_var].isel(valid_time=0, pressure_level=plev_idx, latitude=lat_idx, longitude=lon_idx)
                    variables[f'specific_humidity_{plev}'] = float(q_at_plev.values)
        
        # Extract FULL comprehensive profiles for PI calculation (all 29 levels: 1000-50 hPa)
        # This is required for accurate PI calculation with tcpyPI
        if 't' in ds_plev.data_vars or 'temperature' in ds_plev.data_vars:
            temp_var = 't' if 't' in ds_plev.data_vars else 'temperature'
            if 'q' in ds_plev.data_vars or 'specific_humidity' in ds_plev.data_vars:
                q_var = 'q' if 'q' in ds_plev.data_vars else 'specific_humidity'
                if 'pressure_level' in ds_plev[temp_var].dims and 'pressure_level' in ds_plev[q_var].dims:
                    # Extract full profiles for PI calculation
                    temp_profile_pi = []
                    q_profile_pi = []
                    plevs_pi = []
                    
                    for plev in ERA5_PI_PRESSURE_LEVELS:
                        # Find nearest available level in dataset
                        plev_idx = int(np.abs(plev_vals - plev).argmin())
                        actual_plev = float(plev_vals[plev_idx])
                        
                        # Extract temperature and humidity at this level
                        temp_at_plev = ds_plev[temp_var].isel(valid_time=0, pressure_level=plev_idx, latitude=lat_idx, longitude=lon_idx)
                        q_at_plev = ds_plev[q_var].isel(valid_time=0, pressure_level=plev_idx, latitude=lat_idx, longitude=lon_idx)
                        
                        temp_profile_pi.append(float(temp_at_plev.values))
                        q_profile_pi.append(float(q_at_plev.values))
                        plevs_pi.append(actual_plev)
                    
                    # Store full profiles for PI calculation (as lists, will convert to arrays in PI section)
                    variables['_temperature_profile_pi'] = temp_profile_pi
                    variables['_specific_humidity_profile_pi'] = q_profile_pi
                    variables['_pressure_levels_pi'] = plevs_pi
        
        # Relative humidity at 600 hPa (keep for backward compatibility if needed)
        if 'r' in ds_plev.data_vars or 'relative_humidity' in ds_plev.data_vars:
            rh_var = 'r' if 'r' in ds_plev.data_vars else 'relative_humidity'
            if 'pressure_level' in ds_plev[rh_var].dims:
                plev_idx = int(np.abs(plev_vals - 600).argmin())
                rh_600 = ds_plev[rh_var].isel(valid_time=0, pressure_level=plev_idx, latitude=lat_idx, longitude=lon_idx)
                variables['relative_humidity_600'] = float(rh_600.values)
    
    # 2. Extract from ERA5 single-level data
    if 'single_level' in era5_datasets:
        ds_sl = era5_datasets['single_level']
        
        # Use pre-computed coordinate arrays (thread-safe, already in cache)
        cache_key_sl = (time.year, time.month, 'sl_coords')
        with _coord_cache_lock:
            if cache_key_sl not in _coordinate_cache:
                # Fallback: compute on-the-fly if not pre-computed
                _coordinate_cache[cache_key_sl] = {
                    'lat': np.array(ds_sl.latitude.values).copy(),
                    'lon': np.array(ds_sl.longitude.values).copy()
                }
            coords = _coordinate_cache[cache_key_sl]
        
        # Access cached coordinates (read-only, thread-safe)
        lat_vals = coords['lat']
        lon_vals = coords['lon']
        
        # Find nearest indices manually (thread-safe)
        lat_idx = int(np.abs(lat_vals - lat).argmin())
        lon_idx = int(np.abs(lon_vals - lon).argmin())
        
        # Surface pressure
        if 'sp' in ds_sl.data_vars or 'surface_pressure' in ds_sl.data_vars:
            ps_var = 'sp' if 'sp' in ds_sl.data_vars else 'surface_pressure'
            ps = ds_sl[ps_var].isel(valid_time=0, latitude=lat_idx, longitude=lon_idx)
            variables['surface_pressure'] = float(ps.values)
    
    # 2.5. Extract SST from ORAS5 (PREFERRED - ocean reanalysis, more accurate)
    # ORAS5 SST is extracted from surface level of ocean temperature (more accurate than ERA5 atmospheric estimate)
    # Fall back to ERA5 SST if ORAS5 is not available
    if 'sst' not in variables and oras5_dataset is not None:
        try:
            oras5_file = DATA_DIR / 'oras5' / f'oras5_monthly_{time.year}_{time.month:02d}.nc'
            if oras5_file.exists():
                sst_celsius = get_oras5_sst(oras5_file, lat, lon)
                if sst_celsius is not None:
                    # Convert from Celsius to Kelvin for consistency with other temperature variables
                    variables['sst'] = sst_celsius + 273.15
        except Exception as e:
            pass  # Silent fail, will try ERA5 SST as fallback
    
    # 2.6. Fallback: Extract SST from ERA5 (atmospheric model estimate - less accurate)
    # Only use if ORAS5 SST extraction failed or ORAS5 data is not available
    if 'sst' not in variables and 'single_level' in era5_datasets:
        ds_sl = era5_datasets['single_level']
        
        # Use pre-computed coordinate arrays (thread-safe)
        cache_key_sl = (time.year, time.month, 'sl_coords')
        with _coord_cache_lock:
            if cache_key_sl not in _coordinate_cache:
                _coordinate_cache[cache_key_sl] = {
                    'lat': np.array(ds_sl.latitude.values).copy(),
                    'lon': np.array(ds_sl.longitude.values).copy()
                }
            coords = _coordinate_cache[cache_key_sl]
        
        lat_vals = coords['lat']
        lon_vals = coords['lon']
        lat_idx = int(np.abs(lat_vals - lat).argmin())
        lon_idx = int(np.abs(lon_vals - lon).argmin())
        
        # SST from ERA5 (atmospheric model estimate)
        # NOTE: Store in Kelvin for consistency with other temperature variables and FAST model requirements
        if 'sst' in ds_sl.data_vars or 'sea_surface_temperature' in ds_sl.data_vars:
            sst_var = 'sst' if 'sst' in ds_sl.data_vars else 'sea_surface_temperature'
            sst_kelvin = ds_sl[sst_var].isel(valid_time=0, latitude=lat_idx, longitude=lon_idx)
            # Store in Kelvin (consistent with temperature profiles and FAST model)
            variables['sst'] = float(sst_kelvin.values)
    
    # 3. Calculate PI using tcpyPI (Bister & Emanuel 2002 with true reversible adiabatic CAPE)
    # Uses peer-reviewed pyPI implementation with full reversible adiabatic parcel lifting
    # REQUIRES comprehensive pressure level profiles (29 levels: 1000-50 hPa) for accurate calculation
    if 'sst' in variables and 'surface_pressure' in variables:
        sst_k = variables['sst']  # Now in Kelvin
        
        # Check if we have full comprehensive profiles for PI calculation (preferred)
        has_full_profiles = (
            '_temperature_profile_pi' in variables and
            '_specific_humidity_profile_pi' in variables and
            '_pressure_levels_pi' in variables
        )
        
        if has_full_profiles:
            # Use comprehensive profiles (29 levels: 1000-50 hPa) for accurate PI calculation
            temperature_profile = np.array(variables['_temperature_profile_pi'])
            specific_humidity_profile = np.array(variables['_specific_humidity_profile_pi'])
            pressure_levels = np.array(variables['_pressure_levels_pi']) * 100.0  # Convert hPa to Pa
            
            # Clean up temporary profile variables (not needed in output CSV)
            del variables['_temperature_profile_pi']
            del variables['_specific_humidity_profile_pi']
            del variables['_pressure_levels_pi']
            
            # Use tcpyPI (Bister & Emanuel 2002) - true reversible adiabatic CAPE calculation
            try:
                variables['pi'] = calculate_pi_tcpyPI(
                    sst_k=sst_k,
                    surface_pressure=variables['surface_pressure'],
                    temperature_profile=temperature_profile,
                    pressure_levels=pressure_levels,
                    specific_humidity_profile=specific_humidity_profile
                    # Wrapper handles all unit conversions automatically (Pa→hPa, K→°C, kg/kg→g/kg)
                )
            except Exception as e:
                # If PI calculation fails, set to NaN
                warnings.warn(f"PI calculation (tcpyPI) with full profile failed: {e}. Setting PI to NaN.")
                variables['pi'] = np.nan
        
        else:
            # Fallback: Check if we have basic 3-level profiles (for backward compatibility)
            has_temp_profiles = all(
                f'temperature_{plev}' in variables 
                for plev in [850, 600, 200]
            )
            has_q_profiles = all(
                f'specific_humidity_{plev}' in variables 
                for plev in [850, 600, 200]
            )
            
            if has_temp_profiles and has_q_profiles:
                # Use basic 3-level profiles (less accurate, but better than nothing)
                warnings.warn("Using basic 3-level profile for PI calculation. Results will be less accurate. Consider extracting full profiles.")
                temperature_profile = np.array([
                    variables['temperature_850'],
                    variables['temperature_600'],
                    variables['temperature_200']
                ])
                specific_humidity_profile = np.array([
                    variables['specific_humidity_850'],
                    variables['specific_humidity_600'],
                    variables['specific_humidity_200']
                ])
                pressure_levels = np.array([85000.0, 60000.0, 20000.0])  # Pa (will be converted to hPa by wrapper)
                
                try:
                    variables['pi'] = calculate_pi_tcpyPI(
                        sst_k=sst_k,
                        surface_pressure=variables['surface_pressure'],
                        temperature_profile=temperature_profile,
                        pressure_levels=pressure_levels,
                        specific_humidity_profile=specific_humidity_profile
                    )
                except Exception as e:
                    warnings.warn(f"PI calculation (tcpyPI) with basic profile failed: {e}. Setting PI to NaN.")
                    variables['pi'] = np.nan
            else:
                # Missing required data for PI calculation
                missing = []
                if not has_temp_profiles:
                    missing.append("temperature profiles")
                if not has_q_profiles:
                    missing.append("specific humidity profiles")
                warnings.warn(f"Cannot calculate PI - missing: {', '.join(missing)}. Setting PI to NaN.")
                variables['pi'] = np.nan
    
    # 4. Extract ocean temperature profile from ORAS5 for MLD
    if oras5_dataset is not None:
        try:
            oras5_file = DATA_DIR / 'oras5' / f'oras5_monthly_{time.year}_{time.month:02d}.nc'
            temp_profile = get_ocean_temperature_profile(oras5_file, lat, lon)
            
            if temp_profile and 'temperature' in temp_profile:
                if 'sst' in variables:
                    # MLD calculation expects SST in same units as ocean temperature (Celsius)
                    # variables['sst'] is stored in Kelvin, convert to Celsius
                    sst_celsius = variables['sst'] - 273.15
                    mld = calculate_mixed_layer_depth(
                        ocean_temperature=temp_profile['temperature'],
                        sst=sst_celsius,
                        depth_coord=temp_profile['depth']
                    )
                    variables['mixed_layer_depth'] = float(mld)
                    
                    stratification = calculate_thermal_stratification(
                        ocean_temperature=temp_profile['temperature'],
                        mixed_layer_depth=mld,
                        depth_coord=temp_profile['depth']
                    )
                    variables['thermal_stratification'] = float(stratification)
        except Exception as e:
            pass  # Silent fail for MLD - optional variable
    
    # 5. Translation speed (if trajectory provided)
    if trajectory_df is not None and len(trajectory_df) > 1:
        try:
            traj_with_speed = calculate_translation_speed(trajectory_df)
            time_match = traj_with_speed[traj_with_speed['time'] == time]
            if len(time_match) > 0:
                variables['translation_speed'] = float(time_match['translation_speed_ms'].iloc[0])
        except Exception:
            pass
    
    # 6. Bathymetry
    try:
        bathymetry = extract_bathymetry_at_location(lat, lon)
        variables['bathymetry'] = bathymetry
    except Exception:
        pass
    
    return variables

def extract_single_observation(args: Tuple, ibtracs_df: pd.DataFrame) -> Tuple[int, Optional[Dict], Optional[str]]:
    """Extract variables for a single TC observation."""
    idx, row_dict, basin = args
    
    try:
        # Validate inputs
        if not isinstance(ibtracs_df, pd.DataFrame):
            return (idx, None, f"ibtracs_df is not a DataFrame (type: {type(ibtracs_df)})")
        
        # Convert dict to Series for easier access, but use integer index
        row = pd.Series(row_dict)
        
        lat = row['lat']
        lon = row['lon']
        time = pd.Timestamp(row['time'])
        storm_id = row.get('storm_id', 'UNKNOWN')  # Get from row_dict directly
        
        # Convert longitude to 0-360 range if needed (ERA5 uses 0-360)
        if lon < 0:
            lon = lon + 360.0
        
        year_month = (time.year, time.month)
        
        # Load monthly data (thread-safe with caching)
        era5_datasets = load_monthly_era5_grids(time.year, time.month)
        oras5_dataset = load_monthly_oras5_grid(time.year, time.month)
        
        if era5_datasets is None:
            return (idx, None, f"No ERA5 data for {time.year}-{time.month:02d}")
        
        # Get trajectory for this storm (ensure fresh copy with unique indices)
        # Use .loc to avoid potential reindexing issues, then reset index
        if 'storm_id' not in ibtracs_df.columns:
            return (idx, None, f"storm_id column not found in DataFrame. Columns: {list(ibtracs_df.columns)}")
        
        storm_mask = ibtracs_df['storm_id'] == storm_id
        storm_traj = ibtracs_df.loc[storm_mask].copy()
        storm_traj = storm_traj.reset_index(drop=True)
        
        # Double-check index is unique
        if not storm_traj.index.is_unique:
            storm_traj = storm_traj.reset_index(drop=True)
        
        # Extract all environmental variables
        try:
            variables = extract_all_environmental_variables_at_tc_location(
                lat, lon, time,
                era5_datasets,
                oras5_dataset=oras5_dataset,
                trajectory_df=storm_traj if len(storm_traj) > 1 else None
            )
            
            # Add TC metadata
            variables.update({
                'storm_id': storm_id,
                'max_wind_ms': row.get('max_wind_ms', np.nan),
                'year': row.get('year', np.nan),
                'basin': row.get('basin', basin),
            })
        finally:
            # Explicitly close datasets to free memory immediately
            if era5_datasets:
                for ds in era5_datasets.values():
                    if isinstance(ds, xr.Dataset):
                        try:
                            ds.close()
                        except:
                            pass
            if oras5_dataset is not None:
                try:
                    oras5_dataset.close()
                except:
                    pass
        
        return (idx, variables, None)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        error_msg = f"Error extracting variables for observation {idx}: {str(e)}"
        # Log full traceback for debugging
        log_message(f"   Full error traceback for observation {idx}:", "ERROR")
        log_message(f"   {error_details}", "ERROR")
        return (idx, None, error_msg)

def process_single_basin_parallel(
    basin: str,
    start_year: int = 1980,
    end_year: int = 2020,
    min_wind_ms: float = 17.0,
    test_mode: bool = False,
    max_test_obs: int = 100,
    max_workers: int = 1  # Default to 1 (sequential) to avoid NetCDF threading issues
) -> pd.DataFrame:
    """Process environmental variable extraction for a single basin (sequential processing for thread safety)."""
    basin_name = BASIN_CODES.get(basin, basin)
    
    print_header(f"Processing Basin: {basin} ({basin_name}) - SEQUENTIAL (THREAD-SAFE)")
    log_message(f"Period: {start_year}-{end_year}")
    log_message(f"Minimum wind speed: {min_wind_ms} m/s")
    log_message(f"Processing mode: Sequential (thread-safe, avoids NetCDF segfaults)")
    
    # Initialize statistics
    _extraction_stats['start_time'] = datetime.now()
    _extraction_stats['total'] = 0
    _extraction_stats['success'] = 0
    _extraction_stats['failed'] = 0
    
    # Step 1: Load IBTrACS tracks
    log_message(f"[1] Loading IBTrACS tracks for basin {basin}...")
    try:
        ibtracs_df = load_ibtracs_tracks(
            cache_file=OUTPUT_DIR.parent / 'ibtracs_tracks.csv',
            start_year=start_year,
            end_year=end_year,
            basins=[basin],
            min_wind_ms=min_wind_ms,
            force_download=False
        )
        log_message(f"✅ Loaded {len(ibtracs_df):,} TC observations for basin {basin}")
        
        if len(ibtracs_df) == 0:
            log_message(f"⚠️  No observations found for basin {basin}", "WARNING")
            return pd.DataFrame()
        
    except Exception as e:
        log_message(f"❌ Error loading IBTrACS for basin {basin}: {e}", "ERROR")
        return pd.DataFrame()
    
    # Step 2: Load monthly data catalog
    log_message(f"[2] Loading monthly data catalog...")
    try:
        catalog = load_monthly_data_catalog()
        log_message(f"✅ Catalog loaded:")
        log_message(f"   ERA5 pressure-level: {len(catalog['era5_pressure_levels'])} files")
        log_message(f"   ERA5 single-level: {len(catalog['era5_single_level'])} files")
        log_message(f"   ORAS5: {len(catalog['oras5'])} files")
    except Exception as e:
        log_message(f"❌ Error loading catalog: {e}", "ERROR")
        return pd.DataFrame()
    
    # Step 3: Prepare observations
    log_message(f"[3] Preparing observations for parallel extraction...")
    
    if test_mode:
        log_message(f"   TEST MODE: Processing first {max_test_obs} observations only")
        ibtracs_df = ibtracs_df.head(max_test_obs).copy()
    
    # Reset index to ensure unique indices for parallel processing
    # This prevents "Reindexing only valid with uniquely valued Index objects" errors
    ibtracs_df = ibtracs_df.reset_index(drop=True)
    
    _extraction_stats['total'] = len(ibtracs_df)
    
    # Step 3.5: Note about on-demand loading (removed pre-loading to avoid OOM)
    unique_year_months = ibtracs_df['time'].apply(lambda x: (pd.Timestamp(x).year, pd.Timestamp(x).month)).unique()
    log_message(f"[3.5] Datasets will be loaded on-demand during extraction...")
    log_message(f"   Unique year-month combinations: {len(unique_year_months)}")
    log_message(f"   Note: Loading all datasets at once causes OOM - using on-demand loading instead")
    
    # Create list of arguments for sequential processing
    # CRITICAL FIX: Don't copy entire DataFrame - just pass indices and storm_id
    # Creating tuples with full DataFrame copies caused OOM (12,697 copies!)
    extraction_args = [
        (int_idx, row.to_dict(), basin)
        for int_idx, (original_idx, row) in enumerate(ibtracs_df.iterrows())
    ]
    
    # Step 4: Extract variables sequentially (thread-safe)
    log_message(f"[4] Extracting environmental variables sequentially (thread-safe mode)...")
    log_message(f"   Processing {len(extraction_args)} observations...")
    log_message(f"   Note: Using sequential processing to avoid NetCDF threading issues")
    
    all_variables_list = []
    failed_observations = []
    
    # Process observations sequentially (thread-safe, avoids segfaults)
    with tqdm(total=len(extraction_args), desc=f"Extracting {basin}") as pbar:
        for args in extraction_args:
            idx = args[0]
            try:
                obs_idx, variables, error_msg = extract_single_observation(args, ibtracs_df)
                
                if variables is not None:
                    all_variables_list.append(variables)
                    _extraction_stats['success'] += 1
                else:
                    if error_msg:
                        log_message(f"   ⚠️  Observation {obs_idx}: {error_msg}", "WARNING")
                    failed_observations.append(obs_idx)
                    _extraction_stats['failed'] += 1
                
                pbar.update(1)
                
                # Update progress message every 10 observations
                if _extraction_stats['success'] % 10 == 0 and _extraction_stats['success'] > 0:
                    elapsed = (datetime.now() - _extraction_stats['start_time']).total_seconds()
                    rate = _extraction_stats['success'] / elapsed if elapsed > 0 else 0
                    remaining = (_extraction_stats['total'] - _extraction_stats['success'] - _extraction_stats['failed']) / rate if rate > 0 else 0
                    log_message(f"   Progress: {_extraction_stats['success']}/{_extraction_stats['total']} successful ({rate:.2f} obs/s, ~{remaining/60:.1f} min remaining)")
                    
            except Exception as e:
                log_message(f"   ❌ Exception processing observation {idx}: {e}", "ERROR")
                failed_observations.append(idx)
                _extraction_stats['failed'] += 1
                pbar.update(1)
    
    # Step 5: Create training DataFrame
    elapsed = (datetime.now() - _extraction_stats['start_time']).total_seconds()
    log_message(f"\n✅ Extraction complete:")
    log_message(f"   Successful: {_extraction_stats['success']}/{_extraction_stats['total']}")
    log_message(f"   Failed: {_extraction_stats['failed']}/{_extraction_stats['total']}")
    if elapsed > 0:
        log_message(f"   Processing rate: {_extraction_stats['success']/elapsed:.2f} observations/second")
    log_message(f"   Total time: {elapsed/60:.1f} minutes")
    
    if failed_observations:
        log_message(f"   Failed observation indices: {failed_observations[:10]}{'...' if len(failed_observations) > 10 else ''}")
    
    if all_variables_list:
        training_df = pd.DataFrame(all_variables_list)
        return training_df
    else:
        log_message("⚠️  No variables extracted", "WARNING")
        return pd.DataFrame()

def main():
    """Main extraction workflow with parallel processing."""
    parser = argparse.ArgumentParser(
        description='Extract environmental variables at TC locations by basin (parallelized)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available basins: {', '.join([f"{k} ({v})" for k, v in BASIN_CODES.items()])}

Examples:
  # Test mode with 4 workers
  python {Path(__file__).name} --basin NA --test --max-workers 4
        """
    )
    
    parser.add_argument(
        '--basin',
        type=str,
        default='NA',
        choices=ALL_BASINS,
        help=f'Basin code to process (default: NA). Options: {", ".join(ALL_BASINS)}'
    )
    parser.add_argument(
        '--start-year',
        type=int,
        default=1980,
        help='Start year (default: 1980)'
    )
    parser.add_argument(
        '--end-year',
        type=int,
        default=2020,
        help='End year (default: 2020)'
    )
    parser.add_argument(
        '--min-wind-ms',
        type=float,
        default=17.0,
        help='Minimum wind speed in m/s (default: 17.0)'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test mode: only process first 100 observations'
    )
    parser.add_argument(
        '--max-test-obs',
        type=int,
        default=50,
        help='Maximum observations in test mode (default: 50)'
    )
    parser.add_argument(
        '--max-workers',
        type=int,
        default=1,
        help='Number of workers for extraction (default: 1, sequential processing for thread safety)'
    )
    
    args = parser.parse_args()
    
    print_header("ENVIRONMENTAL VARIABLE EXTRACTION BY BASIN - SEQUENTIAL (THREAD-SAFE)")
    log_message(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_message(f"Period: {args.start_year}-{args.end_year}")
    log_message(f"Minimum wind speed: {args.min_wind_ms} m/s")
    log_message(f"Processing mode: Sequential (thread-safe)")
    
    basin_name = BASIN_CODES.get(args.basin, args.basin)
    log_message(f"\n{'='*70}")
    log_message(f"Processing basin: {args.basin} ({basin_name})")
    log_message(f"{'='*70}")
    
    # Process this basin
    training_df = process_single_basin_parallel(
        basin=args.basin,
        start_year=args.start_year,
        end_year=args.end_year,
        min_wind_ms=args.min_wind_ms,
        test_mode=args.test,
        max_test_obs=args.max_test_obs,
        max_workers=args.max_workers
    )
    
    if len(training_df) > 0:
        # Save basin-specific output
        output_file = OUTPUT_DIR / f'tc_training_data_{args.basin}.csv'
        if args.test:
            output_file = OUTPUT_DIR / f'tc_training_data_{args.basin}_test.csv'
        
        training_df.to_csv(output_file, index=False)
        log_message(f"\n✅ Saved training dataset: {output_file}")
        log_message(f"   Observations: {len(training_df):,}")
        log_message(f"   Variables: {len(training_df.columns)}")
        
        # Show variable coverage
        log_message(f"\n   Variable coverage:")
        for col in sorted(training_df.columns):
            n_valid = training_df[col].notna().sum()
            pct_valid = (n_valid / len(training_df)) * 100
            if pct_valid < 100:
                log_message(f"      {col}: {n_valid}/{len(training_df)} ({pct_valid:.1f}%)")
    
    print_header("EXTRACTION COMPLETE")
    log_message(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == '__main__':
    main()
