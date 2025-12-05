#!/usr/bin/env python3
"""
Clean TC Training Data

Apply consistent cleaning rules:
1. Drop observations where translation_speed is NaN (no previous point)
2. Drop observations where SST is NaN (data gaps - PI will also be NaN)

This ensures consistent, complete datasets for all analyses.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional
import argparse
import sys


def clean_tc_dataset(
    input_file: Path,
    output_file: Optional[Path] = None,
    create_backup: bool = True,
    replace_original: bool = True
) -> pd.DataFrame:
    """
    Clean TC training dataset according to rules.
    
    Parameters
    ----------
    input_file : Path
        Path to input CSV file
    output_file : Path, optional
        Path to save cleaned file (if None, uses input_file with '_cleaned' suffix)
    create_backup : bool
        Create backup of original file
    replace_original : bool
        Replace original file with cleaned version
        
    Returns
    -------
    pd.DataFrame
        Cleaned dataset
    """
    input_file = Path(input_file)
    
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    # Determine output file path
    if output_file is None:
        output_file = input_file.parent / f"{input_file.stem}_cleaned.csv"
    else:
        output_file = Path(output_file)
    
    backup_file = input_file.parent / f"{input_file.stem}_original.csv"
    
    print(f"Loading: {input_file}")
    df = pd.read_csv(input_file)
    original_count = len(df)
    print(f"  Original observations: {original_count:,}")
    
    # Create backup
    if create_backup and not backup_file.exists():
        print(f"\nCreating backup: {backup_file}")
        df.to_csv(backup_file, index=False)
        print("  ✅ Backup created")
    elif backup_file.exists():
        print(f"\nBackup already exists: {backup_file}")
    
    # Apply cleaning rules
    print("\n" + "=" * 70)
    print("APPLYING CLEANING RULES")
    print("=" * 70)
    
    # Rule 1: Drop where translation_speed is NaN
    before_rule1 = len(df)
    missing_trans = df['translation_speed'].isna()
    df = df[~missing_trans].copy()
    after_rule1 = len(df)
    dropped_trans = before_rule1 - after_rule1
    
    print(f"\nRule 1: Drop observations with missing translation_speed")
    print(f"  Before: {before_rule1:,} observations")
    print(f"  Dropped: {dropped_trans:,} observations ({dropped_trans/before_rule1*100:.1f}%)")
    print(f"  After: {after_rule1:,} observations")
    
    # Rule 2: Drop where SST is NaN
    before_rule2 = len(df)
    missing_sst = df['sst'].isna()
    df = df[~missing_sst].copy()
    after_rule2 = len(df)
    dropped_sst = before_rule2 - after_rule2
    
    print(f"\nRule 2: Drop observations with missing SST")
    print(f"  Before: {before_rule2:,} observations")
    print(f"  Dropped: {dropped_sst:,} observations ({dropped_sst/before_rule2*100:.1f}%)")
    print(f"  After: {after_rule2:,} observations")
    
    # Verify PI is also clean (should be, since PI depends on SST)
    missing_pi = df['pi'].isna().sum()
    if missing_pi > 0:
        print(f"\n⚠️  WARNING: {missing_pi} observations still have missing PI!")
        print("   Dropping these for consistency...")
        df = df[~df['pi'].isna()].copy()
        print(f"   ✅ Dropped {missing_pi} additional observations")
    else:
        print(f"\n✅ Verification: No missing PI (as expected)")
    
    # Final statistics
    print("\n" + "=" * 70)
    print("FINAL STATISTICS")
    print("=" * 70)
    print(f"  Original observations: {original_count:,}")
    print(f"  Final observations: {len(df):,}")
    total_dropped = original_count - len(df)
    print(f"  Total dropped: {total_dropped:,} ({total_dropped/original_count*100:.1f}%)")
    print(f"  Data retention: {len(df)/original_count*100:.1f}%")
    
    # Check for any remaining missing values
    print(f"\nRemaining missing values:")
    remaining_missing = df.isnull().sum()
    remaining_missing = remaining_missing[remaining_missing > 0]
    if len(remaining_missing) == 0:
        print("  ✅ None! All variables have complete data.")
    else:
        for col, count in remaining_missing.items():
            print(f"  {col}: {count:,} ({count/len(df)*100:.1f}%)")
    
    # Save cleaned dataset
    print(f"\nSaving cleaned dataset: {output_file}")
    df.to_csv(output_file, index=False)
    print("  ✅ Cleaned dataset saved")
    
    # Replace original if requested
    if replace_original:
        print(f"\nReplacing original file: {input_file}")
        df.to_csv(input_file, index=False)
        print("  ✅ Original file replaced with cleaned version")
    
    print("\n" + "=" * 70)
    print("CLEANING COMPLETE!")
    print("=" * 70)
    
    return df


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Clean TC training dataset',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Cleaning Rules:
  1. Drop observations where translation_speed is NaN (no previous point)
  2. Drop observations where SST is NaN (data gaps)

Examples:
  # Clean EP basin data
  python clean_tc_data.py outputs/tc_intensity/training_data/tc_training_data_EP.csv
  
  # Clean and save to new file (keep original)
  python clean_tc_data.py input.csv --output cleaned.csv --no-replace
        """
    )
    
    parser.add_argument(
        'input_file',
        type=str,
        help='Path to input CSV file'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Path to output cleaned file (default: input_file with _cleaned suffix)'
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Do not create backup of original file'
    )
    parser.add_argument(
        '--no-replace',
        action='store_true',
        help='Do not replace original file (only create cleaned version)'
    )
    
    args = parser.parse_args()
    
    try:
        clean_tc_dataset(
            input_file=Path(args.input_file),
            output_file=Path(args.output) if args.output else None,
            create_backup=not args.no_backup,
            replace_original=not args.no_replace
        )
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

