# ROI Solidity Report Script

## Purpose

This script produces a multi-channel ROI shape report ranked specifically by **Solidity**.

It reads ROI pixel-coordinate CSVs and their corresponding 2-D fluorescence TIFFs, reconstructs ROI geometry directly from the pixel coordinates, calculates a full set of shape measurements, ranks ROIs by `Solidity`, divides them into 5%-wide rank-based percentile groups, randomly samples example ROIs from each group, and produces detailed PDF and CSV outputs.

This script does **not** require a CellProfiler label-image TIFF. The ROI pixel CSV is the segmentation source.

## Current configured output directory

```text
/home/oltij/Desktop/ROI_solidity_report
```

The directory is created automatically.


Current configured channels:

```text
PV:
  ROI CSV: /home/oltij/Desktop/ROI_intensitymetric_filtering/PV/PV_ROI_pixels_FILTERED.csv
  TIFF:    /home/oltij/Desktop/PVAligned/aligned_PV_max.tif

Hoescht:
  ROI CSV: /home/oltij/Desktop/ROI_intensitymetric_filtering/Hoescht/Hoescht_ROI_pixels_FILTERED.csv
  TIFF:    /home/oltij/Desktop/HoeschtAligned/aligned_Hoechst_max.tif

LHX6:
  ROI CSV: /home/oltij/Desktop/ROI_intensitymetric_filtering/LHX6/LHX6_ROI_pixels_FILTERED.csv
  TIFF:    /home/oltij/Desktop/LHX6Aligned/aligned_LHX6_max.tif
```



## Inputs

The script is configured by editing the `channels` list near the top of the file.

Each channel is a dictionary with three entries:

```python
{
    "name": "PV",
    "roi_csv": "/path/to/PV_ROI_pixels_FILTERED.csv",
    "original": "/path/to/aligned_PV_max.tif",
}
```

You can add as many channels as needed.

### Input 1 — ROI pixel-coordinate CSV

Each channel requires a CSV containing **one row per ROI pixel**.

Accepted identifier column:

```text
ROI
```

or:

```text
CellID
```

If both are present, `ROI` is used first.

Required coordinate columns:

```text
X
Y
```

Minimal example:

```csv
ROI,X,Y
1,1834,1902
1,1835,1902
1,1836,1902
2,2050,1711
2,2051,1711
```

The script converts the identifier, `X`, and `Y` to integers, creates an internal `ObjectID`, and removes duplicate `(ObjectID, X, Y)` rows.

The pixel coordinates themselves are treated as the segmentation. **No CellProfiler segmentation-overlay TIFF is required.**

### Input 2 — fluorescence TIFF

Each channel also requires the corresponding fluorescence image.

Expected type:

```text
TIFF (.tif or .tiff)
```

The TIFF is loaded with `tifffile.imread()` and then `numpy.squeeze()` is applied.

After squeezing, it must be exactly:

```text
2-D: (Y, X)
```

Example:

```text
shape = (3840, 3840)
dtype = uint16
```

All ROI coordinates must satisfy:

```text
0 <= X < image width
0 <= Y < image height
```

The script stops with an error if any ROI pixel lies outside the TIFF.

### Coordinate convention

CSV coordinates:

```text
X = horizontal pixel coordinate
Y = vertical pixel coordinate
```

NumPy image indexing:

```python
image[Y, X]
```

### Current physical pixel size

```python
PIXEL_SIZE_X_UM = 0.312843137
PIXEL_SIZE_Y_UM = 0.312836345
```

These values are used for physical shape measurements and should be changed if a different image scale is analyzed.


## Dependencies

The script imports:

```text
numpy
pandas
tifffile
matplotlib
scipy
```

Specifically, SciPy is used for:

```text
scipy.spatial.ConvexHull
scipy.spatial.QhullError
```

Example installation:

```bash
pip install numpy pandas tifffile matplotlib scipy
```

Matplotlib is forced to the non-interactive:

```text
Agg
```

backend, making the script suitable for headless execution.


## Shape measurements calculated for every ROI

Even though this script ranks ROIs by one focal metric, it calculates a full set of shape measurements for every ROI.

### Area

```text
Area_px = number of ROI pixels

Area_um2 =
    Area_px
    × PIXEL_SIZE_X_UM
    × PIXEL_SIZE_Y_UM
```

### Extent

A tight integer-pixel bounding box is calculated as:

```text
width  = max(X) - min(X) + 1
height = max(Y) - min(Y) + 1
```

Then:

```text
Extent = Area_px / (width × height)
```

### Perimeter

A local binary mask is constructed for each ROI.

