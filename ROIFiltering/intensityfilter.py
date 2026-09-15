import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import numpy as np
import pandas as pd
import tifffile
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import ListedColormap
from matplotlib.patches import Rectangle


# ============================================================
# USER SETTINGS
# ============================================================

output_dir = Path("/home/oltij/Desktop/ROI_intensity_report")
output_dir.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# ADD AS MANY CHANNELS AS YOU WANT
# ------------------------------------------------------------
# Each channel needs:
#   name = name shown in the PDF/CSV
#   roi_csv = CSV containing one row per ROI pixel
#   original = original fluorescence TIFF
#
# The ROI CSV must contain:
#   ROI or CellID   -> object identifier
#   X               -> pixel X coordinate
#   Y               -> pixel Y coordinate
#
# The script uses the ROI pixel coordinates themselves as the
# segmentation. No CellProfiler segmentation overlay TIFF is used.
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
    },
    {
        "name": "Hoescht",
        "roi_csv": (
            "/home/oltij/Desktop/HoeschtAligned/ROI_analysis/Hoescht_ROI_pixels.csv"
        ),
        "original": (
            "/home/oltij/Desktop/HoeschtAligned/aligned_Hoechst_max.tif"
        ),
    },
    {
        "name": "LHX6",
        "roi_csv": (
            "/home/oltij/Desktop/LHX6Aligned/ROI_analysis/LHX6_ROI_pixels.csv"
        ),
        "original": (
            "/home/oltij/Desktop/LHX6Aligned/aligned_LHX6_max.tif"
        ),
    },
]


# ============================================================
# ANALYSIS SETTINGS
# ============================================================

# Percentile-bin width. 5% = 20 percentile divisions.
PERCENTILE_BIN_WIDTH = 5

# Maximum number of ROIs sampled from each percentile bin.
# A bin may contain fewer than this and then all available ROIs are used.
MAX_SAMPLE_PER_BIN = 5

# Reproducible random selection
RANDOM_SEED = 42

# Histogram bins
N_BINS = 50

# Extra pixels around ROI for crop visualization
CROP_PADDING = 15

# Intensity display percentiles for grayscale images
DISPLAY_LOW_PERCENTILE = 1
DISPLAY_HIGH_PERCENTILE = 99

# ROI visualization
ALL_ROI_COLOR = "yellow"
SELECTED_ROI_COLOR = "blue"
ROI_LINEWIDTH = 0.7
SELECTED_ROI_LINEWIDTH = 2.0

# Require the CSV to have at least this many objects so that each
# Each percentile bin may contain fewer than 5 ROIs; that is handled automatically.
N_PERCENTILE_BINS = int(round(100 / PERCENTILE_BIN_WIDTH))
if N_PERCENTILE_BINS <= 0 or 100 % PERCENTILE_BIN_WIDTH != 0:
    raise ValueError("PERCENTILE_BIN_WIDTH must divide evenly into 100.")

# With 20 bins and a maximum of 5 per bin, the usual maximum is 100
# selected ROIs per channel + metric. If fewer objects exist, bins
# naturally contain fewer ROIs and all available objects are used.
MAX_SELECTED_ROIS_PER_METRIC = N_PERCENTILE_BINS * MAX_SAMPLE_PER_BIN


# ============================================================
# OUTPUT FILES
# ============================================================

pdf_path = output_dir / "All_Channel_ROI_Intensity_Report.pdf"
csv_output_path = output_dir / "All_Channel_ROI_Intensity_Selected.csv"
all_measurements_csv = output_dir / "All_Channel_ROI_Intensity_AllObjects.csv"


# ============================================================
# INTENSITY METRICS
# ============================================================

# These are calculated directly from the fluorescence TIFF pixels
# belonging to each ROI.
INTENSITY_METRICS = {
    "Mean intensity": np.mean,
    "Median intensity": np.median,
    "Maximum intensity": np.max,
    "Integrated intensity": np.sum,
    "Intensity SD": np.std,
}


