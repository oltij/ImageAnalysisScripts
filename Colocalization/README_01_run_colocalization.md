# `01_run_colocalization.py`

This README documents the analysis-only colocalization script uploaded as:

```text
Pasted text (2)(1).txt
```

The script performs pixelwise overlap analysis, thresholding, preference construction, one-to-one stable matching, summary calculations, and writes one self-contained HDF5 analysis file.

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

# 5. `01_run_colocalization.py`

Uploaded source:

```text
Pasted text (2)(1).txt
```

---

## 5.1 Purpose

This is the analysis-only stage.

It:

1. loads two ROI pixel-coordinate CSVs;
2. calculates exact shared pixels;
3. calculates directional overlap percentages;
4. applies the configured Object-A overlap threshold;
5. builds A-side and B-side preference lists;
6. runs **Object-A-proposing stable matching / deferred acceptance**;
7. assigns shared `CellID` values to final pairs;
8. calculates summary statistics and optional density statistics; and
9. writes everything needed for visualization into **one HDF5 file**.

After that HDF5 file has been successfully created, the visualization script does not require the original TIFFs or CSVs.

---

## 5.2 Dependencies

```text
pandas
numpy
tifffile
h5py
```

Example:

```bash
pip install pandas numpy tifffile h5py
```

---

## 5.3 Configuration style

This script does **not** currently use command-line arguments.

Edit its `USER SETTINGS` section.

Current settings:

```python
OBJECT_A_NAME = "LHX6"
OBJECT_B_NAME = "PV"

OBJECT_A_CSV = Path(
    "/home/oltij/Desktop/ROI_intensitymetric_filtering/LHX6/LHX6_ROI_pixels_FILTERED.csv"
)

OBJECT_B_CSV = Path(
    "/home/oltij/Desktop/ROI_intensitymetric_filtering/PV/PV_ROI_pixels_FILTERED.csv"
)

OBJECT_A_TIFF = Path(
    "/home/oltij/Desktop/LHX6Aligned/aligned_LHX6_max.tif"
)

OBJECT_B_TIFF = Path(
    "/home/oltij/Desktop/PVAligned/aligned_PV_max.tif"
)

ORGANOID_CSV = Path(
    "/home/oltij/Desktop/HoeschtAligned/MyExpt_FilterObjects.csv"
)

RESULTS_FILE = Path(
    "/home/oltij/Desktop/Aligned_LHX6PV_colocalization_results_25_new/"
    "Aligned_LHX6PV_colocalization_analysis.h5"
)

THRESHOLD = 0.25

PIXEL_SIZE_X_UM = 0.312843137
PIXEL_SIZE_Y_UM = 0.312836345
```

---

## 5.4 Input 1 — Object-A ROI pixel CSV

### Current example

```text
/home/oltij/Desktop/ROI_intensitymetric_filtering/LHX6/LHX6_ROI_pixels_FILTERED.csv
```

### Expected origin

The unfiltered precursor is naturally produced by the ROI export script:

```text
LHX6_ROI_pixels.csv
```

The configured input, however, is a **filtered version** produced by an intermediate filtering stage not included in these four scripts:

```text
LHX6_ROI_pixels_FILTERED.csv
```

### Required file type

```text
CSV
```

### Required ID column

The file must contain either:

```text
ROI
```

or:

```text
CellID
```

If both exist, the script uses `ROI` because it is checked first.

### Required coordinate columns

```text
X
Y
```

### Required numeric behavior

The script explicitly converts:

```text
ID -> int
X  -> int
Y  -> int
```

and raises an error for non-numeric values.

Duplicate rows with the same:

```text
ObjectID, X, Y
```

are removed.

### Minimal example

```csv
ROI,X,Y
1,1900,1999
1,1901,1999
1,1902,1999
2,2196,1738
```

---

## 5.5 Input 2 — Object-B ROI pixel CSV

### Current example

```text
/home/oltij/Desktop/ROI_intensitymetric_filtering/PV/PV_ROI_pixels_FILTERED.csv
```

Same format requirements as Object A:

```text
ROI or CellID
X
Y
```

---

## 5.6 Input 3 — Object-A original/aligned fluorescence TIFF

### Current path

```text
/home/oltij/Desktop/LHX6Aligned/aligned_LHX6_max.tif
```

### Expected origin

The aligned/max-projected fluorescence image corresponding to the Object-A ROI coordinates.

For pixelwise analysis, the image and ROI pixels must refer to the same coordinate frame.

### Required format

```text
TIFF
2-D after squeeze
```

---

## 5.7 Input 4 — Object-B original/aligned fluorescence TIFF

### Current path

```text
/home/oltij/Desktop/PVAligned/aligned_PV_max.tif
```

