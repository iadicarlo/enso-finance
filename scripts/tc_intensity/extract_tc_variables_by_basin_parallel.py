"""
Extract Environmental Variables at TC Locations by Basin (Parallelized)

Parallelized version using ThreadPoolExecutor for faster processing.
Groups observations by year/month to efficiently load monthly data grids.

This script:
1. Loads IBTrACS TC tracks filtered by basin
2. Loads monthly ERA5 and ORAS5 data (cached per month)
3. Extracts environmental variables with spatial averaging (2.5° radius) for atmospheric variables
4. Creates training dataset per basin

Spatial Averaging:
- Atmospheric variables (temperature, wind, humidity, pressure): 2.5° radius spatial averaging
  following SHIPS and standard TC research practice. Represents environmental envelope affecting TCs.
- Bathymetry: Point extraction (fixed field, coastal boundaries important)

Usage:
    # Test mode with parallel processing
    python scripts/tc_intensity/extract_tc_variables_by_basin_parallel.py \
        --basin NA --test --max-workers 4
"""

import sys
import os
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
from concurrent.futures import ThreadPoolExecutor, as_completed  # Enable parallel extraction when requested
import threading
from functools import partial

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# --- Ensure ESMF/xESMF environment is available --------------------------------
# Hardwire known ESMF paths so extraction never depends on manual sourcing.
ESMF_MK_DEFAULT = "/nethome/abdel042/esmf_build/esmf/lib/libO/Linux.gfortran.64.mpiuni.default/esmf.mk"
ESMF_DIR_DEFAULT = "/nethome/abdel042/esmf_build/esmf"
ESMF_LIB_DEFAULT = "/nethome/abdel042/esmf_build/esmf/lib/libO/Linux.gfortran.64.mpiuni.default"

if "ESMFMKFILE" not in os.environ and Path(ESMF_MK_DEFAULT).exists():
    os.environ["ESMFMKFILE"] = ESMF_MK_DEFAULT
if "ESMF_DIR" not in os.environ and Path(ESMF_DIR_DEFAULT).exists():
    os.environ["ESMF_DIR"] = ESMF_DIR_DEFAULT
if Path(ESMF_LIB_DEFAULT).exists():
    ld = os.environ.get("LD_LIBRARY_PATH", "")
    if ESMF_LIB_DEFAULT not in ld:
        os.environ["LD_LIBRARY_PATH"] = f"{ESMF_LIB_DEFAULT}:{ld}" if ld else ESMF_LIB_DEFAULT

# Try to import esmpy/xesmf early to fail fast with a clear message
try:
    import esmpy  # noqa: F401
except Exception as e:
    warnings.warn(f"ESMF/ESMPy not available: {e}. Ensure ESMFMKFILE and LD_LIBRARY_PATH are set.")
try:
    import xesmf  # noqa: F401
except Exception as e:
    warnings.warn(f"xESMF not available: {e}. Ensure esmpy/ESMF are installed and env is set.")

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

# Spatial averaging configuration (following SHIPS and standard TC research practice)
SPATIAL_AVERAGE_RADIUS_DEG = 2.5  # 2.5° ≈ 250-300 km radius for environmental variables
# Use spatial averaging for atmospheric variables to represent environmental envelope
# Point extraction kept for bathymetry (fixed field, coastal boundaries important)

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

