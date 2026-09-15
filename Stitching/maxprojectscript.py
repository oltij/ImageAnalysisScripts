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
PY
