# ROI Intensity Report Script

## Purpose

This script measures fluorescence intensity directly from every ROI's pixel coordinates across one or more channels.

For each ROI, it calculates:

```text
Mean intensity
Median intensity
Maximum intensity
Integrated intensity
Intensity SD
```

It then independently ranks ROIs for each intensity metric, divides the ranked objects into 5%-wide rank-based percentile bins, samples up to five ROIs from each bin, and generates PDF and CSV reports.

The ROI pixel CSV itself is used as the segmentation. No CellProfiler label-overlay TIFF is required.

## Current output directory

```text
/home/oltij/Desktop/ROI_intensity_report
```

Created automatically.

## Current configured inputs

```text
PV:
  ROI CSV: /home/oltij/Desktop/PVAligned/ROI_analysis/PV_ROI_pixels.csv
  TIFF:    /home/oltij/Desktop/PVAligned/aligned_PV_max.tif

Hoescht:
  ROI CSV: /home/oltij/Desktop/HoeschtAligned/ROI_analysis/Hoescht_ROI_pixels.csv
  TIFF:    /home/oltij/Desktop/HoeschtAligned/aligned_Hoechst_max.tif

LHX6:
  ROI CSV: /home/oltij/Desktop/LHX6Aligned/ROI_analysis/LHX6_ROI_pixels.csv
  TIFF:    /home/oltij/Desktop/LHX6Aligned/aligned_LHX6_max.tif
```

Unlike the shape-report scripts uploaded alongside this one, the current intensity-report configuration reads the **unfiltered** ROI pixel CSVs from each channel's `ROI_analysis` directory.

## Input format

Each channel entry contains:

```python
{
    "name": "PV",
    "roi_csv": "/path/PV_ROI_pixels.csv",
    "original": "/path/aligned_PV_max.tif",
}
```

### ROI pixel CSV

Must contain:

```text
ROI or CellID
X
Y
```

Example:

```csv
ROI,X,Y
1,1820,1941
1,1821,1941
1,1822,1941
2,2170,1675
```

One row represents one pixel belonging to one ROI.

The identifier and coordinates are converted to integers and duplicate `(ObjectID, X, Y)` rows are removed.

### Fluorescence TIFF

Expected:

```text
TIFF
2-D after numpy.squeeze()
```

The ROI coordinates are used to retrieve intensities exactly as:

```python
values = image[Y, X]
```

Every coordinate must lie within the TIFF bounds.

## Dependencies

```text
numpy
pandas
tifffile
matplotlib
```

Example:

```bash
pip install numpy pandas tifffile matplotlib
```

Matplotlib uses the headless `Agg` backend.

## Exact intensity measurements

For the pixel intensity array belonging to one ROI:

### Mean intensity

```text
numpy.mean(values)
```

### Median intensity

```text
numpy.median(values)
```

### Maximum intensity

```text
numpy.max(values)
```

### Integrated intensity

```text
numpy.sum(values)
```

This is the sum of the raw TIFF pixel values inside the ROI.

### Intensity SD

```text
numpy.std(values)
```

NumPy's default population standard deviation is used (`ddof=0`).

## Other exported ROI fields

Each ROI also records:

```text
Channel
ObjectID
ROI pixel count
Center_X
Center_Y
BoundingBoxMinimum_X
BoundingBoxMaximum_X
BoundingBoxMinimum_Y
BoundingBoxMaximum_Y
```

The centroid is the arithmetic mean of ROI pixel coordinates.

## Intensity metrics processed

```python
INTENSITY_METRICS = {
    "Mean intensity": np.mean,
    "Median intensity": np.median,
    "Maximum intensity": np.max,
    "Integrated intensity": np.sum,
    "Intensity SD": np.std,
}
```

Each metric gets its own percentile analysis, PDF, all-ROI CSV, and selected-ROI CSV.

## Percentile-bin sampling

Defaults:

```text
PERCENTILE_BIN_WIDTH = 5
MAX_SAMPLE_PER_BIN = 5
RANDOM_SEED = 42
```

Therefore:

```text
20 rank-based percentile bins
maximum 5 sampled ROIs per bin
maximum ~100 sampled ROIs per channel per metric
```

Objects are sorted by the intensity metric and `ObjectID`, then divided using `numpy.array_split()`.

Thus these are **rank-based percentile groups**, not numeric percentile-cutoff intervals.

## Visualization settings

```text
N_BINS = 50
CROP_PADDING = 15
DISPLAY_LOW_PERCENTILE = 1
DISPLAY_HIGH_PERCENTILE = 99

ALL_ROI_COLOR = "yellow"
SELECTED_ROI_COLOR = "blue"
ROI_LINEWIDTH = 0.7
SELECTED_ROI_LINEWIDTH = 2.0
```

