#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Photo and video organizer - manage your library as small copies.

The software will collect all files from the source directory and copy
them in smaller size to the destination directory.

homepage: https://github.com/Znapy/pv-organizer
Copyright 2024 Alic Znapy
SPDX-License-Identifier: Apache-2.0
"""

import argparse
from io import StringIO
import sys
import logging
import math
from pathlib import Path
import tarfile
from typing import cast

import numpy as np
from PIL import Image, ImageFile, UnidentifiedImageError
import cv2


class Settings:
    """Contains launch parameters and default settings."""

    VERSION = "2.0.1"
    DIRECTORY_MODE = 0o750
    SOURCE = "./tests/examples"
    DESTINATION = "./tests/"

    small_size = (128, 128)
    frames_percents = (1, 35, 65, 99)
    do_not_tar = False
    source: Path
    thumbnails: Path
    launch_args: argparse.Namespace

    @staticmethod
    def get_args() -> argparse.Namespace:
        """Parse launch parameters."""
        parser = argparse.ArgumentParser(
            description=f"{__doc__}",
            formatter_class=argparse.RawTextHelpFormatter)

        parser.add_argument(
            '-v', '--version', action='version',
            version=f"%(prog)s v{Settings.VERSION}")

        parser.add_argument(
            '-s', '--source',
            help=f'Path to source directory, default is {Settings.SOURCE}')

        parser.add_argument(
            '-d', '--destination',
            help='Path to destination directory, '
                 f'default is {Settings.DESTINATION}')

        parser.add_argument(
            '-p', '--plain', action="store_true",
            help='Do not compress to a file - leave the plain directory')

        parser.add_argument(
            '-l', '--loglevel',
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            help='Choose log lavel, default is WARNING')

        parser.add_argument(
            '-z', '--small_size',
            help='Small image size, default is '
                 f'{Settings.small_size[0]}x{Settings.small_size[1]}')

        parser.add_argument(
            '-f', '--frames_percents',
            help='Four frames as a percentage, default is '
                 f'{Settings.frames_percents[0]}/'
                 f'{Settings.frames_percents[1]}/'
                 f'{Settings.frames_percents[2]}/'
                 f'{Settings.frames_percents[3]}')

        return parser.parse_args()

    @staticmethod
    def set_log_level(args: argparse.Namespace) -> None:
        """Set log level from launch parameter."""
        if args.loglevel:
            levels = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}
            logging.getLogger().setLevel(levels[args.loglevel])

    def set_source(self) -> None:
        """Define 'source' property or rise error."""
        path = Path(Settings.SOURCE)
        if self.launch_args.source:
            path = Path(self.launch_args.source)
        if not path.exists():
            raise RuntimeError(f"Source directory '{path}' does not exist")
        if not path.is_dir():
            raise RuntimeError(f"Source path '{path}' is not a directory")

        self.source = path.resolve()
        logging.debug("source path is %s", self.source)

    def set_thumbnails(self) -> None:
        """Define 'destination' property or rise error."""
        path = Path(Settings.DESTINATION)
        if self.launch_args.destination:
            path = Path(self.launch_args.destination)
        if not path.exists():
            raise RuntimeError(f"Destinanion path '{path}' is not exist")
        if not path.is_dir():
            raise RuntimeError(f"Destinanion path '{path}' is not a directory")

        self.thumbnails = path.resolve() / (self.source.name + "-thumbnails")
        logging.debug("path to thumbnails is %s", self.thumbnails)

    def set_small_size(self) -> None:
        """Define thumbnail size from launch parameter."""
        if not self.launch_args.small_size:
            return

        candidate = tuple(map(int, self.launch_args.small_size.split("x")))
        assert len(candidate) == 2
        if candidate[0] >= 1000 or candidate[1] >= 1000:
            raise RuntimeError("The width and height of a small size "
                               "should be less than 1000")
        self.small_size = cast(tuple[int, int], candidate)

    def set_frames_percents(self) -> None:
        """Define percents of frames for picture from video."""
        if not self.launch_args.frames_percents:
            return

        candidate = tuple(map(int,
                              self.launch_args.frames_percents.split("/")))
        assert len(candidate) == 4
        if not (0 <= candidate[0] <= 100 and
                0 <= candidate[1] <= 100 and
                0 <= candidate[2] <= 100 and
                0 <= candidate[3] <= 100):
            raise RuntimeError("Percents of frames "
                               "should be >=0 and <=100")
        self.frames_percents = cast(tuple[int, int, int, int], candidate)

    def __init__(self, launch_args: argparse.Namespace) -> None:
        self.launch_args = launch_args

        Settings.set_log_level(launch_args)
        logging.debug("Running %s version %s",
                      Path(__file__).name, Settings.VERSION)

        self.set_source()
        self.set_thumbnails()
        self.set_small_size()
        self.set_frames_percents()
        self.do_not_tar = launch_args.plain is True

        ImageFile.LOAD_TRUNCATED_IMAGES = True


class Copier:
    """To copy files from source to destination with resizing."""

    SUFFIXES_IMAGES = {".jpg", ".jpeg", ".png", ".gif", '.bmp'}
    SUFFIXES_VIDEOS = {".mp4", ".avi", '.mov', '.mpg', '.m4v', ".wav", ".mts",
                       ".3gp"}
    settings: Settings

    @staticmethod
    def frames_numbers(frames_percents: tuple[int, int, int, int],
                       max_number: int) -> list[int]:
        """
        Calculate the frame numbers from their percentages.

        The 'max_number' is 0-based index.
        """
        return [math.ceil(i*max_number/100) for i in frames_percents]

    def clone_image(self, source: Path, destination: Path) -> None:
        """Make a sized copy of image."""
        logging.debug("processing image %s", destination.name)
        try:
            img = Image.open(source)
        except UnidentifiedImageError as e:
            logging.error(e)
        else:
            with img:
                try:
                    img.thumbnail(self.settings.small_size)
                except OSError as e:
                    logging.error("%s, %s", e, source.name)
                    return
                logging.info("Creating image thumbnail %s", destination.name)
                img.save(destination)

    def clone_video(self, source: Path, destination: Path) -> None:
        """Make a 2x2 collage of video frames."""
        logging.debug("processing video %s", destination.name)
        sys.stderr = temp_stderr = StringIO()
        vid_cap = cv2.VideoCapture(str(source))
        frames_max_number = int(vid_cap.get(cv2.CAP_PROP_FRAME_COUNT)) - 1
        frames_img = []
        for frame in Copier.frames_numbers(
                self.settings.frames_percents, frames_max_number):
            vid_cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            success, image = vid_cap.read()
            if success:
                frames_img.append(cv2.resize(image, self.settings.small_size))

        sys.stderr = sys.__stderr__
        logging.debug(temp_stderr.getvalue())
        temp_stderr.close()

        compression_params = [cv2.IMWRITE_JPEG_QUALITY, 80]
        if len(frames_img) == 4:
            logging.info("Creating video thumbnail %s", destination.name)
            row1 = np.hstack((frames_img[0], frames_img[1]))
            row2 = np.hstack((frames_img[2], frames_img[3]))
            collage = np.vstack((row1, row2))
            cv2.imwrite(str(destination), collage, compression_params)

    def create_thumbnails(self) -> None:
        """Walk through source directory to make a thumbnail."""
        for cur_source, _, files in self.settings.source.walk(
                on_error=logging.error):
            print(f"Iterate through {cur_source} [{len(files)} file(s)]")
            cur_destination = Path(str(cur_source).replace(
                str(self.settings.source), str(self.settings.thumbnails)))
            cur_destination.mkdir(mode=Settings.DIRECTORY_MODE, exist_ok=True)

            for file_name in files:
                source_child = cur_source / file_name
                suffix = source_child.suffix.lower()

                destination_child = cur_destination / file_name
                if suffix in Copier.SUFFIXES_VIDEOS:
                    destination_child = destination_child.with_suffix(
                        destination_child.suffix + ".jpg")

                if destination_child.exists():
                    logging.info("Skipp exist file %s", destination_child.name)
                    continue

                if suffix in Copier.SUFFIXES_IMAGES:
                    self.clone_image(source_child, destination_child)
                elif suffix in Copier.SUFFIXES_VIDEOS:
                    self.clone_video(source_child, destination_child)
                else:
                    print("unsupported file:", file_name)

    def to_tar(self) -> None:
        """Compress destination directory."""
        if self.settings.do_not_tar:
            logging.info("Leave plain directory (not compressed)")
            return

        dest = self.settings.thumbnails
        tar_file_name = dest.with_suffix(".tar.gz")
        logging.info("Compress to %s", tar_file_name)
        with tarfile.open(tar_file_name, "w:gz") as tar:
            tar.add(dest, arcname=dest.name)

        self.remove_thumbnails_directory()

    def remove_thumbnails_directory(self) -> None:
        """Remove temporary thumbnails directory."""
        dest = self.settings.thumbnails
        for root, dirs, files in dest.walk(top_down=False):
            for name in files:
                (root / name).unlink()
            for name in dirs:
                (root / name).rmdir()
        dest.rmdir()

    def __init__(self, settings: Settings):
        self.settings = settings


def _main() -> None:

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt='%Y%m%d_%H%M%S')

    settings = Settings(Settings.get_args())
    copier = Copier(settings)
    copier.create_thumbnails()
    copier.to_tar()


if __name__ == "__main__":
    _main()
    print("script is complete")
