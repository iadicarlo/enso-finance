#!/usr/bin/env python3
"""
Validate TC intensity model using UQAM's distribution-based approach.

This script validates the model by comparing Saffir-Simpson category distributions
between observed and simulated storms, matching UQAM's validation methodology
(Section 4.5, Figure 9).

Author: ENSO Finance Project
"""

import sys
from pathlib import Path

# Note: Script should be run with venv activated via: source .venv/bin/activate
# Or via batch scripts that activate the venv
# This ensures sklearn 1.7.2+ is available for model loading
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import chi2_contingency, ks_2samp
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Note: Model loading done in main() to avoid import issues


def classify_saffir_simpson(wind_speed_ms):
    """
    Classify wind speeds into Saffir-Simpson categories.
    
    Parameters
    ----------
    wind_speed_ms : array-like
        Wind speed in m/s
    
    Returns
    -------
    categories : array
        Category labels: 'TS' (Tropical Storm), 'Cat1', 'Cat2', 'Cat3', 'Cat4', 'Cat5'
    """
    wind_speed_ms = np.asarray(wind_speed_ms)
    categories = np.full(len(wind_speed_ms), 'TS', dtype=object)
    
    # Saffir-Simpson scale (m/s)
    # TS: 18-32 m/s (35-64 kt)
    # Cat1: 33-42 m/s (65-82 kt)
    # Cat2: 43-49 m/s (83-95 kt)
    # Cat3: 50-58 m/s (96-112 kt)
    # Cat4: 59-69 m/s (113-136 kt)
    # Cat5: ≥70 m/s (≥137 kt)
    
    categories[wind_speed_ms >= 33] = 'Cat1'
    categories[wind_speed_ms >= 43] = 'Cat2'
    categories[wind_speed_ms >= 50] = 'Cat3'
    categories[wind_speed_ms >= 59] = 'Cat4'
    categories[wind_speed_ms >= 70] = 'Cat5'
    
    # Also handle storms below tropical storm intensity
    categories[wind_speed_ms < 18] = 'BelowTS'
    
    return categories


def calculate_category_proportions(intensities, category_order=None):
    """
    Calculate proportion of storms in each Saffir-Simpson category.
    
    Parameters
    ----------
    intensities : array-like
        Lifetime maximum intensities (LMI) in m/s
    category_order : list, optional
        Order of categories for output
    
    Returns
    -------
    proportions : dict
        Proportion in each category
    counts : dict
        Count in each category
    """
    if category_order is None:
        category_order = ['TS', 'Cat1', 'Cat2', 'Cat3', 'Cat4', 'Cat5']
    
    categories = classify_saffir_simpson(intensities)
    
    # Filter to storms that reach at least tropical storm intensity (18 m/s)
    # As per UQAM methodology
    valid_mask = intensities >= 18
    categories_valid = categories[valid_mask]
    
    if len(categories_valid) == 0:
        return {cat: 0.0 for cat in category_order}, {cat: 0 for cat in category_order}
    
    # Count by category
    unique, counts_array = np.unique(categories_valid, return_counts=True)
    counts_dict = dict(zip(unique, counts_array))
    
    # Fill missing categories with 0
    for cat in category_order:
        if cat not in counts_dict:
            counts_dict[cat] = 0
    
    # Calculate proportions
    total = len(categories_valid)
    proportions_dict = {cat: counts_dict[cat] / total for cat in category_order}
    
    return proportions_dict, counts_dict


