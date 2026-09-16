#!/usr/bin/env python3

import argparse
import subprocess
import tempfile
import shutil
from pathlib import Path


def run_cellprofiler(pipeline_path, input_file, output_dir):

    pipeline_path = Path(pipeline_path).resolve()
    input_file = Path(input_file).resolve()
    output_dir = Path(output_dir).resolve()

    # ============================================================
    # CHECK INPUTS
    # ============================================================

    if not pipeline_path.exists():
        raise FileNotFoundError(
            f"CellProfiler pipeline not found:\n{pipeline_path}"
        )

    if not input_file.exists():
        raise FileNotFoundError(
            f"Input image not found:\n{input_file}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("CELLPROFILER HEADLESS RUN")
    print("=" * 70)
    print(f"Pipeline:   {pipeline_path}")
    print(f"Input file: {input_file}")
    print(f"Output dir: {output_dir}")
    print("=" * 70)

    # ============================================================
    # TEMPORARY INPUT DIRECTORY
    # ============================================================

    with tempfile.TemporaryDirectory(
        prefix="cellprofiler_input_"
    ) as temp_dir_string:

        temp_dir = Path(temp_dir_string)

        temporary_input = temp_dir / input_file.name

        # Symlink instead of copying the large microscopy TIFF
        temporary_input.symlink_to(input_file)

        print(f"\nTemporary input directory:")
        print(f"  {temp_dir}")

        print(f"\nLinked input image:")
        print(f"  {temporary_input}")

        # ========================================================
        # RUN CELLPROFILER
        # ========================================================

        command = [
            "cellprofiler",
            "-c",
            "-r",
            "-p", str(pipeline_path),
            "-i", str(temp_dir),
            "-o", str(output_dir),
            "-L", "INFO",
        ]

        print("\nRunning:")
        print(
            " ".join(
                f'"{item}"' if " " in item else item
                for item in command
            )
        )

        print()

        result = subprocess.run(command)

        if result.returncode != 0:
            raise RuntimeError(
                f"CellProfiler exited with code "
                f"{result.returncode}"
            )

        # ========================================================
        # COLLECT FILES WRITTEN BESIDE THE INPUT IMAGE
        # ========================================================
        #
        # Some CellProfiler pipelines have SaveImages and/or
        # ExportToSpreadsheet configured to save into the input
        # image's directory.
        #
        # Since our input directory is temporary, copy all outputs
        # out of it before TemporaryDirectory deletes the directory.
        #
        # The original input symlink itself is skipped.
        # ========================================================

        print()
        print("=" * 70)
        print("COLLECTING CELLPROFILER OUTPUTS")
        print("=" * 70)

        copied_files = []

        for item in temp_dir.iterdir():

            # Do NOT copy the input-image symlink
            if item == temporary_input:
                continue

            destination = output_dir / item.name

            # ----------------------------------------------------
            # Directory output
            # ----------------------------------------------------
            if item.is_dir():

                if destination.exists():
                    shutil.rmtree(destination)

                shutil.copytree(
                    item,
                    destination
                )

                copied_files.append(destination)

                print(
                    f"Copied directory:\n"
                    f"  {item}\n"
                    f"      -> {destination}"
                )

            # ----------------------------------------------------
            # File output
            # ----------------------------------------------------
            elif item.is_file():

                shutil.copy2(
                    item,
                    destination
                )

                copied_files.append(destination)

                print(
                    f"Copied:\n"
                    f"  {item}\n"
                    f"      -> {destination}"
                )

        # ========================================================
        # FINAL REPORT
        # ========================================================

        print()
        print("=" * 70)
        print("CELLPROFILER COMPLETED SUCCESSFULLY")
        print("=" * 70)

        print(f"\nFinal output directory:\n{output_dir}")

        print("\nFiles now present:")

        final_files = sorted(output_dir.iterdir())

        if not final_files:
            print("  [NO FILES FOUND]")

        else:
            for file in final_files:
                print(f"  {file.name}")

        print()

        if copied_files:
            print(
                f"Recovered {len(copied_files)} "
                f"output item(s) written beside the input image."
            )


# ================================================================
# COMMAND-LINE INTERFACE
# ================================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=(
            "Run CellProfiler headlessly on one image and collect "
            "all generated outputs into a specified directory."
        )
    )

    parser.add_argument(
        "--pipeline",
        required=True,
        help="Path to CellProfiler .cppipe pipeline.",
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to input TIFF/image.",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Destination directory for all CellProfiler outputs.",
    )

    args = parser.parse_args()

    run_cellprofiler(
        pipeline_path=args.pipeline,
        input_file=args.input,
        output_dir=args.output,
    )
