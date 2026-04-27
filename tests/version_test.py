import pathlib
import re

import cornerstone_forge as cf


def test_version():
    assert isinstance(cf.__version__, str)
    pyproject = pathlib.Path("pyproject.toml")
    if pyproject.is_file():
        contents = pyproject.read_text()
        match = re.search('version = "([^"]*)"', contents)
        assert match and match.groups(1)[0] == cf.__version__
