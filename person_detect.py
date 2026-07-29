#!/usr/bin/env python3
"""
Detect people in every image in a folder using a one-class YOLO model.

Example:
    python person_detect.py --inputfolder images1

By default, the script loads person_posco1.pt from the same directory as this
file and saves annotated images to a folder named <inputfolder>_detected.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
from ultralytics import YOLO


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_MODEL = SCRIPT_DIR / "person_posco1.pt"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect people in all images in a folder with YOLO."
    )
    parser.add_argument(
        "--inputfolder",
        type=Path,
        required=True,
        help="Folder containing the input images.",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=DEFAULT_MODEL,
        help="Path to the one-class person YOLO model (default: person_posco1.pt).",
    )
    parser.add_argument(
        "--outputfolder",
        type=Path,
        default=None,
        help="Folder for annotated images (default: <inputfolder>_detected).",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.25,
        help="Minimum detection confidence from 0 to 1 (default: 0.25).",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        help="YOLO inference image size (default: 640).",
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Inference device, for example 0, 1, cpu, or cuda:0.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    input_folder = args.inputfolder.expanduser().resolve()
    model_path = args.model.expanduser().resolve()

    if not input_folder.is_dir():
        raise FileNotFoundError(f"Input folder not found: {input_folder}")
    if not model_path.is_file():
        raise FileNotFoundError(f"YOLO model not found: {model_path}")
    if not 0.0 <= args.conf <= 1.0:
        raise ValueError("--conf must be between 0 and 1.")
    if args.imgsz <= 0:
        raise ValueError("--imgsz must be greater than zero.")

    if args.outputfolder is None:
        output_folder = input_folder.parent / f"{input_folder.name}_detected"
    else:
        output_folder = args.outputfolder.expanduser().resolve()

    if output_folder == input_folder:
        raise ValueError("The output folder must be different from the input folder.")

    return input_folder, model_path, output_folder


def find_images(input_folder: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in input_folder.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        ),
        key=lambda path: path.name.lower(),
    )


def draw_person_box(
    image,
    box: tuple[int, int, int, int],
    confidence: float,
) -> None:
    x1, y1, x2, y2 = box
    color = (0, 255, 0)
    label = f"person {confidence:.2f}"

    cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.55
    thickness = 1
    (text_width, text_height), baseline = cv2.getTextSize(
        label, font, font_scale, thickness
    )
    label_top = max(0, y1 - text_height - baseline - 6)
    label_bottom = label_top + text_height + baseline + 6
    cv2.rectangle(
        image,
        (x1, label_top),
        (x1 + text_width + 6, label_bottom),
        color,
        -1,
    )
    cv2.putText(
        image,
        label,
        (x1 + 3, label_bottom - baseline - 3),
        font,
        font_scale,
        (0, 0, 0),
        thickness,
        cv2.LINE_AA,
    )


def process_images(
    model: YOLO,
    image_paths: list[Path],
    output_folder: Path,
    confidence_threshold: float,
    image_size: int,
    device: str | None,
) -> tuple[int, int]:
    output_folder.mkdir(parents=True, exist_ok=True)

    processed_images = 0
    total_people = 0

    for index, image_path in enumerate(image_paths, start=1):
        image = cv2.imread(str(image_path))
        if image is None:
            print(f"[WARN] Could not read image: {image_path}", file=sys.stderr)
            continue

        predict_options = {
            "source": image,
            "conf": confidence_threshold,
            "imgsz": image_size,
            "classes": [0],
            "verbose": False,
        }
        if device is not None:
            predict_options["device"] = device

        result = model.predict(**predict_options)[0]
        detections: list[tuple[tuple[int, int, int, int], float]] = []

        if result.boxes is not None:
            boxes = result.boxes.xyxy.cpu().tolist()
            confidences = result.boxes.conf.cpu().tolist()
            image_height, image_width = image.shape[:2]

            for raw_box, raw_confidence in zip(boxes, confidences):
                x1, y1, x2, y2 = raw_box
                box = (
                    max(0, min(int(round(x1)), image_width - 1)),
                    max(0, min(int(round(y1)), image_height - 1)),
                    max(0, min(int(round(x2)), image_width)),
                    max(0, min(int(round(y2)), image_height)),
                )
                if box[2] <= box[0] or box[3] <= box[1]:
                    continue
                detections.append((box, float(raw_confidence)))

        for box, detection_confidence in detections:
            draw_person_box(image, box, detection_confidence)

        output_path = output_folder / image_path.name
        if not cv2.imwrite(str(output_path), image):
            print(f"[WARN] Could not save image: {output_path}", file=sys.stderr)
            continue

        person_count = len(detections)
        processed_images += 1
        total_people += person_count
        print(
            f"[{index}/{len(image_paths)}] {image_path.name}: "
            f"{person_count} person(s) -> {output_path}"
        )

    return processed_images, total_people


def main() -> int:
    args = parse_args()

    try:
        input_folder, model_path, output_folder = validate_args(args)
        image_paths = find_images(input_folder)
        if not image_paths:
            print(f"No supported images found in: {input_folder}", file=sys.stderr)
            return 1

        print(f"Model:  {model_path}")
        print(f"Input:  {input_folder}")
        print(f"Output: {output_folder}")
        print(f"Images: {len(image_paths)}")

        model = YOLO(str(model_path))
        processed_images, total_people = process_images(
            model=model,
            image_paths=image_paths,
            output_folder=output_folder,
            confidence_threshold=args.conf,
            image_size=args.imgsz,
            device=args.device,
        )
    except (FileNotFoundError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nStopped by user.", file=sys.stderr)
        return 130

    print(
        f"Done: processed {processed_images}/{len(image_paths)} image(s), "
        f"detected {total_people} person(s)."
    )
    return 0 if processed_images == len(image_paths) else 2


if __name__ == "__main__":
    raise SystemExit(main())
