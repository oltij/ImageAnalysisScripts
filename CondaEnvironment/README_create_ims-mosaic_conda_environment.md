# Creating the `ims-mosaic` Conda Environment

This README explains how to recreate the Conda environment described by the provided YAML file.

The environment is named:

```text
ims-mosaic
```

and the YAML specifies the installation prefix:

```text
/home/oltij/miniconda3/envs/ims-mosaic
```

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
/home/oltij/Desktop/ImageAnalysisScripts/CondaEnvironment/ims-mosaic.yml
```

For example:

```bash
nano /home/oltij/Desktop/ImageAnalysisScripts/CondaEnvironment/ims-mosaic.yml
```

Paste the complete YAML contents into the file, then save with:

```text
Ctrl+O
Enter
Ctrl+X
```

## 2. Make sure Conda is available

Check:

```bash
conda --version
```

You can also check existing environments with:

```bash
conda env list
```

## 3. Create the environment

Run:

```bash
conda env create \
    -f /home/oltij/Desktop/ImageAnalysisScripts/CondaEnvironment/ims-mosaic.yml
```

Because the YAML contains:

```yaml
name: ims-mosaic
```

and:

```yaml
prefix: /home/oltij/miniconda3/envs/ims-mosaic
```

the environment is intended to be created at:

```text
/home/oltij/miniconda3/envs/ims-mosaic
```

## 4. Activate the environment

After creation finishes:

```bash
conda activate ims-mosaic
```

Your prompt should change to something similar to:

```text
(ims-mosaic) [oltij@gl1000 ~]$
```

## 5. Verify the environment

Run:

```bash
conda env list
```

You should see an entry similar to:

```text
ims-mosaic    /home/oltij/miniconda3/envs/ims-mosaic
```

Check Python:

```bash
python --version
```

The YAML specifies Python 3.11.

Check the executable:

```bash
which python
```

Expected:

```text
/home/oltij/miniconda3/envs/ims-mosaic/bin/python
```

## 6. Verify important packages

Run:

```bash
python - <<'PY'
import numpy
import pandas
import scipy
import tifffile
import h5py
import hdf5plugin
import matplotlib
import skimage
import basicpy
import castalign

print("numpy:", numpy.__version__)
print("pandas:", pandas.__version__)
print("scipy:", scipy.__version__)
print("tifffile:", tifffile.__version__)
print("h5py:", h5py.__version__)
print("matplotlib:", matplotlib.__version__)
print("scikit-image:", skimage.__version__)

print("All major ims-mosaic imports succeeded.")
PY
```

## 7. Verify BaSiCPy

```bash
python - <<'PY'
from basicpy import BaSiC
print("BaSiCPy import succeeded.")
PY
```

## 8. Verify CASTalign

```bash
python - <<'PY'
import castalign
print("CASTalign import succeeded.")
PY
```

## 9. If `ims-mosaic` already exists

Inspect existing environments:

```bash
conda env list
```

If you intentionally want to rebuild the environment from scratch:

```bash
conda deactivate
```

then:

```bash
conda env remove -n ims-mosaic
```

and recreate it:

```bash
conda env create \
    -f /home/oltij/Desktop/ImageAnalysisScripts/CondaEnvironment/ims-mosaic.yml
```

Then reactivate:

```bash
conda activate ims-mosaic
```

Only remove the existing environment if you actually intend to rebuild it.

## 10. Short version

If the YAML is already saved at:

```text
/home/oltij/Desktop/ImageAnalysisScripts/CondaEnvironment/ims-mosaic.yml
```

run:

```bash
cd /home/oltij/Desktop/ImageAnalysisScripts/CondaEnvironment

conda env create -f ims-mosaic.yml

conda activate ims-mosaic

python --version

conda env list
```

## 11. Deactivate when finished

```bash
conda deactivate
```

To use it again later:

```bash
conda activate ims-mosaic
```
