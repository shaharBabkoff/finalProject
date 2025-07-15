import abc
import typing
from pathlib import Path

from cgshop2025_pyutils.data_schemas.instance import Cgshop2025Instance

from ..io import read_instance


class InstanceBaseDatabase(abc.ABC):
    """
    Abstract base class (ABC) for accessing instance databases.
    Subclasses must implement methods to iterate over instances and retrieve a specific instance by name.
    """

    def __init__(self, path: str, enable_cache: bool = False):
        """
        Initializes the InstanceBaseDatabase with a path and optional caching.
        :param path: Path to the folder containing the instance files. The instance files
                     can be in subfolders, but their names must follow the pattern NAME.instance.json.
        :param enable_cache: Whether to enable caching of loaded instances. Caching can
                             consume a significant amount of memory.
        """
        self._path = Path(path)
        self._is_cache_enabled = enable_cache
        self._cache: dict[str, Cgshop2025Instance] = {}
        self.extension = ".json"

        if not self._path.exists():
            msg = f"The folder {self._path.resolve()} does not exist"
            raise ValueError(msg)

    def _filename_fits_name(self, filename: str, name: str) -> bool:
        """Checks if the filename matches the given instance name and follows the naming convention."""
        if not self._filename_fits_instance_convention(filename):
            return False
        return filename.split(".")[0] == name

    def _filename_fits_instance_convention(self, filename: str) -> bool:
        """Checks if the file follows the required instance file naming convention (i.e., ends with .json)."""
        return filename.endswith(self.extension)

    def read(self, f) -> Cgshop2025Instance:
        """Reads an instance from a file."""
        return read_instance(f)

    def _cache_and_return(self, instance: Cgshop2025Instance) -> Cgshop2025Instance:
        """Caches the instance if caching is enabled and returns the instance."""
        if self._is_cache_enabled:
            self._cache[instance.instance_uid] = instance
        return instance

    def _is_hidden_folder_name(self, name: str) -> bool:
        """
        Checks if the folder is hidden based on UNIX naming conventions.
        Hidden folders start with a dot (.) or __ (Mac OS).
        """
        return name.startswith((".", "__"))

    def _is_hidden_folder(self, path: str) -> bool:
        """Checks if any part of the folder path is hidden."""
        return any(self._is_hidden_folder_name(folder) for folder in Path(path).parts)

    def _extract_instance_name_from_path(self, path: str) -> str:
        """Extracts the instance name from the given file path."""
        filename = Path(path).name
        return filename.split(".")[0]

    @abc.abstractmethod
    def __iter__(self) -> typing.Iterator[Cgshop2025Instance]:
        """
        Abstract method to iterate over all instances in the database.
        :return: An iterable of Cgshop2025Instance objects.
        """

    @abc.abstractmethod
    def __getitem__(self, name: str) -> Cgshop2025Instance:
        """
        Abstract method to retrieve an instance by name.
        :param name: The name of the instance to retrieve.
        :return: The Cgshop2025Instance object corresponding to the given name.
        :raises KeyError: If the instance with the given name is not found.
        """
