# Methods

## 1. Data Sources and Preprocessing

### 1.1 Tropical Cyclone Observations

Tropical cyclone (TC) track data were obtained from the International Best Track Archive for Climate Stewardship (IBTrACS; Knapp et al., 2010). The IBTrACS dataset provides global TC observations with 6-hourly temporal resolution, including position (latitude, longitude), maximum sustained wind speed, and minimum central pressure.

**Processing steps:**
- Filtered observations from 1980-2020 (satellite era for reliable global coverage)
- Applied minimum wind speed threshold of 17 m/s (≈34 knots, tropical storm intensity)
- Separated observations by ocean basin for basin-specific analysis
- Converted wind speeds to m/s and standardized coordinates to 0-360° longitude format

**Ocean basins included:**
- North Atlantic (NA)
- East Pacific (EP)
- West Pacific (WP)
- North Indian (NI)
- South Indian (SI)
- South Pacific (SP)
- South Atlantic (SA)

### 1.2 Atmospheric Reanalysis Data

Monthly-mean atmospheric fields were extracted from the ERA5 reanalysis (Hersbach et al., 2020) at 0.25° spatial resolution. ERA5 data were accessed through the Copernicus Climate Data Store (CDS) API.

**Variables extracted from ERA5:**

**Pressure-level data (29 levels: 1000, 975, 950, 925, 900, 875, 850, 825, 800, 775, 750, 700, 650, 600, 550, 500, 450, 400, 350, 300, 250, 225, 200, 175, 150, 125, 100, 70, 50 hPa):**
- Temperature (K) - full vertical profile
- Zonal wind component (m/s) - full vertical profile
- Meridional wind component (m/s) - full vertical profile
- Relative humidity (%) - at key levels (600 hPa)
- Specific humidity (kg/kg) - full vertical profile

**Single-level data:**
- Sea surface temperature (K) - used as fallback if ORAS5 unavailable
- Surface pressure (Pa)

**Rationale for 29 pressure levels:**
- Comprehensive vertical profiles required for accurate Potential Intensity (PI) calculation using the Bister & Emanuel (2002) method
- Enables full atmospheric thermodynamic profiling necessary for precise PI estimation
- Standard implementation uses 29 levels from surface (1000 hPa) to upper troposphere (50 hPa)

**Processing approach:**
- Downloaded monthly-mean data for the period 1980-2020
- No temporal aggregation required (data already monthly means)
- Direct pressure-level access eliminates need for model-level conversion
- Data stored as monthly grids with full spatial coverage

### 1.3 Ocean Reanalysis Data

Monthly-mean ocean temperature profiles were obtained from the Ocean Reanalysis System 5 (ORAS5; Zuo et al., 2019) at 0.25° spatial resolution with vertical resolution of 75 depth levels (0-6000 m). ORAS5 data were accessed through the Copernicus Climate Data Store (CDS) API.

**Variables extracted:**
- Ocean temperature (`votemper`, °C) at all depth levels
- Used to calculate mixed layer depth and thermal stratification
- **Sea surface temperature (SST)**: Extracted from surface level (~0.5 m depth) of ocean temperature

**Processing approach:**
- Monthly-mean data for 1980-2020
- Full 3D temperature profiles extracted at TC locations
- SST extracted from surface layer of ocean temperature (preferred over ERA5 atmospheric SST estimate for accuracy)
- Enables calculation of ocean heat content and mixed layer properties

**SST source priority:**
1. **ORAS5 SST** (preferred): Ocean reanalysis provides more accurate SST than atmospheric model estimates
2. **ERA5 SST** (fallback): Used if ORAS5 data unavailable for specific time/location

### 1.4 Temporal Interpolation Strategy

Environmental variables are stored as monthly grids. To extract values at specific TC observation times (6-hourly), we employ multilinear interpolation in time and space:

1. **Temporal interpolation**: Monthly-mean grids are interpolated to the exact TC observation time using linear interpolation between adjacent monthly means
2. **Spatial interpolation**: Values at TC location (lat, lon) are extracted using bilinear interpolation from the nearest grid points

This approach is computationally efficient while maintaining accuracy, as monthly means adequately capture environmental conditions relevant to TC intensity (monthly variability dominates over sub-monthly fluctuations for large-scale environmental fields).

## 2. Environmental Variable Extraction

### 2.1 Atmospheric Variables

For each TC observation, the following atmospheric variables were extracted:

**Temperature:**
- Temperature at 850, 600, and 200 hPa
- Used for atmospheric stability calculations and potential intensity estimation