The script counts exposed pixel edges and converts them to physical units while respecting the slightly different X and Y pixel sizes:

```text
top + bottom exposed edges -> multiplied by X pixel size
left + right exposed edges -> multiplied by Y pixel size
```

The resulting field is:

```text
Perimeter_um
```

### Convex hull area

ROI pixel centers are converted to physical coordinates:

```text
X_um = X × PIXEL_SIZE_X_UM
Y_um = Y × PIXEL_SIZE_Y_UM
```

A 2-D SciPy `ConvexHull` is fit when at least three points are available.

Output:

```text
ConvexHullArea_um2
```

Degenerate hulls are stored as `NaN`.

### Solidity

```text
Solidity = Area_um2 / ConvexHullArea_um2
```

If no finite positive convex-hull area can be calculated, the implementation uses `1.0` for a non-empty ROI.

### Eccentricity and axis lengths

The script computes the covariance matrix of the ROI's physical-coordinate pixel centers.

If:

```text
lambda_minor <= lambda_major
```

are the covariance eigenvalues:

```text
Eccentricity =
    sqrt(1 - lambda_minor / lambda_major)

MajorAxisLength_um =
    4 × sqrt(lambda_major)

MinorAxisLength_um =
    4 × sqrt(lambda_minor)

AspectRatio =
    MajorAxisLength_um / MinorAxisLength_um
```

Degenerate cases can produce `NaN`.

### Circularity

```text
Circularity =
    4 × pi × Area_um2 / Perimeter_um²
```

If perimeter is zero, circularity is `NaN`.

### Equivalent diameter

```text
EquivalentDiameter_um =
    sqrt(4 × Area_um2 / pi)
```

### Additional geometric fields

The output also records:

```text
ROI pixel count
Center_X
Center_Y
BoundingBoxMinimum_X
BoundingBoxMaximum_X
BoundingBoxMinimum_Y
BoundingBoxMaximum_Y
```


## Focal ranking metric — Solidity

The focal ranking metric is:

```text
Solidity =
    Area_um2 / ConvexHullArea_um2
```

The convex hull is calculated from physical-coordinate ROI pixel centers with SciPy `ConvexHull`.

Higher solidity means the ROI more completely fills its convex hull; concave or fragmented shapes generally produce lower values.


The script's metric configuration is:

```python
SHAPE_METRICS = {
    "Solidity": None,
}

METRIC_DISPLAY_NAME = "Solidity"
```

Only this focal metric is ranked in this script, although all shape measurements above are still calculated and exported.

## Analysis and visualization settings

Defaults:

```text
PERCENTILE_BIN_WIDTH = 5
MAX_SAMPLE_PER_BIN = 5
RANDOM_SEED = 42
N_BINS = 50
CROP_PADDING = 15
DISPLAY_LOW_PERCENTILE = 1
DISPLAY_HIGH_PERCENTILE = 99

ALL_ROI_COLOR = "yellow"
SELECTED_ROI_COLOR = "blue"
ROI_LINEWIDTH = 0.7
SELECTED_ROI_LINEWIDTH = 2.0
```

`PERCENTILE_BIN_WIDTH` must divide evenly into 100 or the script raises a `ValueError`.


## Percentile-bin sampling

The focal metric values are sorted from low to high, with `ObjectID` used as a deterministic secondary sort key.

With the default:

```python
PERCENTILE_BIN_WIDTH = 5
```

the data are split into:

```text
20 rank-based percentile bins
```

using `numpy.array_split()`.

This is rank-based binning, not a calculation based on numeric percentile cut points. Every valid ROI belongs to exactly one bin.

The default maximum sampled per bin is:

```python
MAX_SAMPLE_PER_BIN = 5
```

so the usual maximum selected per channel is:

```text
20 bins × 5 ROIs = 100 ROIs
```

If a bin contains fewer than five ROIs, all available ROIs in that bin are selected.

Sampling is reproducible because the script uses:

```python
RANDOM_SEED = 42
```

Selected rows receive:

```text
PercentileBinIndex
PercentileRange
ShapeGroup
DisplayNumber
Channel
Metric
```


## Fluorescence TIFF usage

The fluorescence image is used as the grayscale background for ROI visualizations.

Display contrast is based on:

```text
1st percentile -> black end
99th percentile -> white end
```

by default.

The **shape measurements themselves come from the ROI pixel coordinates**, not fluorescence intensity.

## Output structure

The script creates:

