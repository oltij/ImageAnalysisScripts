# ROI Reconstruction, Verification, and Pixel-Coordinate Export

This README documents the ROI reconstruction / verification / pixel-coordinate export script uploaded as:

```text
Pasted text (4).txt
```

The script does not declare its own filename in the source. A descriptive repository filename could be:

```text
extract_verify_cellprofiler_rois.py
```

This document is intentionally limited to this script.

# 2. Common coordinate conventions

These scripts use standard image-array and CellProfiler-style pixel coordinates, but the ordering is worth stating explicitly.

## Image arrays

NumPy/TIFF arrays are indexed as:

```text
image[Y, X]
```

For a 2-D image:

```text
shape = (height, width)
      = (Y, X)
```

Example:

```text
shape = (3840, 3840)
```

## ROI pixel-coordinate CSVs

Pixel-coordinate tables use:

```text
ROI,X,Y
```

Example:

```csv
ROI,X,Y
1,1834,1902
1,1835,1902
1,1836,1902
2,2050,1711
```

`X` is the horizontal image coordinate and `Y` is the vertical image coordinate.

## Current physical pixel size

The registration and colocalization scripts currently use:

```text
X = 0.312843137 µm/pixel
Y = 0.312836345 µm/pixel
```

Change these values if the analyzed image has a different physical scale.

---

# 3. ROI reconstruction / verification / pixel-coordinate export script

Uploaded source:

```text
Pasted text (4).txt
```

This script currently has no filename declared in its source, so this README refers to it descriptively.

A reasonable repository filename would be something such as:

```text
extract_verify_cellprofiler_rois.py
```

That is only a suggested name; it is not hard-coded into the script.

---

## 3.1 Purpose

This script takes:

1. a **CellProfiler object-label TIFF** for one fluorescence channel;
2. the corresponding **CellProfiler object-measurement CSV**; and
3. a **CellProfiler organoid-mask CSV**.

It then:

1. reconstructs integer ROI labels from the non-zero intensity levels in the TIFF;
2. checks that the reconstructed ROIs agree with CellProfiler object measurements;
3. exports every ROI pixel as `(ROI, X, Y)`;
4. calculates ROI count and organoid-area-based density statistics; and
5. creates visual QC images.

The most important downstream output is:

```text
<CHANNEL_NAME>_ROI_pixels.csv
```

because that pixel-coordinate representation can be filtered and then passed into the colocalization analysis.

---

## 3.2 Dependencies

The script imports:

```text
numpy
pandas
tifffile
Pillow
matplotlib
```

Example installation:

```bash
pip install numpy pandas tifffile pillow matplotlib
```

---

## 3.3 How inputs are configured

This script does **not** use command-line arguments.

Edit the `USER SETTINGS` section at the top of the script:

```python
tiff_path = Path(
    "/home/oltij/Desktop/LHX6Aligned/CellMask.tiff"
)

channel_csv_path = Path(
    "/home/oltij/Desktop/LHX6Aligned/MyExpt_FilterObjects2.csv"
)

organoid_csv_path = Path(
    "/home/oltij/Desktop/LHX6Aligned/MyExpt_FilterObjects.csv"
)

CHANNEL_NAME = "LHX6"
CENTER_TOLERANCE = 1e-6
```

---

## 3.4 Input 1 — CellProfiler object-label TIFF

### Current configured path

```text
/home/oltij/Desktop/LHX6Aligned/CellMask.tiff
```

### Expected origin

This should come from the **same CellProfiler segmentation run and same image/channel** as `MyExpt_FilterObjects2.csv`.

It is expected to be the saved CellProfiler object-mask / object-label image.

### Required file type

```text
TIFF
Extension: .tif or .tiff
```

### Required dimensionality

Exactly one 2-D grayscale image:

```text
shape = (Y, X)
```

The script rejects non-2-D arrays.

Example:

```text
shape = (3840, 3840)
dtype = uint16
```

### Required background

Background must be:

```text
0
```

The script raises an error if no zero-valued pixels exist.

### Required object encoding

Every segmented object must be represented by its own non-zero intensity level.

Conceptual example:

```text
0      = background
21845  = object 1
43690  = object 2
65535  = object 3
```

The exact values do not have to follow a formula. The script extracts the actual unique non-zero values and sorts them.

It then assigns:

```text
lowest non-zero intensity  -> ROI 1
next intensity             -> ROI 2
next intensity             -> ROI 3
...
```

This behavior is intended to recover a CellProfiler label image that was rescaled when saved as a grayscale/16-bit TIFF.

### Critical assumption

The order of the unique TIFF intensities must correspond to CellProfiler `ObjectNumber`.

For example, the first non-zero intensity must correspond to:

```text
ObjectNumber = 1
```

and so on.