# ============================================================
# HELPERS
# ============================================================


def find_id_column(df, channel_name):
    """Find the ROI identifier column used by the pixel CSV."""
    if "ROI" in df.columns:
        return "ROI"
    if "CellID" in df.columns:
        return "CellID"
    raise ValueError(
        f"{channel_name} ROI CSV must contain either 'ROI' or 'CellID'. "
        f"Found columns: {list(df.columns)}"
    )


def load_roi_pixels(csv_path, channel_name):
    """Load and validate ROI pixel CSV."""
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
    return df


def load_original_tiff(tiff_path, channel_name):
    """Load a 2D fluorescence TIFF."""
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
    """Ensure ROI coordinates fall inside the image."""
    height, width = image.shape

    bad_x = (df["X"] < 0) | (df["X"] >= width)
    bad_y = (df["Y"] < 0) | (df["Y"] >= height)

    if bad_x.any() or bad_y.any():
        bad = df[bad_x | bad_y]
        raise ValueError(
            f"{channel_name} has {len(bad):,} ROI pixels outside the TIFF bounds. "
            f"Image is {width} x {height}."
        )


def make_roi_mask(roi_pixels, xmin, ymin, xmax, ymax):
    """Rasterize ROI pixel coordinates into a boolean crop mask."""
    crop_width = xmax - xmin
    crop_height = ymax - ymin
    mask = np.zeros((crop_height, crop_width), dtype=bool)

    local_x = roi_pixels[:, 0].astype(int) - xmin
    local_y = roi_pixels[:, 1].astype(int) - ymin

    valid = (
        (local_x >= 0)
        & (local_x < crop_width)
        & (local_y >= 0)
        & (local_y < crop_height)
    )

    mask[local_y[valid], local_x[valid]] = True
    return mask


def make_roi_outline(roi_pixels, crop_xmin, crop_ymin, crop_xmax, crop_ymax):
    """Create a one-pixel outline mask from ROI pixels."""
    mask = make_roi_mask(
        roi_pixels,
        crop_xmin,
        crop_ymin,
        crop_xmax,
        crop_ymax,
    )

    boundary = np.zeros_like(mask)

    boundary[1:, :] |= mask[1:, :] & ~mask[:-1, :]
    boundary[:-1, :] |= mask[:-1, :] & ~mask[1:, :]
    boundary[:, 1:] |= mask[:, 1:] & ~mask[:, :-1]
    boundary[:, :-1] |= mask[:, :-1] & ~mask[:, 1:]

    return boundary


def thicken_outline(outline):
    """Slightly thicken an outline for clearer PDF visualization."""
    if not outline.any():
        return outline

    padded = np.pad(outline, 1, mode="constant", constant_values=False)
    result = np.zeros_like(outline)

    for dy in range(3):
        for dx in range(3):
            result |= padded[dy : dy + outline.shape[0], dx : dx + outline.shape[1]]

    return result


def draw_outline(ax, outline, color, linewidth):
    """Draw an existing one-pixel raster outline."""
    if outline.any():
        ax.imshow(
            np.ma.masked_where(~outline, outline),
            cmap=ListedColormap([color]),
            alpha=0.95,
            interpolation="nearest",
        )


def draw_filled_mask_outline(ax, mask, color, linewidth):
    """Draw one clean outline around a filled ROI mask."""
    if mask.any():
        ax.contour(
            mask.astype(float),
            levels=[0.5],
            colors=color,
            linewidths=linewidth,
        )


def get_crop_for_object(roi_pixels, image_shape, padding):
    """Get a padded crop around one ROI."""
    image_height, image_width = image_shape

    xs = roi_pixels[:, 0]
    ys = roi_pixels[:, 1]

    xmin = max(0, int(xs.min()) - padding)
    xmax = min(image_width, int(xs.max()) + padding + 1)
    ymin = max(0, int(ys.min()) - padding)
    ymax = min(image_height, int(ys.max()) + padding + 1)

    return xmin, ymin, xmax, ymax