def haversine_distance_fast(lat1: float, lon1: float, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    """
    Fast distance calculation for small distances (optimized for spatial averaging).
    
    For distances < 5°, uses simple approximation which is ~10x faster than full haversine.
    For larger distances, falls back to haversine.
    
    Parameters
    ----------
    lat1, lon1 : float
        Reference point coordinates (degrees)
    lat2, lon2 : np.ndarray
        Array of target point coordinates (degrees)
    
    Returns
    -------
    np.ndarray
        Distance in degrees
    """
    # Fast approximation for small distances (valid for < 5°, error < 0.1%)
    # Uses planar approximation: sqrt((dlat)^2 + (dlon*cos(lat))^2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    # Handle longitude wrapping
    dlon = np.where(dlon > 180, dlon - 360, dlon)
    dlon = np.where(dlon < -180, dlon + 360, dlon)
    
    # Scale longitude by cosine of mean latitude (good approximation for small regions)
    lat_mean_rad = np.deg2rad((lat1 + lat2.mean()) / 2)
    dlon_scaled = dlon * np.cos(lat_mean_rad)
    
    # Simple Euclidean distance in lat-lon space (fast)
    distance_deg = np.sqrt(dlat**2 + dlon_scaled**2)
    
    return distance_deg

def extract_spatial_average_batch(
    data_arrays: List[xr.DataArray],
    lat: float,
    lon: float,
    radius_deg: float = 2.5
) -> List[float]:
    """
    OPTIMIZATION V2: Extract spatial averages for multiple variables at once.
    
    Reduces redundant coordinate lookups and distance calculations when
    extracting multiple variables at the same location.
    """
    if not data_arrays:
        return []
    
    first_array = data_arrays[0]
    lat_min = lat - radius_deg - 0.5
    lat_max = lat + radius_deg + 0.5
    lon_min = lon - radius_deg - 0.5
    lon_max = lon + radius_deg + 0.5
    
    lon_coords_full = np.array(first_array.longitude.values)
    if np.any(lon_coords_full > 180) and lon < 0:
        lon = lon + 360.0
        lon_min = lon_min + 360.0
        lon_max = lon_max + 360.0
    elif np.any(lon_coords_full <= 180) and lon > 180:
        lon = lon - 360.0
        lon_min = lon_min - 360.0
        lon_max = lon_max - 360.0
    
    try:
        region_arrays = [
            arr.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
            for arr in data_arrays
        ]
    except (KeyError, ValueError):
        lat_idx = int(np.abs(first_array.latitude.values - lat).argmin())
        lon_idx = int(np.abs(first_array.longitude.values - lon).argmin())
        return [float(arr.isel(latitude=lat_idx, longitude=lon_idx).values) 
                for arr in data_arrays]
    
    if region_arrays[0].size == 0:
        lat_idx = int(np.abs(first_array.latitude.values - lat).argmin())
        lon_idx = int(np.abs(first_array.longitude.values - lon).argmin())
        return [float(arr.isel(latitude=lat_idx, longitude=lon_idx).values)
                for arr in data_arrays]
    
    lat_region = np.array(region_arrays[0].latitude.values)
    lon_region = np.array(region_arrays[0].longitude.values)
    lat_2d, lon_2d = np.meshgrid(lat_region, lon_region, indexing='ij')
    
    # Compute distance mask once
    dlat = lat_2d - lat
    dlon = lon_2d - lon
    dlon = np.where(dlon > 180, dlon - 360, dlon)
    dlon = np.where(dlon < -180, dlon + 360, dlon)
    lat_mean_rad = np.deg2rad((lat + lat_2d.mean()) / 2)
    dlon_scaled = dlon * np.cos(lat_mean_rad)
    distances = np.sqrt(dlat**2 + dlon_scaled**2)
    mask = distances <= radius_deg
    
    if not np.any(mask):
        lat_idx = int(np.abs(lat_region - lat).argmin())
        lon_idx = int(np.abs(lon_region - lon).argmin())
        return [float(arr.isel(latitude=lat_idx, longitude=lon_idx).values)
                for arr in region_arrays]
    
    # Compute weights once
    weights_base = np.cos(np.deg2rad(lat_2d)) * mask
    weights_base[~mask] = 0.0
    
    results = []
    for region_arr in region_arrays:
        data_values = region_arr.values.squeeze()
        if data_values.ndim == 0:
            results.append(float(data_values))
            continue
        elif data_values.ndim == 1:
            data_values = data_values.reshape(len(lat_region), len(lon_region))
        if data_values.shape != lat_2d.shape:
            lat_idx = int(np.abs(lat_region - lat).argmin())
            lon_idx = int(np.abs(lon_region - lon).argmin())
            results.append(float(region_arr.isel(latitude=lat_idx, longitude=lon_idx).values))
            continue
        
        valid_mask = ~np.isnan(data_values)
        combined_mask = mask & valid_mask
        if not np.any(combined_mask):
            lat_idx = int(np.abs(lat_region - lat).argmin())
            lon_idx = int(np.abs(lon_region - lon).argmin())
            fallback_val = float(region_arr.isel(latitude=lat_idx, longitude=lon_idx).values)
            results.append(fallback_val if not np.isnan(fallback_val) else np.nan)
            continue
        
        weights_valid = weights_base * combined_mask
        total_weight = np.sum(weights_valid)
        if total_weight == 0:
            results.append(np.nan)
            continue
        
        weights_valid = weights_valid / total_weight
        masked_data = np.where(combined_mask, data_values, 0.0)
        weighted_sum = np.sum(masked_data * weights_valid)
        results.append(float(weighted_sum) if not np.isnan(weighted_sum) else np.nan)
    
    return results

def extract_spatial_average(
    data_array: xr.DataArray,
    lat: float,
    lon: float,
    radius_deg: float = 2.5,
    lat_coords: Optional[np.ndarray] = None,
    lon_coords: Optional[np.ndarray] = None
) -> float:
    """
    OPTIMIZED: Extract area-weighted spatial average within circular radius around TC location.
    
    Following SHIPS and standard TC research practice, environmental variables are
    averaged over a 2-3° radius to represent the environmental envelope affecting
    the TC, rather than using point values.
    
    Optimizations:
    - Pre-selects bounding box region first (much faster)
    - Uses fast distance approximation for small distances
    - Leverages xarray's optimized selection operations
    
    Parameters
    ----------
    data_array : xr.DataArray
        Data array with 'latitude' and 'longitude' dimensions
    lat, lon : float
        TC center coordinates (degrees)
    radius_deg : float
        Radius for spatial averaging in degrees (default: 2.5° ≈ 250-300 km)
    lat_coords, lon_coords : np.ndarray, optional
        Pre-computed coordinate arrays for efficiency (not used in optimized version)
    
    Returns
    -------
    float
        Area-weighted spatial average
    """
    # OPTIMIZATION 1: Pre-select bounding box region first (much faster than processing full grid)
    # This reduces the number of points we need to process by ~90%
    lat_min = lat - radius_deg - 0.5  # Add buffer for circular mask
    lat_max = lat + radius_deg + 0.5
    lon_min = lon - radius_deg - 0.5
    lon_max = lon + radius_deg + 0.5
    
    # Handle longitude wrapping
    lon_coords_full = np.array(data_array.longitude.values)
    if np.any(lon_coords_full > 180) and lon < 0:
        lon = lon + 360.0
        lon_min = lon_min + 360.0
        lon_max = lon_max + 360.0
    elif np.any(lon_coords_full <= 180) and lon > 180:
        lon = lon - 360.0
        lon_min = lon_min - 360.0
        lon_max = lon_max - 360.0
    
    # Select region (xarray's sel is highly optimized)
    try:
        # Select bounding box first
        region_data = data_array.sel(
            latitude=slice(lat_min, lat_max),
            longitude=slice(lon_min, lon_max)
        )
    except (KeyError, ValueError):
        # Fallback if selection fails
        lat_idx = int(np.abs(data_array.latitude.values - lat).argmin())
        lon_idx = int(np.abs(data_array.longitude.values - lon).argmin())
        return float(data_array.isel(latitude=lat_idx, longitude=lon_idx).values)
    
    # Check if we have data in region
    if region_data.size == 0:
        # Fallback to nearest neighbor
        lat_idx = int(np.abs(data_array.latitude.values - lat).argmin())
        lon_idx = int(np.abs(data_array.longitude.values - lon).argmin())
        return float(data_array.isel(latitude=lat_idx, longitude=lon_idx).values)
    
    # Get coordinates from selected region
    lat_region = np.array(region_data.latitude.values)
    lon_region = np.array(region_data.longitude.values)
    
    # OPTIMIZATION 2: Use broadcasting instead of meshgrid (faster)
    # Create 2D coordinate arrays using broadcasting
    lat_2d, lon_2d = np.meshgrid(lat_region, lon_region, indexing='ij')
    
    # OPTIMIZATION 3: Fast distance calculation (approximation for small distances)
    distances = haversine_distance_fast(lat, lon, lat_2d.flatten(), lon_2d.flatten())
    distances = distances.reshape(lat_2d.shape)
    
    # Create circular mask
    mask = distances <= radius_deg
    
    if not np.any(mask):
        # Fallback to nearest neighbor
        lat_idx = int(np.abs(lat_region - lat).argmin())
        lon_idx = int(np.abs(lon_region - lon).argmin())
        return float(region_data.isel(latitude=lat_idx, longitude=lon_idx).values)
    
    # Get data values (already selected to region, so smaller array)
    data_values = region_data.values.squeeze()
    
    # Handle dimensions
    if data_values.ndim == 0:
        return float(data_values)
    elif data_values.ndim == 1:
        # Shouldn't happen for lat-lon data, but handle gracefully
        if len(data_values) == len(lat_region) * len(lon_region):
            data_values = data_values.reshape(len(lat_region), len(lon_region))
        else:
            lat_idx = int(np.abs(lat_region - lat).argmin())
            lon_idx = int(np.abs(lon_region - lon).argmin())
            return float(region_data.isel(latitude=lat_idx, longitude=lon_idx).values)
    
    # Ensure shape matches
    if data_values.shape != lat_2d.shape:
        lat_idx = int(np.abs(lat_region - lat).argmin())
        lon_idx = int(np.abs(lon_region - lon).argmin())
        return float(region_data.isel(latitude=lat_idx, longitude=lon_idx).values)
    
    # OPTIMIZATION 4: Vectorized operations (much faster than np.where loops)
    # Calculate area weights (cosine latitude weighting)
    weights = np.cos(np.deg2rad(lat_2d)) * mask  # Apply mask directly
    weights[~mask] = 0.0  # Zero outside mask
    
    # NaN HANDLING: Filter out NaN values from data before averaging
    # This ensures we only average valid data points
    valid_data_mask = ~np.isnan(data_values)
    combined_mask = mask & valid_data_mask  # Both within radius AND valid data
    
    if not np.any(combined_mask):
        # No valid data in radius - try fallback to nearest neighbor
        lat_idx = int(np.abs(lat_region - lat).argmin())
        lon_idx = int(np.abs(lon_region - lon).argmin())
        fallback_value = float(region_data.isel(latitude=lat_idx, longitude=lon_idx).values)
        # If fallback is also NaN, return NaN
        if np.isnan(fallback_value):
            return np.nan
        return fallback_value
    
    # Recalculate weights only for valid data points
    weights_valid = np.cos(np.deg2rad(lat_2d)) * combined_mask
    weights_valid[~combined_mask] = 0.0
    
    total_weight = np.sum(weights_valid)
    if total_weight == 0:
        # Fallback
        lat_idx = int(np.abs(lat_region - lat).argmin())
        lon_idx = int(np.abs(lon_region - lon).argmin())
        fallback_value = float(region_data.isel(latitude=lat_idx, longitude=lon_idx).values)
        if np.isnan(fallback_value):
            return np.nan
        return fallback_value
    
    # Normalize and calculate weighted average (vectorized, only valid data)
    weights_valid = weights_valid / total_weight
    masked_data = np.where(combined_mask, data_values, 0.0)  # Use 0 for invalid points
    weighted_sum = np.sum(masked_data * weights_valid)
    
    # Check if result is valid
    if np.isnan(weighted_sum):
        # Fallback to nearest neighbor
        lat_idx = int(np.abs(lat_region - lat).argmin())
        lon_idx = int(np.abs(lon_region - lon).argmin())
        fallback_value = float(region_data.isel(latitude=lat_idx, longitude=lon_idx).values)
        return fallback_value
    
    return float(weighted_sum)

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
    # Ensure land/sea diagnostics always present even if extraction fails
    variables['bathymetry'] = np.nan
    variables['is_land'] = np.nan
    
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
        
        # OPTIMIZATION V2: Batch temperature extraction (4 levels at once)
        # Temperature at pressure levels (with spatial averaging)
        if 't' in ds_plev.data_vars or 'temperature' in ds_plev.data_vars:
            temp_var = 't' if 't' in ds_plev.data_vars else 'temperature'
            if 'pressure_level' in ds_plev[temp_var].dims:
                # Extract all 4 temperature levels at once
                temp_plevs = [850, 600, 250, 200]
                temp_plev_indices = [int(np.abs(plev_vals - plev).argmin()) for plev in temp_plevs]
                temp_data_arrays = [
                    ds_plev[temp_var].isel(valid_time=0, pressure_level=idx)
                    for idx in temp_plev_indices
                ]
                # Batch spatial averaging (reduces from 4 calls to 1)
                temp_results = extract_spatial_average_batch(temp_data_arrays, lat, lon, SPATIAL_AVERAGE_RADIUS_DEG)
                for i, plev in enumerate(temp_plevs):
                    variables[f'temperature_{plev}'] = temp_results[i]
        
        # OPTIMIZATION V2: Batch wind extraction (6 arrays: 3 levels × 2 components)
        # Wind components (with spatial averaging)
        if 'u' in ds_plev.data_vars or 'u_component_of_wind' in ds_plev.data_vars:
            u_var = 'u' if 'u' in ds_plev.data_vars else 'u_component_of_wind'
            v_var = 'v' if 'v' in ds_plev.data_vars else 'v_component_of_wind'
            
            if 'pressure_level' in ds_plev[u_var].dims:
                wind_plevs = [850, 250, 200]
                wind_plev_indices = [int(np.abs(plev_vals - plev).argmin()) for plev in wind_plevs]
                # Extract all wind components at once
                wind_u_arrays = [
                    ds_plev[u_var].isel(valid_time=0, pressure_level=idx)
                    for idx in wind_plev_indices
                ]
                wind_v_arrays = [
                    ds_plev[v_var].isel(valid_time=0, pressure_level=idx)
                    for idx in wind_plev_indices
                ]
                # Batch spatial averaging (reduces from 6 calls to 2 batch calls)
                u_results = extract_spatial_average_batch(wind_u_arrays, lat, lon, SPATIAL_AVERAGE_RADIUS_DEG)
                v_results = extract_spatial_average_batch(wind_v_arrays, lat, lon, SPATIAL_AVERAGE_RADIUS_DEG)
                
                for i, plev in enumerate(wind_plevs):
                    variables[f'u_{plev}'] = u_results[i]
                    variables[f'v_{plev}'] = v_results[i]
                    # Calculate wind speed from spatially-averaged components
                    wind_speed = np.sqrt(u_results[i]**2 + v_results[i]**2)
                    variables[f'wind_speed_{plev}'] = wind_speed
        
        # Calculate wind shear (850-250 hPa) - Emanuel 2017 requirement
        if 'u_850' in variables and 'v_850' in variables and 'u_250' in variables and 'v_250' in variables:
            u850 = variables['u_850']
            v850 = variables['v_850']
            u250 = variables['u_250']
            v250 = variables['v_250']
            
            wind_shear = np.sqrt((u250 - u850)**2 + (v250 - v850)**2)
            variables['wind_shear'] = wind_shear
        
        # OPTIMIZATION V2: Batch humidity extraction (3 levels at once)
        # Specific humidity at pressure levels (with spatial averaging)
        if 'q' in ds_plev.data_vars or 'specific_humidity' in ds_plev.data_vars:
            q_var = 'q' if 'q' in ds_plev.data_vars else 'specific_humidity'
            if 'pressure_level' in ds_plev[q_var].dims:
                q_plevs = [850, 600, 200]
                q_plev_indices = [int(np.abs(plev_vals - plev).argmin()) for plev in q_plevs]
                # Extract all humidity levels at once
                q_data_arrays = [
                    ds_plev[q_var].isel(valid_time=0, pressure_level=idx)
                    for idx in q_plev_indices
                ]
                # Batch spatial averaging (reduces from 3 calls to 1)
                q_results = extract_spatial_average_batch(q_data_arrays, lat, lon, SPATIAL_AVERAGE_RADIUS_DEG)
                for i, plev in enumerate(q_plevs):
                    variables[f'specific_humidity_{plev}'] = q_results[i]
        
        # Extract FULL comprehensive profiles for PI calculation (all 29 levels: 1000-50 hPa)
        # This is required for accurate PI calculation with tcpyPI
        # Use spatial averaging for profiles to be consistent with other atmospheric variables
        if 't' in ds_plev.data_vars or 'temperature' in ds_plev.data_vars:
            temp_var = 't' if 't' in ds_plev.data_vars else 'temperature'
            if 'q' in ds_plev.data_vars or 'specific_humidity' in ds_plev.data_vars:
                q_var = 'q' if 'q' in ds_plev.data_vars else 'specific_humidity'
                if 'pressure_level' in ds_plev[temp_var].dims and 'pressure_level' in ds_plev[q_var].dims:
                    # OPTIMIZATION V2: Extract full profiles with batch spatial averaging
                    # Instead of 58 individual calls (29 levels × 2 vars), batch them
                    plev_indices = []
                    plevs_pi = []
                    
                    for plev in ERA5_PI_PRESSURE_LEVELS:
                        plev_idx = int(np.abs(plev_vals - plev).argmin())
                        plev_indices.append(plev_idx)
                        plevs_pi.append(float(plev_vals[plev_idx]))
                    
                    # Extract all temperature and humidity levels at once
                    temp_all = ds_plev[temp_var].isel(valid_time=0, pressure_level=plev_indices)
                    q_all = ds_plev[q_var].isel(valid_time=0, pressure_level=plev_indices)
                    
                    # Convert to list of DataArrays for batch processing
                    temp_arrays = [temp_all.isel(pressure_level=i) for i in range(len(ERA5_PI_PRESSURE_LEVELS))]
                    q_arrays = [q_all.isel(pressure_level=i) for i in range(len(ERA5_PI_PRESSURE_LEVELS))]
                    
                    # Batch spatial averaging (reduces from 58 calls to 2 batch calls)
                    temp_profile_pi = extract_spatial_average_batch(temp_arrays, lat, lon, SPATIAL_AVERAGE_RADIUS_DEG)
                    q_profile_pi = extract_spatial_average_batch(q_arrays, lat, lon, SPATIAL_AVERAGE_RADIUS_DEG)
                    
                    # Store full profiles for PI calculation (as lists, will convert to arrays in PI section)
                    variables['_temperature_profile_pi'] = temp_profile_pi
                    variables['_specific_humidity_profile_pi'] = q_profile_pi
                    variables['_pressure_levels_pi'] = plevs_pi
        
        # Relative humidity at 600 hPa (with spatial averaging)
        if 'r' in ds_plev.data_vars or 'relative_humidity' in ds_plev.data_vars:
            rh_var = 'r' if 'r' in ds_plev.data_vars else 'relative_humidity'
            if 'pressure_level' in ds_plev[rh_var].dims:
                plev_idx = int(np.abs(plev_vals - 600).argmin())
                # Extract relative humidity at 600 hPa for spatial averaging
                rh_data = ds_plev[rh_var].isel(valid_time=0, pressure_level=plev_idx)
                variables['relative_humidity_600'] = extract_spatial_average(
                    rh_data, lat, lon, radius_deg=SPATIAL_AVERAGE_RADIUS_DEG,
                    lat_coords=lat_vals, lon_coords=lon_vals
                )
    
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
        
        # Surface pressure (with spatial averaging)
        if 'sp' in ds_sl.data_vars or 'surface_pressure' in ds_sl.data_vars:
            ps_var = 'sp' if 'sp' in ds_sl.data_vars else 'surface_pressure'
            # Extract surface pressure data for spatial averaging
            ps_data = ds_sl[ps_var].isel(valid_time=0)
            variables['surface_pressure'] = extract_spatial_average(
                ps_data, lat, lon, radius_deg=SPATIAL_AVERAGE_RADIUS_DEG,
                lat_coords=lat_vals, lon_coords=lon_vals
            )
    
    # 2.5. Extract SST from ORAS5 (PREFERRED - ocean reanalysis, more accurate)
    # OPTIMIZED: Use pre-loaded oras5_dataset instead of reloading file
    if 'sst' not in variables:
        if oras5_dataset is not None:
            # Extract from pre-loaded dataset (OPTIMIZATION - no file I/O)
            try:
                temp = oras5_dataset['votemper']
                
                # Handle longitude wrapping
                lon_sst = lon if lon <= 180 else lon - 360.0
                if lon_sst < 0:
                    lon_sst = lon_sst + 360.0
                
                # Regridded data uses latitude/longitude (regular grid)
                if 'latitude' in temp.coords and 'longitude' in temp.coords:
                    temp_at_loc = temp.sel(latitude=lat, longitude=lon_sst, method='nearest')
                elif 'lat' in temp.coords and 'lon' in temp.coords:
                    temp_at_loc = temp.sel(lat=lat, lon=lon_sst, method='nearest')
                else:
                    raise ValueError("Could not find lat/lon coordinates in ORAS5 data")
                
                # Get surface temperature (first depth level)
                if 'deptht' in temp_at_loc.dims:
                    sst_celsius = float(temp_at_loc.isel(deptht=0).values)
                else:
                    sst_celsius = float(temp_at_loc.values)
                
                # Convert from Celsius to Kelvin
                variables['sst'] = sst_celsius + 273.15
            except Exception as e:
                # Fallback to file-based extraction if dataset extraction fails
                oras5_file = DATA_DIR / 'oras5' / f'oras5_monthly_{time.year}_{time.month:02d}.nc'
                if oras5_file.exists():
                    try:
                        sst_celsius = get_oras5_sst(oras5_file, lat, lon)
                        if sst_celsius is not None:
                            variables['sst'] = sst_celsius + 273.15
                    except:
                        pass
    
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
        
        # SST from ERA5 (atmospheric model estimate, with spatial averaging)
        # NOTE: Store in Kelvin for consistency with other temperature variables and FAST model requirements
        if 'sst' in ds_sl.data_vars or 'sea_surface_temperature' in ds_sl.data_vars:
            sst_var = 'sst' if 'sst' in ds_sl.data_vars else 'sea_surface_temperature'
            # Extract SST data for spatial averaging
            sst_data = ds_sl[sst_var].isel(valid_time=0)
            # Use spatial averaging for SST (fallback case, ORAS5 preferred)
            variables['sst'] = extract_spatial_average(
                sst_data, lat, lon, radius_deg=SPATIAL_AVERAGE_RADIUS_DEG,
                lat_coords=lat_vals, lon_coords=lon_vals
            )
    
    # 3. Calculate PI using tcpyPI (Bister & Emanuel 2002 with true reversible adiabatic CAPE)
    # Uses peer-reviewed pyPI implementation with full reversible adiabatic parcel lifting
    # REQUIRES comprehensive pressure level profiles (29 levels: 1000-50 hPa) for accurate calculation
    # NO FALLBACKS: Only full profiles are allowed - fail hard if not available
    if 'sst' in variables and 'surface_pressure' in variables:
        sst_k = variables['sst']  # Now in Kelvin
        
        # Check if we have full comprehensive profiles for PI calculation (REQUIRED)
        has_full_profiles = (
            '_temperature_profile_pi' in variables and
            '_specific_humidity_profile_pi' in variables and
            '_pressure_levels_pi' in variables
        )
        
        if not has_full_profiles:
            # NO FALLBACK: Fail hard if full profiles aren't available
            missing = []
            if '_temperature_profile_pi' not in variables:
                missing.append("_temperature_profile_pi")
            if '_specific_humidity_profile_pi' not in variables:
                missing.append("_specific_humidity_profile_pi")
            if '_pressure_levels_pi' not in variables:
                missing.append("_pressure_levels_pi")
            
            error_msg = (
                f"❌ CRITICAL: Full 29-level profiles are REQUIRED for PI calculation. "
                f"Missing profile variables: {', '.join(missing)}. "
                f"Full profiles must be extracted from ERA5 pressure level data (all 29 levels: 1000-50 hPa). "
                f"Cannot proceed without full profiles - NO FALLBACKS ALLOWED."
            )
            log_message(error_msg, "ERROR")
            raise ValueError(error_msg)
        
        # Use comprehensive profiles (29 levels: 1000-50 hPa) for accurate PI calculation
        temperature_profile = np.array(variables['_temperature_profile_pi'])
        specific_humidity_profile = np.array(variables['_specific_humidity_profile_pi'])
        pressure_levels = np.array(variables['_pressure_levels_pi']) * 100.0  # Convert hPa to Pa
        
        # Verify we have exactly 29 levels
        if len(temperature_profile) != 29 or len(specific_humidity_profile) != 29 or len(pressure_levels) != 29:
            error_msg = (
                f"❌ CRITICAL: Expected exactly 29 pressure levels for PI calculation. "
                f"Got: temp={len(temperature_profile)}, q={len(specific_humidity_profile)}, p={len(pressure_levels)}. "
                f"Cannot proceed without full 29-level profiles."
            )
            log_message(error_msg, "ERROR")
            raise ValueError(error_msg)
        
        # Debug: log once using module-level flag to avoid NameError in certain contexts
        global _LOGGED_PROFILE_INFO
        try:
            if not globals().get("_LOGGED_PROFILE_INFO", False):
                log_message(
                    f"✅ Using full 29-level profiles for PI: "
                    f"P range={pressure_levels[0]/100:.0f}-{pressure_levels[-1]/100:.0f} hPa, "
                    f"T range={temperature_profile.min():.1f}-{temperature_profile.max():.1f} K, "
                    f"q range={specific_humidity_profile.min():.6f}-{specific_humidity_profile.max():.6f} kg/kg",
                    "DEBUG"
                )
                _LOGGED_PROFILE_INFO = True
        except Exception:
            # Never fail PI calculation due to logging issues
            pass
        
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
            # Verify PI is reasonable (should be ~15-50 m/s for most basins)
            if np.isnan(variables['pi']) or variables['pi'] < 0:
                log_message(
                    f"⚠️  PI calculation returned invalid value: {variables['pi']} m/s. "
                    f"This may indicate data quality issues.",
                    "WARNING"
                )
        except Exception as e:
            # If PI calculation fails, raise error (no fallback to NaN)
            error_msg = (
                f"❌ CRITICAL: PI calculation (tcpyPI) with full 29-level profile failed: {e}. "
                f"Cannot proceed without valid PI. Check: SST={sst_k:.2f} K, "
                f"surface_pressure={variables.get('surface_pressure', 'N/A')} Pa, "
                f"profile lengths: temp={len(temperature_profile)}, q={len(specific_humidity_profile)}, p={len(pressure_levels)}."
            )
            log_message(error_msg, "ERROR")
            raise RuntimeError(error_msg) from e
    
    # 4. Extract ocean temperature profile from ORAS5 for MLD
    # OPTIMIZED: Extract from pre-loaded dataset instead of reloading file
    if oras5_dataset is not None:
        try:
            temp = oras5_dataset['votemper']
            
            # Handle longitude wrapping
            lon_mld = lon if lon <= 180 else lon - 360.0
            if lon_mld < 0:
                lon_mld = lon_mld + 360.0
            
            # Extract temperature profile at location
            if 'latitude' in temp.coords and 'longitude' in temp.coords:
                temp_profile = temp.sel(latitude=lat, longitude=lon_mld, method='nearest')
            elif 'lat' in temp.coords and 'lon' in temp.coords:
                temp_profile = temp.sel(lat=lat, lon=lon_mld, method='nearest')
            else:
                temp_profile = None
            
            if temp_profile is not None:
                # Get depth coordinate
                if 'deptht' in temp_profile.coords:
                    depths = temp_profile.deptht.values
                elif 'depth' in temp_profile.coords:
                    depths = temp_profile.depth.values
                else:
                    depths = None
                
                # Get temperature values
                temps = temp_profile.values
                
                # Handle time dimension
                if 'time_counter' in temp_profile.dims:
                    temps = temps[0] if len(temps.shape) > 1 else temps
                
                if depths is not None and temps is not None:
                    # Filter NaN values
                    valid_mask = ~np.isnan(temps)
                    temps_valid = np.asarray(temps)[valid_mask]
                    depths_valid = np.asarray(depths)[valid_mask]
                    
                    if np.any(valid_mask) and 'sst' in variables and not np.isnan(variables['sst']):
                        # MLD calculation expects SST in Celsius
                        sst_celsius = variables['sst'] - 273.15
                        
                        if len(temps_valid) > 0:
                            mld = calculate_mixed_layer_depth(
                                ocean_temperature=temps_valid,
                                sst=sst_celsius,
                                depth_coord=depths_valid
                            )
                            
                            if not np.isnan(mld):
                                variables['mixed_layer_depth'] = float(mld)
                                
                                stratification = calculate_thermal_stratification(
                                    ocean_temperature=temps_valid,
                                    mixed_layer_depth=mld,
                                    depth_coord=depths_valid
                                )
                                if not np.isnan(stratification):
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
        if not np.isnan(bathymetry):
            variables['bathymetry'] = float(bathymetry)
            # ETOPO1: positive = land elevation, negative = ocean depth
            variables['is_land'] = 1 if bathymetry >= 0 else 0
        else:
            # Keep NaN if extraction failed
            variables['bathymetry'] = np.nan
            variables['is_land'] = np.nan
    except Exception as e:
        # Log warning but don't fail extraction - bathymetry is optional for intensity modeling
        # Only used for landfall detection
        log_message(
            f"   ⚠️  Bathymetry extraction failed at ({lat:.2f}, {lon:.2f}): {e}",
            "WARNING"
        )
        variables['bathymetry'] = np.nan
        variables['is_land'] = np.nan
    
    return variables

def extract_single_observation_optimized(
    row: pd.Series,
    idx: int,
    era5_datasets: Dict[str, xr.Dataset],
    oras5_dataset: Optional[xr.Dataset],
    ibtracs_df: pd.DataFrame,
    basin: str
) -> Tuple[int, Optional[Dict], Optional[str]]:
    """Extract variables for a single TC observation (optimized - datasets pre-loaded)."""
    try:
        lat = row['lat']
        lon = row['lon']
        time = pd.Timestamp(row['time'])
        storm_id = row.get('storm_id', 'UNKNOWN')
        
        # Convert longitude to 0-360 range if needed (ERA5 uses 0-360)
        if lon < 0:
            lon = lon + 360.0
        
        if era5_datasets is None:
            return (idx, None, f"No ERA5 data for {time.year}-{time.month:02d}")
        
        # Get trajectory for this storm
        if 'storm_id' not in ibtracs_df.columns:
            return (idx, None, f"storm_id column not found in DataFrame")
        
        storm_mask = ibtracs_df['storm_id'] == storm_id
        storm_traj = ibtracs_df.loc[storm_mask].copy()
        storm_traj = storm_traj.reset_index(drop=True)
        
        if not storm_traj.index.is_unique:
            storm_traj = storm_traj.reset_index(drop=True)
        
        # Extract all environmental variables (datasets already loaded)
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
        
        return (idx, variables, None)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        error_msg = f"Error extracting variables for observation {idx}: {str(e)}"
        return (idx, None, error_msg)

def process_single_basin_parallel(
    basin: str,
    start_year: int = 1980,
    end_year: int = 2020,
    min_wind_ms: float = 17.0,
    test_mode: bool = False,
    max_test_obs: int = 100,
    max_workers: int = 1,  # If >1, enable ThreadPoolExecutor for parallel extraction
    chunk_start: int = 0,
    chunk_size: Optional[int] = None,
    output_file: Optional[Path] = None,
    ibtracs_file: Optional[Path] = None
) -> pd.DataFrame:
    """Process environmental variable extraction for a single basin (parallel if max_workers > 1)."""
    basin_name = BASIN_CODES.get(basin, basin)
    
    mode = "PARALLEL" if max_workers and max_workers > 1 else "SEQUENTIAL (THREAD-SAFE)"
    print_header(f"Processing Basin: {basin} ({basin_name}) - {mode}")
    log_message(f"Period: {start_year}-{end_year}")
    log_message(f"Minimum wind speed: {min_wind_ms} m/s")
    if max_workers and max_workers > 1:
        log_message(f"Processing mode: Parallel (ThreadPoolExecutor) with max_workers={max_workers}")
    else:
        log_message(f"Processing mode: Sequential (thread-safe, avoids NetCDF threading issues)")
    log_message(f"Spatial averaging: {SPATIAL_AVERAGE_RADIUS_DEG}° radius for atmospheric variables (SHIPS standard)")
    
    # Initialize statistics
    _extraction_stats['start_time'] = datetime.now()
    _extraction_stats['total'] = 0
    _extraction_stats['success'] = 0
    _extraction_stats['failed'] = 0
    
    # Step 1: Load IBTrACS tracks
    log_message(f"[1] Loading IBTrACS tracks for basin {basin}...")
    try:
        # Use provided ibtracs_file if available, otherwise default cache location
        if ibtracs_file is not None:
            cache_file = Path(ibtracs_file)
        else:
            cache_file = OUTPUT_DIR.parent / 'ibtracs_tracks.csv'
        
        ibtracs_df = load_ibtracs_tracks(
            cache_file=cache_file,
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
    
    if chunk_size is not None:
        start_idx = max(0, int(chunk_start))
        end_idx = start_idx + int(chunk_size)
        log_message(f"   CHUNK MODE: Processing observations {start_idx}:{end_idx}")
        ibtracs_df = ibtracs_df.iloc[start_idx:end_idx].copy()
    elif test_mode:
        log_message(f"   TEST MODE: Processing first {max_test_obs} observations only")
        ibtracs_df = ibtracs_df.head(max_test_obs).copy()
    
    # Reset index to ensure unique indices for parallel processing
    # This prevents "Reindexing only valid with uniquely valued Index objects" errors
    ibtracs_df = ibtracs_df.reset_index(drop=True)
    
    _extraction_stats['total'] = len(ibtracs_df)
    
    # Step 3.5: Group observations by year/month for optimized dataset loading
    ibtracs_df['year_month'] = ibtracs_df['time'].apply(lambda x: (pd.Timestamp(x).year, pd.Timestamp(x).month))
    unique_year_months = sorted(ibtracs_df['year_month'].unique())
    log_message(f"[3.5] OPTIMIZATION: Grouping observations by year/month...")
    log_message(f"   Unique year-month combinations: {len(unique_year_months)}")
    log_message(f"   This reduces dataset loading from {len(ibtracs_df)} to {len(unique_year_months)} times")
    
    # Step 4: Extract variables grouped by year/month (OPTIMIZED)
    log_message(f"[4] Extracting environmental variables (OPTIMIZED: grouped by year/month)...")
    log_message(f"   Processing {len(ibtracs_df)} observations across {len(unique_year_months)} months...")
    
    all_variables_list = []
    failed_observations = []
    
    # Process each year/month group
    with tqdm(total=len(ibtracs_df), desc=f"Extracting {basin}") as pbar:
        for year, month in unique_year_months:
            # Get all observations for this month
            month_mask = ibtracs_df['year_month'] == (year, month)
            month_obs = ibtracs_df[month_mask].copy()
            
            if len(month_obs) == 0:
                continue
            
            # Load datasets once for this month (MAJOR OPTIMIZATION)
            try:
                era5_datasets = load_monthly_era5_grids(year, month)
                oras5_dataset = load_monthly_oras5_grid(year, month)
                
                if era5_datasets is None:
                    log_message(f"   ⚠️  No ERA5 data for {year}-{month:02d}, skipping {len(month_obs)} observations", "WARNING")
                    failed_observations.extend(month_obs.index.tolist())
                    _extraction_stats['failed'] += len(month_obs)
                    pbar.update(len(month_obs))
                    continue
                
                # Process all observations for this month
                for original_idx, row in month_obs.iterrows():
                    idx = int(original_idx)
                    try:
                        result = extract_single_observation_optimized(
                            row, idx, era5_datasets, oras5_dataset, ibtracs_df, basin
                        )
                        obs_idx, variables, error_msg = result
                        
                        if variables is not None:
                            all_variables_list.append(variables)
                            _extraction_stats['success'] += 1
                        else:
                            if error_msg:
                                log_message(f"   ⚠️  Observation {obs_idx}: {error_msg}", "WARNING")
                            failed_observations.append(obs_idx)
                            _extraction_stats['failed'] += 1
                        
                        pbar.update(1)
                        
                        # Progress logging every 50 observations
                        if _extraction_stats['success'] % 50 == 0 and _extraction_stats['success'] > 0:
                            elapsed = (datetime.now() - _extraction_stats['start_time']).total_seconds()
                            rate = _extraction_stats['success'] / elapsed if elapsed > 0 else 0
                            remaining = (_extraction_stats['total'] - _extraction_stats['success'] - _extraction_stats['failed']) / rate if rate > 0 else 0
                            log_message(f"   Progress: {_extraction_stats['success']}/{_extraction_stats['total']} successful ({rate:.2f} obs/s, ~{remaining/60:.1f} min remaining)")
                    
                    except Exception as e:
                        log_message(f"   ❌ Exception processing observation {idx}: {e}", "ERROR")
                        failed_observations.append(idx)
                        _extraction_stats['failed'] += 1
                        pbar.update(1)
                
                # Close datasets after processing this month (free memory)
                try:
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
                except Exception as e:
                    log_message(f"   ⚠️  Error closing datasets for {year}-{month:02d}: {e}", "WARNING")
            
            except Exception as e:
                log_message(f"   ❌ Error loading datasets for {year}-{month:02d}: {e}", "ERROR")
                failed_observations.extend(month_obs.index.tolist())
                _extraction_stats['failed'] += len(month_obs)
                pbar.update(len(month_obs))
    
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
    parser.add_argument(
        '--chunk-start',
        type=int,
        default=0,
        help='Start index for chunked processing (used with --chunk-size)'
    )
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=None,
        help='Chunk size (number of observations) for array/task splitting'
    )
    parser.add_argument(
        '--output-file',
        type=str,
        default=None,
        help='Optional explicit output path (used in array runs)'
    )
    parser.add_argument(
        '--ibtracs-file',
        type=str,
        default=None,
        help='Path to IBTrACS CSV file (default: uses cache or downloads)'
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
        max_workers=args.max_workers,
        chunk_start=args.chunk_start,
        chunk_size=args.chunk_size,
        output_file=Path(args.output_file) if args.output_file else None,
        ibtracs_file=Path(args.ibtracs_file) if args.ibtracs_file else None
    )
    
    if len(training_df) > 0:
        # Save basin-specific output
        if args.output_file:
            output_file = Path(args.output_file)
        else:
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
    # Add immediate startup logging to debug hanging issues
    import sys
    sys.stdout.flush()
    sys.stderr.flush()
    print("[STARTUP] Script starting...", flush=True)
    print(f"[STARTUP] Python: {sys.executable}", flush=True)
    print(f"[STARTUP] Args: {sys.argv}", flush=True)
    sys.stdout.flush()
    try:
        main()
    except Exception as e:
        print(f"[FATAL] Error in main(): {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