The script explicitly verifies area, bounding box, and centroid afterward, so an incorrect intensity-to-object ordering should be detected.

### Internal reconstructed-label type

The script reconstructs labels into:

```text
numpy.uint16
```

Therefore the implementation implicitly assumes no more than 65,535 distinct non-background ROI labels.

---

## 3.5 Input 2 — channel CellProfiler object CSV

### Current configured path

```text
/home/oltij/Desktop/LHX6Aligned/MyExpt_FilterObjects2.csv
```

### Expected origin

CellProfiler object measurements for the **same segmented objects represented in `CellMask.tiff`**.

### File type

```text
CSV
Extension: .csv
```

### Required columns

The script requires exactly these named fields to exist:

```text
ImageNumber
ObjectNumber
AreaShape_Area
AreaShape_BoundingBoxMaximum_X
AreaShape_BoundingBoxMaximum_Y
AreaShape_BoundingBoxMinimum_X
AreaShape_BoundingBoxMinimum_Y
AreaShape_Center_X
AreaShape_Center_Y
```

Other columns may be present and are ignored by the verification step.

### Example

```csv
ImageNumber,ObjectNumber,AreaShape_Area,AreaShape_BoundingBoxMaximum_X,AreaShape_BoundingBoxMaximum_Y,AreaShape_BoundingBoxMinimum_X,AreaShape_BoundingBoxMinimum_Y,AreaShape_Center_X,AreaShape_Center_Y
1,1,428,1914,2021,1887,1998,1900.47,2009.28
1,2,356,2210,1755,2188,1732,2198.16,1743.62
```

### `ImageNumber` behavior

If the CSV contains only one unique `ImageNumber`, all rows are used.

If multiple image numbers are present, the script uses:

```text
ImageNumber = 1
```

Therefore the TIFF must correspond to image 1 under that circumstance.

---

## 3.6 Input 3 — organoid-mask CellProfiler CSV

### Current configured path

```text
/home/oltij/Desktop/LHX6Aligned/MyExpt_FilterObjects.csv
```

### Expected origin

CellProfiler measurements for the **whole-organoid mask**, not the individual marker-positive ROIs.

### Required file type

```text
CSV
```

### Required columns

```text
ImageNumber
ObjectNumber
FileName_DNA
AreaShape_Area
AreaShape_BoundingBoxArea
AreaShape_BoundingBoxMaximum_X
AreaShape_BoundingBoxMaximum_Y
AreaShape_BoundingBoxMinimum_X
AreaShape_BoundingBoxMinimum_Y
AreaShape_Center_X
AreaShape_Center_Y
```

### Example

```csv
ImageNumber,ObjectNumber,FileName_DNA,AreaShape_Area,AreaShape_BoundingBoxArea,AreaShape_BoundingBoxMaximum_X,AreaShape_BoundingBoxMaximum_Y,AreaShape_BoundingBoxMinimum_X,AreaShape_BoundingBoxMinimum_Y,AreaShape_Center_X,AreaShape_Center_Y
1,1,aligned_Hoechst_max.tif,8320451,11938421,3610,3594,122,95,1872.3,1844.9
```

### Row-selection behavior

If the organoid CSV contains exactly one row, that row is used.

If it contains multiple rows, the script selects rows with:

```text
ImageNumber = 1
```

If more than one organoid object exists for image 1, all of them are retained and their `AreaShape_Area` values are summed for the density denominator.

---

## 3.7 Output directory

The output directory is created automatically as:

```python
output_dir = tiff_path.parent / "ROI_analysis"
```

For the current input:

```text
/home/oltij/Desktop/LHX6Aligned/CellMask.tiff
```

the output directory is:

```text
/home/oltij/Desktop/LHX6Aligned/ROI_analysis/
```

---

## 3.8 Output 1 — reconstructed label TIFF

### Filename

```text
<CHANNEL_NAME>_reconstructed_labels.tiff
```

Current example:

```text
/home/oltij/Desktop/LHX6Aligned/ROI_analysis/LHX6_reconstructed_labels.tiff
```

### Format

```text
TIFF
2-D
dtype = uint16
shape = same as CellMask.tiff
```

### Meaning

```text
0 = background
1 = ROI 1
2 = ROI 2
3 = ROI 3
...
```

Unlike the original rescaled CellProfiler image, the pixel value is the actual reconstructed ROI ID.

---

## 3.9 Output 2 — ROI verification CSV

### Filename

```text
<CHANNEL_NAME>_ROI_verification.csv
```

Current example:

```text
LHX6_ROI_verification.csv
```

### Format

CSV; one row per reconstructed and/or CellProfiler object.

### Principal columns

CellProfiler-derived fields:

```text
ROI
CP_Area
CP_MaxX_Exclusive
CP_MaxY_Exclusive
CP_MinX
CP_MinY
CP_CenterX
CP_CenterY
```