```text
/home/oltij/Desktop/ROI_solidity_report/
├── All_Channel_ROI_Shape_Report.pdf
├── All_Channel_ROI_Shape_Selected.csv
├── All_Channel_ROI_Shape_AllObjects.csv
├── PV/
│   ├── PV_all_ROI_measurements.csv
│   └── Solidity/
│       ├── PV_Solidity_report.pdf
│       ├── PV_Solidity_selected_ROIs.csv
│       └── PV_Solidity_all_ROIs.csv
├── Hoescht/
│   ├── Hoescht_all_ROI_measurements.csv
│   └── Solidity/
│       ├── Hoescht_Solidity_report.pdf
│       ├── Hoescht_Solidity_selected_ROIs.csv
│       └── Hoescht_Solidity_all_ROIs.csv
└── LHX6/
    ├── LHX6_all_ROI_measurements.csv
    └── Solidity/
        ├── LHX6_Solidity_report.pdf
        ├── LHX6_Solidity_selected_ROIs.csv
        └── LHX6_Solidity_all_ROIs.csv
```

Because `Solidity` contains no spaces, the metric folder and filename component are exactly `Solidity`.

## Output 1 — combined multipage PDF

```text
All_Channel_ROI_Shape_Report.pdf
```

This PDF combines the report pages for all configured channels for the focal metric.

For each channel/metric, the script also writes a dedicated metric PDF:

```text
<Channel>/Solidity/<Channel>_Solidity_report.pdf
```

For example:

```text
PV/Solidity/PV_Solidity_report.pdf
```

The report includes distribution/percentile information and ROI visualizations, including whole-image context and selected ROI crops.

## Output 2 — combined selected-ROI CSV

```text
All_Channel_ROI_Shape_Selected.csv
```

This combines selected percentile-sampled ROIs across all configured channels.

Columns are drawn from:

```text
Channel
Metric
ShapeGroup
PercentileBinIndex
PercentileRange
DisplayNumber
ObjectID
Area
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
Center_X
Center_Y
BoundingBoxMinimum_X
BoundingBoxMaximum_X
BoundingBoxMinimum_Y
BoundingBoxMaximum_Y
```

Columns not present in the DataFrame are omitted automatically.

## Output 3 — combined all-object measurements

```text
All_Channel_ROI_Shape_AllObjects.csv
```

Contains the calculated ROI measurements for all objects from all configured channels.

This is useful for downstream statistical analysis because it is not restricted to the sampled visualization subset.

## Output 4 — per-channel all measurements

Example:

```text
PV/PV_all_ROI_measurements.csv
```

One row per ROI in that channel, containing the full measurement record.

## Output 5 — metric-specific all-ROI CSV

Example:

```text
PV/Solidity/PV_Solidity_all_ROIs.csv
```

Important columns include:

```text
Channel
ObjectID
Solidity
PercentileBinIndex
PercentileRange
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
Center_X
Center_Y
BoundingBoxMinimum_X
BoundingBoxMaximum_X
BoundingBoxMinimum_Y
BoundingBoxMaximum_Y
```

This table contains **all valid ROIs**, not only the sampled examples.

## Output 6 — metric-specific selected-ROI CSV

Example:

```text
PV/Solidity/PV_Solidity_selected_ROIs.csv
```

Contains the ROIs sampled from each rank-based percentile bin.

It includes the full shape measurements plus selection metadata such as:

```text
Metric
ShapeGroup
PercentileBinIndex
PercentileRange
DisplayNumber
```

## Important assumptions

1. The ROI CSV and fluorescence TIFF for each channel must refer to the same image coordinate frame.
2. ROI pixel coordinates must be integer pixel indices inside the TIFF.
3. The script treats each unique ROI/CellID as one object.
4. Duplicate `(ObjectID, X, Y)` rows are removed.
5. Shape calculations use ROI **pixel centers** and a pixel-edge perimeter model.
6. Physical measurements depend directly on `PIXEL_SIZE_X_UM` and `PIXEL_SIZE_Y_UM`.
7. Rank-based percentile groups are based on sorted object order, not direct numerical percentile cutoff values.
8. The current configured inputs are already filtered `*_ROI_pixels_FILTERED.csv` files.

## Example run

Because all paths are configured in the script itself, execution is simply:

```bash
python your_solidity_report_script.py
```

No command-line arguments are parsed.

## Typical input/output relationship

```text
filtered ROI pixel CSVs
    +
aligned 2-D fluorescence TIFFs
        |
        v
ROI Solidity report script
        |
        +--> combined PDF
        +--> combined all-object CSV
        +--> combined selected-object CSV
        +--> per-channel full measurement CSV
        +--> per-channel Solidity PDF
        +--> per-channel Solidity all-ROI CSV
        +--> per-channel Solidity selected-ROI CSV
```
