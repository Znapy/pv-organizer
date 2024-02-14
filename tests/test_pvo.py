#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for main script.

These functional (not unit) tests uses the file subsystem without mock.

Copyright 2024 Alic Znapy
SPDX-License-Identifier: Apache-2.0
"""

import argparse
import logging
from pathlib import Path
from pytest import fixture, raises
from typing import Optional

from pvo import Settings, Copier


def _arg_params() -> dict[str, Optional[str]]:
    """Create settings for reusing in tests."""
    return {"source": None, "destination": None,
            "loglevel": None, "plain": None,
            "small_size": None, "frames_percents": None}


@fixture(scope="module")
def settings_without_args() -> Settings:
    """Create settings for reusing in tests."""
    return Settings(argparse.Namespace(**_arg_params()))


class TestSettings:
    """Test class."""

    @staticmethod
    def test_set_log_level() -> None:
        """Test that the log level sets from launch parameter."""
        func, logger = Settings.set_log_level, logging.getLogger()
        launch_level = logger.level

        try:

            func(argparse.Namespace(loglevel="DEBUG"))
            assert logger.level == logging.DEBUG

            func(argparse.Namespace(loglevel="INFO"))
            assert logger.level == logging.INFO

            func(argparse.Namespace(loglevel="WARNING"))
            assert logger.level == logging.WARNING

            func(argparse.Namespace(loglevel="ERROR"))
            assert logger.level == logging.ERROR

        finally:
            logger.setLevel(launch_level)

    def test_set_source_from_defaults(
            self, settings_without_args: Settings) -> None:
        """Test it gets from defaults if there is no lanch parameter."""
        settings_without_args.set_source()
        assert settings_without_args.source == Path("tests/examples").resolve()

    def test_set_source_from_args(self) -> None:
        arg_params = _arg_params()
        arg_params["source"] = "./tests"
        settings = Settings(argparse.Namespace(**arg_params))
        settings.set_source()
        assert settings.source == Path(str(arg_params["source"])).resolve()

    def test_set_source_from_args_with_source_not_exist(self) -> None:
        arg_params = _arg_params()
        arg_params["source"] = "./a/b"
        with raises(RuntimeError, match="does not exist"):
            Settings(argparse.Namespace(**arg_params))

    def test_set_source_from_args_with_source_not_dir(self) -> None:
        arg_params = _arg_params()
        arg_params["source"] = "tests/examples/a.txt"
        with raises(RuntimeError, match="is not a directory"):
            Settings(argparse.Namespace(**arg_params))


class TestCopier:

    @staticmethod
    def test_frames_numbers_asis() -> None:
        func = Copier.frames_numbers
        assert func([1, 35, 65, 99], 100) == [1, 35, 65, 99]

    @staticmethod
    def test_frames_numbers_x10() -> None:
        func = Copier.frames_numbers
        assert func([1, 35, 65, 99], 1000) == [10, 350, 650, 990]

    @staticmethod
    def test_frames_numbers_max99() -> None:
        func = Copier.frames_numbers
        assert func([1, 35, 65, 99], 99) == [1, 35, 65, 99]

    @staticmethod
    def test_frames_numbers_max4() -> None:
        func = Copier.frames_numbers
        assert func([1, 35, 65, 99], 4) == [1, 2, 3, 4]

    @staticmethod
    def test_frames_numbers_max2() -> None:
        func = Copier.frames_numbers
        assert func([1, 35, 65, 99], 2) == [1, 1, 2, 2]

    @staticmethod
    def test_frames_numbers_max1() -> None:
        func = Copier.frames_numbers
        assert func([1, 35, 65, 99], 1) == [1, 1, 1, 1]

    @staticmethod
    def test_frames_numbers_0_100() -> None:
        func = Copier.frames_numbers
        assert func([0, 100, 0, 100], 99) == [0, 99, 0, 99]

    def test_examples(self, settings_without_args: Settings) -> None:
        copier = Copier(settings_without_args)
        copier.create_thumbnails()
        path = settings_without_args.thumbnails

        try:

            assert path.is_dir()
            assert not (path / "a.txt").exists()
            assert (path / "A.JPG").is_file()
            assert (path / "A.JPG").stat().st_size < 3_000
            assert (path / "A.png").is_file()
            assert (path / "flag.mp4.jpg").is_file()
            assert (path / "flag.mp4.jpg").stat().st_size < 20_000
            assert (path / "some text.gif").is_file()
            assert not (path / "NotImage.jpg").exists()

            subdir_1 = path / "subdir_1"
            assert subdir_1.is_dir()
            assert (subdir_1 / "B.jpg").is_file()
            assert (subdir_1 / "without_files").is_dir()
            assert (subdir_1 / "without_files" / "empty").is_dir()

            subdir_2 = subdir_1 / "subdir_2"
            assert subdir_2.is_dir()
            assert (subdir_2 / "C.jpg").is_file()

            subdir_3 = subdir_1 / "subdir_3"
            assert subdir_3.is_dir()
            assert (subdir_3 / "subdir_4").is_dir()
            assert (subdir_3 / "subdir_4" / "d.gif").is_file()

        finally:
            copier.remove_thumbnails_directory()
