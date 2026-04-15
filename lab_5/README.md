# Lab 5: Hyperspectral Data & Water Quality Analysis

Analysis of water quality using airborne hyperspectral and Sentinel-2 satellite data.

## Overview

This lab implements tools for:
1. **Hyperspectral data visualization** - Browse data cubes, display RGB and false-color composites
2. **Spectral library creation** - Collect and manage spectral signatures for different land cover types
3. **Water quality indices** - Calculate Chlorophyll-a, DOC, and turbidity
4. **Sentinel-2 integration** - Download, process, and compare satellite data
5. **SAM classification** - Spectral Angle Mapper for land cover classification
6. **Cross-sensor calibration** - Calibrate Sentinel-2 using airborne data

## Data

The hyperspectral data is located in `Obrazy lotnicze/` directory:
- **Format**: ENVI BSQ (Band Sequential)
- **Sensor**: Airborne hyperspectral scanner
- **Bands**: 456 spectral bands
- **Wavelength range**: 414-2499 nm
- **Spatial resolution**: 1 meter
- **Reflectance scale**: × 10⁻⁴
- **No-data value**: 15000

Available datasets:
- `221000_Odra_HS_Blok_A_006_VS_join_atm.bsq`
- `221000_Odra_HS_Blok_A_007_VS_join_atm.bsq`
- `221000_Odra_HS_Blok_A_008_VS_join_atm.bsq`
- `221000_Odra_HS_Blok_A_013_VS_join_atm.bsq`
- `221000_Odra_HS_Blok_A_015_VS_join_atm.bsq`

## Installation

```bash
pip install -r requirements.txt
```

Or with conda:
```bash
conda install -c conda-forge numpy matplotlib pandas scipy rasterio
pip install spectral sentinelsat
```

## Usage

### 1. Browse Hyperspectral Data

Use the interactive viewer to explore data and collect spectral signatures:

```bash
python viewer.py
```

**Features:**
- RGB preview with automatic stretch
- Click any pixel to view its spectral signature
- Export signatures to CSV for spectral library
- Memory-efficient (memory-mapped I/O)

**Workflow:**
1. Launch viewer
2. Click on pixels representing different land cover types:
   - Clear water
   - Turbid water
   - Vegetation (grass, trees)
   - Soil/bare ground
   - Urban/built-up areas
3. Export each signature: "Export spectrum to CSV..."
4. Save with descriptive names (e.g., `water_clear.csv`, `vegetation_forest.csv`)

### 2. Create Spectral Library

Manage collected signatures using the spectral library tool:

```python
from spectral_library import SpectralLibrary

# Create library
lib = SpectralLibrary()

# Load signatures from CSV files
lib.load_from_csv('water_clear.csv', 'water_clear')
lib.load_from_csv('water_turbid.csv', 'water_turbid')
lib.load_from_csv('vegetation_forest.csv', 'forest')
lib.load_from_csv('vegetation_grass.csv', 'grass')
lib.load_from_csv('soil.csv', 'soil')

# Plot signatures
lib.plot_signatures()

# Save library
lib.save_library('spectral_library.csv')

# Compare signatures
lib.compare_signatures('water_clear', 'water_turbid')
```

### 3. Water Quality Analysis

Run the main analysis notebook:

```bash
jupyter notebook water_quality_analysis.ipynb
```

The notebook includes:

#### False-Color Composites
- **NIR-Red-Green**: Vegetation and water discrimination
- **SWIR-NIR-Red**: Moisture content analysis
- **NIR-Green-Blue**: Water clarity assessment

#### Water Quality Indices

**Chlorophyll-a (algae/phytoplankton):**
- NDCI: `(R705 - R665) / (R705 + R665)`
- 2-band ratio: `R705 / R665`
- 3-band algorithm: `(1/R665 - 1/R705) × R740`

**DOC (Dissolved Organic Carbon):**
- Blue-green ratio: `R443 / R560`

**Turbidity (suspended sediments):**
- Red-green ratio: `R665 / R560`
- NIR reflectance: `R783`

### 4. Sentinel-2 Data

#### Download Sentinel-2 Data

