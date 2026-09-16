# General Image-Analysis Pipeline

## Overview

This README describes the intended end-to-end workflow for processing a tiled microscopy acquisition consisting of:

```text
4 unstitched fields / quadrants
×
1–4 fluorescence channels
```

A typical experiment may contain:

```text
Nuclear stain
Marker 1
Marker 2
Marker 3
```

but the workflow also works when fewer than four channels are present.

The major stages are:

```text
1. Create/activate Conda environment
2. Build the Fiji + BigStitcher SIF
3. Convert IMS fields, correct illumination, stitch each channel, and make max projections
4. Run CellProfiler on the unaligned max projections
5. Align every non-nuclear channel to the nuclear reference
6. Run CellProfiler again on the aligned images
7. Extract aligned ROI pixel coordinates
8. Perform intensity-first ROI filtering
9. Inspect shape/area distributions after the intensity gate
10. Perform final shape filtering while preserving the intensity gate
11. Colocalize each marker with the nuclear channel
12. Export nuclear-positive marker-cell pixel tables
13. Colocalize nuclear-positive marker cells with other marker cells
14. Inspect the corresponding colocalization QC outputs
```

Several details below are important because the actual scripts do not behave exactly like a purely conceptual pipeline.

---

# 1. Terminology

## Field / quadrant

Each acquisition consists of four tiled microscope fields:

```text
F00
F01
F02
F03
```

For the current BigStitcher workflow, these correspond to the four positions in a 2 × 2 acquisition.

## Channel

A fluorescence channel is one biological/imaging signal, for example:

```text
Hoescht / DAPI
LHX6
PV
GFP
```

The four `.ims` field files can each contain multiple channels.

Therefore the pipeline does **not** require one separate four-file folder per channel when the channels are stored together in the IMS acquisition.

## ROI

An ROI is a segmentation object produced independently within one fluorescence channel.

Before nuclear matching, IDs such as:

```text
ROI 17
ROI 203
ROI 901
```

are channel-specific segmentation-object identifiers.

They should not yet be interpreted as global biological cell identities.

## CellID

The current colocalization script assigns `CellID` values to matched object pairs.

However, an important limitation is:

```text
CellID is local to one colocalization run.
```

A `CellID=5` generated in an LHX6-versus-Hoescht run is not automatically the same biological identifier as `CellID=5` generated in a PV-versus-Hoescht run.

The nuclear ROI/object ID is therefore the more appropriate persistent cross-run anchor if a global cell identity is needed.

This is discussed in detail in the colocalization section.

---

# 2. Software setup

The pipeline uses **two separate Conda environments**:

```text
ims-mosaic
    = main microscopy/image-analysis environment

cellprofiler-native
    = CellProfiler environment
```

The Fiji + BigStitcher container is also built separately as a Singularity `.sif`.

## 2.1 Create the `ims-mosaic` environment

Environment YAML:

```text
ims-mosaic.yml
```

Suggested location:

```text
/home/oltij/Desktop/ImageAnalysisScripts/CondaEnvironment/ims-mosaic.yml
```

Create:

```bash
conda env create \
    -f /home/oltij/Desktop/ImageAnalysisScripts/CondaEnvironment/ims-mosaic.yml
```

Activate:

```bash
conda activate ims-mosaic
```

Use `ims-mosaic` for all non-CellProfiler Python stages, including IMS export/stitching orchestration, BaSiC, TIFF processing, CASTalign, ROI reconstruction/export, filtering, metric reports, and colocalization.

## 2.2 Create the `cellprofiler-native` environment

Environment YAML:

```text
cellprofiler-native.yml
```

Suggested location:

```text
/home/oltij/Desktop/ImageAnalysisScripts/CondaEnvironment/cellprofiler-native.yml
```

Create:

```bash
conda env create \
    -f /home/oltij/Desktop/ImageAnalysisScripts/CondaEnvironment/cellprofiler-native.yml
```

Activate:

```bash
conda activate cellprofiler-native
```

The provided YAML specifies:

```text
Python 3.9.25
CellProfiler 4.2.8
cellprofiler-core 4.2.8
```

Verify:

```bash
which cellprofiler
cellprofiler --version
```

## 2.3 Switching between environments

Start the main workflow in:

```bash
conda activate ims-mosaic
```

Before any CellProfiler stage:

```bash
conda deactivate
conda activate cellprofiler-native
```

After CellProfiler is finished:

```bash
conda deactivate
conda activate ims-mosaic
```

Conceptually:

```text
ims-mosaic
    |
    | enter CellProfiler stage
    v
cellprofiler-native
    |
    | run CellProfiler
    v
ims-mosaic
```

This switch occurs for both:

```text
CellProfiler pass 1 = before alignment
CellProfiler pass 2 = after alignment
```

---

# 3. Build the Fiji + BigStitcher SIF

Use the exact known-working definition:

```text
fiji_latest_bigstitcher.def
```

For example:

```text
/home/oltij/Desktop/ImageAnalysisScripts/Bigstitcher/fiji_latest_bigstitcher.def
```

Load Singularity:

```bash
module load singularity/4.4.1
```

Build:

```bash
cd /home/oltij/Desktop/ImageAnalysisScripts/Bigstitcher

singularity build --fakeroot \
    fiji_latest_bigstitcher.sif \
    fiji_latest_bigstitcher.def
```

The expected built file is:

```text
/home/oltij/Desktop/ImageAnalysisScripts/Bigstitcher/fiji_latest_bigstitcher.sif
```

The IMS pipeline does not require the SIF to have one universal filesystem location because its path is passed explicitly with:

```text
--fiji-sif
```

Therefore the important requirement is simply to know the exact SIF path.

Before starting a long run, confirm that the container launches Fiji successfully.

For example:

```bash
singularity exec \
    /home/oltij/Desktop/ImageAnalysisScripts/Bigstitcher/fiji_latest_bigstitcher.sif \
    /opt/Fiji.app/fiji-linux-x64 \
    --headless \
    --help
```

The current stitching Python script invokes Fiji inside the container using:

```text
/opt/Fiji.app/fiji
```

so it is also useful to verify that this path exists in the successfully built SIF:

```bash
singularity exec \
    /home/oltij/Desktop/ImageAnalysisScripts/Bigstitcher/fiji_latest_bigstitcher.sif \
    test -x /opt/Fiji.app/fiji
```

If your known-working SIF already passes this test, do not change the `.def`.

---

# 4. Organize the raw four-field acquisition

The current IMS mosaic script discovers files named:

```text
<sample>_F00.ims
<sample>_F01.ims
<sample>_F02.ims
<sample>_F03.ims
```

Example:

```text
Exp17_157-2_Set2_DAPI_GFP_LHX6_PV_F00.ims
Exp17_157-2_Set2_DAPI_GFP_LHX6_PV_F01.ims
Exp17_157-2_Set2_DAPI_GFP_LHX6_PV_F02.ims
Exp17_157-2_Set2_DAPI_GFP_LHX6_PV_F03.ims
```

Place the four IMS fields for one acquisition in the same source directory.

The script expects exactly two digits after `F`:

```text
F00
F01
F02
F03
```

not:

```text
F0
F1
F2
F3
```

---

# 5. Run the IMS → TIFF → BaSiC → BigStitcher pipeline

The script is:

```text
ims_mosaic_pipeline_illumination_bigstitcher.py
```

Run the pipeline **once for the acquisition folder**, not once per fluorescence channel.

Example:

```bash
conda activate ims-mosaic

python /path/to/ims_mosaic_pipeline_illumination_bigstitcher.py \
    "/path/to/folder/containing/the/four/IMS/files" \
    --fiji-sif \
    "/home/oltij/Desktop/ImageAnalysisScripts/Bigstitcher/fiji_latest_bigstitcher.sif"
```

The defaults are:

```text
grid = 2 × 2
overlap = 10%
minimum phase-correlation r = 0.55
BaSiC sampled Z planes per tile = 12
```

They can be stated explicitly if desired:

```bash
python /path/to/ims_mosaic_pipeline_illumination_bigstitcher.py \
    "/path/to/folder/containing/the/four/IMS/files" \
    --fiji-sif \
    "/home/oltij/Desktop/ImageAnalysisScripts/Bigstitcher/fiji_latest_bigstitcher.sif" \
    --grid 2 2 \
    --overlap 10 \
    --min-correlation 0.55 \
    --basic-sample-planes 12
```

---

# 6. Important correction: the IMS script processes all channels automatically

The current IMS mosaic script reads the channel list from the IMS files and then loops over:

```python
for channel in channels:
```

Therefore, if the four IMS files contain:

```text
Hoescht
GFP
LHX6
PV
```

you do **not** run the script four times.

You run it once on the acquisition folder.

The pipeline automatically performs, independently for each available channel:

```text
IMS export
→
BaSiC illumination correction
→
BigStitcher registration/fusion
→
maximum-intensity projection
```

If only two or three channels exist, it processes those channels.

The important condition is that every field in the acquisition must have the same channel names/order.

---

# 7. What the IMS pipeline produces

For each sample, the script creates:

```text
<source-folder-name>_IMS_to_TIFF/
└── <sample-name>/
    ├── 01_exported/
    ├── 02_basic_corrected/
    ├── 03_stitched/
    └── 04_max_projections/
```

## `01_exported`

Contains the individual channel Z-stacks exported from each IMS field.

Example:

```text
F00_Confocal - Blue.tif
F01_Confocal - Blue.tif
F02_Confocal - Blue.tif
F03_Confocal - Blue.tif
```

The pipeline trims trailing all-zero XY storage padding by default.

## `02_basic_corrected`

Contains BaSiC-corrected Z-stacks.

## `03_stitched`

Contains the BigStitcher job directories and final fused 3-D stack for every channel.

Conceptually:

```text
<channel>_stitched.tif
```

Each channel gets its own independently stitched 3-D image stack.

## `04_max_projections`

Contains the final 2-D maximum-intensity projection for each channel:

```text
<sample>_<channel>_stitched_max_projection.tif
```

These are the images that should normally enter the next 2-D analysis stages.

---

# 8. Important correction: a separate max-projection step is normally unnecessary

The standalone max-projection script performs:

```python
projection = np.max(image, axis=0)
```

on a fused Z-stack.

However, the current IMS mosaic script already performs exactly this operation at the end of every channel run and writes the result into:

