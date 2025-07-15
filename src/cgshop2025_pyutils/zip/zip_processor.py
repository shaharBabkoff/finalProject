"""
This file contains the ZipSolutionIterator which can read a zip and return all solutions
in it. It is designed to be robust and include basic security features.
"""

from os import PathLike
from typing import BinaryIO, Iterator, Union
from zipfile import BadZipFile, ZipFile

from pydantic import ValidationError

from cgshop2025_pyutils.data_schemas.solution import Cgshop2025Solution

from ..io import read_solution
from .zip_reader_errors import (
    BadZipChecker,
    InvalidZipError,
    NoSolutionsError,
)


class BadSolutionFile(Exception):
    """Custom exception raised for invalid solution files in the zip."""

    def __init__(self, msg: str, file_name: str):
        super().__init__(msg)
        self.file_name = file_name

    def __str__(self):
        return self.args[0]


class ZipSolutionIterator:
    """
    Iterates over all solutions in a zip file.
    After initializing the class, use the instance as an iterator.
    Example:
    ```
    zsi = ZipSolutionIterator("./myzip.zip")
    for solution in zsi:
        print(solution.instance_name)
    ```
    """

    def __init__(
        self,
        path_or_file: Union[BinaryIO, str, PathLike],
        file_size_limit: int = 250 * 1_000_000,  # 250 MB file size limit
        zip_size_limit: int = 2_000 * 1_000_000,  # 2 GB zip size limit
        solution_extensions=(".solution.json",),
    ):
        self.path = path_or_file
        self._checker = BadZipChecker(
            file_size_limit=file_size_limit, zip_size_limit=zip_size_limit
        )
        self._solution_extensions = solution_extensions

    def _check_if_bad_zip(self, zip_file: ZipFile):
        """Checks the validity and security of the zip file using the BadZipChecker."""
        self._checker(zip_file)

    def _is_hidden_folder_name(self, name: str) -> bool:
        """Returns True if the folder is hidden (starts with . or __)."""
        return len(name) > 1 and (name[0] == "." or name[:2] == "__")

    def _is_solution_filename(self, name: str) -> bool:
        """Checks if the file is a valid solution file based on its extension and visibility."""
        # Check extension and skip hidden files/directories
        return any(name.lower().endswith(extension) for extension in self._solution_extensions) and not any(
            self._is_hidden_folder_name(s) for s in name.split("/")
        )

    def _iterate_solution_filenames(self, zip_file: ZipFile) -> Iterator[str]:
        """Yields filenames that match the allowed solution extensions."""
        had_filename = False
        for filename in zip_file.namelist():
            if self._is_solution_filename(filename):
                had_filename = True
                yield filename
        if not had_filename:
            raise NoSolutionsError()

    def __iter__(self) -> Iterator[Cgshop2025Solution]:
        """
        Iterates over all solutions in the zip file.
        :return: An iterator over valid Cgshop2025Solution objects.
        """
        found_an_instance = False
        try:
            with ZipFile(self.path) as zip_file:
                self._check_if_bad_zip(zip_file)
                for file_name in self._iterate_solution_filenames(zip_file):
                    meta = {
                        "zip_info": {
                            "zip_file": zip_file.filename,
                            "file_in_zip": file_name,
                        }
                    }
                    with zip_file.open(file_name, "r") as sol_file:
                        try:
                            solution = read_solution(sol_file)
                            solution.meta.update(meta)
                            found_an_instance = True
                            yield solution
                        except ValidationError as e:
                            msg = f"Error in file '{file_name}': {e}"
                            raise BadSolutionFile(msg,file_name=str(file_name)) from e
        except BadZipFile as e:
            msg = f"Invalid ZIP file: {e}"
            raise InvalidZipError(msg) from e

        if not found_an_instance:
            raise NoSolutionsError()