Same requirements as Object A.

### Cross-channel requirement

The two images must have exactly the same dimensions:

```text
OBJECT_A_TIFF.shape == OBJECT_B_TIFF.shape
```

Pixel-coordinate CSVs should also refer to this same coordinate system.

---

## 5.8 Input 5 — optional organoid CSV

### Current path

```text
/home/oltij/Desktop/HoeschtAligned/MyExpt_FilterObjects.csv
```

### Purpose

Used only to calculate organoid area and density statistics.

### Required column

For **this script**, only:

```text
AreaShape_Area
```

is explicitly required.

This is less strict than the ROI reconstruction script, which requires a larger set of organoid columns.

### Area calculation

All numeric, non-null values in:

```text
AreaShape_Area
```

are summed.

Physical area is calculated from:

```text
pixel area = PIXEL_SIZE_X_UM * PIXEL_SIZE_Y_UM
```

and converted to mm².

### Disable organoid density calculations

Set:

```python
ORGANOID_CSV = None
```

---

# 6. Exact colocalization logic

This is important for interpreting the output.

## 6.1 Shared pixels

The script joins Object-A and Object-B pixels on:

```text
X
Y
```

Therefore a shared pixel exists only when both ROI masks contain the exact same coordinate.

---

## 6.2 Pairwise overlap fields

For every overlapping A/B pair:

```text
Shared_Area = number of pixels present in both objects

A_Percent_Inside_B =
    Shared_Area / A_Area * 100

B_Percent_Inside_A =
    Shared_Area / B_Area * 100
```

---

## 6.3 Eligibility threshold

Current:

```text
THRESHOLD = 0.25
```

A pair is eligible when:

```text
A_Percent_Inside_B >= 25%
```

This is **directional**.

The eligibility condition does not require 25% of B to be inside A.

---

## 6.4 Preference ranking

Object A ranks eligible B partners primarily by:

```text
A_Percent_Inside_B
```

Object B also ranks candidate A partners by:

```text
A_Percent_Inside_B
```

This behavior is deliberately preserved from the original script.

---

## 6.5 Final matching

The script performs:

```text
Object-A-proposing stable matching / deferred acceptance
```

The final result is one-to-one:

```text
one A object <= one B object
one B object <= one A object
```

An object can therefore have a spatially eligible partner but still remain unmatched if it loses the one-to-one competition.

---

# 7. `01_run_colocalization.py` output

## 7.1 Output location

Current:

```text
/home/oltij/Desktop/Aligned_LHX6PV_colocalization_results_25_new/
```

The parent directory is created automatically.

## 7.2 Only filesystem output

The script intentionally writes one file:

```text
Aligned_LHX6PV_colocalization_analysis.h5
```

Full current path:

```text
/home/oltij/Desktop/Aligned_LHX6PV_colocalization_results_25_new/Aligned_LHX6PV_colocalization_analysis.h5
```

### File type

```text
HDF5
Extension: .h5
```

### Root attributes

```text
format = "colocalization_analysis_v1"
created_by = script filename
```

---

## 7.3 HDF5 structure

```text
Aligned_LHX6PV_colocalization_analysis.h5
│
├── metadata/
│   └── json
│
├── images/
│   ├── object_a_original
│   └── object_b_original
│
└── tables/
    ├── object_a_pixels
    ├── object_b_pixels
    ├── overlap_results
    ├── eligible_pairs
    ├── preference_matrix
    ├── stable_matching
    ├── cell_id_mapping
    ├── filtered_object_a_pixels
    ├── filtered_object_b_pixels
    ├── positive_objects
    ├── unmatched_object_a
    ├── summary_statistics
    └── filtering_stage_counts
```

---

## 7.4 `metadata/json`

Stored as UTF-8 JSON bytes.

Contains:

```text
run date/time
script name
Object-A name
Object-B name
original ID-column names
all input file paths
threshold
threshold percentage
matching direction
matching algorithm
pixel sizes
pixel area
image height
image width
Object-A image dtype
Object-B image dtype
```

---

## 7.5 Original fluorescence image datasets

```text
images/object_a_original
images/object_b_original
```

These store the actual NumPy image arrays from the two input TIFFs.

Compression:

```text
gzip level 4
shuffle = true
```

This is why the visualization script can operate without reopening the source TIFFs.

---

## 7.6 Table storage format

Each DataFrame is first serialized to CSV text, then UTF-8 encoded, converted to a `uint8` byte array, and stored in HDF5 under:

```text
tables/<name>
```

Compression:

```text
gzip level 6
```

The visualization script reconstructs each table with `pandas.read_csv()`.

---

## 7.7 `tables/object_a_pixels` and `tables/object_b_pixels`

These contain the deduplicated input pixel tables plus the internally created:

```text
ObjectID
```

field.

At minimum:

```text
original ID column
X
Y
ObjectID
```

---

## 7.8 `tables/overlap_results`

Exact core columns:

```text
A_ObjectID
B_ObjectID
A_Area
B_Area
Shared_Area
A_Percent_Inside_B
B_Percent_Inside_A
Eligible
```

---

## 7.9 `tables/eligible_pairs`

Subset of `overlap_results` for which:

```text
A_Percent_Inside_B >= THRESHOLD * 100
```

---

## 7.10 `tables/preference_matrix`

Columns:

```text
A_ObjectID
B_ObjectID
A_Percent_Inside_B
B_Percent_Inside_A
A_Preference_Rank
B_Preference_Rank
```

---

## 7.11 `tables/stable_matching`

Columns:

```text
A_ObjectID
B_ObjectID
A_Area
B_Area
Shared_Area
A_Percent_Inside_B
B_Percent_Inside_A
A_Preference_Rank
B_Preference_Rank
Pass_Threshold
```

This is the final one-to-one matching table.

---

## 7.12 `tables/cell_id_mapping`

Columns:

```text
CellID
A_ObjectID
B_ObjectID
```

`CellID` is assigned sequentially:

```text
1, 2, 3, ...
```

after sorting final matched pairs.

Example:

```csv
CellID,A_ObjectID,B_ObjectID
1,14,9
2,18,12
3,23,15
```

---

## 7.13 `tables/filtered_object_a_pixels`

Only Object-A pixels belonging to final matched objects.

The original `ObjectID` column is removed and replaced by the shared:

```text
CellID
```

The core layout is:

```text
CellID
<original input columns other than ObjectID>
```

At minimum:

```text
CellID,X,Y
```

---

## 7.14 `tables/filtered_object_b_pixels`

Same structure as the filtered A table, using the same shared final `CellID` values.

---

## 7.15 `tables/positive_objects`

Copy of the final `stable_matching` table.

---

## 7.16 `tables/unmatched_object_a`

This table specifically describes Object-A objects that fail to participate in any eligible pair.

Columns:

```text
A_ObjectID
Best_B_ObjectID
Best_Shared_Area
Best_A_Percent_Inside_B
Best_B_Percent_Inside_A
```

When an A object has no overlapping B object, the best-partner fields are empty/zero as appropriate.

---

## 7.17 `tables/summary_statistics`

Columns:

```text
Metric
Value
Units
```

Metrics include:

```text
Total Object-A objects
Matched Object-A objects
Proportion of Object-A objects matched
Total Object-B objects
Matched Object-B objects
Proportion of Object-B objects matched
Matched CellIDs
Object-A objects below threshold
Organoid area in pixels
Organoid area in mm^2
Object-A density in objects/mm^2
Object-B density in objects/mm^2
Matched Object-A density in objects/mm^2
Matched Object-B density in objects/mm^2
```

Density fields become NaN when no valid organoid area is supplied.

---

## 7.18 `tables/filtering_stage_counts`

Columns:

```text
Marker
Stage
Count
```

For each marker, stages are:

```text
All segmented objects
At least one overlapping partner
Participating in eligible pair (A >= threshold inside B)
Final one-to-one matched objects
```

This table is later used to generate the filtering Sankey/QC.

---

# Important implementation notes

## 26.3 Colocalization threshold is directional

With:

```text
OBJECT_A_NAME = "LHX6"
OBJECT_B_NAME = "PV"
THRESHOLD = 0.25
```

the criterion is:

```text
at least 25% of LHX6 ROI area lies inside the PV ROI
```

It is not:

```text
25% of either object
```

and not:

```text
25% of both objects
```

Switching A and B can therefore change the eligible-pair set.

---

## 26.4 Final one-to-one matching is not the same as raw overlap

A marker-positive object may:

```text
overlap another object
```

and even:

```text
pass the threshold
```

but still fail to appear in the final stable matching because another object wins the one-to-one assignment.

This is why the visualization script distinguishes final unmatched classes from strictly non-overlapping objects.

---

## 26.5 Pixelwise colocalization assumes a common coordinate frame

The core overlap calculation is an exact merge on:

```text
X,Y
```

No tolerance is applied at this stage.

A one-pixel alignment difference changes which pixels are counted as overlapping.

Registration quality therefore directly affects colocalization.

---

## 26.6 HDF5 is intended to be self-contained

Once `01_run_colocalization.py` has produced its HDF5 result, the visualization stage uses:

```text
embedded original fluorescence images
embedded pixel tables
embedded matching tables
embedded metadata
```

rather than reopening the original CSV/TIFF inputs.

This makes the HDF5 file the analysis record that should be archived with the run.

---
