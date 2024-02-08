#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Photo and video organizer - manage your library as small copies.

The software will collect all files from the source directory and copy
them in smaller size to the destination directory.

Copyright 2024 Alic Znapy
SPDX-License-Identifier: Apache-2.0
"""

import argparse
import logging
from pathlib import Path
import tomllib
from typing import Any, Union, Tuple, List

import numpy as np
from PIL import Image
import cv2


class Settings:
    """Contains launch parameters with variables from 'pyproject.toml'."""

    source: Path
    destination: Path
    small_size: Tuple[int, int]
    frames_percents: List[int]
    DIRECTORY_MODE = 0o740

    @staticmethod
    def get_args(meta: dict[str, Any]) -> argparse.Namespace:
        """Parse launch parameters."""
        parser = argparse.ArgumentParser(
            prog=meta['name'],
            description=f"{__doc__}{meta['urls']['homepage']}",
            formatter_class=argparse.RawTextHelpFormatter)

        parser.add_argument(
            '-v', '--version', action='version',
            version=f"%(prog)s v{meta['version']}")

        parser.add_argument(
            '-s', '--source',
            help='Path to source directory (more priority than in toml)')

        parser.add_argument(
            '-d', '--destination',
            help='Path to destination directory (more priority than in toml)')

        parser.add_argument(
            '-l', '--loglevel',
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            help='Choose log lavel, default is WARNING')

        args = parser.parse_args()
        if args.loglevel:
            levels = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}
            logging.getLogger().setLevel(levels[args.loglevel])

        logging.debug("Running %s version %s", meta['name'], meta['version'])

        return args

    def set_source(self, toml: dict[str, Union[str, list]],
                   args: argparse.Namespace) -> None:
        """Define 'source' property or rise error."""
        path = Path(str(toml['source']))
        if args.source:
            path = Path(args.source)
        if not path.exists():
            raise RuntimeError(f"Source directory '{path}' does not exist")
        if not path.is_dir():
            raise RuntimeError(f"Source path '{path}' is not a directory")

        self.source = path.resolve()
        logging.debug("source path is %s", self.source)

    def set_destination(self, toml: dict[str, Union[str, list]],
                        args: argparse.Namespace) -> None:
        """Define 'destination' property or rise error."""
        path = Path(str(toml['destination']))
        if args.destination:
            path = Path(args.destination)
        if not path.exists():
            logging.warning("Creating new destinanion directory '%s'", path)
            path.mkdir(mode=Settings.DIRECTORY_MODE)
        if not path.is_dir():
            raise RuntimeError(f"Destinanion path '{path}' is not a directory")

        self.destination = path.resolve()
        logging.debug("destination path is %s", self.destination)

    def __init__(self) -> None:
        cur_dir = Path(__file__).resolve().parent

        with open(cur_dir / "pyproject.toml", "rb") as file:
            toml = tomllib.load(file)

        args = Settings.get_args(toml['project'])
        ps = toml['project-settings']
        self.set_source(ps, args)
        self.set_destination(ps, args)
        self.small_size = (int(ps['small_size'][0]),
                           int(ps['small_size'][1]))
        self.frames_percents = [int(i) for i in ps['frames']]


class Copier:
    """To copy files from source to destination with resizing."""

    SUFFIXES_IMAGES = {".jpg", ".png", ".gif"}
    SUFFIXES_VIDEOS = {".mp4"}

    @staticmethod
    def frames_numbers(frames_percents: List[int], max_number: int
                       ) -> List[int]:
        """Calculate the frame numbers from their percentages."""
        return [int(i*max_number/100) for i in frames_percents]

    @staticmethod
    def clone_image(source: Path, destination: Path,
                    small_size: Tuple[int, int]) -> None:
        """Make a sized copy of image."""
        with Image.open(source) as img:
            logging.debug("Creating image thumbnail %s", destination)
            img.thumbnail(small_size)
            img.save(destination)

    @staticmethod
    def clone_video(source: Path, destination_jpg: Path, settings: Settings
                    ) -> None:
        """Make a 2x2 collage of video frames."""
        vid_cap = cv2.VideoCapture(str(source))
        frames_max_number = int(vid_cap.get(cv2.CAP_PROP_FRAME_COUNT)) - 1
        frames_img = []
        for frame in Copier.frames_numbers(
                settings.frames_percents, frames_max_number):
            vid_cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            success, image = vid_cap.read()
            if success:
                frames_img.append(cv2.resize(image, settings.small_size))
        if len(frames_img) == 4:

            logging.debug("Creating video thumbnail %s", destination_jpg)
            row1 = np.hstack((frames_img[0], frames_img[1]))
            row2 = np.hstack((frames_img[2], frames_img[3]))
            cv2.imwrite(str(destination_jpg), np.vstack((row1, row2)))

    @staticmethod
    def _clone_file(source: Path, destination: Path, settings: Settings
                    ) -> None:
        if destination.exists():
            logging.debug("Skipp exist file %s", destination)
            return

        path = destination.parent
        if not path.exists():
            logging.info("Creating new destinanion subdirectory '%s'", path)
            path.mkdir(mode=Settings.DIRECTORY_MODE)

        if source.suffix.lower() in Copier.SUFFIXES_IMAGES:
            Copier.clone_image(source, destination, settings.small_size)

        if source.suffix.lower() in Copier.SUFFIXES_VIDEOS:
            destination_jpg = destination.with_suffix(
                destination.suffix + ".jpg")
            Copier.clone_video(source, destination_jpg, settings)

    @staticmethod
    def iterate_files(source: Path, destination: Path, settings: Settings
                      ) -> None:
        """Walk through source directory to make a thumbnail."""
        suffixes = Copier.SUFFIXES_IMAGES | Copier.SUFFIXES_VIDEOS
        for child in source.iterdir():
            destination_child = destination / child.name
            if child.is_dir():
                logging.warning("iterate through %s", child)
                Copier.iterate_files(child, destination_child, settings)
            if child.is_file() and child.suffix.lower() in suffixes:
                logging.debug("processing %s", child)
                Copier._clone_file(child, destination_child, settings)


def _main() -> None:

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt='%Y%m%d_%H%M%S')

    settings = Settings()
    Copier.iterate_files(settings.source, settings.destination, settings)


if __name__ == "__main__":
    _main()
