#!/usr/bin/env python3
"""
Generate Event Set for Validation

Generate a large set of synthetic tracks and validate against IBTrACS observations.

Usage:
    uv run python scripts/tc_intensity/generate_event_set.py --basin NA --n-tracks 100
"""

import sys
from pathlib import Path
import argparse
import warnings
from typing import Optional
import numpy as np
import pandas as pd
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.tc_intensity.uqam.simulation_pipeline import UQAMSimulationPipeline
from src.tc_intensity.uqam.utils import LMI_THRESHOLD_MS
from src.tc_intensity.bathymetry.etopo1 import extract_bathymetry_at_location
from src.tc_intensity.physics.land_decay import kaplan_demaria_decay

warnings.filterwarnings('ignore')


def add_landfall_and_kd_decay(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add landfall detection and apply Kaplan-DeMaria (1995) decay over land.
    
    Hybrid approach:
    - FAST model for ocean intensification (physics-based)
    - K&D empirical decay over land (λ=0.105 h⁻¹, R=0.90/hour)
    
    This matches STORM model (Bloemendaal 2020) and industry best practices.
    """
    print("\n🌴 Adding landfall detection and K&D decay...")
    print("  Extracting bathymetry...")
    
    # Extract bathymetry for all points
    bathymetry = []
    for _, row in df.iterrows():
        try:
            bathy = extract_bathymetry_at_location(row['lat'], row['lon'])
            bathymetry.append(bathy)
        except:
            bathymetry.append(np.nan)
    
    df['bathymetry'] = bathymetry
    df['is_land'] = (np.array(bathymetry) >= 0) & ~np.isnan(bathymetry)
    
    # Apply K&D decay to each landfalling track
    print("  Applying Kaplan-DeMaria (1995) decay over land...")
    
    for track_id in df['track_id'].unique():
        track_mask = df['track_id'] == track_id
        track_data = df[track_mask].copy()
        
        # Find landfall transitions (ocean → land)
        is_land = track_data['is_land'].values
        wind_speeds = track_data['wind_speed_ms'].values
        times = track_data['time_hours'].values  # Already in hours
        
        # Track landfall events
        for i in range(1, len(is_land)):
            if not is_land[i-1] and is_land[i]:
                # Landfall detected
                v_landfall = wind_speeds[i-1]  # Wind at last ocean point
                t_landfall = times[i]
                
                # Apply K&D decay to all subsequent land points
                j = i
                while j < len(is_land) and is_land[j]:
                    hours_over_land = times[j] - t_landfall
                    wind_speeds[j] = kaplan_demaria_decay(
                        v_landfall, 
                        hours_over_land,
                        decay_rate=0.90,  # Standard K&D
                        v_inland=18.0     # TS threshold
                    )
                    j += 1
        
        # Update dataframe
        df.loc[track_mask, 'wind_speed'] = wind_speeds
    
    n_land = df['is_land'].sum()
    n_landfall = df.groupby('track_id')['is_land'].any().sum()
    print(f"  ✅ {n_landfall} landfalling tracks ({100*n_landfall/df['track_id'].nunique():.1f}%), {n_land} land points")
    print(f"  ✅ K&D decay applied (R=0.90/hour, λ=0.105 h⁻¹)")
    
    return df


def generate_event_set(
    basin: str,
    n_tracks: int = 100,
    calibration_dir: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    random_seed: Optional[int] = None
) -> pd.DataFrame:
    """
    Generate an event set of synthetic tracks.
    
    Parameters
    ----------
    basin : str
        Basin code
    n_tracks : int
        Number of tracks to generate
    calibration_dir : Path, optional
        Calibration directory
    output_dir : Path, optional
        Output directory for saving tracks
    random_seed : int, optional
        Random seed
        
    Returns
    -------
    pd.DataFrame
        Summary statistics of generated tracks
    """
    print("="*70)
    print(f"GENERATING EVENT SET: {basin} BASIN")
    print("="*70)
    print(f"Target tracks: {n_tracks}")
    print(f"Basin: {basin}")
    
    # Initialize pipeline
    if calibration_dir is None:
        calibration_dir = project_root / "outputs" / "tc_intensity" / "uqam_calibration"
    
    print(f"\nInitializing pipeline...")
    pipeline = UQAMSimulationPipeline(
        basin=basin,
        calibration_dir=calibration_dir,
        random_seed=random_seed
    )
    
    # Test different ENSO conditions
    # Note: Uses 4-phase ENSO classification (Extreme/Moderate El Nino, La Nina, Neutral)
    test_cases = [
        {"jmai": 0.0, "phase": "Neutral"},
        {"jmai": 1.0, "phase": "Moderate El Nino"},  # Matches calibration PDFs
        {"jmai": -1.0, "phase": "La Nina"},  # Matches calibration PDFs
    ]
    
    all_tracks = []
    all_summaries = []
    
    for test_case in test_cases:
        jmai = test_case["jmai"]
        phase = test_case["phase"]
        
        print(f"\n{'='*70}")
        print(f"Generating {phase} tracks (JMAI={jmai})...")
        print(f"{'='*70}")
        
        tracks_per_phase = n_tracks // len(test_cases)
        remaining = n_tracks - (tracks_per_phase * len(test_cases))
        
        # Give extra tracks to Neutral phase if remainder
        target = tracks_per_phase + (remaining if phase == "Neutral" else 0)
        
        print(f"Target: {target} tracks")
        
        event_set = pipeline.generate_event_set(
            jmai_value=jmai,
            enso_phase=phase,
            target_n_tracks=target,
            max_attempts=target * 10,  # Allow more attempts
            max_steps=200,
            dt_hours=6,
            lmi_threshold_ms=LMI_THRESHOLD_MS
        )
        
        print(f"Generated: {len(event_set)} tracks")
        
        # Summarize tracks
        for i, track in enumerate(event_set):
            summary = {
                'track_id': f"{basin}_{phase}_{i+1}",
                'basin': basin,
                'enso_phase': phase,
                'jmai': jmai,
                'lmi_ms': float(track['wind_speed_ms'].max()),
                'duration_hours': float(
                    (track['time_hours'].iloc[-1] - track['time_hours'].iloc[0])
                    if len(track) > 1 else 0
                ),
                'n_points': len(track),
                'genesis_lat': float(track['lat'].iloc[0]),
                'genesis_lon': float(track['lon'].iloc[0]),
                'mean_rmw_km': float(track['rmw_m'].mean() / 1000) if 'rmw_m' in track.columns else np.nan,
            }
            
            all_summaries.append(summary)
            all_tracks.append(track)
    
    # Create summary DataFrame
    summary_df = pd.DataFrame(all_summaries)
    
    # Save tracks if output directory provided
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save summary
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        summary_file = output_dir / f"event_set_summary_{basin}_{timestamp}.csv"
        summary_df.to_csv(summary_file, index=False)
        print(f"\n✅ Summary saved to: {summary_file}")
        
        # Save full event set (concatenate all tracks)
        if all_tracks:
            # Add track_id and metadata to each track
            for track, summary in zip(all_tracks, all_summaries):
                track['track_id'] = summary['track_id']
                track['basin'] = summary['basin']
                track['enso_phase'] = summary['enso_phase']
                track['jmai'] = summary['jmai']
            
    # Concatenate all tracks
    full_event_set = pd.concat(all_tracks, ignore_index=True)
    
    # Add landfall detection and K&D decay (hybrid: FAST ocean + K&D land)
    full_event_set = add_landfall_and_kd_decay(full_event_set)
    
    # Save to file
    event_set_file = output_dir / f"synthetic_event_set_{basin}_{timestamp}.csv"
    full_event_set.to_csv(event_set_file, index=False)
    print(f"✅ Full event set saved to: {event_set_file}")
    
    # Save individual tracks (optional - can be large)
    # tracks_dir = output_dir / f"tracks_{basin}_{timestamp}"
    # tracks_dir.mkdir(parents=True, exist_ok=True)
    # for track, summary in zip(all_tracks, all_summaries):
    #     track_file = tracks_dir / f"{summary['track_id']}.csv"
    #     track.to_csv(track_file, index=False)
    
    return summary_df


def print_statistics(summary_df: pd.DataFrame, basin: str):
    """Print summary statistics."""
    print(f"\n{'='*70}")
    print(f"EVENT SET STATISTICS: {basin} BASIN")
    print(f"{'='*70}")
    
    print(f"\nOverall:")
    print(f"  Total tracks: {len(summary_df)}")
    print(f"  Mean LMI: {summary_df['lmi_ms'].mean():.1f} m/s")
    print(f"  Median LMI: {summary_df['lmi_ms'].median():.1f} m/s")
    print(f"  Max LMI: {summary_df['lmi_ms'].max():.1f} m/s")
    print(f"  Min LMI: {summary_df['lmi_ms'].min():.1f} m/s")
    
    if 'mean_rmw_km' in summary_df.columns and not summary_df['mean_rmw_km'].isna().all():
        print(f"  Mean RMW: {summary_df['mean_rmw_km'].mean():.1f} km")
    
    print(f"\nBy ENSO Phase:")
    for phase in summary_df['enso_phase'].unique():
        phase_data = summary_df[summary_df['enso_phase'] == phase]
        print(f"\n  {phase}:")
        print(f"    Count: {len(phase_data)}")
        print(f"    Mean LMI: {phase_data['lmi_ms'].mean():.1f} m/s")
        print(f"    Mean duration: {phase_data['duration_hours'].mean():.1f} hours")
        if 'mean_rmw_km' in phase_data.columns and not phase_data['mean_rmw_km'].isna().all():
            print(f"    Mean RMW: {phase_data['mean_rmw_km'].mean():.1f} km")


def main():
    parser = argparse.ArgumentParser(description="Generate event set of synthetic tracks")
    parser.add_argument(
        '--basin',
        type=str,
        default='NA',
        choices=['NA', 'EP', 'WP', 'NI', 'SI', 'SP'],
        help='Basin to simulate (default: NA)'
    )
    parser.add_argument(
        '--n-tracks',
        type=int,
        default=100,
        help='Total number of tracks to generate (default: 100)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='Output directory (default: outputs/tc_intensity/synthetic_tracks)'
    )
    parser.add_argument(
        '--calibration-dir',
        type=str,
        default=None,
        help='Calibration directory (default: outputs/tc_intensity/uqam_calibration)'
    )
    parser.add_argument(
        '--random-seed',
        type=int,
        default=None,
        help='Random seed for reproducibility'
    )
    
    args = parser.parse_args()
    
    # Set output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = project_root / "outputs" / "tc_intensity" / "synthetic_tracks"
    
    # Generate event set
    summary_df = generate_event_set(
        basin=args.basin,
        n_tracks=args.n_tracks,
        calibration_dir=args.calibration_dir,
        output_dir=output_dir,
        random_seed=args.random_seed
    )
    
    # Print statistics
    print_statistics(summary_df, args.basin)
    
    print(f"\n{'='*70}")
    print("EVENT SET GENERATION COMPLETE")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()

