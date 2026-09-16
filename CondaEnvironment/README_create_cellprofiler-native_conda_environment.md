# Creating the `cellprofiler-native` Conda Environment

This README explains how to recreate the Conda environment described by the provided YAML file.

The environment is named:

```text
cellprofiler-native
```

and the YAML specifies the installation prefix:

```text
/home/oltij/miniconda3/envs/cellprofiler-native
```

This environment contains CellProfiler and its native GUI/headless dependencies, including:

```text
CellProfiler 4.2.8
cellprofiler-core 4.2.8
wxPython
python-bioformats
python-javabridge
NumPy
SciPy
scikit-image
scikit-learn
matplotlib
tifffile
h5py
```

---

## 1. Save the YAML file

A convenient location is:

```text
/home/oltij/Desktop/ImageAnalysisScripts/CondaEnvironment/
```

Create the directory if needed:

```bash
mkdir -p /home/oltij/Desktop/ImageAnalysisScripts/CondaEnvironment
```

Save the environment definition as:

```text
/home/oltij/Desktop/ImageAnalysisScripts/CondaEnvironment/cellprofiler-native.yml
```

For example:

```bash
nano /home/oltij/Desktop/ImageAnalysisScripts/CondaEnvironment/cellprofiler-native.yml
```

Paste the complete YAML contents into the file, then save with:

```text
Ctrl+O
Enter
Ctrl+X
```

---

## 2. Make sure Conda is available

Check:

```bash
conda --version
```

You can also inspect the currently installed environments with:

```bash
conda env list
```

---

## 3. Create the environment

Run:

```bash
conda env create \
    -f /home/oltij/Desktop/ImageAnalysisScripts/CondaEnvironment/cellprofiler-native.yml
```

Because the YAML contains:

```yaml
name: cellprofiler-native
```

and:

```yaml
prefix: /home/oltij/miniconda3/envs/cellprofiler-native
```

the resulting environment is intended to live at:

```text
/home/oltij/miniconda3/envs/cellprofiler-native
```

---

## 4. Activate the environment

After creation finishes:

```bash
conda activate cellprofiler-native
```

Your shell prompt should change to something similar to:

```text
(cellprofiler-native) [oltij@gl1000 ~]$
```

---

## 5. Verify that the environment exists

Run:

```bash
conda env list
```

You should see an entry similar to:

```text
cellprofiler-native    /home/oltij/miniconda3/envs/cellprofiler-native
```

---

## 6. Verify Python

Run:

```bash
python --version
```

The provided YAML specifies:

```text
Python 3.9.25
```

You can also check the Python executable:

```bash
which python
```

Expected path:

```text
/home/oltij/miniconda3/envs/cellprofiler-native/bin/python
```

---

## 7. Verify CellProfiler

Check that the command-line executable is available:

```bash
which cellprofiler
```

Expected location should be inside:

```text
/home/oltij/miniconda3/envs/cellprofiler-native/
```

Then check the installed version:

```bash
cellprofiler --version
```

The YAML specifies:

```text
CellProfiler 4.2.8
```

---

## 8. Verify important Python packages

Run:

```bash
python - <<'PY'
import cellprofiler
import cellprofiler_core
import numpy
import scipy
import skimage
import sklearn
import matplotlib
import tifffile
import h5py

print("CellProfiler:", cellprofiler.__version__)
print("NumPy:", numpy.__version__)
print("SciPy:", scipy.__version__)
print("scikit-image:", skimage.__version__)
print("scikit-learn:", sklearn.__version__)
print("matplotlib:", matplotlib.__version__)
print("tifffile:", tifffile.__version__)
print("h5py:", h5py.__version__)

print("All major cellprofiler-native imports succeeded.")
PY
```

---

## 9. Verify Java/Bio-Formats support

CellProfiler uses Java-backed Bio-Formats components through:

```text
python-bioformats
python-javabridge
```

Test the imports:

```bash
python - <<'PY'
import bioformats
import javabridge

print("python-bioformats import succeeded.")
print("python-javabridge import succeeded.")
PY
```

---

## 10. Run CellProfiler through the GUI

The GUI workflow uses:

```text
MGEOPV.cpproj
```

First activate the environment:

```bash
conda activate cellprofiler-native
```

Then launch CellProfiler:

```bash
cellprofiler
```

Load:

```text
MGEOPV.cpproj
```

This option is useful when you want to inspect segmentation interactively or adjust pipeline parameters.

---

## 11. Run CellProfiler headlessly

The headless workflow uses:

```text
MGEOPVFinal.cppipe
```

with the CellProfiler driver script.

Example:

```bash
conda activate cellprofiler-native

python /home/oltij/Desktop/cellprofilerdriver.py \
    --pipeline "/home/oltij/Desktop/MGEOPVFinal.cppipe" \
    --input "/path/to/input_image.tif" \
    --output "/path/to/CellProfiler_output"
```

---

## 12. Switching from `ims-mosaic` to `cellprofiler-native`

The main microscopy-analysis workflow commonly runs in:

```text
ims-mosaic
```

CellProfiler should be run in:

```text
cellprofiler-native
```

If you are currently in:

```text
(ims-mosaic)
```

switch with:

```bash
conda deactivate
conda activate cellprofiler-native
```

Your prompt should then show:

```text
(cellprofiler-native)
```

Run the CellProfiler stage.

---

## 13. Switch back to `ims-mosaic` afterward

When CellProfiler is finished:

```bash
conda deactivate
conda activate ims-mosaic
```

Your prompt should again show:

```text
(ims-mosaic)
```

Conceptually:

```text
ims-mosaic
    |
    | before CellProfiler
    v
cellprofiler-native
    |
    | run GUI or headless CellProfiler
    v
ims-mosaic
```

This environment switch is needed each time the larger analysis pipeline enters or leaves a CellProfiler stage.

---

## 14. If `cellprofiler-native` already exists

Check:

```bash
conda env list
```

If you intentionally want to rebuild it from the YAML:

```bash
conda deactivate
```

Then remove the existing environment:

```bash
conda env remove -n cellprofiler-native
```

Recreate it:

```bash
conda env create \
    -f /home/oltij/Desktop/ImageAnalysisScripts/CondaEnvironment/cellprofiler-native.yml
```

Then activate it:

```bash
conda activate cellprofiler-native
```

Only remove the existing environment if you actually intend to rebuild it.

---

## 15. Short version

If the YAML is already saved as:

```text
/home/oltij/Desktop/ImageAnalysisScripts/CondaEnvironment/cellprofiler-native.yml
```

run:

```bash
cd /home/oltij/Desktop/ImageAnalysisScripts/CondaEnvironment

conda env create -f cellprofiler-native.yml

conda activate cellprofiler-native

python --version

cellprofiler --version

conda env list
```

---

## 16. Expected environment

After successful creation:

```text
Environment name:
cellprofiler-native

Environment path:
/home/oltij/miniconda3/envs/cellprofiler-native

Python:
3.9.25

CellProfiler:
4.2.8
```

---

## 17. Deactivate when finished

To leave the environment:

```bash
conda deactivate
```

To use it again later:

```bash
conda activate cellprofiler-native
```

For the larger image-analysis workflow, normally return to:

```bash
conda activate ims-mosaic
```

after completing the CellProfiler stage.
