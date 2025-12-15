#!/usr/bin/env python3
"""
Apply UQAM-style post-processing to TC intensity predictions.

Implements quantile matching to correct simulated LMI distributions to match
observed distributions, as described in UQAM Section 2.7.

Method:
1. Calculate quantiles of observed LMI distribution (from IBTrACS)
2. Calculate quantiles of simulated LMI distribution  
3. Create mapping function: simulated_quantile -> observed_quantile
4. Apply transformation to all simulated intensities

Author: ENSO Finance Project
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from scipy import interpolate
from typing import Optional, Dict, Tuple
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def calculate_lmi_quantiles(intensities: np.ndarray, quantiles: Optional[np.ndarray] = None) -> np.ndarray:
    """
    Calculate quantiles of LMI distribution.
    
    Parameters
    ----------
    intensities : np.ndarray
        Lifetime maximum intensities (m/s)
    quantiles : np.ndarray, optional
        Quantile levels (0-1). Default: 100 quantiles (0.01, 0.02, ..., 1.0)
    
    Returns
    -------
    np.ndarray
        Quantile values
    """
    if quantiles is None:
        # Default: 100 quantiles for smooth mapping
        quantiles = np.linspace(0.01, 1.0, 100)
    
    # Filter to storms that reach at least tropical storm intensity (18 m/s)
    # As per UQAM methodology
    valid_intensities = intensities[intensities >= 18]
    
    if len(valid_intensities) == 0:
        return np.full(len(quantiles), np.nan)
    
    return np.quantile(valid_intensities, quantiles)


def create_quantile_mapping(
    observed_lmi: np.ndarray,
    simulated_lmi: np.ndarray,
    quantiles: Optional[np.ndarray] = None
) -> Tuple[np.ndarray, interpolate.interp1d]:
    """
    Create quantile mapping function from simulated to observed LMI.
    
    Parameters
    ----------
    observed_lmi : np.ndarray
        Observed lifetime maximum intensities
    simulated_lmi : np.ndarray
        Simulated lifetime maximum intensities
    quantiles : np.ndarray, optional
        Quantile levels to use for mapping
    
    Returns
    -------
    quantiles : np.ndarray
        Quantile levels used
    mapping_func : scipy.interpolate.interp1d
        Interpolation function: simulated_intensity -> corrected_intensity
    """
    if quantiles is None:
        # Use 100 quantiles for smooth mapping
        quantiles = np.linspace(0.01, 1.0, 100)
    
    # Calculate quantiles
    obs_quantiles = calculate_lmi_quantiles(observed_lmi, quantiles)
    sim_quantiles = calculate_lmi_quantiles(simulated_lmi, quantiles)
    
    # Remove NaN values
    valid_mask = np.isfinite(sim_quantiles) & np.isfinite(obs_quantiles)
    sim_quantiles_valid = sim_quantiles[valid_mask]
    obs_quantiles_valid = obs_quantiles[valid_mask]
    
    if len(sim_quantiles_valid) == 0:
        raise ValueError("No valid quantiles for mapping")
    
    # Create interpolation function
    # Use 'linear' interpolation with extrapolation
    # For values outside range, use nearest endpoint
    mapping_func = interpolate.interp1d(
        sim_quantiles_valid,
        obs_quantiles_valid,
        kind='linear',
        bounds_error=False,
        fill_value=(obs_quantiles_valid[0], obs_quantiles_valid[-1])
    )
    
    return quantiles, mapping_func


def apply_quantile_correction(
    simulated_intensities: np.ndarray,
    mapping_func: interpolate.interp1d
) -> np.ndarray:
    """
    Apply quantile correction to simulated intensities.
    
    Parameters
    ----------
    simulated_intensities : np.ndarray
        Simulated intensities to correct
    mapping_func : scipy.interpolate.interp1d
        Quantile mapping function
    
    Returns
    -------
    np.ndarray
        Corrected intensities
    """
    # Apply mapping
    corrected = mapping_func(simulated_intensities)
    
    # Ensure values are finite and non-negative
    corrected = np.clip(corrected, 0, np.inf)
    corrected = np.nan_to_num(corrected, nan=0.0, posinf=0.0)
    
    return corrected


def apply_postprocessing_to_storms(
    df: pd.DataFrame,
    observed_lmi: np.ndarray,
    simulated_lmi: np.ndarray,
    basin: Optional[str] = None,
    per_enso_phase: bool = False
) -> Tuple[np.ndarray, Dict]:
    """
    Apply UQAM-style post-processing to simulated LMI values.
    
    Parameters
    ----------
    df : pd.DataFrame
        Dataframe with storm information (must have 'storm_id' and optionally 'basin', 'enso_phase')
    observed_lmi : np.ndarray
        Observed LMI per storm (same order as df['storm_id'].unique())
    simulated_lmi : np.ndarray
        Simulated LMI per storm (same order as df['storm_id'].unique())
    basin : str, optional
        If provided, apply post-processing per basin
    per_enso_phase : bool
        If True, apply post-processing per ENSO phase (as per UQAM)
    
    Returns
    -------
    corrected_lmi : np.ndarray
        Post-processed LMI values
    mapping_info : dict
        Information about the mapping applied
    """
    if basin is not None and per_enso_phase:
        raise ValueError("Cannot specify both basin and per_enso_phase")
    
    if not ('storm_id' in df.columns):
        raise ValueError("DataFrame must have 'storm_id' column")
    
    # Get unique storms
    unique_storms = df['storm_id'].unique()
    if len(unique_storms) != len(observed_lmi) or len(unique_storms) != len(simulated_lmi):
        raise ValueError(f"Mismatch: {len(unique_storms)} storms, {len(observed_lmi)} observed, {len(simulated_lmi)} simulated")
    
    corrected_lmi = np.full_like(simulated_lmi, np.nan)
    mapping_info = {
        'method': 'quantile_matching',
        'basin': basin if basin else 'all',
        'per_enso_phase': per_enso_phase,
        'mappings': {}
    }
    
    if per_enso_phase:
        # Apply per ENSO phase (recommended by UQAM)
        if 'enso_phase' not in df.columns:
            raise ValueError("DataFrame must have 'enso_phase' column for per-phase processing")
        
        for phase in df['enso_phase'].dropna().unique():
            phase_mask = df['enso_phase'] == phase
            phase_storms = df[phase_mask]['storm_id'].unique()
            
            # Get indices of phase storms
            phase_storm_indices = np.where(np.isin(unique_storms, phase_storms))[0]
            
            if len(phase_storm_indices) < 10:  # Need minimum storms for quantile calculation
                # Use overall mapping if too few storms
                _, mapping_func = create_quantile_mapping(observed_lmi, simulated_lmi)
                corrected_lmi[phase_storm_indices] = apply_quantile_correction(
                    simulated_lmi[phase_storm_indices], mapping_func
                )
                mapping_info['mappings'][phase] = 'used_overall_mapping'
            else:
                # Create phase-specific mapping
                phase_obs = observed_lmi[phase_storm_indices]
                phase_sim = simulated_lmi[phase_storm_indices]
                
                try:
                    _, mapping_func = create_quantile_mapping(phase_obs, phase_sim)
                    corrected_lmi[phase_storm_indices] = apply_quantile_correction(
                        phase_sim, mapping_func
                    )
                    mapping_info['mappings'][phase] = 'phase_specific'
                except:
                    # Fallback to overall mapping
                    _, mapping_func = create_quantile_mapping(observed_lmi, simulated_lmi)
                    corrected_lmi[phase_storm_indices] = apply_quantile_correction(
                        simulated_lmi[phase_storm_indices], mapping_func
                    )
                    mapping_info['mappings'][phase] = 'fallback_overall'
    
    elif basin is not None:
        # Apply per basin
        if 'basin' not in df.columns:
            raise ValueError("DataFrame must have 'basin' column for per-basin processing")
        
        basin_mask = df['basin'] == basin
        basin_storms = df[basin_mask]['storm_id'].unique()
        basin_storm_indices = np.where(np.isin(unique_storms, basin_storms))[0]
        
        if len(basin_storm_indices) < 10:
            # Use overall mapping
            _, mapping_func = create_quantile_mapping(observed_lmi, simulated_lmi)
            corrected_lmi[basin_storm_indices] = apply_quantile_correction(
                simulated_lmi[basin_storm_indices], mapping_func
            )
            mapping_info['mappings'][basin] = 'used_overall_mapping'
        else:
            # Create basin-specific mapping
            basin_obs = observed_lmi[basin_storm_indices]
            basin_sim = simulated_lmi[basin_storm_indices]
            
            try:
                _, mapping_func = create_quantile_mapping(basin_obs, basin_sim)
                corrected_lmi[basin_storm_indices] = apply_quantile_correction(
                    basin_sim, mapping_func
                )
                mapping_info['mappings'][basin] = 'basin_specific'
            except:
                # Fallback
                _, mapping_func = create_quantile_mapping(observed_lmi, simulated_lmi)
                corrected_lmi[basin_storm_indices] = apply_quantile_correction(
                    simulated_lmi[basin_storm_indices], mapping_func
                )
                mapping_info['mappings'][basin] = 'fallback_overall'
    
    else:
        # Apply overall mapping
        _, mapping_func = create_quantile_mapping(observed_lmi, simulated_lmi)
        corrected_lmi = apply_quantile_correction(simulated_lmi, mapping_func)
        mapping_info['mappings']['all'] = 'overall'
    
    return corrected_lmi, mapping_info


def main():
    """Test post-processing on validation data."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Apply UQAM-style post-processing')
    parser.add_argument(
        '--data-file',
        type=str,
        default='outputs/tc_intensity/training_data/tc_training_data_ALL_basins.csv',
        help='Path to data file'
    )
    parser.add_argument(
        '--model-file',
        type=str,
        required=True,
        help='Path to trained model pickle file'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='outputs/tc_intensity/validation',
        help='Output directory'
    )
    parser.add_argument(
        '--per-enso-phase',
        action='store_true',
        help='Apply post-processing per ENSO phase (recommended)'
    )
    
    args = parser.parse_args()
    
    # Load data
    print(f"Loading data from: {args.data_file}")
    df = pd.read_csv(args.data_file)
    
    # Get observed LMI
    if 'storm_id' in df.columns and 'max_wind_ms' in df.columns:
        observed_lmi = df.groupby('storm_id')['max_wind_ms'].max().values
        unique_storms = df['storm_id'].unique()
    else:
        raise ValueError("Data must have 'storm_id' and 'max_wind_ms' columns")
    
    # Load model and make predictions
    print(f"Loading model from: {args.model_file}")
    import pickle
    
    try:
        from sklearn_compatibility_shim import load_model_with_compatibility
        model = load_model_with_compatibility(args.model_file)
        print("Model loaded using compatibility shim")
    except:
        with open(args.model_file, 'rb') as f:
            model = pickle.load(f)
        print("Model loaded using standard pickle")
    
    # Make predictions
    print("Making predictions...")
    df_for_pred = df.copy()
    if 'max_wind_ms' in df_for_pred.columns:
        df_for_pred = df_for_pred.drop(columns=['max_wind_ms'])
    
    predicted_intensities = model.predict(df_for_pred, sequential=True)
    
    # Calculate simulated LMI
    df_pred = df.copy()
    df_pred['predicted_intensity'] = predicted_intensities
    simulated_lmi = df_pred.groupby('storm_id')['predicted_intensity'].max().values
    
    print(f"Observed LMI: {len(observed_lmi)} storms")
    print(f"Simulated LMI: {len(simulated_lmi)} storms")
    
    # Apply post-processing
    print(f"\nApplying post-processing (per_enso_phase={args.per_enso_phase})...")
    corrected_lmi, mapping_info = apply_postprocessing_to_storms(
        df,
        observed_lmi,
        simulated_lmi,
        per_enso_phase=args.per_enso_phase
    )
    
    print(f"Mappings applied: {mapping_info['mappings']}")
    
    # Create comparison DataFrame
    comparison_df = pd.DataFrame({
        'storm_id': unique_storms,
        'observed_lmi': observed_lmi,
        'simulated_lmi_raw': simulated_lmi,
        'simulated_lmi_corrected': corrected_lmi
    })
    
    # Save results
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f'postprocessed_lmi_{timestamp}.csv'
    comparison_df.to_csv(output_file, index=False)
    
    # Save mapping info
    mapping_file = output_dir / f'postprocessing_mapping_info_{timestamp}.json'
    with open(mapping_file, 'w') as f:
        json.dump(mapping_info, f, indent=2, default=str)
    
    print(f"\n✅ Post-processing complete!")
    print(f"Results saved to: {output_file}")
    print(f"Mapping info saved to: {mapping_file}")
    
    # Print statistics
    print("\nStatistics:")
    print(f"Observed LMI: mean={observed_lmi.mean():.2f} m/s, std={observed_lmi.std():.2f} m/s")
    print(f"Simulated LMI (raw): mean={simulated_lmi.mean():.2f} m/s, std={simulated_lmi.std():.2f} m/s")
    print(f"Simulated LMI (corrected): mean={corrected_lmi.mean():.2f} m/s, std={corrected_lmi.std():.2f} m/s")
    
    return corrected_lmi, mapping_info


if __name__ == '__main__':
    main()


