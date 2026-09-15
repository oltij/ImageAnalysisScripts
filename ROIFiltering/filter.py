#!/usr/bin/env python3

import math
from pathlib import Path

import numpy as np
import pandas as pd
import tifffile
from scipy.spatial import ConvexHull, QhullError


# ============================================================
# USER SETTINGS
# ============================================================

output_dir = Path("/home/oltij/Desktop/ROI_finalmetric_filtering")
output_dir.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# ADD AS MANY CHANNELS AS YOU WANT
# ------------------------------------------------------------
# Each channel needs:
#   name     = name shown in output files
#   roi_csv  = ROI-pixel CSV
#   original = original fluorescence TIFF used for intensity
# ------------------------------------------------------------

channels = [
    {
        "name": "PV",
        "roi_csv": (
            "/home/oltij/Desktop/PVAligned/ROI_analysis/PV_ROI_pixels.csv"
        ),
        "original": (
            "/home/oltij/Desktop/PVAligned/aligned_PV_max.tif"
        ),
    }
]


# ============================================================
# PIXEL SIZE
# ============================================================

PIXEL_SIZE_X_UM = 0.312843137
PIXEL_SIZE_Y_UM = 0.312836345


# ============================================================
# FILTER SETTINGS
# ============================================================
#
# percentile = 0  -> filter OFF, keep everything for that metric
#
# Examples:
#   10 + "above" -> keep metric >= 10th-percentile cutoff
#   95 + "below" -> keep metric <= 95th-percentile cutoff
#
# All percentile cutoffs are calculated from ALL valid ROIs in
# the channel before filtering.
#
# Enabled filters are combined with AND logic.
# ============================================================