Register at [Copernicus SciHub](https://scihub.copernicus.eu/) and use:

```python
from sentinelsat import SentinelAPI

# Connect to API
api = SentinelAPI('username', 'password', 'https://scihub.copernicus.eu/dhus')

# Define area of interest (WGS84 coordinates)
bbox = (min_lon, min_lat, max_lon, max_lat)

# Search for products
products = api.query(
    footprint,
    date=('2022-10-01', '2022-10-31'),
    platformname='Sentinel-2',
    processinglevel='Level-2A',
    cloudcoverpercentage=(0, 20)
)

# Download
api.download_all(products)
```

#### Calculate Sentinel-2 Water Indices

```python
# Load Sentinel-2 bands (B2, B3, B4, B5, B6, B8)
# Calculate same indices as airborne data
NDCI_S2 = (B5 - B4) / (B5 + B4)
DOC_S2 = B2 / B3
Turbidity_S2 = B4 / B3
```

### 5. SAM Classification

Apply Spectral Angle Mapper using the spectral library:

```python
from water_quality_analysis import spectral_angle_mapper

# Load reference spectrum
ref_spectrum = lib.get_signature('water_clear')

# Compute SAM
sam = spectral_angle_mapper(img, ref_spectrum, lib.wavelengths, wavelengths)

# Classify (smaller angle = better match)
threshold = 0.1  # radians
water_mask = sam < threshold
```

### 6. Cross-Sensor Calibration

Calibrate Sentinel-2 using airborne data as reference:

```python
# Simulate Sentinel-2 band from airborne data
from water_quality_analysis import simulate_s2_band, calibrate_s2_with_airborne

# Simulate S2 band from airborne hyperspectral
airborne_as_s2 = simulate_s2_band(airborne_data, wavelengths, S2_BANDS['B4'])

# Compute calibration coefficients
gain, offset = calibrate_s2_with_airborne(s2_band, airborne_as_s2)

# Apply calibration
s2_calibrated = gain * s2_band + offset
```

## File Structure

```
lab_5/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── viewer.py                          # Interactive hyperspectral viewer
├── spectral_library.py               # Spectral library management
├── water_quality_analysis.ipynb      # Main analysis notebook
├── TODO.pdf                          # Lab assignment
└── Obrazy lotnicze/                  # Hyperspectral data directory
    ├── *.bsq                         # Binary data files
    ├── *.hdr                         # ENVI headers
    └── *.aux.xml                     # Auxiliary metadata
```

## Methodology

### Water Quality Indices

The indices are based on established remote sensing algorithms:

1. **Chlorophyll-a**: Uses red edge bands (705 nm) sensitive to chlorophyll absorption
2. **DOC**: Blue-green ratio correlates with colored dissolved organic matter
3. **Turbidity**: Red-NIR bands respond to suspended sediments

### SAM Classification

Spectral Angle Mapper measures similarity between spectra:
- Computes angle between spectral vectors
- Invariant to illumination differences
- Smaller angle = more similar spectra
- Typical threshold: 0.05-0.15 radians

### Calibration Approach

1. **Spatial resampling**: Aggregate airborne data to Sentinel-2 resolution (10-20m)
2. **Spectral simulation**: Apply Sentinel-2 spectral response functions to airborne data
3. **Regression**: Compute gain and offset between sensors
4. **Validation**: Compare water quality indices before/after calibration

## Expected Results

- **RGB composites**: Visual interpretation of water bodies and land cover
- **False-color composites**: Enhanced discrimination of water features
- **Water quality maps**: Spatial distribution of Chl-a, DOC, turbidity
- **Spectral library**: Reference signatures for 4-6 land cover types
- **SAM classification**: Land cover map with accuracy assessment
- **Calibration coefficients**: Gain and offset for each Sentinel-2 band
- **Index comparison**: Correlation plots between airborne and satellite indices

## Tips

1. **Spectral signatures**: Collect multiple samples per class for robustness
2. **Water pixels**: Look for dark areas in NIR bands
3. **Vegetation**: High NIR, low red reflectance with red edge
4. **Cloud masking**: Essential for Sentinel-2 data quality
5. **Temporal matching**: Use Sentinel-2 data within ±7 days of airborne acquisition
6. **Validation**: Compare results with in-situ measurements if available

## References

- Gitelson, A. A., et al. (2008). "A simple semi-analytical model for remote estimation of chlorophyll-a in turbid waters"
- Kutser, T., et al. (2005). "Monitoring cyanobacterial blooms by satellite remote sensing"
- Nechad, B., et al. (2010). "Calibration and validation of a generic multisensor algorithm for mapping of total suspended matter"

## Troubleshooting

**Issue**: Viewer doesn't find data files
- **Solution**: Ensure data is in `Obrazy lotnicze/` directory with `.hdr` files

**Issue**: Memory error when loading full image
- **Solution**: The viewer uses memory-mapping. For SAM, process in tiles or use subset

**Issue**: Sentinel-2 download fails
- **Solution**: Check credentials, API status, and product availability

**Issue**: NaN values in indices
- **Solution**: Check for division by zero, apply proper masking of no-data values

## Contact

For questions about this lab, refer to the course materials or contact the instructor.
