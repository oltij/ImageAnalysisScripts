# Final ROI Metric Filtering Script

## Purpose

This script calculates fluorescence-intensity and shape measurements for every ROI, applies configurable percentile-based filters, and exports a new ROI pixel CSV containing only objects that pass **all enabled filters**.

It is the script that produces files in the form:

```text
<Channel>_ROI_pixels_FILTERED.csv
```

which can then be used by downstream colocalization or shape-report scripts.

## Current output directory

```text
/home/oltij/Desktop/ROI_finalmetric_filtering
```

Created automatically.

Each channel gets its own subdirectory.

## Current configured input

The uploaded version currently processes one channel:

```text
Channel: PV

ROI CSV:
/home/oltij/Desktop/PVAligned/ROI_analysis/PV_ROI_pixels.csv

Fluorescence TIFF:
/home/oltij/Desktop/PVAligned/aligned_PV_max.tif
```

Additional channel dictionaries can be added to the `channels` list.

## Input 1 — ROI pixel-coordinate CSV

Required columns:

```text
ROI or CellID
X
Y
```

The source identifier convention is preserved in the final filtered ROI-pixel export.

Example:

```csv
ROI,X,Y
1,1834,1902
1,1835,1902
1,1836,1902
2,2050,1711
```

The script:

1. reads the file with pandas;
2. identifies `ROI` or `CellID`;
3. converts ID, X, and Y to integers;
4. creates an internal `ObjectID`;
5. removes duplicate `(ObjectID, X, Y)` rows.

## Input 2 — fluorescence TIFF

Expected:

```text
TIFF
2-D after numpy.squeeze()
```

The TIFF provides raw intensity values for every ROI pixel.

Coordinates are validated so that:

```text
0 <= X < width
0 <= Y < height
```

## Dependencies

```text
numpy
pandas
tifffile
scipy
```

The script uses:

```text
scipy.spatial.ConvexHull
scipy.spatial.QhullError
```

Example:

```bash
pip install numpy pandas tifffile scipy
```

## Current pixel size

```python
PIXEL_SIZE_X_UM = 0.312843137
PIXEL_SIZE_Y_UM = 0.312836345
```

These values affect all physical shape measurements.

## Measurements calculated for every ROI

### Intensity metrics

```text
Mean intensity       = mean(raw TIFF values)
Median intensity     = median(raw TIFF values)
Maximum intensity    = max(raw TIFF values)
Integrated intensity = sum(raw TIFF values)
Intensity SD         = population standard deviation of raw TIFF values
```

No background subtraction is performed in this script.

### Area

```text
Area_px = number of ROI pixels

Area_um2 =
    Area_px
    × PIXEL_SIZE_X_UM
    × PIXEL_SIZE_Y_UM
```

### Extent

```text
Extent =
    ROI pixel count
    / tight bounding-box pixel area
```

### Perimeter

A local binary ROI mask is created and exposed pixel edges are counted.

Physical perimeter accounts for anisotropic pixels:

```text
horizontal exposed edge contribution -> X pixel size
vertical exposed edge contribution   -> Y pixel size
```

Output:

```text
Perimeter_um
```

### Convex hull area

ROI pixel centers are converted to µm coordinates and passed to SciPy `ConvexHull`.

Output:

```text
ConvexHullArea_um2
```

Degenerate cases produce `NaN`.

### Solidity

```text
Solidity =
    Area_um2 / ConvexHullArea_um2
```

If no positive finite hull area is available, a non-empty ROI receives `1.0` in the current implementation.

### Circularity

```text
Circularity =
    4 × pi × Area_um2 / Perimeter_um²
```

### Eccentricity

Calculated from the covariance eigenvalues of physical-coordinate ROI pixel centers:

```text
Eccentricity =
    sqrt(1 - lambda_minor / lambda_major)
```

### Axis lengths