TIFF-derived fields:

```text
OriginalIntensity
TIFF_PixelCount
TIFF_MinX
TIFF_MaxX_ActualPixel
TIFF_MinY
TIFF_MaxY_ActualPixel
TIFF_CenterX
TIFF_CenterY
```

Merge/status fields include:

```text
_merge
ROI_Status
```

where `ROI_Status` can be:

```text
MATCH
CP_ONLY
TIFF_ONLY
```

Comparison fields include:

```text
Area_Difference
Area_Match
MinX_Difference
MaxX_Difference
MinY_Difference
MaxY_Difference
BoundingBox_Match
CenterX_Difference
CenterY_Difference
Center_Match
FULL_MATCH
```

### Bounding-box convention

CellProfiler maximum bounding-box coordinates are treated as exclusive.

Therefore a perfect match is expected to satisfy:

```text
TIFF_MinX - CP_MinX = 0
TIFF_MaxX_ActualPixel - CP_MaxX_Exclusive = -1
TIFF_MinY - CP_MinY = 0
TIFF_MaxY_ActualPixel - CP_MaxY_Exclusive = -1
```

---

## 3.10 Output 3 — ROI pixel-coordinate CSV

### Filename

```text
<CHANNEL_NAME>_ROI_pixels.csv
```

Current example:

```text
/home/oltij/Desktop/LHX6Aligned/ROI_analysis/LHX6_ROI_pixels.csv
```

### This is the principal downstream data product.

### Exact columns

```text
ROI
X
Y
```

### Internal types when constructed

```text
ROI -> uint16
X   -> int32
Y   -> int32
```

CSV itself stores those values as text.

### Row meaning

One CSV row = one pixel belonging to one ROI.

Example:

```csv
ROI,X,Y
1,1900,1999
1,1901,1999
1,1902,1999
1,1899,2000
2,2196,1738
```

If ROI 1 contains 428 pixels, ROI 1 will have 428 rows.

### Expected downstream origin/flow

This file is the natural precursor to a file such as:

```text
LHX6_ROI_pixels_FILTERED.csv
```

after your separate intensity/metric filtering stage.

---

## 3.11 Output 4 — summary statistics CSV

### Filename

```text
<CHANNEL_NAME>_summary_statistics.csv
```

Example:

```text
LHX6_summary_statistics.csv
```

### Contents

The selected organoid-mask row(s), including the required CellProfiler organoid columns, plus:

```text
Channel
ROI_Count
Total_Organoid_Mask_Area_Pixels
ROI_Density_per_Pixel
ROI_Density_per_100000_Pixels
ROI_Density_per_1000000_Pixels
TIFF_ROI_Count
TIFF_File
Channel_CellProfiler_CSV
Organoid_CellProfiler_CSV
```

### Density definition

```text
ROI density per pixel = number of reconstructed ROIs / total organoid mask area in pixels
```

This script does not convert this particular summary to µm² or mm².

---

## 3.12 Output 5 — color-coded reconstructed ROI TIFF

### Filename

```text
<CHANNEL_NAME>_reconstructed_labels_color.tiff
```

Example:

```text
LHX6_reconstructed_labels_color.tiff
```

### Format

```text
RGB TIFF
shape = (Y, X, 3)
dtype = uint8
```

Each ROI receives a different HSV-derived display color. Background is black.

This is a visualization, not an analysis label image.

---

## 3.13 Output 6 — verification overlay TIFF

### Filename

```text
<CHANNEL_NAME>_verification_overlay.tiff
```

### Format

```text
RGB TIFF
dtype = uint8
```

### Meaning

The original CellMask TIFF is normalized to grayscale and reconstructed ROI boundaries are drawn in red.

---

## 3.14 Output 7 — side-by-side visual verification PNG

### Filename

```text
<CHANNEL_NAME>_visual_verification.png
```

### Format

```text
PNG
200 dpi
```

### Meaning

Two panels:

```text
left  = original CellMask TIFF
right = color-coded reconstructed ROIs
```

---

## 3.15 Example output tree

For:

```text
/home/oltij/Desktop/LHX6Aligned/CellMask.tiff
```

the result is:

```text
/home/oltij/Desktop/LHX6Aligned/
├── CellMask.tiff
├── MyExpt_FilterObjects2.csv
├── MyExpt_FilterObjects.csv
└── ROI_analysis/
    ├── LHX6_reconstructed_labels.tiff
    ├── LHX6_ROI_verification.csv
    ├── LHX6_ROI_pixels.csv
    ├── LHX6_summary_statistics.csv
    ├── LHX6_reconstructed_labels_color.tiff
    ├── LHX6_verification_overlay.tiff
    └── LHX6_visual_verification.png
```

---