def show_image(ax, image, vmin, vmax):
    ax.imshow(image, cmap="gray", vmin=vmin, vmax=vmax)


def add_centroid_dot(ax, x, y):
    """Draw one small red dot at the ROI centroid."""
    ax.scatter(
        x,
        y,
        s=18,
        c="red",
        marker="o",
        linewidths=0,
        zorder=40,
    )


def calculate_roi_measurements(roi_pixels, image):
    """Calculate all requested intensity metrics from ROI pixels."""
    xs = roi_pixels["X"].to_numpy(dtype=int)
    ys = roi_pixels["Y"].to_numpy(dtype=int)
    values = image[ys, xs].astype(np.float64)

    return {
        "Mean intensity": float(np.mean(values)),
        "Median intensity": float(np.median(values)),
        "Maximum intensity": float(np.max(values)),
        "Integrated intensity": float(np.sum(values)),
        "Intensity SD": float(np.std(values)),
        "ROI pixel count": int(values.size),
    }


def create_object_pixel_groups(df):
    """Create ObjectID -> Nx2 X/Y pixel array lookup."""
    return {
        int(object_id): group[["X", "Y"]].to_numpy(dtype=int)
        for object_id, group in df.groupby("ObjectID", sort=True)
    }


def create_label_image(pixel_groups, image_shape):
    """Create one label image from ROI pixels; avoids one full-size mask per ROI."""
    label_image = np.zeros(image_shape, dtype=np.uint32)
    for object_id, pixels in pixel_groups.items():
        xs = pixels[:, 0]
        ys = pixels[:, 1]
        label_image[ys, xs] = int(object_id)
    return label_image


def make_boundary_from_labels(label_image):
    """Find boundaries between ROI pixels/background or different ROIs."""
    boundary = np.zeros(label_image.shape, dtype=bool)
    foreground = label_image != 0

    boundary[1:, :] |= foreground[1:, :] & (label_image[1:, :] != label_image[:-1, :])
    boundary[:-1, :] |= foreground[:-1, :] & (label_image[:-1, :] != label_image[1:, :])
    boundary[:, 1:] |= foreground[:, 1:] & (label_image[:, 1:] != label_image[:, :-1])
    boundary[:, :-1] |= foreground[:, :-1] & (label_image[:, :-1] != label_image[:, 1:])

    return boundary


def make_single_roi_outline_from_labels(label_image, object_id, xmin, ymin, xmax, ymax):
    """Get one ROI outline directly from a label-image crop."""
    crop = label_image[ymin:ymax, xmin:xmax]
    mask = crop == int(object_id)
    if not mask.any():
        return mask

    boundary = np.zeros_like(mask)
    boundary[1:, :] |= mask[1:, :] & ~mask[:-1, :]
    boundary[:-1, :] |= mask[:-1, :] & ~mask[1:, :]
    boundary[:, 1:] |= mask[:, 1:] & ~mask[:, :-1]
    boundary[:, :-1] |= mask[:, :-1] & ~mask[:, 1:]
    return boundary


# ============================================================
# CHECK SETTINGS
# ============================================================

if not channels:
    raise ValueError("No channels have been specified.")

print("\n" + "=" * 70)
print(f"Found {len(channels)} channel(s) to process.")
print("=" * 70)
for i, channel in enumerate(channels, start=1):
    print(f"{i}. {channel['name']}")


# ============================================================
# MAIN PROCESSING
# ============================================================

all_selected = []
all_measurements = []

print("\nCreating single multipage PDF...")