```text
MajorAxisLength_um = 4 × sqrt(lambda_major)
MinorAxisLength_um = 4 × sqrt(lambda_minor)
AspectRatio = MajorAxisLength_um / MinorAxisLength_um
```

### Equivalent diameter

```text
EquivalentDiameter_um =
    sqrt(4 × Area_um2 / pi)
```

### Full measurement set

```text
Mean intensity
Median intensity
Maximum intensity
Integrated intensity
Intensity SD
Area_px
Area_um2
Perimeter_um
Solidity
Eccentricity
Circularity
ConvexHullArea_um2
MajorAxisLength_um
MinorAxisLength_um
AspectRatio
EquivalentDiameter_um
Extent
ROI pixel count
```

The script additionally stores:

```text
Channel
ObjectID
Center_X
Center_Y
BoundingBoxMinimum_X
BoundingBoxMaximum_X
BoundingBoxMinimum_Y
BoundingBoxMaximum_Y
```

## Filter configuration

Filters are controlled by:

```python
FILTERS = {
    "Mean intensity":        {"percentile": 0, "keep": "above"},
    "Median intensity":      {"percentile": 0, "keep": "above"},
    "Maximum intensity":     {"percentile": 0, "keep": "above"},
    "Integrated intensity":  {"percentile": 0, "keep": "above"},
    "Intensity SD":          {"percentile": 0, "keep": "above"},

    "Area_um2":              {"percentile": 0, "keep": "above"},
    "Perimeter_um":          {"percentile": 0, "keep": "above"},
    "Solidity":              {"percentile": 0, "keep": "above"},
    "Eccentricity":          {"percentile": 0, "keep": "below"},
    "Circularity":           {"percentile": 0, "keep": "above"},
    "ConvexHullArea_um2":    {"percentile": 0, "keep": "above"},
    "MajorAxisLength_um":    {"percentile": 0, "keep": "above"},
    "MinorAxisLength_um":    {"percentile": 0, "keep": "above"},
    "AspectRatio":           {"percentile": 0, "keep": "below"},
    "EquivalentDiameter_um": {"percentile": 0, "keep": "above"},
    "Extent":                {"percentile": 0, "keep": "above"},
}
```

## Meaning of `percentile = 0`

In this script:

```text
percentile = 0
```

means:

```text
FILTER OFF
```

It does **not** mean the numerical 0th percentile.

With the uploaded configuration, every filter is currently off and therefore every valid ROI is retained.

## Enabling a lower-bound filter

Example:

```python
"Mean intensity": {"percentile": 10, "keep": "above"}
```

The script calculates:

```text
10th percentile of Mean intensity across all valid ROIs
```

and retains objects with:

```text
Mean intensity >= cutoff
```

## Enabling an upper-bound filter

Example:

```python
"Eccentricity": {"percentile": 95, "keep": "below"}
```

The 95th-percentile eccentricity cutoff is calculated and retained ROIs must satisfy:

```text
Eccentricity <= cutoff
```

## Cutoff population

Every enabled cutoff is calculated from:

```text
ALL valid ROIs in that channel BEFORE filtering
```

Filters are not applied sequentially to progressively reduced distributions.

This makes each cutoff independent of filter order.

## AND logic

All enabled filters are combined with:

```text
AND
```

An ROI is retained only when it passes every enabled criterion.

Internally, the audit table contains:

```text
PASS_<metric name>
```

for each metric and:

```text
PASS_ALL_FILTERS
```

for the final decision.

## NaN behavior

For an enabled metric:

1. values are converted to numeric;
2. only finite values are used to calculate the percentile cutoff;
3. a non-finite ROI measurement does not pass that enabled filter.

If there are no finite values for an enabled metric, the script raises an error.

## Output structure

For the current PV configuration:

```text
/home/oltij/Desktop/ROI_finalmetric_filtering/
└── PV/
    ├── PV_ROI_pixels_FILTERED.csv
    ├── PV_all_ROI_metrics_and_filter_status.csv
    ├── PV_kept_ROI_metrics.csv
    ├── PV_filter_cutoffs.csv
    ├── PV_removed_ObjectIDs.csv
    └── PV_kept_ObjectIDs.csv
```

The same six outputs are generated independently for every channel added to `channels`.

## Output 1 — filtered ROI pixel CSV

```text
<Channel>_ROI_pixels_FILTERED.csv
```

Current example:

```text
PV/PV_ROI_pixels_FILTERED.csv
```

This is the principal downstream output.

### Exact structure

The file contains only:

```text
<original identifier column>
X
Y
```

If the input used `ROI`, output uses:

```csv
ROI,X,Y
```

If the input used `CellID`, output uses:

```csv
CellID,X,Y
```

Only pixels belonging to retained objects are written.

Example:

```csv
ROI,X,Y
4,1834,1902
4,1835,1902
4,1836,1902
7,2050,1711
```

## Output 2 — full audit table

```text
<Channel>_all_ROI_metrics_and_filter_status.csv
```

Contains one row per original ROI with:

- all intensity metrics;
- all shape metrics;
- centroid/bounding-box fields;
- one `PASS_<Metric>` column per configured filter;
- final `PASS_ALL_FILTERS`.

This is the best file for auditing why a specific object was kept or removed.

## Output 3 — kept ROI metrics

```text
<Channel>_kept_ROI_metrics.csv
```

Contains the measurement rows for only the ROIs satisfying `PASS_ALL_FILTERS`.

## Output 4 — filter cutoffs

```text
<Channel>_filter_cutoffs.csv
```

Columns:

```text
Metric
Percentile
Keep
CutoffValue
Enabled
```

Example conceptual rows:

```csv
Metric,Percentile,Keep,CutoffValue,Enabled
Mean intensity,10,above,1234.5,True
Eccentricity,95,below,0.91,True
Circularity,0,above,,False
```

This file is essential for recording the exact numeric cutoff used in a run.

## Output 5 — removed IDs

```text
<Channel>_removed_ObjectIDs.csv
```

Exact column:

```text
ObjectID
```

Contains sorted IDs of removed objects.

## Output 6 — kept IDs

```text
<Channel>_kept_ObjectIDs.csv
```

Exact column:

```text
ObjectID
```

Contains sorted IDs of retained objects.

## Current behavior with the uploaded settings

Every filter has:

```text
percentile = 0
```

Therefore:

```text
No filters are enabled.
All valid ROIs are retained.
```

The script will still calculate all metrics and write all six output files, making it possible to inspect metric distributions before choosing thresholds.

## Typical role in the analysis workflow

A common data flow is:

```text
ROI_analysis/<Channel>_ROI_pixels.csv
    +
aligned fluorescence TIFF
        |
        v
final metric filtering script
        |
        +--> all ROI metrics + pass/fail audit
        +--> percentile cutoff record
        +--> kept/removed ObjectID lists
        +--> <Channel>_ROI_pixels_FILTERED.csv
                            |
                            v
            downstream colocalization / QC
```

## Example execution

The script does not parse command-line arguments.

After editing `channels`, `PIXEL_SIZE_*`, and `FILTERS`, run:

```bash
python your_final_metric_filtering_script.py
```

## Important assumptions

1. ROI pixel CSV and fluorescence TIFF must use the same coordinate system.
2. ROI coordinates must be valid integer TIFF indices.
3. Percentiles are channel-specific.
4. Percentile cutoffs are computed from the complete pre-filter measurement distribution.
5. Multiple enabled filters use AND logic.
6. `percentile = 0` disables a metric.
7. The input identifier convention (`ROI` versus `CellID`) is preserved in the filtered pixel CSV.
8. Raw TIFF values are used for all intensity measurements; there is no background subtraction in this script.
9. Physical shape metrics depend directly on the configured pixel sizes.
