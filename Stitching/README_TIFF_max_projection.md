# TIFF Z-Stack Maximum-Intensity Projection Script

## Purpose

This script converts a 3-D TIFF image stack into a single 2-D maximum-intensity projection.

The current source and destination are:

```text
Input:
/home/oltij/Desktop/BLUE_trimmed_padding_test_fused.tif

Output:
/home/oltij/Desktop/BLUE_trimmed_padding_test_max_projection.tif
```

The operation performed is:

```python
projection = np.max(image, axis=0)
```

This means that for every `(Y, X)` pixel location, the output pixel is the maximum value found across the first input axis.

For a standard `ZYX` stack:

```text
input shape:  (Z, Y, X)
output shape: (Y, X)
```

---

## Dependencies

The script requires:

```text
Python
numpy
tifffile
```

Example installation:

```bash
pip install numpy tifffile
```

---

## Input

### File

```text
/home/oltij/Desktop/BLUE_trimmed_padding_test_fused.tif
```

### Expected type

```text
TIFF
```

Typical extensions:

```text
.tif
.tiff
```

### Expected dimensionality

The intended input is a 3-D image stack:

```text
(Z, Y, X)
```

Example:

```text
(85, 3840, 3840)
```

where:

```text
Z = number of optical sections / planes
Y = image height
X = image width
```

### Expected data type

The script does not force a specific input dtype.

Examples that work with `numpy.max()` include:

```text
uint8
uint16
int16
float32
float64
```

The input dtype is printed before projection:

```python
print(f"Input dtype: {image.dtype}")
```

### Important axis assumption

The script assumes that:

```text
axis 0 = Z
```

because it calculates:

```python
np.max(image, axis=0)
```

If the input were instead arranged as:

```text
(Y, X, Z)
```

this would not produce the intended Z projection.

For this workflow, the expected TIFF organization is therefore:

```text
ZYX
```

---

## How the input is loaded

The entire TIFF is read into memory with:

```python
image = tifffile.imread(source)
```

The script then prints:

```text
Input shape
Input dtype
```

This is useful for confirming that the first axis is the stack/Z dimension.

Example:

```text
Input shape: (85, 3840, 3840)
Input dtype: float32
```

---

## Maximum-intensity projection calculation

The projection is calculated as:

```python
projection = np.max(image, axis=0)
```

For each output coordinate:

```text
projection[Y, X]
```

the value is:

```text
max(
    image[0, Y, X],
    image[1, Y, X],
    ...
    image[Z-1, Y, X]
)
```

No averaging, summation, normalization, thresholding, or contrast adjustment is performed.

---

## Output

### File

```text
/home/oltij/Desktop/BLUE_trimmed_padding_test_max_projection.tif
```

### File type

```text
TIFF
```

### Dimensionality

```text
2-D
(Y, X)
```

### Data type

The projection normally retains the input NumPy dtype because `numpy.max()` does not inherently convert the array type.

Examples:

```text
uint16 input -> uint16 projection
float32 input -> float32 projection
```

The script prints:

```text
Projection shape
Projection dtype
```

before writing.

---

## TIFF-writing settings

The output is written as:

```python
tifffile.imwrite(
    destination,
    projection,
    imagej=True,
    metadata={"axes": "YX"},
    compression="zlib"
)
```

### `imagej=True`

Writes the TIFF in an ImageJ-compatible form.

### `metadata={"axes": "YX"}`

Explicitly declares the image axes as:

```text
Y = rows / height
X = columns / width
```

This indicates that the output is a 2-D image rather than a Z-stack.

### `compression="zlib"`

The TIFF is losslessly compressed using zlib.

Compression changes file size but not pixel values.

---

## Example input and output

Example input:

```text
BLUE_trimmed_padding_test_fused.tif

shape:
(85, 3840, 3840)

dtype:
float32
```

After projection:

```text
BLUE_trimmed_padding_test_max_projection.tif

shape:
(3840, 3840)

dtype:
float32
```

---

## Expected origin of the input

Based on the filename:

```text
BLUE_trimmed_padding_test_fused.tif
```

this input is expected to be a previously fused 3-D microscopy stack, such as a stitched/fused output from BigStitcher or another mosaic-fusion step.

The script itself does not care how the stack was generated, provided that:

1. it is readable by `tifffile`;
2. the image is organized with Z on axis 0; and
3. a projection across axis 0 is scientifically appropriate.

---

## Expected use of the output

The 2-D maximum projection can be used for downstream tasks such as:

```text
CellProfiler segmentation
2-D cross-channel registration
ROI visualization
colocalization analysis
publication/QC figures
```

provided that the downstream analysis is intended to operate on maximum projections rather than the original 3-D volume.

---

## Complete example script

```python
import tifffile
import numpy as np

source = "/home/oltij/Desktop/BLUE_trimmed_padding_test_fused.tif"
destination = "/home/oltij/Desktop/BLUE_trimmed_padding_test_max_projection.tif"

image = tifffile.imread(source)
print(f"Input shape: {image.shape}")
print(f"Input dtype: {image.dtype}")

projection = np.max(image, axis=0)

print(f"Projection shape: {projection.shape}")
print(f"Projection dtype: {projection.dtype}")

tifffile.imwrite(
    destination,
    projection,
    imagej=True,
    metadata={"axes": "YX"},
    compression="zlib"
)

print(f"Saved: {destination}")
```

---

## Running the script

If saved as:

```text
max_project_tiff.py
```

run:

```bash
python max_project_tiff.py
```

There are no command-line arguments in the current implementation.

To process another image, edit:

```python
source = "..."
destination = "..."
```

before running.

---

## Output confirmation

On success, the script prints something similar to:

```text
Input shape: (85, 3840, 3840)
Input dtype: float32
Projection shape: (3840, 3840)
Projection dtype: float32
Saved: /home/oltij/Desktop/BLUE_trimmed_padding_test_max_projection.tif
```

---

## Important assumptions and limitations

1. **Axis 0 must represent Z.** The script does not inspect TIFF axis metadata before projecting.
2. The entire TIFF is loaded into RAM with `tifffile.imread()`.
3. The source is expected to contain at least one axis to reduce.
4. No automatic dimensionality check is performed before calling `np.max()`.
5. No physical pixel-size metadata is explicitly copied from the input TIFF.
6. The output records only `YX` axis metadata through `tifffile`.
7. No intensity normalization is performed.
8. No background subtraction is performed.
9. No clipping or dtype conversion is performed.
10. The output is a maximum-intensity projection, not an average- or sum-intensity projection.

---

## Data flow

```text
3-D fused TIFF
(Z, Y, X)
    |
    | np.max(axis=0)
    v
2-D maximum-intensity projection
(Y, X)
    |
    v
ImageJ-compatible zlib-compressed TIFF
```