with PdfPages(pdf_path) as pdf:

    for channel_number, channel_info in enumerate(channels, start=1):
        channel_name = channel_info["name"]
        roi_csv = channel_info["roi_csv"]
        original_tiff = channel_info["original"]

        channel_output_dir = output_dir / channel_name
        channel_output_dir.mkdir(parents=True, exist_ok=True)

        print("\n" + "#" * 70)
        print(f"CHANNEL {channel_number}/{len(channels)}: {channel_name}")
        print("#" * 70)

        # --------------------------------------------------------
        # LOAD INPUTS
        # --------------------------------------------------------
        roi_df = load_roi_pixels(roi_csv, channel_name)
        image = load_original_tiff(original_tiff, channel_name)
        validate_roi_coordinates(roi_df, image, channel_name)

        image_height, image_width = image.shape
        pixel_groups = create_object_pixel_groups(roi_df)

        # Build ONE full-image label map and ONE full-image boundary map.
        # This replaces thousands of repeated 3840x3840 mask allocations.
        print("Preparing efficient ROI boundary map...")
        label_image = create_label_image(pixel_groups, image.shape)
        all_roi_outline = make_boundary_from_labels(label_image)
        print(f"ROI boundary pixels: {int(all_roi_outline.sum()):,}")

        vmin = np.percentile(image, DISPLAY_LOW_PERCENTILE)
        vmax = np.percentile(image, DISPLAY_HIGH_PERCENTILE)

        # --------------------------------------------------------
        # CALCULATE INTENSITY FROM ROI PIXELS
        # --------------------------------------------------------
        measurement_rows = []

        print("\nCalculating intensity directly from ROI pixels...")

        for object_id, object_pixels_df in roi_df.groupby("ObjectID", sort=True):
            measurements = calculate_roi_measurements(object_pixels_df, image)

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
        all_measurements.append(measurements_df)

        print(f"Calculated measurements for {len(measurements_df):,} objects.")

        if len(measurements_df) == 0:
            raise ValueError(
                f"{channel_name} contains no valid ROI objects."
            )

        # --------------------------------------------------------
        # PROCESS EACH METRIC
        # --------------------------------------------------------
        for metric_number, metric_name in enumerate(INTENSITY_METRICS, start=1):
            print("\n" + "-" * 70)
            print(f"{channel_name} | {metric_number}/{len(INTENSITY_METRICS)}: {metric_name}")
            print("-" * 70)

            # ----------------------------------------------------
            # METRIC-SPECIFIC OUTPUT FOLDER
            # ----------------------------------------------------
            metric_folder_name = metric_name.replace(" ", "_")
            metric_output_dir = channel_output_dir / metric_folder_name
            metric_output_dir.mkdir(parents=True, exist_ok=True)

            metric_pdf_path = metric_output_dir / (
                f"{channel_name}_{metric_folder_name}_report.pdf"
            )
            metric_selected_csv = metric_output_dir / (
                f"{channel_name}_{metric_folder_name}_selected_ROIs.csv"
            )
            metric_all_csv = metric_output_dir / (
                f"{channel_name}_{metric_folder_name}_all_ROIs.csv"
            )

            # One 2-page PDF for this channel + metric.
            metric_pdf = PdfPages(metric_pdf_path)

            temp = measurements_df.copy()
            temp[metric_name] = pd.to_numeric(temp[metric_name], errors="coerce")
            temp = temp.dropna(subset=[metric_name])
            temp = temp[temp[metric_name] >= 0].copy()

            values = temp[metric_name].to_numpy()

            if len(temp) == 0:
                print("No valid ROI values for this metric; skipping.")
                metric_pdf.close()
                continue

            # ----------------------------------------------------
            # 5% PERCENTILE BINS
            # ----------------------------------------------------
            # Use rank-based percentile bins so every ROI belongs to exactly
            # one bin and the bins are as evenly populated as possible.
            # This also behaves sensibly when there are fewer than 100 ROIs:
            # no bin can contribute more than MAX_SAMPLE_PER_BIN ROIs, and
            # bins with fewer available ROIs simply contribute fewer examples.
            sorted_temp = temp.sort_values(
                by=[metric_name, "ObjectID"],
                ascending=[True, True],
            ).reset_index(drop=True)

            percentile_bin_dfs = []

            for bin_index, bin_df in enumerate(
                np.array_split(sorted_temp, N_PERCENTILE_BINS)
            ):
                start_pct = bin_index * PERCENTILE_BIN_WIDTH
                end_pct = (bin_index + 1) * PERCENTILE_BIN_WIDTH
                bin_df = bin_df.copy()
                bin_df["PercentileBinIndex"] = bin_index
                bin_df["PercentileRange"] = (
                    f"{start_pct:g}–{end_pct:g}th percentile"
                )
                percentile_bin_dfs.append(bin_df)

            # Print bin sizes and randomly sample up to the requested maximum.
            rng = np.random.default_rng(RANDOM_SEED)
            selected_bins = []

            print(
                f"Using {N_PERCENTILE_BINS} percentile bins of "
                f"{PERCENTILE_BIN_WIDTH}% each."
            )

            for bin_index, bin_df in enumerate(percentile_bin_dfs):
                start_pct = bin_index * PERCENTILE_BIN_WIDTH
                end_pct = (bin_index + 1) * PERCENTILE_BIN_WIDTH

                n_available = len(bin_df)
                n_select = min(MAX_SAMPLE_PER_BIN, n_available)

                if n_select > 0:
                    selected_indices = rng.choice(
                        n_available,
                        size=n_select,
                        replace=False,
                    )
                    selected = (
                        bin_df.iloc[selected_indices]
                        .copy()
                        .reset_index(drop=True)
                    )
                else:
                    selected = bin_df.copy()

                selected["IntensityGroup"] = (
                    f"{start_pct:g}–{end_pct:g}th percentile"
                )
                selected["PercentileBinIndex"] = bin_index
                selected["PercentileRange"] = (
                    f"{start_pct:g}–{end_pct:g}th percentile"
                )
                selected["DisplayNumber"] = np.arange(1, len(selected) + 1)
                selected["Channel"] = channel_name
                selected["Metric"] = metric_name

                selected_bins.append(selected)

                print(
                    f"{start_pct:>3g}–{end_pct:<3g}%: "
                    f"{n_available:,} available; "
                    f"{n_select:,} selected"
                )

            selected_all = (
                pd.concat(selected_bins, ignore_index=True)
                if selected_bins
                else pd.DataFrame()
            )

            all_selected.append(selected_all.copy())

            print(
                f"Total selected for {channel_name} / {metric_name}: "
                f"{len(selected_all):,} / {MAX_SELECTED_ROIS_PER_METRIC:,} maximum"
            )

            if len(selected_all) > 0:
                print("\nSelected objects:")
                print(
                    selected_all[
                        [
                            "IntensityGroup",
                            "DisplayNumber",
                            "ObjectID",
                            metric_name,
                            "Center_X",
                            "Center_Y",
                        ]
                    ].to_string(index=False)
                )

            # ====================================================
            # HISTOGRAM + PERCENTILE BOUNDARIES
            # ====================================================
            percentile_values = [
                np.percentile(values, pct)
                for pct in range(PERCENTILE_BIN_WIDTH, 100, PERCENTILE_BIN_WIDTH)
            ]

            fig = plt.figure(figsize=(18, 10))
            ax_hist = fig.add_subplot(1, 1, 1)

            ax_hist.hist(
                values,
                bins=N_BINS,
                edgecolor="black",
                alpha=0.75,
            )

            # Delineate every 5% percentile boundary, but do not label them.
            for boundary in percentile_values:
                ax_hist.axvline(
                    boundary,
                    color="red",
                    linewidth=1.0,
                    alpha=0.65,
                )

            ax_hist.set_xlabel(metric_name, fontsize=13)
            ax_hist.set_ylabel("Number of ROIs", fontsize=13)
            ax_hist.set_title(
                f"{channel_name} — {metric_name} distribution "
                f"(n={len(values):,} ROIs)\n"
                f"Red lines = 5% percentile boundaries",
                fontsize=16,
                fontweight="bold",
            )

            fig.suptitle(
                f"{channel_name} — {metric_name} — Percentile Distribution",
                fontsize=18,
                fontweight="bold",
                y=0.995,
            )
            fig.tight_layout(rect=[0, 0, 1, 0.95])
            metric_pdf.savefig(fig, bbox_inches="tight")
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)

            # ====================================================
            # WHOLE-ORGANOID PERCENTILE PANELS
            # ====================================================
            # Twenty percentile bins are displayed as four panels per page.
            # Each panel identifies its percentile range and shows up to five
            # selected ROIs from that bin.
            for page_start in range(0, N_PERCENTILE_BINS, 4):
                page_bins = list(
                    range(
                        page_start,
                        min(page_start + 4, N_PERCENTILE_BINS),
                    )
                )

                fig_whole = plt.figure(figsize=(18, 22))
                whole_gs = fig_whole.add_gridspec(2, 2, hspace=0.20, wspace=0.08)

                for panel_pos, bin_index in enumerate(page_bins):
                    ax = fig_whole.add_subplot(whole_gs[panel_pos // 2, panel_pos % 2])

                    show_image(ax, image, vmin, vmax)

                    start_pct = bin_index * PERCENTILE_BIN_WIDTH
                    end_pct = (bin_index + 1) * PERCENTILE_BIN_WIDTH
                    bin_label = f"{start_pct:g}–{end_pct:g}th percentile"

                    selected_df = selected_all[
                        selected_all["PercentileBinIndex"] == bin_index
                    ]

                    # Selected ROIs are blue only. Remove their actual boundary
                    # from the yellow layer first so no yellow remains underneath.
                    selected_ids = selected_df["ObjectID"].astype(int).to_numpy()
                    selected_mask = np.zeros_like(label_image, dtype=bool)
                    selected_boundary = np.zeros_like(all_roi_outline, dtype=bool)
                    if len(selected_ids) > 0:
                        selected_mask = np.isin(label_image, selected_ids)
                        selected_boundary = make_boundary_from_labels(
                            np.where(selected_mask, 1, 0).astype(np.uint32)
                        )

                    other_outline = all_roi_outline & ~selected_boundary
                    draw_outline(
                        ax,
                        other_outline,
                        ALL_ROI_COLOR,
                        ROI_LINEWIDTH,
                    )
                    draw_filled_mask_outline(
                        ax,
                        selected_mask,
                        SELECTED_ROI_COLOR,
                        SELECTED_ROI_LINEWIDTH,
                    )
                    for _, row in selected_df.iterrows():
                        add_centroid_dot(
                            ax,
                            float(row["Center_X"]),
                            float(row["Center_Y"]),
                        )

                    ax.set_title(
                        f"{bin_label} — {len(selected_df)} selected "
                        f"(maximum {MAX_SAMPLE_PER_BIN})\n"
                        f"Yellow = other ROIs | Blue = selected ROI | Red dot = centroid",
                        fontsize=11.5,
                        fontweight="bold",
                    )
                    ax.set_xlim(0, image_width)
                    ax.set_ylim(image_height, 0)
                    ax.axis("off")

                fig_whole.suptitle(
                    f"{channel_name} — {metric_name} — Whole-Organoid Percentile ROIs\n"
                    f"Percentile bins {page_start + 1}–{min(page_start + 4, N_PERCENTILE_BINS)} of {N_PERCENTILE_BINS}",
                    fontsize=18,
                    fontweight="bold",
                    y=0.995,
                )
                fig_whole.tight_layout(rect=[0, 0, 1, 0.97])
                metric_pdf.savefig(fig_whole, bbox_inches="tight")
                pdf.savefig(fig_whole, bbox_inches="tight")
                plt.close(fig_whole)

            # ====================================================
            # INDIVIDUAL ROI CROPS — UP TO 25 PER PAGE
            # ====================================================
            selected_for_crops = selected_all.copy()
            selected_for_crops["PercentileBinIndex"] = selected_for_crops[
                "PercentileBinIndex"
            ].astype(int)

            crop_page_size = 25
            n_crop_pages = int(np.ceil(len(selected_for_crops) / crop_page_size))

            for crop_page in range(n_crop_pages):
                page_df = selected_for_crops.iloc[
                    crop_page * crop_page_size : (crop_page + 1) * crop_page_size
                ].copy()

                n_cols = 5
                n_rows = int(np.ceil(len(page_df) / n_cols))

                fig_crops = plt.figure(figsize=(18, max(10, 3.2 * n_rows)))
                crop_gs = fig_crops.add_gridspec(
                    n_rows,
                    n_cols,
                    hspace=0.55,
                    wspace=0.20,
                )

                for plot_idx, (_, row) in enumerate(page_df.iterrows()):
                    ax = fig_crops.add_subplot(
                        crop_gs[plot_idx // n_cols, plot_idx % n_cols]
                    )
                    object_id = int(row["ObjectID"])
                    roi_pixels = pixel_groups[object_id]

                    xmin, ymin, xmax, ymax = get_crop_for_object(
                        roi_pixels,
                        image.shape,
                        CROP_PADDING,
                    )

                    crop = image[ymin:ymax, xmin:xmax]
                    show_image(ax, crop, vmin, vmax)

                    selected_crop_mask = (
                        label_image[ymin:ymax, xmin:xmax] == object_id
                    )
                    selected_outline = make_single_roi_outline_from_labels(
                        label_image,
                        object_id,
                        xmin,
                        ymin,
                        xmax,
                        ymax,
                    )
                    other_outline = all_roi_outline[ymin:ymax, xmin:xmax].copy()
                    other_outline &= ~selected_outline
                    draw_outline(
                        ax,
                        other_outline,
                        ALL_ROI_COLOR,
                        ROI_LINEWIDTH,
                    )
                    draw_filled_mask_outline(
                        ax,
                        selected_crop_mask,
                        SELECTED_ROI_COLOR,
                        SELECTED_ROI_LINEWIDTH,
                    )
                    center_x = float(row["Center_X"]) - xmin
                    center_y = float(row["Center_Y"]) - ymin
                    add_centroid_dot(
                        ax,
                        center_x,
                        center_y,
                    )
                    ax.set_title(
                        f"{row['IntensityGroup']}\n"
                        f"ROI {int(row['DisplayNumber'])} | Object {object_id}\n"
                        f"{metric_name}: {float(row[metric_name]):.4g}",
                        fontsize=8.0,
                    )
                    ax.axis("off")

                # Hide unused slots on the final crop page.
                for plot_idx in range(len(page_df), n_rows * n_cols):
                    ax = fig_crops.add_subplot(
                        crop_gs[plot_idx // n_cols, plot_idx % n_cols]
                    )
                    ax.axis("off")

                fig_crops.suptitle(
                    f"{channel_name} — {metric_name} — Individual ROI Crops\n"
                    f"Page {crop_page + 1} of {n_crop_pages} | "
                    f"{len(selected_for_crops)} selected ROIs total\n"
                    f"Yellow = other ROI outlines | Blue = selected ROI | Red dot = centroid",
                    fontsize=15,
                    fontweight="bold",
                )
                fig_crops.tight_layout(rect=[0, 0, 1, 0.93])
                metric_pdf.savefig(fig_crops, bbox_inches="tight")
                pdf.savefig(fig_crops, bbox_inches="tight")
                plt.close(fig_crops)

            metric_pdf.close()

            metric_selected_columns = [
                "Channel",
                "Metric",
                "IntensityGroup",
                "PercentileBinIndex",
                "PercentileRange",
                "DisplayNumber",
                "ObjectID",
                "Mean intensity",
                "Median intensity",
                "Maximum intensity",
                "Integrated intensity",
                "Intensity SD",
                "ROI pixel count",
                "Center_X",
                "Center_Y",
                "BoundingBoxMinimum_X",
                "BoundingBoxMaximum_X",
                "BoundingBoxMinimum_Y",
                "BoundingBoxMaximum_Y",
            ]
            metric_selected_columns = [
                col for col in metric_selected_columns
                if col in selected_all.columns
            ]
            # Save ALL ROIs for this channel + metric in the same metric folder.
            # PercentileBinIndex and PercentileRange are included so every ROI
            # in the all-ROI CSV can be traced back to its 5% percentile bin.
            metric_all_columns = [
                "Channel",
                "ObjectID",
                metric_name,
                "PercentileBinIndex",
                "PercentileRange",
                "ROI pixel count",
                "Center_X",
                "Center_Y",
                "BoundingBoxMinimum_X",
                "BoundingBoxMaximum_X",
                "BoundingBoxMinimum_Y",
                "BoundingBoxMaximum_Y",
            ]
            metric_all_columns = [
                col for col in metric_all_columns
                if col in measurements_df.columns
            ]
            measurements_df[metric_all_columns].to_csv(
                metric_all_csv,
                index=False,
            )

            selected_all[metric_selected_columns].to_csv(
                metric_selected_csv,
                index=False,
            )

            print(f"Metric PDF saved: {metric_pdf_path}")
            print(f"All-ROI CSV saved: {metric_all_csv}")
            print(f"Selected ROI CSV saved: {metric_selected_csv}")
            print(f"Finished metric: {metric_name}")

        channel_measurements_csv = channel_output_dir / (
            f"{channel_name}_all_ROI_measurements.csv"
        )
        measurements_df.to_csv(channel_measurements_csv, index=False)

        print(f"Channel measurements saved: {channel_measurements_csv}")
        print(f"Finished channel: {channel_name}")


# ============================================================
# SAVE ALL OBJECT MEASUREMENTS
# ============================================================

if all_measurements:
    combined_measurements = pd.concat(all_measurements, ignore_index=True)
    combined_measurements.to_csv(all_measurements_csv, index=False)

    print("\nAll ROI measurements saved to:")
    print(all_measurements_csv)


else:
    raise RuntimeError("No ROI measurements were generated.")


# ============================================================
# SAVE SELECTED ROI TABLE
# ============================================================

if all_selected:
    combined_selected = pd.concat(all_selected, ignore_index=True)

    selected_columns = [
        "Channel",
        "Metric",
        "IntensityGroup",
        "PercentileBinIndex",
        "PercentileRange",
        "DisplayNumber",
        "ObjectID",
        "Mean intensity",
        "Median intensity",
        "Maximum intensity",
        "Integrated intensity",
        "Intensity SD",
        "ROI pixel count",
        "Center_X",
        "Center_Y",
        "BoundingBoxMinimum_X",
        "BoundingBoxMaximum_X",
        "BoundingBoxMinimum_Y",
        "BoundingBoxMaximum_Y",
    ]

    selected_columns = [
        col for col in selected_columns if col in combined_selected.columns
    ]

    combined_selected[selected_columns].to_csv(
        csv_output_path,
        index=False,
    )

    print("\nSelected ROI CSV saved to:")
    print(csv_output_path)
else:
    raise RuntimeError("No ROIs were selected.")


# ============================================================
# FINISHED
# ============================================================

print("\n" + "=" * 70)
print("DONE!")
print("=" * 70)
print("\nSingle PDF containing all channels and metrics:")
print(pdf_path)
print("\nEach channel/metric folder contains the PDF, all-ROI CSV, and selected-ROI CSV.")
print("\nSelected ROI table:")
print(csv_output_path)
print("\nNo segmentation overlay TIFFs were used.")
print("ROI outlines were reconstructed directly from the ROI pixel CSVs.")
print("=" * 70)