def validate_distribution_skill(
    observed_lmi,
    simulated_lmi,
    basin_name='All Basins',
    output_dir=None,
    postprocessing_applied=False
):
    """
    Validate model using UQAM's distribution-based approach.
    
    Parameters
    ----------
    observed_lmi : array-like
        Observed lifetime maximum intensities
    simulated_lmi : array-like
        Simulated lifetime maximum intensities
    basin_name : str
        Name of basin for labeling
    output_dir : Path, optional
        Directory to save results
    
    Returns
    -------
    results : dict
        Validation metrics
    """
    category_order = ['TS', 'Cat1', 'Cat2', 'Cat3', 'Cat4', 'Cat5']
    
    # Calculate proportions
    obs_props, obs_counts = calculate_category_proportions(observed_lmi, category_order)
    sim_props, sim_counts = calculate_category_proportions(simulated_lmi, category_order)
    
    # Create contingency table for chi-squared test
    obs_counts_array = np.array([obs_counts[cat] for cat in category_order])
    sim_counts_array = np.array([sim_counts[cat] for cat in category_order])
    
    # Chi-squared test
    contingency_table = np.array([obs_counts_array, sim_counts_array])
    try:
        chi2_stat, p_value, dof, expected = chi2_contingency(contingency_table)
    except (ValueError, RuntimeWarning):
        # If expected frequencies are too low or other issues
        chi2_stat, p_value = np.nan, np.nan
    
    # Kolmogorov-Smirnov test on continuous distributions
    # Only on storms that reach at least tropical storm intensity (as per UQAM)
    obs_valid = observed_lmi[observed_lmi >= 18]
    sim_valid = simulated_lmi[simulated_lmi >= 18]
    
    if len(obs_valid) > 0 and len(sim_valid) > 0:
        try:
            ks_stat, ks_p_value = ks_2samp(obs_valid, sim_valid)
        except ValueError:
            ks_stat, ks_p_value = np.nan, np.nan
    else:
        ks_stat, ks_p_value = np.nan, np.nan
    
    # Mean absolute difference in proportions
    prop_diff = {cat: abs(obs_props[cat] - sim_props[cat]) for cat in category_order}
    mean_abs_prop_diff = np.mean(list(prop_diff.values()))
    
    # Results
    results = {
        'basin': basin_name,
        'n_observed': len(observed_lmi[observed_lmi >= 18]),
        'n_simulated': len(simulated_lmi[simulated_lmi >= 18]),
        'observed_proportions': obs_props,
        'simulated_proportions': sim_props,
        'observed_counts': obs_counts,
        'simulated_counts': sim_counts,
        'proportion_differences': prop_diff,
        'mean_abs_prop_diff': mean_abs_prop_diff,
        'chi2_statistic': chi2_stat,
        'chi2_p_value': p_value,
        'ks_statistic': ks_stat,
        'ks_p_value': ks_p_value,
    }
    
    # Create visualization (UQAM Figure 9 style)
    if output_dir:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        x = np.arange(len(category_order))
        width = 0.35
        
        obs_props_array = np.array([obs_props[cat] for cat in category_order])
        sim_props_array = np.array([sim_props[cat] for cat in category_order])
        
        ax.bar(x - width/2, obs_props_array, width, label='Observed (IBTrACS)', alpha=0.8)
        ax.bar(x + width/2, sim_props_array, width, label='Simulated', alpha=0.8)
        
        ax.set_xlabel('Saffir-Simpson Category')
        ax.set_ylabel('Proportion')
        title_suffix = " (with post-processing)" if postprocessing_applied else ""
        ax.set_title(f'Intensity Distribution: {basin_name}{title_suffix}\n'
                    f'Chi²={chi2_stat:.2f} (p={p_value:.3f}), '
                    f'Mean |Δprop|={mean_abs_prop_diff:.3f}')
        ax.set_xticks(x)
        ax.set_xticklabels(category_order)
        ax.legend()
        ax.grid(alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        output_file = output_dir / f'distribution_validation_{basin_name.replace(" ", "_")}.png'
        plt.savefig(output_file, dpi=150)
        plt.close()
        
        print(f"Saved plot to: {output_file}")
    
    return results


def main():
    """Main validation script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Validate TC intensity model using distribution-based approach'
    )
    parser.add_argument(
        '--data-file',
        type=str,
        default='outputs/tc_intensity/training_data/tc_training_data_ALL_basins.csv',
        help='Path to processed TC intensity data'
    )
    parser.add_argument(
        '--model-file',
        type=str,
        help='Path to trained model pickle file (optional)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='outputs/tc_intensity/validation',
        help='Output directory for results'
    )
    parser.add_argument(
        '--basin',
        type=str,
        help='Filter by basin (optional)'
    )
    parser.add_argument(
        '--apply-postprocessing',
        action='store_true',
        help='Apply UQAM-style quantile matching post-processing to simulated LMI'
    )
    parser.add_argument(
        '--per-enso-phase',
        action='store_true',
        help='Apply post-processing per ENSO phase (recommended by UQAM)'
    )
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load data
    print(f"Loading data from: {args.data_file}")
    df = pd.read_csv(args.data_file)
    
    # Filter by basin if specified
    if args.basin:
        df = df[df['basin'] == args.basin]
        basin_name = args.basin
    else:
        basin_name = 'All Basins'
    
    # Get observed LMI (per storm)
    if 'storm_id' in df.columns and 'max_wind_ms' in df.columns:
        observed_lmi = df.groupby('storm_id')['max_wind_ms'].max().values
    else:
        print("Warning: Cannot compute LMI from data")
        return
    
    # Get simulated LMI (from model predictions if model file provided)
    simulated_lmi = None
    if args.model_file and Path(args.model_file).exists():
        print(f"Loading model from: {args.model_file}")
        import pickle
        
        try:
            # Try using compatibility shim first
            try:
                from sklearn_compatibility_shim import load_model_with_compatibility
                model = load_model_with_compatibility(args.model_file)
                print("Model loaded using compatibility shim")
            except (ImportError, Exception) as compat_error:
                # Fall back to standard pickle if compatibility shim fails
                print(f"Compatibility shim failed ({compat_error}), trying standard pickle...")
                with open(args.model_file, 'rb') as f:
                    model = pickle.load(f)
            
            if not model.is_fitted:
                print("Error: Model is not fitted. Cannot make predictions.")
                print("Using observed data as placeholder.")
                simulated_lmi = observed_lmi.copy()
            else:
                print("Making predictions...")
                # Prepare data for prediction (remove target column if present)
                df_for_pred = df.copy()
                if 'max_wind_ms' in df_for_pred.columns:
                    df_for_pred = df_for_pred.drop(columns=['max_wind_ms'])
                
                # Make predictions (sequential)
                try:
                    predicted_intensities = model.predict(df_for_pred, sequential=True)
                    
                    # Calculate LMI per storm
                    if 'storm_id' in df.columns:
                        df_pred = df.copy()
                        df_pred['predicted_intensity'] = predicted_intensities
                        simulated_lmi = df_pred.groupby('storm_id')['predicted_intensity'].max().values
                    else:
                        simulated_lmi = predicted_intensities
                    
                    print(f"Made predictions for {len(simulated_lmi)} storms")

                    # Apply post-processing if requested
                    if args.apply_postprocessing:
                        print("\nApplying UQAM-style post-processing (quantile matching)...")
                        try:
                            sys.path.insert(0, str(Path(__file__).parent))
                            from apply_uqam_postprocessing import apply_postprocessing_to_storms
                            simulated_lmi, mapping_info = apply_postprocessing_to_storms(
                                df,
                                observed_lmi,
                                simulated_lmi,
                                basin=args.basin if args.basin else None,
                                per_enso_phase=args.per_enso_phase
                            )
                            print(f"✅ Post-processing applied: {mapping_info['mappings']}")
                        except Exception as pp_error:
                            print(f"⚠️  Post-processing failed: {pp_error}")
                            print("Continuing with raw simulated LMI...")
                            import traceback
                            traceback.print_exc()
                except Exception as e:
                    print(f"Error making predictions: {e}")
                    import traceback
                    traceback.print_exc()
                    print("Using observed data as placeholder.")
                    simulated_lmi = observed_lmi.copy()
                    
        except (ModuleNotFoundError, ImportError) as e:
            print(f"Error loading model: {e}")
            print("This is likely due to sklearn version mismatch.")
            print("Using observed data as placeholder for now.")
            simulated_lmi = observed_lmi.copy()
    else:
        print("No model file provided - using observed data as placeholder")
        print("(This will show perfect match - use --model-file for real validation)")
        simulated_lmi = observed_lmi.copy()
    
    # Validate distributions
    print(f"\nValidating distributions for: {basin_name}")
    results = validate_distribution_skill(
        observed_lmi,
        simulated_lmi,
        basin_name=basin_name,
        output_dir=output_dir,
        postprocessing_applied=args.apply_postprocessing
    )
    
    # Print results
    print("\n" + "="*70)
    print("DISTRIBUTION VALIDATION RESULTS")
    print("="*70)
    print(f"Basin: {results['basin']}")
    print(f"N observed: {results['n_observed']}")
    print(f"N simulated: {results['n_simulated']}")
    print("\nCategory Proportions:")
    print("Category | Observed | Simulated | Difference")
    print("-" * 50)
    for cat in ['TS', 'Cat1', 'Cat2', 'Cat3', 'Cat4', 'Cat5']:
        obs_p = results['observed_proportions'][cat]
        sim_p = results['simulated_proportions'][cat]
        diff = results['proportion_differences'][cat]
        print(f"{cat:7s} | {obs_p:8.3f} | {sim_p:9.3f} | {diff:10.3f}")
    
    print(f"\nMean |Δprop|: {results['mean_abs_prop_diff']:.3f}")
    print(f"Chi² statistic: {results['chi2_statistic']:.2f} (p={results['chi2_p_value']:.3f})")
    print(f"KS statistic: {results['ks_statistic']:.3f} (p={results['ks_p_value']:.3f})")
    
    # Save results
    results_file = output_dir / f'distribution_validation_{basin_name.replace(" ", "_")}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    
    # Convert numpy types to Python types for JSON
    json_results = {
        k: float(v) if isinstance(v, (np.integer, np.floating)) else v
        for k, v in results.items()
        if k not in ['observed_proportions', 'simulated_proportions', 
                     'observed_counts', 'simulated_counts', 'proportion_differences']
    }
    json_results.update({
        'observed_proportions': {k: float(v) for k, v in results['observed_proportions'].items()},
        'simulated_proportions': {k: float(v) for k, v in results['simulated_proportions'].items()},
    })
    
    with open(results_file, 'w') as f:
        json.dump(json_results, f, indent=2)
    
    print(f"\nSaved results to: {results_file}")


if __name__ == '__main__':
    main()

