#!/usr/bin/env python3
"""Split a YOLO image/label dataset into training and validation sets."""

from __future__ import annotations

import argparse
import random
import shutil
import sys
from pathlib import Path


# Change this value if you want a different split.
# The validation ratio is automatically 1.0 minus the training ratio.
DEFAULT_TRAIN_RATIO = 0.8
DEFAULT_RANDOM_SEED = 42

IMAGE_EXTENSIONS = {
    ".bmp",
    ".jpeg",
    ".jpg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Copy a YOLO dataset into images/train, images/val, "
            "labels/train, and labels/val folders."
        )
    )
    parser.add_argument(
        "--inputfolder",
        "--inputfoder",
        dest="inputfolder",
        required=True,
        help="Dataset folder containing images/ and labels/.",
    )
    parser.add_argument(
        "--outputfolder",
        default=None,
        help=(
            "Output folder. Default: a new '<input name>_split' folder "
            "beside the input folder."
        ),
    )
    parser.add_argument(
        "--train-ratio",
        type=float,
        default=DEFAULT_TRAIN_RATIO,
        help=f"Training ratio. Default: {DEFAULT_TRAIN_RATIO}.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_RANDOM_SEED,
        help=f"Random seed for a repeatable split. Default: {DEFAULT_RANDOM_SEED}.",
    )
    return parser.parse_args()


def find_images(images_dir: Path) -> list[Path]:
    images = sorted(
        path
        for path in images_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )

    seen_stems: dict[str, Path] = {}
    for image_path in images:
        normalized_stem = image_path.stem.casefold()
        previous = seen_stems.get(normalized_stem)
        if previous is not None:
            raise ValueError(
                "Two images have the same base name: "
                f"'{previous.name}' and '{image_path.name}'."
            )
        seen_stems[normalized_stem] = image_path

    return images


def copy_sample(
    image_path: Path,
    labels_dir: Path,
    output_images_dir: Path,
    output_labels_dir: Path,
) -> bool:
    shutil.copy2(image_path, output_images_dir / image_path.name)

    label_path = labels_dir / f"{image_path.stem}.txt"
    if label_path.is_file():
        shutil.copy2(label_path, output_labels_dir / label_path.name)
        return True

    return False


def main() -> int:
    args = parse_args()

    if not 0.0 < args.train_ratio < 1.0:
        print("Error: --train-ratio must be between 0 and 1.", file=sys.stderr)
        return 1

    input_dir = Path(args.inputfolder).expanduser().resolve()
    images_dir = input_dir / "images"
    labels_dir = input_dir / "labels"

    if not images_dir.is_dir():
        print(f"Error: images folder not found: {images_dir}", file=sys.stderr)
        return 1

    if not labels_dir.is_dir():
        print(f"Error: labels folder not found: {labels_dir}", file=sys.stderr)
        return 1

    if args.outputfolder:
        output_dir = Path(args.outputfolder).expanduser().resolve()
    else:
        output_dir = input_dir.parent / f"{input_dir.name}_split"

    if output_dir == input_dir:
        print(
            "Error: output folder must be different from the input folder.",
            file=sys.stderr,
        )
        return 1

    if output_dir.exists():
        if not output_dir.is_dir():
            print(
                f"Error: output path is not a folder: {output_dir}",
                file=sys.stderr,
            )
            return 1

        if any(output_dir.iterdir()):
            print(
                f"Error: output folder is not empty: {output_dir}",
                file=sys.stderr,
            )
            print(
                "Choose another --outputfolder or empty it manually first.",
                file=sys.stderr,
            )
            return 1

    try:
        images = find_images(images_dir)
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    if not images:
        print(f"Error: no supported images found in: {images_dir}", file=sys.stderr)
        return 1

    random.Random(args.seed).shuffle(images)

    train_count = int(len(images) * args.train_ratio)
    if len(images) >= 2:
        train_count = max(1, min(train_count, len(images) - 1))

    train_images = images[:train_count]
    val_images = images[train_count:]

    train_images_dir = output_dir / "images" / "train"
    val_images_dir = output_dir / "images" / "val"
    train_labels_dir = output_dir / "labels" / "train"
    val_labels_dir = output_dir / "labels" / "val"

    for directory in (
        train_images_dir,
        val_images_dir,
        train_labels_dir,
        val_labels_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    labels_found = 0

    for image_path in train_images:
        labels_found += copy_sample(
            image_path,
            labels_dir,
            train_images_dir,
            train_labels_dir,
        )

    for image_path in val_images:
        labels_found += copy_sample(
            image_path,
            labels_dir,
            val_images_dir,
            val_labels_dir,
        )

    missing_labels = len(images) - labels_found
    actual_train_ratio = len(train_images) / len(images)
    actual_val_ratio = len(val_images) / len(images)

    print("Dataset split completed.")
    print(f"Source: {input_dir}")
    print(f"Output: {output_dir}")
    print(
        f"Train:  {len(train_images)} images "
        f"({actual_train_ratio:.1%})"
    )
    print(
        f"Val:    {len(val_images)} images "
        f"({actual_val_ratio:.1%})"
    )
    print(f"Labels copied: {labels_found}")

    if missing_labels:
        print(
            f"Warning: {missing_labels} images had no matching .txt label. "
            "They were kept as background images."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
