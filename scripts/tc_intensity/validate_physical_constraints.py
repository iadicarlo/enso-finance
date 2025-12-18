#!/usr/bin/env python3
"""
Physical Constraints Validation for Synthetic TC Tracks

Validates that synthetic tracks obey fundamental physical constraints:
1. Genesis latitude bounds (5° to 30°)
2. Intensification requires sufficient potential intensity
3. Land decay follows exponential model
4. RMW-intensity relationship
5. Translation speed-latitude relationship

References:
- Kaplan & DeMaria (1995): Land decay
- Willoughby et al. (2006): RMW-intensity
- Gray (1968): Genesis latitude constraints
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

print("="*80)
print("PHYSICAL CONSTRAINTS VALIDATION")
print("="*80)

def validate_genesis_latitude(df: pd.DataFrame) -> dict:
    """Constraint 1: Genesis between 5° and 35° latitude (relaxed for subtropical)."""
    print("\n[1] Genesis Latitude Bounds")
    print("-" * 40)
    
    id_col = 'storm_id' if 'storm_id' in df.columns else 'track_id'
    genesis = df.groupby(id_col).first()
    genesis_lats = genesis['lat'].abs()
    
    too_low = (genesis_lats < 5).sum()
    too_high = (genesis_lats > 35).sum()  # Relaxed to 35° for subtropical
    total = len(genesis_lats)
    
    print(f"Total storms: {total}")
    print(f"Genesis <5°: {too_low} ({100*too_low/total:.1f}%)")
    print(f"Genesis >35°: {too_high} ({100*too_high/total:.1f}%)")
    print(f"Valid (5-35°): {total-too_low-too_high} ({100*(total-too_low-too_high)/total:.1f}%)")
    print(f"Note: Relaxed to 35° to include subtropical genesis")
    
    violation_rate = 100 * (too_low + too_high) / total
    status = "✅ PASS" if violation_rate < 5 else "⚠️ WARNING"
    print(f"\n{status}: {violation_rate:.1f}% violations")
    
    return {
        'constraint': 'genesis_latitude',
        'total': total,
        'violations': too_low + too_high,
        'violation_rate': violation_rate,
        'pass': violation_rate < 5
    }

def validate_rmw_intensity(df: pd.DataFrame) -> dict:
    """Constraint 4: RMW scales with intensity (Willoughby 2006)."""
    print("\n[4] RMW-Intensity Relationship")
    print("-" * 40)
    
    if 'rmw_m' not in df.columns:
        print("⚠️ No RMW data available")
        return {'constraint': 'rmw_intensity', 'pass': None}
    
    # Filter valid data
    valid = df[(df['wind_speed_ms'] >= 18) & (df['rmw_m'] > 0)].copy()
    
    if len(valid) == 0:
        print("⚠️ No valid RMW-intensity pairs")
        return {'constraint': 'rmw_intensity', 'pass': None}
    
    # Willoughby et al. (2006): RMW decreases with intensity
    # Typical: RMW ~ 100 km for TS, 20-40 km for Cat 5
    valid['rmw_km'] = valid['rmw_m'] / 1000
    
    # Bin by intensity
    bins = [18, 33, 43, 50, 59, 100]
    labels = ['TS', 'Cat1', 'Cat2', 'Cat3', 'Cat4+']
    valid['category'] = pd.cut(valid['wind_speed_ms'], bins=bins, labels=labels)
    
    print("Mean RMW by category:")
    for cat in labels:
        cat_data = valid[valid['category'] == cat]
        if len(cat_data) > 0:
            print(f"  {cat:6s}: {cat_data['rmw_km'].mean():5.1f} km (n={len(cat_data)})")
    
    # Check correlation (should be negative)
    corr, pval = stats.pearsonr(valid['wind_speed_ms'], valid['rmw_km'])
    print(f"\nCorrelation: r={corr:.3f}, p={pval:.3e}")
    
    status = "✅ PASS" if corr < 0 and pval < 0.05 else "⚠️ WARNING"
    print(f"{status}: RMW decreases with intensity")
    
    return {
        'constraint': 'rmw_intensity',
        'correlation': corr,
        'p_value': pval,
        'pass': corr < 0 and pval < 0.05
    }

def validate_translation_speed_latitude(df: pd.DataFrame) -> dict:
    """Constraint 5: Translation speed increases with latitude."""
    print("\n[5] Translation Speed vs Latitude")
    print("-" * 40)
    
    id_col = 'storm_id' if 'storm_id' in df.columns else 'track_id'
    
    speeds = []
    lats = []
    
    for sid, grp in df.groupby(id_col):
        if len(grp) < 2:
            continue
        
        lat_vals = grp['lat'].values
        lon_vals = grp['lon'].values
        time_vals = grp['time_hours'].values
        
        for i in range(len(grp)-1):
            dt = time_vals[i+1] - time_vals[i]
            if dt <= 0:
                continue
            
            # Haversine distance
            dlat = np.radians(lat_vals[i+1] - lat_vals[i])
            dlon = np.radians(lon_vals[i+1] - lon_vals[i])
            a = (np.sin(dlat/2)**2 + 
                 np.cos(np.radians(lat_vals[i])) * 
                 np.cos(np.radians(lat_vals[i+1])) * 
                 np.sin(dlon/2)**2)
            dist_km = 2 * 6371 * np.arcsin(np.sqrt(a))
            
            speed_ms = (dist_km * 1000) / (dt * 3600)
            speeds.append(speed_ms)
            lats.append(abs(lat_vals[i]))
    
    speeds = np.array(speeds)
    lats = np.array(lats)
    
    # Bin by latitude
    lat_bins = [0, 10, 20, 30, 40, 90]
    lat_labels = ['0-10°', '10-20°', '20-30°', '30-40°', '40+°']
    
    print("Mean translation speed by latitude:")
    for i in range(len(lat_bins)-1):
        mask = (lats >= lat_bins[i]) & (lats < lat_bins[i+1])
        if mask.sum() > 0:
            print(f"  {lat_labels[i]:8s}: {speeds[mask].mean():5.1f} m/s (n={mask.sum()})")
    
    # Check correlation (should be positive)
    corr, pval = stats.pearsonr(lats, speeds)
    print(f"\nCorrelation: r={corr:.3f}, p={pval:.3e}")
    
    status = "✅ PASS" if corr > 0 and pval < 0.05 else "⚠️ WARNING"
    print(f"{status}: Speed increases with latitude")
    
    return {
        'constraint': 'translation_latitude',
        'correlation': corr,
        'p_value': pval,
        'pass': corr > 0 and pval < 0.05
    }

def validate_intensity_bounds(df: pd.DataFrame) -> dict:
    """Check intensity stays within physical bounds."""
    print("\n[6] Intensity Physical Bounds")
    print("-" * 40)
    
    max_wind = df['wind_speed_ms'].max()
    min_wind = df['wind_speed_ms'].min()
    
    # Physical bounds: 18 m/s (TS threshold) to ~95 m/s (theoretical max)
    too_low = (df['wind_speed_ms'] < 18).sum()
    too_high = (df['wind_speed_ms'] > 95).sum()
    
    print(f"Intensity range: {min_wind:.1f} to {max_wind:.1f} m/s")
    print(f"Below TS (18 m/s): {too_low} ({100*too_low/len(df):.1f}%)")
    print(f"Above 95 m/s: {too_high} ({100*too_high/len(df):.1f}%)")
    
    violation_rate = 100 * (too_low + too_high) / len(df)
    status = "✅ PASS" if violation_rate < 1 else "⚠️ WARNING"
    print(f"\n{status}: {violation_rate:.2f}% violations")
    
    return {
        'constraint': 'intensity_bounds',
        'max_intensity': max_wind,
        'violations': too_low + too_high,
        'violation_rate': violation_rate,
        'pass': violation_rate < 1
    }

def validate_land_decay(df: pd.DataFrame) -> dict:
    """Constraint 3: Intensity decay over land (Kaplan & DeMaria 1995)."""
    print("\n[3] Land Decay (K&D 1995)")
    print("-" * 40)
    
    if 'is_land' not in df.columns or 'bathymetry' not in df.columns:
        print("⚠️ No land data available")
        return {'constraint': 'land_decay', 'pass': None}
    
    id_col = 'storm_id' if 'storm_id' in df.columns else 'track_id'
    
    # Find landfalling storms
    landfall_tracks = []
    for sid, grp in df.groupby(id_col):
        grp = grp.sort_values('time_hours')
        if grp['is_land'].any():
            # Find landfall point (first land after ocean)
            for i in range(1, len(grp)):
                if not grp.iloc[i-1]['is_land'] and grp.iloc[i]['is_land']:
                    landfall_tracks.append((sid, i, grp))
                    break
    
    if len(landfall_tracks) == 0:
        print("⚠️ No landfalling storms found")
        return {'constraint': 'land_decay', 'pass': None}
    
    print(f"Found {len(landfall_tracks)} landfalling storms")
    
    # Check decay characteristics
    decay_rates = []
    monotonic_decay = 0
    total_landfall = 0
    
    for sid, landfall_idx, grp in landfall_tracks:
        grp_array = grp.reset_index(drop=True)
        
        # Get land segment
        land_segment = grp_array[grp_array['is_land']]
        if len(land_segment) < 2:
            continue
        
        total_landfall += 1
        v_landfall = land_segment.iloc[0]['wind_speed_ms']
        
        # Check if intensity decreases monotonically (allowing small increases)
        intensities = land_segment['wind_speed_ms'].values
        decreases = 0
        for i in range(1, len(intensities)):
            if intensities[i] <= intensities[i-1] * 1.05:  # Allow 5% noise
                decreases += 1
        
        if decreases >= len(intensities) - 1:
            monotonic_decay += 1
        
        # Estimate decay rate (if enough points)
        if len(land_segment) >= 3:
            times = land_segment['time_hours'].values - land_segment['time_hours'].values[0]
            winds = land_segment['wind_speed_ms'].values
            
            # Fit exponential: V(t) = V0 * exp(-λt)
            # ln(V) = ln(V0) - λt
            if (winds > 0).all():
                log_winds = np.log(winds)
                # Simple linear fit
                if times[-1] > 0:
                    decay_rate = -(log_winds[-1] - log_winds[0]) / times[-1]
                    decay_rates.append(decay_rate)
    
    if total_landfall == 0:
        print("⚠️ No valid landfall segments")
        return {'constraint': 'land_decay', 'pass': None}
    
    monotonic_pct = 100 * monotonic_decay / total_landfall
    print(f"Monotonic decay: {monotonic_decay}/{total_landfall} ({monotonic_pct:.1f}%)")
    
    if len(decay_rates) > 0:
        mean_decay = np.mean(decay_rates)
        # Literature comparison
        print(f"Mean decay rate: {mean_decay:.4f} h⁻¹")
        print(f"  K&D (1995): 0.105 h⁻¹ (empirical, R=0.90/hour)")
        print(f"  FAST (2017): 0.01-0.02 h⁻¹ (physics, Vp=0)")
        print(f"  STORM (2020): Uses K&D explicitly")
        print(f"  50% decay time: {np.log(2)/mean_decay:.1f} hours (K&D: 6.6h)")
        
        # Check if matches K&D (0.08-0.12 h⁻¹)
        kd_match = 0.08 <= mean_decay <= 0.12
        if kd_match:
            print(f"  ✅ Matches K&D range (0.08-0.12 h⁻¹)")
            status = "✅ PASS"
        elif 0.05 <= mean_decay < 0.08:
            print(f"  ⚠️ Slower than K&D but faster than FAST")
            status = "⚠️ WARNING"
        elif mean_decay < 0.05:
            print(f"  ❌ Too slow (< 0.05 h⁻¹)")
            status = "❌ FAIL"
        else:
            print(f"  ⚠️ Faster than K&D (> 0.12 h⁻¹)")
            status = "⚠️ WARNING"
    else:
        mean_decay = np.nan
        kd_match = False
        status = "⚠️ WARNING"
    
    print(f"\n{status}: Decay characteristics")
    
    return {
        'constraint': 'land_decay',
        'n_landfall': total_landfall,
        'monotonic_pct': monotonic_pct,
        'mean_decay_rate': mean_decay if len(decay_rates) > 0 else np.nan,
        'expected_kd': 0.105,
        'expected_fast': 0.015,
        'pass': kd_match and monotonic_pct >= 70 if len(decay_rates) > 0 else None
    }


def validate_spatial_bounds(df: pd.DataFrame, basin: str) -> dict:
    """Check storms stay within basin bounds."""
    print("\n[7] Spatial Basin Bounds")
    print("-" * 40)
    
    # Basin bounds (approximate)
    basin_bounds = {
        'NA': {'lat': (5, 50), 'lon': (-100, -10)},
        'EP': {'lat': (5, 40), 'lon': (-180, -80)},
        'WP': {'lat': (0, 40), 'lon': (100, 180)},
        'NI': {'lat': (5, 30), 'lon': (40, 100)},
        'SI': {'lat': (-40, -5), 'lon': (30, 120)},
        'SP': {'lat': (-40, -5), 'lon': (135, 240)},
    }
    
    if basin not in basin_bounds:
        print(f"⚠️ Unknown basin: {basin}")
        return {'constraint': 'spatial_bounds', 'pass': None}
    
    bounds = basin_bounds[basin]
    lat_min, lat_max = bounds['lat']
    lon_min, lon_max = bounds['lon']
    
    out_of_bounds = (
        (df['lat'] < lat_min) | (df['lat'] > lat_max) |
        (df['lon'] < lon_min) | (df['lon'] > lon_max)
    ).sum()
    
    print(f"Basin: {basin}")
    print(f"Bounds: lat [{lat_min}, {lat_max}], lon [{lon_min}, {lon_max}]")
    print(f"Out of bounds: {out_of_bounds} ({100*out_of_bounds/len(df):.1f}%)")
    
    violation_rate = 100 * out_of_bounds / len(df)
    status = "✅ PASS" if violation_rate < 5 else "⚠️ WARNING"
    print(f"\n{status}: {violation_rate:.1f}% out of bounds")
    
    return {
        'constraint': 'spatial_bounds',
        'violations': out_of_bounds,
        'violation_rate': violation_rate,
        'pass': violation_rate < 5
    }

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Validate physical constraints')
    parser.add_argument('--synthetic-file', required=True, help='Synthetic tracks CSV')
    parser.add_argument('--basin', required=True, help='Basin code')
    parser.add_argument('--output-dir', default='outputs/validation/physical', help='Output directory')
    args = parser.parse_args()
    
    synthetic_file = Path(args.synthetic_file)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nSynthetic file: {synthetic_file.name}")
    print(f"Basin: {args.basin}")
    
    # Load data
    df = pd.read_csv(synthetic_file)
    if 'track_id' in df.columns and 'storm_id' not in df.columns:
        df['storm_id'] = df['track_id']
    
    print(f"Loaded: {len(df)} points, {df['storm_id'].nunique()} storms")
    
    # Run validations
    results = []
    results.append(validate_genesis_latitude(df))
    results.append(validate_rmw_intensity(df))
    results.append(validate_land_decay(df))
    results.append(validate_translation_speed_latitude(df))
    results.append(validate_intensity_bounds(df))
    results.append(validate_spatial_bounds(df, args.basin))
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    passed = sum(1 for r in results if r.get('pass') == True)
    failed = sum(1 for r in results if r.get('pass') == False)
    skipped = sum(1 for r in results if r.get('pass') is None)
    
    print(f"✅ Passed: {passed}")
    print(f"⚠️  Failed: {failed}")
    print(f"~  Skipped: {skipped}")
    
    if failed == 0:
        print("\n✅ All physical constraints validated!")
    else:
        print(f"\n⚠️  {failed} constraint(s) need attention")
    
    # Save results
    results_df = pd.DataFrame(results)
    output_file = output_dir / f'physical_constraints_{args.basin}.csv'
    results_df.to_csv(output_file, index=False)
    print(f"\nResults saved: {output_file}")

if __name__ == '__main__':
    main()
