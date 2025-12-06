"""
Test TC Variable Extraction Pipeline with Downloaded Files

This script tests:
1. Loading TC track data
2. Extracting environmental variables from ERA5/ORAS5
3. Calculating PI with 29-level data
4. Validating output quality
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime
import warnings

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.preprocessing.load_ibtracs_tracks import load_ibtracs_tracks
from scripts.tc_intensity.extract_tc_variables_by_basin_parallel import (
    load_monthly_era5_grids,
    load_monthly_oras5_grid,
    extract_all_environmental_variables_at_tc_location
)

warnings.filterwarnings('ignore')

def test_loaded_files():
    """Check what ERA5/ORAS5 files we have available."""
    print("=" * 70)
    print("TEST 1: CHECKING DOWNLOADED FILES")
    print("=" * 70)
    
    era5_dir = project_root / 'data' / 'tc_intensity' / 'monthly' / 'era5' / 'pressure_levels'
    oras5_dir = project_root / 'data' / 'tc_intensity' / 'monthly' / 'oras5'
    
    era5_files = sorted(era5_dir.glob("*.nc")) if era5_dir.exists() else []
    oras5_files = sorted(oras5_dir.glob("*.nc")) if oras5_dir.exists() else []
    
    print(f"\n📁 ERA5 pressure-level files: {len(era5_files)}")
    if era5_files:
        # Check sample file
        import xarray as xr
        sample_file = era5_files[0]
        try:
            ds = xr.open_dataset(sample_file)
            if 'pressure_level' in ds.dims:
                levels = len(ds.pressure_level)
                print(f"   ✅ Sample file: {sample_file.name}")
                print(f"   ✅ Pressure levels: {levels}")
                if levels >= 29:
                    print(f"   ✅ GOOD: Has 29+ levels")
                else:
                    print(f"   ❌ BAD: Only {levels} levels (need 29+)")
            print(f"   Variables: {list(ds.data_vars)}")
            print(f"   Years available: {era5_files[0].stem.split('_')[-2]} - {era5_files[-1].stem.split('_')[-2]}")
            ds.close()
        except Exception as e:
            print(f"   ⚠️  Error reading sample: {e}")
    
    print(f"\n📁 ORAS5 files: {len(oras5_files)}")
    if oras5_files:
        print(f"   Years available: {oras5_files[0].stem.split('_')[-2]} - {oras5_files[-1].stem.split('_')[-2]}")
    
    return len(era5_files), len(oras5_files)


def test_tc_tracks():
    """Load and check TC track data."""
    print("\n" + "=" * 70)
    print("TEST 2: LOADING TC TRACK DATA")
    print("=" * 70)
    
    # Try to load IBTrACS tracks
    try:
        tracks = load_ibtracs_tracks(
            start_year=1980,
            end_year=2020,
            basins=['EP']  # East Pacific (NA not available in IBTrACS)
        )
        
        print(f"\n✅ Loaded {len(tracks)} TC observations")
        print(f"   Period: {tracks['time'].min()} to {tracks['time'].max()}")
        print(f"   Basins: {tracks['basin'].unique()}")
        
        # Show sample
        print(f"\n📋 Sample observations:")
        print(f"   Available columns: {list(tracks.columns)}")
        # Try different possible column names
        cols_to_show = ['storm_id', 'time', 'lat', 'lon']
        if 'max_wind_ms' in tracks.columns:
            cols_to_show.append('max_wind_ms')
        elif 'wind' in tracks.columns:
            cols_to_show.append('wind')
        if 'min_pressure' in tracks.columns:
            cols_to_show.append('min_pressure')
        elif 'pressure' in tracks.columns:
            cols_to_show.append('pressure')
        print(tracks[cols_to_show].head())
        
        return tracks
        
    except Exception as e:
        print(f"\n❌ Error loading tracks: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_variable_extraction(tracks, num_tests=5):
    """Test extracting variables for a few TC observations."""
    print("\n" + "=" * 70)
    print(f"TEST 3: EXTRACTING VARIABLES ({num_tests} test cases)")
    print("=" * 70)
    
    if tracks is None or len(tracks) == 0:
        print("❌ No track data available for testing")
        return []
    
    # Filter to years where we have data
    # We have 1980-2020 files, but check what's actually available
    available_years = set()
    era5_dir = project_root / 'data' / 'tc_intensity' / 'monthly' / 'era5' / 'pressure_levels'
    if era5_dir.exists():
        for f in era5_dir.glob("era5_monthly_plev_*.nc"):
            parts = f.stem.split('_')
            if len(parts) >= 4:
                try:
                    year = int(parts[-2])
                    available_years.add(year)
                except:
                    pass
    
    print(f"\n📅 Years with ERA5 data: {sorted(available_years)}")
    
    # Filter tracks to available years
    tracks['year'] = pd.to_datetime(tracks['time']).dt.year
    tracks['month'] = pd.to_datetime(tracks['time']).dt.month
    test_tracks = tracks[tracks['year'].isin(available_years)].copy()
    
    if len(test_tracks) == 0:
        print("❌ No tracks in available years")
        return []
    
    print(f"   Tracks in available years: {len(test_tracks)}")
    
    # Select a few diverse test cases
    test_cases = test_tracks.sample(min(num_tests, len(test_tracks)), random_state=42)
    
    results = []
    
    for idx, (_, obs) in enumerate(test_cases.iterrows(), 1):
        print(f"\n🧪 Test {idx}/{num_tests}: {obs.get('storm_id', 'UNKNOWN')} at {obs['time']}")
        print(f"   Location: ({obs['lat']:.2f}, {obs['lon']:.2f})")
        
        time = pd.to_datetime(obs['time'])
        year = time.year
        month = time.month
        
        try:
            # Load monthly grids
            era5_datasets = load_monthly_era5_grids(year, month)
            if not era5_datasets:
                print(f"   ⚠️  No ERA5 data for {year}/{month:02d}")
                continue
            
            oras5_dataset = load_monthly_oras5_grid(year, month)
            
            # Extract variables
            variables = extract_all_environmental_variables_at_tc_location(
                lat=obs['lat'],
                lon=obs['lon'],
                time=time,
                era5_datasets=era5_datasets,
                oras5_dataset=oras5_dataset,
                trajectory_df=None
            )
            
            # Check key variables
            required_vars = ['temperature_850', 'temperature_250', 'u_wind_850', 'v_wind_850', 'sst']
            missing = [v for v in required_vars if v not in variables]
            
            if missing:
                print(f"   ⚠️  Missing variables: {missing}")
            else:
                print(f"   ✅ All key variables extracted")
            
            # Check PI if available
            if 'pi' in variables:
                pi_value = variables['pi']
                print(f"   ✅ PI calculated: {pi_value:.2f} m/s")
                if pi_value < 10 or pi_value > 150:
                    print(f"   ⚠️  PI value seems unusual (expected 30-90 m/s)")
                else:
                    print(f"   ✅ PI in reasonable range")
            
            # Show sample variables
            print(f"   📊 Sample values:")
            for var in ['temperature_850', 'temperature_250', 'sst', 'surface_pressure']:
                if var in variables:
                    val = variables[var]
                    unit = 'K' if 'temperature' in var or var == 'sst' else 'hPa' if 'pressure' in var else ''
                    print(f"      {var}: {val:.2f} {unit}")
            
            results.append({
                'storm_id': obs.get('storm_id', 'UNKNOWN'),
                'time': obs['time'],
                'lat': obs['lat'],
                'lon': obs['lon'],
                'variables': variables,
                'success': True
            })
            
            # Close datasets to free memory
            for ds in era5_datasets.values():
                if hasattr(ds, 'close'):
                    ds.close()
            if oras5_dataset is not None and hasattr(oras5_dataset, 'close'):
                oras5_dataset.close()
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'storm_id': obs.get('storm_id', 'UNKNOWN'),
                'time': obs['time'],
                'success': False,
                'error': str(e)
            })
    
    return results


def test_pi_calculation():
    """Test PI calculation specifically with 29-level data."""
    print("\n" + "=" * 70)
    print("TEST 4: TESTING PI CALCULATION")
    print("=" * 70)
    
    try:
        from src.tc_intensity.physics.potential_intensity_tcpyPI import calculate_pi_tcpyPI
        
        # Check if we have a good ERA5 file with 29 levels
        era5_dir = project_root / 'data' / 'tc_intensity' / 'monthly' / 'era5' / 'pressure_levels'
        era5_files = sorted(era5_dir.glob("*.nc")) if era5_dir.exists() else []
        
        if not era5_files:
            print("❌ No ERA5 files available")
            return
        
        # Load one file
        import xarray as xr
        test_file = era5_files[0]
        print(f"\n📁 Testing with: {test_file.name}")
        
        ds = xr.open_dataset(test_file)
        
        if 'pressure_level' not in ds.dims:
            print("❌ File doesn't have pressure_level dimension")
            ds.close()
            return
        
        levels = len(ds.pressure_level)
        print(f"   Pressure levels: {levels}")
        
        if levels < 29:
            print(f"   ⚠️  Only {levels} levels, but PI calculation will still work")
        
        # Check required variables (ERA5 uses short names: t, u, v, q)
        required_vars = ['t', 'u', 'v', 'q']  # ERA5 variable names
        available_vars = list(ds.data_vars)
        missing = [v for v in required_vars if v not in available_vars]
        
        if missing:
            print(f"   ⚠️  Missing variables for PI: {missing}")
            print(f"   Available: {available_vars}")
        else:
            print(f"   ✅ All required variables present")
        
        # Try a sample PI calculation
        print(f"\n🧪 Attempting sample PI calculation...")
        
        # Get a sample location (e.g., tropical Atlantic)
        lat_idx = len(ds.latitude) // 2
        lon_idx = len(ds.longitude) // 2
        
        # Extract profiles (ERA5 uses short names: t, u, v, q)
        temp_profile = ds['t'].isel(valid_time=0, latitude=lat_idx, longitude=lon_idx).values
        u_profile = ds['u'].isel(valid_time=0, latitude=lat_idx, longitude=lon_idx).values
        v_profile = ds['v'].isel(valid_time=0, latitude=lat_idx, longitude=lon_idx).values
        q_profile = ds['q'].isel(valid_time=0, latitude=lat_idx, longitude=lon_idx).values
        pressure_levels = ds['pressure_level'].values
        
        # Get SST from single-level data if available
        sl_file = project_root / 'data' / 'tc_intensity' / 'monthly' / 'era5' / 'single_level' / test_file.name.replace('plev_', 'sl_')
        sst = None
        if sl_file.exists():
            ds_sl = xr.open_dataset(sl_file)
            if 'sst' in ds_sl.data_vars or 'sea_surface_temperature' in ds_sl.data_vars:
                sst_var = 'sst' if 'sst' in ds_sl.data_vars else 'sea_surface_temperature'
                sst = float(ds_sl[sst_var].isel(valid_time=0, latitude=lat_idx, longitude=lon_idx).values)
                print(f"   SST from ERA5: {sst:.2f} K ({sst-273.15:.2f} °C)")
            ds_sl.close()
        
        if sst is None:
            print(f"   ⚠️  SST not available, using default")
            sst = 303.15  # 30°C default
        
        # Calculate PI (tcpyPI wrapper signature)
        try:
            from src.tc_intensity.physics.potential_intensity_tcpyPI import calculate_pi_tcpyPI
            
            pi_result = calculate_pi_tcpyPI(
                sst_k=sst,  # Already in Kelvin
                surface_pressure=1013.25,  # hPa
                temperature_profile=temp_profile,  # K
                pressure_levels=pressure_levels * 100.0,  # Convert hPa to Pa
                specific_humidity_profile=q_profile  # kg/kg
            )
            
            print(f"\n   ✅ PI calculation successful!")
            print(f"   PI value: {pi_result:.2f} m/s")
            if 30 <= pi_result <= 90:
                print(f"   ✅ PI in expected range (30-90 m/s)")
            else:
                print(f"   ⚠️  PI outside typical range (might be valid for this location)")
                
        except Exception as e:
            print(f"   ❌ PI calculation failed: {e}")
            import traceback
            traceback.print_exc()
        
        ds.close()
        
    except Exception as e:
        print(f"❌ Error in PI test: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("TC INTENSITY EXTRACTION PIPELINE TEST")
    print("=" * 70)
    print(f"Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Check files
    era5_count, oras5_count = test_loaded_files()
    
    if era5_count == 0:
        print("\n❌ No ERA5 files available for testing")
        return
    
    # Test 2: Load tracks
    tracks = test_tc_tracks()
    
    # Test 3: Extract variables
    extraction_results = test_variable_extraction(tracks, num_tests=5)
    
    # Test 4: PI calculation
    test_pi_calculation()
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"✅ ERA5 files available: {era5_count}")
    print(f"✅ ORAS5 files available: {oras5_count}")
    
    if tracks is not None:
        print(f"✅ TC tracks loaded: {len(tracks)}")
    
    if extraction_results:
        successful = sum(1 for r in extraction_results if r.get('success', False))
        print(f"✅ Variable extractions tested: {successful}/{len(extraction_results)} successful")
    
    print("\n" + "=" * 70)
    print("✅ TESTING COMPLETE")
    print("=" * 70)


if __name__ == '__main__':
    main()