```text
04_max_projections/
```

Therefore, for the current end-to-end IMS script:

```text
DO NOT need:
stitched stack
→ manually run standalone max-projection script
```

because the current pipeline already does:

```text
stitched stack
→ max projection automatically
```

Use the standalone max-projection script only when:

```text
you have a fused stack produced outside the IMS pipeline
```

or:

```text
you intentionally want to regenerate a projection manually
```

This avoids producing duplicate projection files.

---

# 9. First CellProfiler pass: segment the unaligned channel projections

At this stage, use the max projections from:

```text
04_max_projections/
```

First switch into the CellProfiler environment:

```bash
conda deactivate
conda activate cellprofiler-native
```

There are **two supported ways to run CellProfiler**.

## Option A — GUI

Launch:

```bash
cellprofiler
```

and open:

```text
MGEOPV.cpproj
```

Use this option when you want to inspect segmentation interactively, adjust thresholds/settings, step through modules, or visually confirm ROI identification.

## Option B — headless

Use:

```text
MGEOPVFinal.cppipe
```

with:

```text
cellprofilerdriver.py
```

Example:

```bash
python /home/oltij/Desktop/cellprofilerdriver.py \
    --pipeline "/home/oltij/Desktop/MGEOPVFinal.cppipe" \
    --input "/path/to/channel_max_projection.tif" \
    --output "/path/to/CellProfiler_output"
```

The two options are:

```text
GUI:
    MGEOPV.cpproj

Headless:
    MGEOPVFinal.cppipe
    +
    cellprofilerdriver.py
```

Run CellProfiler independently for each channel image:

```text
nuclear projection
marker 1 projection
marker 2 projection
marker 3 projection
```

The required CellProfiler outputs for the ROI-extraction/alignment workflow include the relevant object-measurement CSVs and segmentation image.

Typical files used by the scripts are:

```text
CellMask.tiff
MyExpt_FilterObjects2.csv
MyExpt_FilterObjects.csv
```

`MyExpt_FilterObjects2.csv` contains individual object measurements such as:

```text
ObjectNumber
AreaShape_Area
AreaShape_BoundingBoxMinimum_X
AreaShape_BoundingBoxMaximum_X
AreaShape_BoundingBoxMinimum_Y
AreaShape_BoundingBoxMaximum_Y
AreaShape_Center_X
AreaShape_Center_Y
```

`MyExpt_FilterObjects.csv` can contain the organoid-level object/area information used by some downstream scripts.

After all pre-alignment CellProfiler runs are complete, switch back to:

```bash
conda deactivate
conda activate ims-mosaic
```

Continue alignment and all other non-CellProfiler stages from `ims-mosaic`.

---

# 10. Are pre-alignment ROI pixel CSVs required?

There is an important distinction.

The CASTalign registration script uses:

```text
the fluorescence TIFF
+
CellProfiler centroid CSV
```

It does **not** require the extracted:

```text
<Channel>_ROI_pixels.csv
```

for registration.

Therefore:

```text
CellProfiler before alignment = required
ROI-pixel extraction before alignment = optional for registration itself
```

You may still run ROI extraction before alignment for:

```text
QC
archival purposes
verification of CellProfiler masks
pre-alignment analyses
```

but the alignment code does not consume those pixel CSVs.

The ROI extraction step becomes essential **after alignment**, because those aligned ROI coordinates are used for filtering and colocalization.

---

# 11. Optional pre-alignment ROI extraction

If desired, run the ROI reconstruction/extraction script for each channel.

For each channel it uses:

```text
CellMask.tiff
channel CellProfiler CSV
organoid CellProfiler CSV
```

and produces, among other outputs:

```text
ROI_analysis/<Channel>_ROI_pixels.csv
```

Format:

```csv
ROI,X,Y
1,100,200
1,101,200
1,102,200
2,450,775
```

Each row is one pixel belonging to one segmentation object.

---

# 12. Choose the nuclear reference channel

One channel should be designated as the common spatial reference.

Examples:

```text
Hoescht
DAPI
```

From this point forward:

```text
fixed image = nuclear channel
moving image = one non-nuclear marker channel
```

Every non-nuclear channel is aligned independently to the same nuclear image.

For example:

```text
LHX6 → Hoescht
PV   → Hoescht
GFP  → Hoescht
```

Do not align LHX6 to PV and then PV to Hoescht.

All markers should independently reference the same nuclear coordinate system.

---

# 13. Align every non-nuclear channel to the nuclear reference

Use:

```text
CASTalign_2D_maxproj_registration.py
```

For each non-nuclear marker, provide:

```text
fixed TIFF = nuclear max projection
moving TIFF = marker max projection

fixed CSV = nuclear CellProfiler object CSV
moving CSV = marker CellProfiler object CSV
```

The CellProfiler files in this workflow use centroid columns:

```text
AreaShape_Center_X
AreaShape_Center_Y
```

whereas the alignment script's automatic column detection is oriented toward `Location_Center_*`.

Therefore explicitly provide the CellProfiler centroid column names.

Generic example:

```bash
python CASTalign_2D_maxproj_registration.py \
    --fixed-image "/path/to/Hoescht_max_projection.tif" \
    --moving-image "/path/to/LHX6_max_projection.tif" \
    --fixed-csv "/path/to/Hoescht/MyExpt_FilterObjects2.csv" \
    --moving-csv "/path/to/LHX6/MyExpt_FilterObjects2.csv" \
    --fixed-x-col AreaShape_Center_X \
    --fixed-y-col AreaShape_Center_Y \
    --moving-x-col AreaShape_Center_X \
    --moving-y-col AreaShape_Center_Y \
    --output "/path/to/LHX6Aligned"
```

Repeat for every non-nuclear channel.

---

# 14. Alignment output naming

The uploaded alignment script currently uses some hard-coded output names associated with its original Hoescht/PV use case.

Therefore, after each run, verify exactly which file is the registered moving image.

Keep the final registered marker files under clear names such as:

```text
aligned_LHX6_max.tif
aligned_PV_max.tif
aligned_GFP_max.tif
```

and preserve the nuclear reference as:

```text
aligned_Hoechst_max.tif
```

or equivalent.

The scientific requirement is more important than the literal filename:

```text
all final channel images must be in the same nuclear-reference coordinate frame
```

---

# 15. The nuclear image itself does not need a transformation

The nuclear image is the fixed reference.

Therefore:

```text
nuclear aligned image = nuclear reference image
```

It does not need to be warped against itself.

However, keeping a copy in an aligned-analysis directory can make downstream path organization easier.

---

# 16. Second CellProfiler pass: segment the aligned images

After alignment, run CellProfiler again on the final aligned images.

This second CellProfiler pass is essential.

Do not use the pre-alignment ROI pixel coordinates for downstream overlap analysis because the moving fluorescence image has changed coordinate frame.

Switch back into the CellProfiler environment:

```bash
conda deactivate
conda activate cellprofiler-native
```

Again choose one of two execution modes.

## Option A — GUI

Launch:

```bash
cellprofiler
```

and open:

```text
MGEOPV.cpproj
```

Use the aligned image for the corresponding channel.

## Option B — headless

Use:

```text
MGEOPVFinal.cppipe
```

with:

```text
cellprofilerdriver.py
```

Example:

```bash
python /home/oltij/Desktop/cellprofilerdriver.py \
    --pipeline "/home/oltij/Desktop/MGEOPVFinal.cppipe" \
    --input "/path/to/aligned_channel.tif" \
    --output "/path/to/aligned_channel_CellProfiler_output"
```

Run CellProfiler for:

```text
aligned nuclear reference
aligned marker 1
aligned marker 2
aligned marker 3
```

The nuclear image may be unchanged geometrically, but rerunning it in the aligned-analysis workflow keeps the segmentation products and directory structure consistent.

After all aligned CellProfiler runs are complete:

```bash
conda deactivate
conda activate ims-mosaic
```

Continue ROI extraction, filtering, reports, and colocalization from `ims-mosaic`.

---

# 17. Extract ROIs from all aligned channels

Run the ROI reconstruction/extraction script on each aligned channel's CellProfiler outputs.

For each channel, the important downstream result is:

```text
<Channel>/ROI_analysis/<Channel>_ROI_pixels.csv
```

Example:

```text
HoeschtAligned/ROI_analysis/Hoescht_ROI_pixels.csv
LHX6Aligned/ROI_analysis/LHX6_ROI_pixels.csv
PVAligned/ROI_analysis/PV_ROI_pixels.csv
```

These are the **unaltered aligned segmentation-object pixel tables**.

They should be preserved as the starting point for filtering.

---

# 18. Filtering philosophy

The intended filtering strategy is deliberately two-stage:

```text
Stage 1:
remove low-quality/dim objects using intensity

Stage 2:
inspect shape among the surviving intensity-positive objects,
then apply shape/area filtering
```

The reason for this order is to avoid letting poorly segmented low-intensity objects dominate the apparent distribution of:

```text
area
circularity
eccentricity
solidity
```

In other words:

```text
intensity quality gate first
shape quality gate second
```

---

# 19. Intensity visualization

Use the ROI intensity-report script on the **aligned, unfiltered ROI pixel CSVs**.

Inputs per channel:

```text
aligned <Channel>_ROI_pixels.csv
aligned fluorescence TIFF
```

The script reports:

```text
Mean intensity
Median intensity
Maximum intensity
Integrated intensity
Intensity SD
```

and produces percentile-based visualization/QC outputs.

Inspect these manually to decide which intensity metric(s) and percentile cutoff(s) are appropriate.

Do not choose shape thresholds yet.

---

# 20. First filtering pass: intensity only

Use the final metric filtering script.

For this first pass:

```text
INPUT:
unaltered aligned ROI pixel CSVs

ENABLE:
chosen intensity filter(s)

DISABLE:
all shape filters
```

In this filtering script:

```text
percentile = 0
```

means:

```text
filter OFF
```

Therefore the shape entries should remain at:

```python
{"percentile": 0, ...}
```

during the intensity-only pass.

Example conceptual configuration:

```python
FILTERS = {
    "Mean intensity":        {"percentile": 10, "keep": "above"},

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

The important output is:

```text
<Channel>_ROI_pixels_FILTERED.csv
```

At this point, interpret it as:

```text
intensity-filtered ROI population
```

rather than the final population.

Keep these files.

---

# 21. Inspect shape/area only after the intensity gate

Run the separate report scripts on the **intensity-filtered ROI pixel CSVs**:

```text
Area report
Circularity report
Eccentricity report
Solidity report
```

These scripts calculate the full geometry for surviving objects and then visualize/rank the selected metric.

This means the shape distributions now describe:

```text
objects that already passed the intensity quality gate
```

rather than being contaminated by the dim objects you intentionally removed.

Manually inspect the reports and choose any desired shape/area thresholds.

---

# 22. Critical rule for the second filtering pass

Your proposed logic was:

```text
turn the intensity filter off
then enable the chosen shape filters
```

That is correct **only if the input to the second filtering pass is the intensity-filtered CSV produced by pass 1**.

The second pass must therefore be:

```text
INPUT:
pass-1 <Channel>_ROI_pixels_FILTERED.csv

INTENSITY FILTERS:
off / percentile = 0

SHAPE FILTERS:
chosen values enabled
```

This produces:

```text
intensity-passed
AND
shape-passed
```

objects.

---

# 23. What not to do during the second filtering pass

Do **not** do this:

```text
original unfiltered aligned ROI CSV
+
intensity filter OFF
+
shape filter ON
```

because the low-intensity objects removed in pass 1 would be eligible again.

That would break the intended intensity-first gate.

---

# 24. Recommended two-pass filtering directory structure

A clean structure is:

```text
Filtering/
├── 01_intensity_reports/
├── 02_intensity_filter/
│   ├── Hoescht/
│   │   └── Hoescht_ROI_pixels_FILTERED.csv
│   ├── LHX6/
│   │   └── LHX6_ROI_pixels_FILTERED.csv
│   └── PV/
│       └── PV_ROI_pixels_FILTERED.csv
│
├── 03_shape_reports_after_intensity/
│   ├── area/
│   ├── circularity/
│   ├── eccentricity/
│   └── solidity/
│
└── 04_final_shape_filter/
    ├── Hoescht/
    │   └── Hoescht_ROI_pixels_FILTERED.csv
    ├── LHX6/
    │   └── LHX6_ROI_pixels_FILTERED.csv
    └── PV/
        └── PV_ROI_pixels_FILTERED.csv
```

The files under:

```text
04_final_shape_filter/
```

are the final filtered segmentation objects used for colocalization.

---

# 25. Why the second filtering pass works sequentially

Suppose the original aligned channel has:

```text
3,000 ROIs
```

Intensity filtering retains:

```text
2,300 ROIs
```

Then the shape-filtering script receives only those 2,300 ROI pixel sets.

The shape percentiles are therefore calculated from:

```text
the 2,300 intensity-passing ROIs
```

and perhaps retain:

```text
2,050 final ROIs
```

The final population is:

```text
original ROIs
∩
intensity quality
∩
shape quality
```

which matches the intended biological/QC rationale.

---

# 26. Final filtered images must all share one coordinate frame

Before beginning colocalization, verify that the following all correspond to the same aligned image canvas:

```text
final nuclear ROI pixels
final marker-1 ROI pixels
final marker-2 ROI pixels
final marker-3 ROI pixels

aligned nuclear TIFF
aligned marker-1 TIFF
aligned marker-2 TIFF
aligned marker-3 TIFF
```

This is essential because colocalization uses exact shared:

```text
X,Y
```

pixel coordinates.

---

# 27. First colocalization stage: marker versus nuclear stain

For each biological marker, perform a separate colocalization against the nuclear reference.

Examples:

```text
LHX6 versus Hoescht
PV versus Hoescht
GFP versus Hoescht
```

For this stage, a useful convention is:

```text
Object A = marker
Object B = nuclear stain
```

because the current eligibility threshold is directional.

It tests:

```text
A_Percent_Inside_B
```

against the configured threshold.

Thus with:

```text
A = marker
B = nucleus
```

the threshold asks how much of the marker ROI lies inside its candidate nuclear ROI.

Choose the threshold according to the biology/segmentation logic of the marker rather than assuming the same threshold is appropriate for every marker.

---

# 28. Inputs to `01_run_colocalization.py`

For a marker-versus-nuclear run:

```text
OBJECT_A_NAME = marker
OBJECT_B_NAME = nuclear stain

OBJECT_A_CSV = final filtered marker ROI-pixel CSV
OBJECT_B_CSV = final filtered nuclear ROI-pixel CSV