The 1st–99th percentile range controls grayscale display contrast in figures; it does not alter raw intensity measurements.

## Main outputs

Top-level files:

```text
/home/oltij/Desktop/ROI_intensity_report/
├── All_Channel_ROI_Intensity_Report.pdf
├── All_Channel_ROI_Intensity_Selected.csv
├── All_Channel_ROI_Intensity_AllObjects.csv
└── <Channel>/
```

For each channel:

```text
<Channel>/
├── <Channel>_all_ROI_measurements.csv
├── Mean_intensity/
├── Median_intensity/
├── Maximum_intensity/
├── Integrated_intensity/
└── Intensity_SD/
```

Each metric folder contains:

```text
<Channel>_<Metric>_report.pdf
<Channel>_<Metric>_selected_ROIs.csv
<Channel>_<Metric>_all_ROIs.csv
```

Spaces in metric names are replaced with underscores in folder and file names.

### Example PV tree

```text
PV/
├── PV_all_ROI_measurements.csv
├── Mean_intensity/
│   ├── PV_Mean_intensity_report.pdf
│   ├── PV_Mean_intensity_selected_ROIs.csv
│   └── PV_Mean_intensity_all_ROIs.csv
├── Median_intensity/
│   └── ...
├── Maximum_intensity/
│   └── ...
├── Integrated_intensity/
│   └── ...
└── Intensity_SD/
    └── ...
```

## Output — `All_Channel_ROI_Intensity_Report.pdf`

Combined multipage PDF containing report pages for all configured channels and all five intensity metrics.

Dedicated per-channel/per-metric PDFs are also saved in the metric folders.

## Output — `All_Channel_ROI_Intensity_AllObjects.csv`

One combined table containing all measured ROIs from all configured channels.

Typical fields:

```text
Channel
ObjectID
Mean intensity
Median intensity
Maximum intensity
Integrated intensity
Intensity SD
ROI pixel count
Center_X
Center_Y
BoundingBoxMinimum_X
BoundingBoxMaximum_X
BoundingBoxMinimum_Y
BoundingBoxMaximum_Y
```

## Output — `All_Channel_ROI_Intensity_Selected.csv`

Contains the percentile-sampled ROIs across all channels and metrics.

Selection fields include:

```text
Channel
Metric
IntensityGroup
PercentileBinIndex
PercentileRange
DisplayNumber
ObjectID
```

followed by all five intensity metrics and ROI geometry fields.

## Output — `<Channel>_all_ROI_measurements.csv`

Example:

```text
PV/PV_all_ROI_measurements.csv
```

Contains the full raw intensity measurement table for all PV ROIs.

## Output — metric-specific all-ROI CSV

Example:

```text
PV/Mean_intensity/PV_Mean_intensity_all_ROIs.csv
```

Core fields:

```text
Channel
ObjectID
Mean intensity
PercentileBinIndex
PercentileRange
ROI pixel count
Center_X
Center_Y
BoundingBoxMinimum_X
BoundingBoxMaximum_X
BoundingBoxMinimum_Y
BoundingBoxMaximum_Y
```

The analogous metric field is used for the other metric folders.

## Output — metric-specific selected-ROI CSV

Example:

```text
PV/Mean_intensity/PV_Mean_intensity_selected_ROIs.csv
```

Contains selected examples plus:

```text
Channel
Metric
IntensityGroup
PercentileBinIndex
PercentileRange
DisplayNumber
ObjectID
Mean intensity
Median intensity
Maximum intensity
Integrated intensity
Intensity SD
ROI pixel count
Center_X
Center_Y
BoundingBoxMinimum_X
BoundingBoxMaximum_X
BoundingBoxMinimum_Y
BoundingBoxMaximum_Y
```

## Important assumptions

1. ROI coordinates and fluorescence TIFF must share exactly the same coordinate frame.
2. Raw TIFF intensity values are used for measurements; display normalization does not modify them.
3. No background subtraction is performed by this script.
4. No flat-field correction is performed by this script.
5. Integrated intensity depends on both ROI area and pixel intensity.
6. Duplicate ROI-pixel rows are removed before measurement.
7. Percentile bins are rank-based.
8. This script currently uses unfiltered ROI CSVs; if you substitute filtered CSVs, only retained objects will be measured.

## Example execution

All inputs are hard-coded/configured at the top, so run:

```bash
python your_roi_intensity_report_script.py
```

No command-line arguments are parsed.

## Data flow

```text
ROI pixel CSV
    +
aligned fluorescence TIFF
        |
        v
exact TIFF intensities at ROI X/Y pixels
        |
        v
five ROI intensity metrics
        |
        +--> all-object tables
        +--> percentile ranking
        +--> selected example tables
        +--> channel/metric PDFs
        +--> combined multipage PDF
```