FILTERS = {
    # Intensity
    "Mean intensity":        {"percentile": 0, "keep": "above"},
    "Median intensity":      {"percentile": 0, "keep": "above"},
    "Maximum intensity":     {"percentile": 0, "keep": "above"},
    "Integrated intensity":  {"percentile": 0, "keep": "above"},
    "Intensity SD":          {"percentile": 0, "keep": "above"},

    # Shape
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


# ============================================================
# HELPERS
# ============================================================

def find_id_column(df, channel_name):
    if "ROI" in df.columns:
        return "ROI"
    if "CellID" in df.columns:
        return "CellID"
    raise ValueError(
        f"{channel_name} ROI CSV must contain either 'ROI' or 'CellID'. "
        f"Found columns: {list(df.columns)}"
    )


def load_roi_pixels(csv_path, channel_name):
    print(f"\nLoading {channel_name} ROI pixels...")
    df = pd.read_csv(csv_path)

    id_column = find_id_column(df, channel_name)
    required = {id_column, "X", "Y"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"{channel_name} ROI CSV is missing required columns: {missing}"
        )

    df = df.copy()
    df["ObjectID"] = pd.to_numeric(df[id_column], errors="raise").astype(int)
    df["X"] = pd.to_numeric(df["X"], errors="raise").astype(int)
    df["Y"] = pd.to_numeric(df["Y"], errors="raise").astype(int)

    df = df.drop_duplicates(subset=["ObjectID", "X", "Y"]).copy()

    if len(df) == 0:
        raise ValueError(f"{channel_name} ROI CSV contains no ROI pixels.")

    print(f"ROI pixel rows: {len(df):,}")
    print(f"Objects: {df['ObjectID'].nunique():,}")
    return df, id_column


def load_original_tiff(tiff_path, channel_name):
    print(f"Loading {channel_name} original TIFF...")
    image = np.squeeze(tifffile.imread(tiff_path))

    if image.ndim != 2:
        raise ValueError(
            f"{channel_name} TIFF is not 2D after squeezing. "
            f"Got shape {image.shape}."
        )

    print(f"Image shape: {image.shape}")
    print(f"Image dtype: {image.dtype}")
    return image


def validate_roi_coordinates(df, image, channel_name):
    height, width = image.shape

    bad_x = (df["X"] < 0) | (df["X"] >= width)
    bad_y = (df["Y"] < 0) | (df["Y"] >= height)

    if bad_x.any() or bad_y.any():
        bad = df[bad_x | bad_y]
        raise ValueError(
            f"{channel_name} has {len(bad):,} ROI pixels outside TIFF bounds. "
            f"Image is {width} x {height}."
        )


# ============================================================
# SHAPE CALCULATION HELPERS
# ============================================================

def make_local_mask(xs, ys):
    min_x, max_x = int(xs.min()), int(xs.max())
    min_y, max_y = int(ys.min()), int(ys.max())

    mask = np.zeros(
        (max_y - min_y + 1, max_x - min_x + 1),
        dtype=bool,
    )
    mask[ys - min_y, xs - min_x] = True
    return mask


def anisotropic_perimeter(mask):
    up = np.zeros_like(mask)
    up[1:, :] = mask[:-1, :]

    down = np.zeros_like(mask)
    down[:-1, :] = mask[1:, :]

    left = np.zeros_like(mask)
    left[:, 1:] = mask[:, :-1]

    right = np.zeros_like(mask)
    right[:, :-1] = mask[:, 1:]

    horizontal_edges = int(
        (mask & ~up).sum() + (mask & ~down).sum()
    )
    vertical_edges = int(
        (mask & ~left).sum() + (mask & ~right).sum()
    )

    return float(
        horizontal_edges * PIXEL_SIZE_X_UM
        + vertical_edges * PIXEL_SIZE_Y_UM
    )


def convex_hull_area_um2(xs, ys):
    if len(xs) < 3:
        return np.nan

    points_um = np.column_stack([
        xs.astype(float) * PIXEL_SIZE_X_UM,
        ys.astype(float) * PIXEL_SIZE_Y_UM,
    ])

    try:
        hull = ConvexHull(points_um)
        return float(hull.volume)  # 2-D area
    except QhullError:
        return np.nan


def second_moment_shape_metrics(xs, ys):
    if len(xs) < 2:
        return np.nan, np.nan, np.nan, np.nan

    points_um = np.column_stack([
        xs.astype(float) * PIXEL_SIZE_X_UM,
        ys.astype(float) * PIXEL_SIZE_Y_UM,
    ])

    centered = points_um - points_um.mean(axis=0, keepdims=True)
    covariance = (centered.T @ centered) / len(centered)
    eigenvalues = np.clip(np.linalg.eigvalsh(covariance), 0, None)

    lambda_minor = float(eigenvalues[0])
    lambda_major = float(eigenvalues[1])

    if lambda_major <= 0:
        return 0.0, 0.0, 0.0, np.nan

    eccentricity = math.sqrt(
        max(0.0, 1.0 - lambda_minor / lambda_major)
    )

    major_axis_um = 4.0 * math.sqrt(lambda_major)
    minor_axis_um = 4.0 * math.sqrt(lambda_minor)
    aspect_ratio = (
        major_axis_um / minor_axis_um
        if minor_axis_um > 0
        else np.nan
    )

    return (
        float(eccentricity),
        float(major_axis_um),
        float(minor_axis_um),
        float(aspect_ratio),
    )


# ============================================================
# ROI MEASUREMENTS
# ============================================================

def calculate_roi_measurements(object_pixels_df, image):
    xs = object_pixels_df["X"].to_numpy(dtype=int)
    ys = object_pixels_df["Y"].to_numpy(dtype=int)
    values = image[ys, xs].astype(np.float64)

    # Intensity
    mean_intensity = float(np.mean(values))
    median_intensity = float(np.median(values))
    maximum_intensity = float(np.max(values))
    integrated_intensity = float(np.sum(values))
    intensity_sd = float(np.std(values))

    # Area
    area_px = int(len(xs))
    area_um2 = (
        area_px
        * PIXEL_SIZE_X_UM
        * PIXEL_SIZE_Y_UM
    )

    # Bounding box / extent
    min_x, max_x = int(xs.min()), int(xs.max())
    min_y, max_y = int(ys.min()), int(ys.max())

    bbox_width_px = max_x - min_x + 1
    bbox_height_px = max_y - min_y + 1
    bbox_area_px = bbox_width_px * bbox_height_px

    extent = (
        area_px / bbox_area_px
        if bbox_area_px > 0
        else np.nan
    )

    # Perimeter
    local_mask = make_local_mask(xs, ys)
    perimeter_um = anisotropic_perimeter(local_mask)

    # Convex hull / solidity
    convex_area_um2 = convex_hull_area_um2(xs, ys)

    if np.isfinite(convex_area_um2) and convex_area_um2 > 0:
        solidity = area_um2 / convex_area_um2
    else:
        solidity = 1.0 if area_px > 0 else np.nan

    # Circularity
    circularity = (
        4.0 * math.pi * area_um2 / (perimeter_um ** 2)
        if perimeter_um > 0
        else np.nan
    )

    # Eccentricity / axes
    (
        eccentricity,
        major_axis_um,
        minor_axis_um,
        aspect_ratio,
    ) = second_moment_shape_metrics(xs, ys)

    # Equivalent diameter
    equivalent_diameter_um = (
        math.sqrt(4.0 * area_um2 / math.pi)
        if area_um2 > 0
        else np.nan
    )

    return {
        "Mean intensity": mean_intensity,
        "Median intensity": median_intensity,
        "Maximum intensity": maximum_intensity,
        "Integrated intensity": integrated_intensity,
        "Intensity SD": intensity_sd,
        "Area_px": area_px,
        "Area_um2": float(area_um2),
        "Perimeter_um": perimeter_um,
        "Solidity": float(solidity),
        "Eccentricity": eccentricity,
        "Circularity": float(circularity),
        "ConvexHullArea_um2": (
            float(convex_area_um2)
            if np.isfinite(convex_area_um2)
            else np.nan
        ),
        "MajorAxisLength_um": major_axis_um,
        "MinorAxisLength_um": minor_axis_um,
        "AspectRatio": aspect_ratio,
        "EquivalentDiameter_um": float(equivalent_diameter_um),
        "Extent": float(extent),
        "ROI pixel count": area_px,
    }


# ============================================================
# FILTERING
# ============================================================

def validate_filter_settings():
    for metric_name, settings in FILTERS.items():
        percentile = settings["percentile"]
        keep = settings["keep"]

        if not (0 <= percentile <= 100):
            raise ValueError(
                f"{metric_name}: percentile must be between 0 and 100. "
                f"Got {percentile}."
            )

        if keep not in {"above", "below"}:
            raise ValueError(
                f"{metric_name}: keep must be 'above' or 'below'. "
                f"Got {keep!r}."
            )


def apply_filters(measurements_df):
    audit = measurements_df.copy()
    audit["PASS_ALL_FILTERS"] = True

    cutoff_rows = []
    enabled_count = 0

    print("\nApplying percentile filters...")

    for metric_name, settings in FILTERS.items():
        percentile = float(settings["percentile"])
        keep = settings["keep"]

        pass_col = f"PASS_{metric_name}"

        if percentile == 0:
            print(f"{metric_name}: OFF (percentile = 0)")
            audit[pass_col] = True

            cutoff_rows.append({
                "Metric": metric_name,
                "Percentile": 0,
                "Keep": keep,
                "CutoffValue": np.nan,
                "Enabled": False,
            })
            continue

        enabled_count += 1

        values = pd.to_numeric(
            measurements_df[metric_name],
            errors="coerce",
        )

        finite_mask = np.isfinite(values)
        finite_values = values[finite_mask]

        if len(finite_values) == 0:
            raise ValueError(
                f"No valid values found for metric: {metric_name}"
            )

        cutoff = float(
            np.percentile(finite_values, percentile)
        )

        if keep == "above":
            pass_mask = (values >= cutoff) & finite_mask
            rule_text = f">= {cutoff:.6g}"
        else:
            pass_mask = (values <= cutoff) & finite_mask
            rule_text = f"<= {cutoff:.6g}"

        audit[pass_col] = pass_mask
        audit["PASS_ALL_FILTERS"] &= pass_mask

        n_pass = int(pass_mask.sum())
        n_total = len(audit)

        print(
            f"{metric_name}: {percentile:g}th percentile "
            f"cutoff = {cutoff:.6g}; keep {keep} "
            f"({rule_text}); {n_pass:,}/{n_total:,} pass"
        )

        cutoff_rows.append({
            "Metric": metric_name,
            "Percentile": percentile,
            "Keep": keep,
            "CutoffValue": cutoff,
            "Enabled": True,
        })

    if enabled_count == 0:
        print("\nNo filters were enabled. All ROIs will be retained.")

    filtered_measurements = (
        audit[audit["PASS_ALL_FILTERS"]]
        .copy()
        .reset_index(drop=True)
    )

    cutoff_table = pd.DataFrame(cutoff_rows)

    return filtered_measurements, audit, cutoff_table


# ============================================================
# MAIN
# ============================================================

validate_filter_settings()

print("\n" + "=" * 70)
print(f"Found {len(channels)} channel(s) to process.")
print("=" * 70)

for i, channel in enumerate(channels, start=1):
    print(f"{i}. {channel['name']}")


for channel_number, channel_info in enumerate(channels, start=1):
    channel_name = channel_info["name"]
    roi_csv = Path(channel_info["roi_csv"])
    original_tiff = Path(channel_info["original"])

    print("\n" + "#" * 70)
    print(
        f"CHANNEL {channel_number}/{len(channels)}: {channel_name}"
    )
    print("#" * 70)

    roi_df, original_id_column = load_roi_pixels(
        roi_csv,
        channel_name,
    )

    image = load_original_tiff(
        original_tiff,
        channel_name,
    )

    validate_roi_coordinates(
        roi_df,
        image,
        channel_name,
    )

    print(
        "\nCalculating intensity and shape metrics "
        "directly from ROI pixels..."
    )

    measurement_rows = []

    for object_id, object_pixels_df in roi_df.groupby(
        "ObjectID",
        sort=True,
    ):
        measurements = calculate_roi_measurements(
            object_pixels_df,
            image,
        )

        row = {
            "Channel": channel_name,
            "ObjectID": int(object_id),
            **measurements,
            "Center_X": float(object_pixels_df["X"].mean()),
            "Center_Y": float(object_pixels_df["Y"].mean()),
            "BoundingBoxMinimum_X": int(object_pixels_df["X"].min()),
            "BoundingBoxMaximum_X": int(object_pixels_df["X"].max()),
            "BoundingBoxMinimum_Y": int(object_pixels_df["Y"].min()),
            "BoundingBoxMaximum_Y": int(object_pixels_df["Y"].max()),
        }

        measurement_rows.append(row)

    measurements_df = pd.DataFrame(measurement_rows)

    print(
        f"Calculated measurements for "
        f"{len(measurements_df):,} objects."
    )

    (
        filtered_measurements,
        audit_table,
        cutoff_table,
    ) = apply_filters(measurements_df)

    kept_ids = set(
        filtered_measurements["ObjectID"]
        .astype(int)
        .tolist()
    )

    filtered_roi_df = (
        roi_df[
            roi_df["ObjectID"].isin(kept_ids)
        ]
        .copy()
    )

    # Preserve the source ID convention and output only ROI pixels.
    if original_id_column not in filtered_roi_df.columns:
        filtered_roi_df[original_id_column] = filtered_roi_df["ObjectID"]

    filtered_roi_export = filtered_roi_df[
        [original_id_column, "X", "Y"]
    ].copy()

    channel_output_dir = output_dir / channel_name
    channel_output_dir.mkdir(parents=True, exist_ok=True)

    filtered_roi_csv = (
        channel_output_dir
        / f"{channel_name}_ROI_pixels_FILTERED.csv"
    )

    all_measurements_csv = (
        channel_output_dir
        / f"{channel_name}_all_ROI_metrics_and_filter_status.csv"
    )

    kept_measurements_csv = (
        channel_output_dir
        / f"{channel_name}_kept_ROI_metrics.csv"
    )

    cutoff_csv = (
        channel_output_dir
        / f"{channel_name}_filter_cutoffs.csv"
    )

    removed_ids_csv = (
        channel_output_dir
        / f"{channel_name}_removed_ObjectIDs.csv"
    )

    kept_ids_csv = (
        channel_output_dir
        / f"{channel_name}_kept_ObjectIDs.csv"
    )

    filtered_roi_export.to_csv(
        filtered_roi_csv,
        index=False,
    )

    audit_table.to_csv(
        all_measurements_csv,
        index=False,
    )

    filtered_measurements.to_csv(
        kept_measurements_csv,
        index=False,
    )

    cutoff_table.to_csv(
        cutoff_csv,
        index=False,
    )

    all_ids = set(
        measurements_df["ObjectID"]
        .astype(int)
        .tolist()
    )

    removed_ids = sorted(all_ids - kept_ids)
    kept_ids_sorted = sorted(kept_ids)

    pd.DataFrame({
        "ObjectID": removed_ids
    }).to_csv(
        removed_ids_csv,
        index=False,
    )

    pd.DataFrame({
        "ObjectID": kept_ids_sorted
    }).to_csv(
        kept_ids_csv,
        index=False,
    )

    n_before = len(measurements_df)
    n_after = len(filtered_measurements)
    n_removed = n_before - n_after

    percent_kept = (
        100.0 * n_after / n_before
        if n_before > 0
        else 0.0
    )

    print("\n" + "=" * 70)
    print(f"{channel_name} FILTERING SUMMARY")
    print("=" * 70)
    print(f"Objects before filtering: {n_before:,}")
    print(f"Objects kept:             {n_after:,}")
    print(f"Objects removed:          {n_removed:,}")
    print(f"Percent kept:             {percent_kept:.2f}%")
    print(
        f"Filtered ROI pixel rows:  "
        f"{len(filtered_roi_export):,}"
    )

    print("\nSaved:")
    print(f"  {filtered_roi_csv}")
    print(f"  {all_measurements_csv}")
    print(f"  {kept_measurements_csv}")
    print(f"  {cutoff_csv}")
    print(f"  {kept_ids_csv}")
    print(f"  {removed_ids_csv}")


print("\n" + "=" * 70)
print("DONE!")
print("=" * 70)