**Wind:**
- Zonal (U) and meridional (V) wind components at 850 and 200 hPa
- Wind speeds calculated as: $\sqrt{U^2 + V^2}$
- Vertical wind shear calculated as the magnitude of the difference vector between 200 hPa and 850 hPa winds:
  $$ \text{Wind Shear} = \sqrt{(U_{200} - U_{850})^2 + (V_{200} - V_{850})^2} $$

**Moisture:**
- Relative humidity at 600 hPa
- Specific humidity at pressure levels

**Surface conditions:**
- Sea surface temperature (SST)
- Surface pressure

### 2.2 Ocean Variables

**Mixed Layer Depth (MLD):**
MLD was calculated from ocean temperature profiles using the threshold method (de Boyer Montégut et al., 2004):
- MLD defined as the depth where temperature decreases by 1°C from the sea surface temperature
- Temperature profiles extracted from ORAS5 monthly data

**Thermal Stratification:**
Vertical temperature gradient across the mixed layer and thermocline, calculated as:
$$ \text{Stratification} = \frac{\Delta T}{\Delta z} $$
where $\Delta T$ is the temperature difference across a depth interval $\Delta z$.

**Ocean Heat Content:**
Calculated as the vertically-integrated temperature anomaly relative to 26°C (typical threshold for TC development):
$$ \text{OHC} = \rho c_p \int_{0}^{h} \max(T(z) - 26°C, 0) \, dz $$
where $\rho$ is seawater density, $c_p$ is specific heat capacity, and $h$ is the integration depth (typically 100 m).

### 2.3 Derived Variables

**Potential Intensity (PI):**
Potential Intensity is calculated using the Bister & Emanuel (2002) method with true reversible adiabatic CAPE calculation, implemented via the `tcpyPI` Python library (Gilford, 2021). This method requires comprehensive atmospheric profiles (temperature, specific humidity, wind components) at 29 pressure levels (1000-50 hPa) along with sea surface temperature and surface pressure.

**PI calculation inputs:**
- Full vertical temperature profile (29 levels, 1000-50 hPa)
- Full vertical specific humidity profile (29 levels, 1000-50 hPa)
- Full vertical wind profiles (U and V components, 29 levels, 1000-50 hPa)
- Sea surface temperature (SST, K)
- Surface pressure (hPa)

**PI calculation method:**
- Uses reversible adiabatic parcel lifting (Bister & Emanuel, 2002)
- Calculates maximum possible TC intensity from thermodynamic principles
- Accounts for atmospheric stability, moisture content, and surface conditions
- Provides physical upper bound on TC intensity for given environmental conditions

**Rationale for comprehensive PI calculation:**
- Simplified PI formulas (e.g., SST-only relationships) provide rough estimates but lack accuracy
- Full thermodynamic PI calculation captures atmospheric structure effects on TC potential
- Required for accurate intensity prediction and validation against observed intensities
- Enables proper physical constraints in TC intensity emulator development

**Translation Speed:**
TC translation speed calculated from trajectory data as the distance traveled between consecutive observations divided by time interval:
$$ v_{trans} = \frac{\sqrt{(\Delta \text{lat})^2 + (\Delta \text{lon})^2}}{\Delta t} $$

**Bathymetry:**
Ocean depth at TC location, used to identify coastal/landfall conditions.

### 2.4 Variable Extraction at TC Locations

Environmental variables were extracted at each TC observation location using the following procedure:

1. **Identify temporal context**: Determine which monthly grids bracket the TC observation time
2. **Temporal interpolation**: Interpolate monthly grids to exact TC observation time
3. **Spatial extraction**: Extract values at TC location (lat, lon) using nearest-neighbor or bilinear interpolation
4. **Ocean profile extraction**: Extract full vertical temperature profile from ORAS5 at TC location
5. **Derived calculations**: Calculate wind shear, MLD, thermal stratification, and other derived variables

All extraction operations use monthly-mean grids, with temporal interpolation handling the sub-monthly TC observation times. This approach is both computationally efficient and scientifically appropriate, as large-scale environmental conditions that control TC intensity vary on monthly rather than sub-monthly timescales.

## 3. Basin-Specific Processing

### 3.1 Rationale

TC characteristics vary substantially across ocean basins due to:
- Different climatological environmental conditions
- Basin-specific TC development mechanisms
- Varying data quality and completeness across basins

We therefore process each basin separately to:
1. Allow basin-specific quality control and validation
2. Enable basin-specific model development if needed
3. Identify basin-specific environmental relationships
4. Manage computational resources efficiently

### 3.2 Processing Workflow

For each ocean basin:

1. **Filter IBTrACS data**: Extract TC observations for the specified basin and time period
2. **Group by time period**: Organize observations by year/month to efficiently load monthly reanalysis grids
3. **Extract environmental variables**: For each TC observation, extract all atmospheric and oceanic variables
4. **Calculate derived variables**: Compute wind shear, MLD, thermal stratification, PI, etc.
5. **Create training dataset**: Compile all variables into a structured dataset with TC metadata

**Output format:**
- One CSV file per basin: `tc_training_data_{BASIN}.csv`
- Combined file (optional): `tc_training_data_all_basins.csv`
- Each row represents one TC observation with all environmental variables

### 3.3 Data Quality Control

Several quality control measures are implemented:

1. **Missing data handling**: Variables with missing values are flagged but retained (allows for flexible model development)
2. **Spatial validation**: Verify lat/lon coordinates are within valid ranges for each basin
3. **Temporal validation**: Ensure TC observation time falls within available reanalysis data period
4. **File validation**: Check that monthly reanalysis files exist and are readable before extraction

## 4. Training Dataset Structure

### 4.1 Variables Included

The training dataset includes:

**TC Metadata:**
- Storm ID
- Observation time (timestamp)
- Latitude, longitude
- Maximum wind speed (m/s)
- Minimum pressure (hPa, when available)
- Basin code
- Year

**Atmospheric Variables:**
- Temperature at 850, 600, 250, 200 hPa (key levels)
- Full vertical temperature profile (29 levels, 1000-50 hPa) for PI calculation
- U and V wind components at 850, 250, 200 hPa
- Full vertical wind profiles (29 levels, 1000-50 hPa) for PI calculation
- Wind speed at 850, 250, 200 hPa
- Vertical wind shear (850-250 hPa, standard calculation)
- Relative humidity at 600 hPa
- Specific humidity at 850, 600, 200 hPa (key levels)
- Full vertical specific humidity profile (29 levels, 1000-50 hPa) for PI calculation
- Sea surface temperature (SST, K) - preferentially from ORAS5, ERA5 as fallback
- Surface pressure (hPa)

**Ocean Variables:**
- Mixed layer depth
- Thermal stratification
- Ocean temperature profile (full depth)

**Derived Variables:**
- **Potential Intensity (PI, m/s)**: Calculated using Bister & Emanuel (2002) method with full 29-level atmospheric profiles via tcpyPI library
- Translation speed (m/s)
- Bathymetry (m)

### 4.2 Dataset Statistics

**Temporal coverage:** 1980-2020 (41 years)

**Spatial coverage:** Global (all major ocean basins)

**Expected observations per basin (1980-2020):**
- North Atlantic: ~5,000 observations
- East Pacific: ~8,000 observations
- West Pacific: ~15,000 observations
- North Indian: ~2,000 observations
- South Indian: ~4,000 observations
- South Pacific: ~3,000 observations
- South Atlantic: ~100 observations

**Total:** ~37,000+ TC observations globally

### 4.3 Data Completeness

Variable coverage varies by:
- **Basin**: Some basins have more complete TC records (e.g., North Atlantic) than others
- **Time period**: Earlier periods (1980s) may have fewer observations or lower quality
- **Variable type**: Atmospheric variables from ERA5 have higher coverage than ocean variables from ORAS5 (ocean data may be missing near coastlines)

All variables are retained in the dataset regardless of completeness, allowing flexibility in model development and analysis of data availability patterns.

## 5. Computational Implementation

### 5.1 Software and Tools

**Data processing:**
- Python 3.x
- xarray for NetCDF data handling
- pandas for data manipulation
- numpy for numerical computations

**Data access:**
- Copernicus Climate Data Store (CDS) API for ERA5 and ORAS5 downloads
- Direct file access from local storage for processed data

**Reproducibility:**
- All scripts include version control information
- Processing parameters documented in script headers
- Monthly data catalog tracks available files and metadata

### 5.2 Processing Efficiency

**Optimizations implemented:**

1. **Monthly grid approach**: Using monthly-mean data instead of hourly/daily eliminates need for temporal aggregation, reducing data volume by ~2-3 orders of magnitude

2. **Batch processing by time period**: Monthly grids are loaded once per month and reused for all TC observations in that month, minimizing file I/O operations

3. **Basin-specific processing**: Processing basins separately allows parallelization and reduces memory requirements

4. **Caching**: IBTrACS data and monthly data catalogs are cached to avoid redundant downloads

**Typical processing times:**
- Single basin (e.g., North Atlantic, ~5K observations): 30-60 minutes
- All basins sequentially (~37K observations): 6-12 hours
- Times scale approximately linearly with number of observations