OBJECT_A_TIFF = aligned marker TIFF
OBJECT_B_TIFF = aligned nuclear TIFF
```

Optional:

```text
ORGANOID_CSV
```

can be supplied when density/area calculations are desired.

The script requires the two TIFFs to have the same image shape.

---

# 29. Colocalization matching behavior

The current analysis:

```text
calculates exact shared pixels
calculates directional overlap percentages
applies the overlap threshold
builds preference lists
performs one-to-one stable matching
assigns CellIDs to matched pairs
```

The threshold is based on:

```text
A_Percent_Inside_B
```

not the reverse percentage.

The stable matching is one-to-one.

Therefore one marker object cannot ultimately be assigned to several nuclear objects, and one nuclear object cannot ultimately be assigned to several marker objects within that run.

---

# 30. What `01_run_colocalization.py` writes

The script writes one self-contained:

```text
.h5
```

analysis file.

It contains:

```text
original fluorescence images
original object pixel tables
overlap table
eligible-pair table
preference matrix
stable matching table
CellID mapping
filtered matched Object-A pixels
filtered matched Object-B pixels
positive-object table
unmatched-object information
summary statistics
filtering-stage counts
```

Important internal tables include:

```text
tables/cell_id_mapping
tables/filtered_object_a_pixels
tables/filtered_object_b_pixels
```

---

# 31. Nuclear-positive marker objects

When:

```text
Object A = marker
Object B = nuclear
```

the HDF5 table:

```text
tables/filtered_object_a_pixels
```

contains only marker objects that survived the one-to-one marker-versus-nuclear matching.

These are the marker segmentation objects that can be treated as:

```text
nuclear-associated / nuclear-positive marker cells
```

under the chosen overlap criterion.

The table is formatted using:

```text
CellID
X
Y
```

and is therefore directly compatible with the next colocalization analysis after exporting it to CSV.

---

# 32. Important CellID limitation

The current script creates `CellID` using:

```text
1, 2, 3, ..., N
```

after sorting the matched pairs in that specific analysis run.

Therefore:

```text
LHX6-vs-Hoescht CellID 10
```

and:

```text
PV-vs-Hoescht CellID 10
```

are **not guaranteed to refer to the same nucleus**.

The values are only shared between Object A and Object B within one `.h5` result.

---

# 33. Recommended nomenclature for global cell identity

For a stable identity across marker-vs-nuclear runs, preserve:

```text
B_ObjectID
```

from:

```text
tables/cell_id_mapping
```

when Object B is the nuclear channel.

Conceptually:

```text
Nuclear ObjectID = canonical nucleus/cell key
```

while:

```text
CellID = pairwise-run-local convenience identifier
```

If a future script is added to construct a global multi-marker table, it should join marker relationships through this nuclear `B_ObjectID`.

---

# 34. Run colocalization visualization/QC

After each analysis HDF5 is created, run:

```text
02_generate_colocalization_visualizations.py
```

Set:

```text
RESULTS_FILE
```

to the corresponding HDF5.

This creates the visual QC outputs without rerunning the underlying colocalization.

Inspect:

```text
matched-pair examples
below-threshold examples
filtering Sankey
before/after ROI overlays
unmatched-object QC
overlap-percent QC
```

before accepting the nuclear-matching result.

---

# 35. Export the nuclear-positive marker pixels for the next stage

The current `01_run_colocalization.py` stores the matched marker pixel table **inside the HDF5**.

It does not automatically write that table as a standalone CSV for the next analysis stage.

Therefore an export step is required before marker-vs-marker colocalization.

A minimal helper is:

```python
import io
from pathlib import Path

import h5py
import pandas as pd


results_file = Path(
    "/path/to/marker_vs_nuclear_analysis.h5"
)

output_csv = Path(
    "/path/to/Marker_nuclear_positive_cells.csv"
)


with h5py.File(results_file, "r") as h5:
    payload = h5[
        "tables/filtered_object_a_pixels"
    ][()]

    marker_cells = pd.read_csv(
        io.BytesIO(payload.tobytes())
    )


marker_cells.to_csv(
    output_csv,
    index=False
)

print(f"Saved: {output_csv}")
print(marker_cells.head())
```

The exported CSV will have the form:

```csv
CellID,X,Y
1,1200,1800
1,1201,1800
1,1201,1801
2,2340,1670
```

Because `01_run_colocalization.py` accepts either:

```text
ROI
```

or:

```text
CellID
```

as its object identifier, this exported table can be used directly in the next colocalization analysis.

---

# 36. Export one nuclear-positive CSV per marker

After nuclear matching, the workflow should produce something conceptually like:

```text
NuclearPositiveCells/
├── LHX6_nuclear_positive_cells.csv
├── PV_nuclear_positive_cells.csv
└── GFP_nuclear_positive_cells.csv
```

Each contains only the pixels belonging to marker objects that passed nuclear matching.

---

# 37. Second colocalization stage: marker versus marker

Now compare the nuclear-positive marker populations to each other.

Examples:

```text
LHX6-positive cells versus PV-positive cells
LHX6-positive cells versus GFP-positive cells
PV-positive cells versus GFP-positive cells
```

Inputs are:

```text
Object A CSV:
nuclear-positive marker-A CellID/X/Y table

Object B CSV:
nuclear-positive marker-B CellID/X/Y table

Object A TIFF:
aligned marker-A fluorescence image

Object B TIFF:
aligned marker-B fluorescence image
```

Because all images were aligned to the same nuclear reference, their coordinates should now be directly comparable.

---

# 38. Pairwise marker relationships

For a four-channel experiment containing:

```text
nuclear
A
B
C
```

the nuclear-gating analyses are:

```text
A ↔ nuclear
B ↔ nuclear
C ↔ nuclear
```

Potential downstream marker-marker analyses are:

```text
A ↔ B
A ↔ C
B ↔ C
```

Only run the pairwise comparisons relevant to the biological question.

---

# 39. Pairwise marker CellIDs are again local

The second marker-marker colocalization run creates another new run-local:

```text
CellID
```

namespace.

That is acceptable for pairwise overlap analysis because the code determines matches from:

```text
pixel coordinates
```

rather than assuming that input IDs already match across channels.

However, pairwise analysis alone does not automatically create one universal:

```text
cell × all markers
```

table.

For a future global multi-marker identity table, join all results through the corresponding nuclear object IDs from the first nuclear-gating stage.

---

# 40. Recommended conceptual identity hierarchy

Use the following terminology consistently:

```text
ROI
    = one segmentation object in one channel

Nuclear-positive marker ROI
    = marker ROI successfully matched to one nuclear ROI

Pairwise CellID
    = ID assigned to a matched pair inside one colocalization run

Canonical nuclear ID
    = nuclear ObjectID used to connect identities across runs
```

This avoids accidentally treating two unrelated run-local CellID numbers as the same cell.

---

# 41. Complete corrected workflow

The complete pipeline is:

```text
SETUP
│
├── Create ims-mosaic Conda environment
├── Activate ims-mosaic
└── Build/locate Fiji + BigStitcher SIF
     │
     v
RAW ACQUISITION
│
├── F00.ims
├── F01.ims
├── F02.ims
└── F03.ims
     │
     v
IMS MOSAIC PIPELINE — RUN ONCE
│
├── discover all available channels
│
├── export every channel from each field
├── trim trailing zero padding
├── BaSiC correction
├── BigStitcher each channel independently
└── max-project every stitched channel automatically
     │
     v
UNALIGNED MAX PROJECTIONS
│
├── nuclear
├── marker A
├── marker B
└── marker C
     │
     v
SWITCH ENVIRONMENT
│
└── ims-mosaic → cellprofiler-native
     │
     v
CELLPROFILER PASS 1
│
├── GUI: MGEOPV.cpproj
│   OR
├── headless: MGEOPVFinal.cppipe + cellprofilerdriver.py
│
└── object centroids/masks for registration
     │
     v
SWITCH ENVIRONMENT
│
└── cellprofiler-native → ims-mosaic
     │
     v
ALIGNMENT
│
├── marker A → nuclear
├── marker B → nuclear
└── marker C → nuclear
     │
     v
COMMON NUCLEAR COORDINATE FRAME
     │
     v
SWITCH ENVIRONMENT
│
└── ims-mosaic → cellprofiler-native
     │
     v
CELLPROFILER PASS 2
│
├── GUI: MGEOPV.cpproj
│   OR
├── headless: MGEOPVFinal.cppipe + cellprofilerdriver.py
│
└── segment aligned images
     │
     v
SWITCH ENVIRONMENT
│
└── cellprofiler-native → ims-mosaic
     │
     v
ROI EXTRACTION
│
└── aligned <Channel>_ROI_pixels.csv
     │
     v
INTENSITY REPORTS
│
└── manually inspect intensity distributions
     │
     v
FILTER PASS 1
│
├── intensity filters ON
└── shape filters OFF
     │
     v
INTENSITY-FILTERED ROI PIXELS
     │
     v
SHAPE REPORTS
│
├── area
├── circularity
├── eccentricity
└── solidity
     │
     v
MANUALLY CHOOSE SHAPE FILTERS
     │
     v
FILTER PASS 2
│
├── INPUT = intensity-filtered ROI pixels
├── intensity filters OFF
└── chosen shape filters ON
     │
     v
FINAL FILTERED ALIGNED ROI PIXELS
     │
     v
MARKER ↔ NUCLEAR COLOCALIZATION
│
├── marker A ↔ nuclear
├── marker B ↔ nuclear
└── marker C ↔ nuclear
     │
     ├── run QC visualization script
     │
     v
EXPORT tables/filtered_object_a_pixels
     │
     v
NUCLEAR-POSITIVE MARKER CELL PIXELS
     │
     v
MARKER ↔ MARKER COLOCALIZATION
│
├── A ↔ B
├── A ↔ C
└── B ↔ C
     │
     v