## 6. Methodology Validation

### 6.1 Data Consistency Checks

- **Spatial consistency**: Verify that extracted SST values are consistent with known climatological patterns
- **Temporal consistency**: Check that variables vary smoothly across time (no unrealistic jumps)
- **Physical constraints**: Validate that calculated variables (wind shear, MLD) fall within physically reasonable ranges

### 6.2 Comparison with Literature

Our methodology aligns with established practices in TC intensity prediction research:

- **Environmental variable selection**: Variables chosen based on their demonstrated importance in TC intensity prediction (e.g., Emanuel, 1988; Kaplan & DeMaria, 2003)
- **Monthly temporal resolution**: Consistent with approaches that use environmental conditions rather than high-frequency atmospheric dynamics (e.g., Carozza et al., 2024)
- **Multi-variable approach**: Comprehensive set of atmospheric and oceanic variables enables investigation of multiple physical processes

### 6.3 Sensitivity Analysis

Key methodological choices that could affect results:

1. **Temporal interpolation method**: Linear interpolation between monthly means is appropriate for large-scale environmental fields but may miss sub-monthly variations
2. **Spatial interpolation**: Nearest-neighbor vs. bilinear interpolation may yield slightly different values, but differences are typically small at 0.25° resolution
3. **MLD calculation method**: Threshold method (1°C from SST) is standard but alternative methods (density-based, gradient-based) could be explored

These choices are documented and can be modified in the processing scripts if needed for sensitivity analysis.

## 7. Data Availability and Reproducibility

### 7.1 Data Sources

All data sources are publicly available:

- **IBTrACS**: https://www.ncei.noaa.gov/products/international-best-track-archive
- **ERA5**: https://cds.climate.copernicus.eu/ (requires registration)
- **ORAS5**: https://cds.climate.copernicus.eu/ (requires registration)

### 7.2 Code Availability

Processing scripts are available in the project repository:
- `scripts/tc_intensity/extract_tc_variables_by_basin.py`: Main extraction script
- `scripts/tc_intensity/download_monthly_training_data.py`: Data download scripts
- `src/data_loaders/`: Data loading modules

### 7.3 Processing Parameters

Key parameters that can be modified:

- **Time period**: Default 1980-2020, can be adjusted via command-line arguments
- **Minimum wind speed**: Default 17 m/s (tropical storm threshold), can be modified
- **Basin selection**: Can process individual basins or all basins
- **Interpolation methods**: Can be modified in extraction functions

All parameters are documented in script headers and command-line help messages.

---

## References

de Boyer Montégut, C., Madec, G., Fischer, A. S., Lazar, A., & Iudicone, D. (2004). Mixed layer depth over the global ocean: An examination of profile data and a profile-based climatology. *Journal of Geophysical Research: Oceans*, 109(C12).

Emanuel, K. A. (1988). The maximum intensity of hurricanes. *Journal of the Atmospheric Sciences*, 45(7), 1143-1155.

Bister, M., & Emanuel, K. A. (2002). Low frequency variability of tropical cyclone potential intensity 1. Interannual to interdecadal variability. *Journal of Geophysical Research: Atmospheres*, 107(D24), ACL-26.

Gilford, D. M. (2021). pyPI (v1.3): Tropical Cyclone Potential Intensity Calculations in Python. *Geosci. Model Dev.*, 14(6), 3621-3633. https://doi.org/10.5194/gmd-14-3621-2021

Hersbach, H., Bell, B., Berrisford, P., Hirahara, S., Horányi, A., Muñoz-Sabater, J., ... & Thépaut, J. N. (2020). The ERA5 global reanalysis. *Quarterly Journal of the Royal Meteorological Society*, 146(730), 1999-2049.

Kaplan, J., & DeMaria, M. (2003). Large-scale characteristics of rapidly intensifying tropical cyclones in the North Atlantic basin. *Weather and Forecasting*, 18(6), 1093-1108.

Knapp, K. R., Kruk, M. C., Levinson, D. H., Diamond, H. J., & Neumann, C. J. (2010). The International Best Track Archive for Climate Stewardship (IBTrACS): Unifying tropical cyclone data. *Bulletin of the American Meteorological Society*, 91(3), 363-376.

Zuo, H., Balmaseda, M. A., Tietsche, S., Mogensen, K., & Mayer, M. (2019). The ECMWF operational ensemble reanalysis-analysis system for ocean and sea ice: A description of the system and assessment. *Ocean Science*, 15(3), 779-808.

---

*Last updated: December 2024*