FINAL PAIRWISE BIOLOGICAL RELATIONSHIPS
```

---

# 42. Which steps happen once versus per channel

## Once per software setup

```text
Create ims-mosaic Conda environment
Create cellprofiler-native Conda environment
Build Fiji + BigStitcher SIF
```

## Once per four-field acquisition

```text
Run IMS mosaic pipeline
```

The IMS pipeline automatically processes all channels in the acquisition.

## Once per channel before alignment

```text
CellProfiler pass 1
```

## Once per non-nuclear channel

```text
CASTalign to nuclear reference
```

## Once per aligned channel

```text
CellProfiler pass 2
ROI extraction
intensity filtering
shape filtering
```

## Once per marker

```text
marker-versus-nuclear colocalization
colocalization QC
export nuclear-positive marker pixels
```

## Once per desired marker pair

```text
marker-versus-marker colocalization
colocalization QC
```

---

# 43. Suggested project directory

A practical analysis directory could be:

```text
Experiment/
├── 00_raw_ims/
│   ├── Sample_F00.ims
│   ├── Sample_F01.ims
│   ├── Sample_F02.ims
│   └── Sample_F03.ims
│
├── 01_mosaic_pipeline/
│   └── ... IMS_to_TIFF outputs ...
│
├── 02_cellprofiler_prealignment/
│   ├── Nuclear/
│   ├── MarkerA/
│   ├── MarkerB/
│   └── MarkerC/
│
├── 03_aligned/
│   ├── Nuclear/
│   ├── MarkerA/
│   ├── MarkerB/
│   └── MarkerC/
│
├── 04_cellprofiler_aligned/
│   ├── Nuclear/
│   ├── MarkerA/
│   ├── MarkerB/
│   └── MarkerC/
│
├── 05_aligned_roi_pixels/
│   ├── Nuclear/
│   ├── MarkerA/
│   ├── MarkerB/
│   └── MarkerC/
│
├── 06_filtering/
│   ├── 01_intensity_reports/
│   ├── 02_intensity_filter/
│   ├── 03_shape_reports_after_intensity/
│   └── 04_final_shape_filter/
│
├── 07_nuclear_colocalization/
│   ├── MarkerA_vs_Nuclear/
│   ├── MarkerB_vs_Nuclear/
│   └── MarkerC_vs_Nuclear/
│
├── 08_nuclear_positive_marker_cells/
│   ├── MarkerA_nuclear_positive_cells.csv
│   ├── MarkerB_nuclear_positive_cells.csv
│   └── MarkerC_nuclear_positive_cells.csv
│
└── 09_marker_marker_colocalization/
    ├── MarkerA_vs_MarkerB/
    ├── MarkerA_vs_MarkerC/
    └── MarkerB_vs_MarkerC/
```

The exact directory names are optional, but keeping each stage separate helps prevent accidentally feeding pre-alignment, unfiltered, or first-pass-filtered objects into a later stage.

---

# 44. Files that should never be overwritten accidentally

Preserve separately:

```text
raw IMS files

unaligned max projections

CellProfiler pass-1 measurements

aligned TIFFs

CellProfiler pass-2 measurements

unfiltered aligned ROI pixel CSVs

intensity-filtered ROI pixel CSVs

final intensity+shape-filtered ROI pixel CSVs

marker-versus-nuclear HDF5 files

marker-versus-marker HDF5 files

all visualization/QC directories
```

These represent different biological/processing stages and should not share ambiguous filenames in one directory.

---

# 45. QC checkpoints

Do not treat the pipeline as one completely blind automated chain.

Recommended manual QC checkpoints are:

```text
after stitching
    inspect seams and gross spatial failures

after cross-channel alignment
    inspect nuclear/marker overlays and residuals

after CellProfiler segmentation
    inspect ROI masks

after intensity report
    select/justify intensity filtering

after intensity-only filtering
    verify low-intensity segmentation artifacts were removed

after shape reports
    choose shape thresholds

after final filtering
    inspect retained/removed populations

after marker-versus-nuclear colocalization
    inspect matched and unmatched objects

after marker-versus-marker colocalization
    inspect representative matched pairs
```

---

# 46. Key implementation corrections relative to the conceptual workflow

## Correction 1 — stitching is not run separately per channel

Run the IMS mosaic script once on the four-field acquisition.

It automatically loops over all available channels.

## Correction 2 — the IMS script already creates max projections

The standalone max-projection script is optional when using the current IMS mosaic pipeline.

## Correction 3 — ROI extraction before alignment is optional

The alignment script consumes CellProfiler centroid CSVs, not ROI-pixel CSVs.

Aligned ROI extraction is the critical extraction stage for filtering/colocalization.

## Correction 4 — intensity must remain logically upstream of shape filtering

If the intensity filter is disabled for the second pass, the second pass must read the **intensity-filtered CSV**, not the original ROI CSV.

## Correction 5 — current CellIDs are not globally stable

The current colocalization script assigns sequential CellIDs independently for each pairwise run.

Use the nuclear ObjectID mapping when a persistent cross-marker cell identity is required.

## Correction 6 — nuclear-positive marker pixels are stored in HDF5

The first colocalization script does not automatically emit those pixels as a standalone downstream CSV.

Export:

```text
tables/filtered_object_a_pixels
```

before feeding nuclear-positive marker cells into another colocalization run.

---

## Correction 7 — CellProfiler uses a separate environment and has two execution modes

The main pipeline runs in:

```text
ims-mosaic
```

CellProfiler runs in:

```text
cellprofiler-native
```

At each CellProfiler stage:

```text
ims-mosaic
→
cellprofiler-native
→
run CellProfiler
→
ims-mosaic
```

CellProfiler may be run either:

```text
GUI: MGEOPV.cpproj
```

or:

```text
Headless: MGEOPVFinal.cppipe + cellprofilerdriver.py
```

Both are valid execution options for the CellProfiler stages of the same larger workflow.

---

# 47. Final interpretation

The pipeline has three conceptual identity levels:

```text
1. Segmentation ROI
   independent object in one channel

2. Nuclear-associated marker cell
   marker ROI that successfully matches a nucleus

3. Multi-marker relationship
   nuclear-associated marker cells that overlap/match another
   nuclear-associated marker population
```

Keeping these levels separate prevents channel-specific ROI labels from being mistaken for biological cell identities too early in the workflow.

The nuclear reference provides the shared spatial coordinate system, while nuclear-object matching provides the most natural anchor for eventual global cell identity.
