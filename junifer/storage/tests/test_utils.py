"""Provide tests for utils."""

# Authors: Federico Raimondo <f.raimondo@fz-juelich.de>
#          Synchon Mandal <s.mandal@fz-juelich.de>
# License: AGPL

from typing import Dict, List, Tuple, Union

import pytest

from junifer.storage.utils import (
    element_to_prefix,
    process_meta,
)


def test_process_meta_invalid_metadata_type() -> None:
    """Test invalid metadata type check for metadata hash processing."""
    meta = None
    with pytest.raises(ValueError, match=r"`meta` must be a dict"):
        process_meta(meta)  # type: ignore


# TODO: parameterize
def test_process_meta_hash() -> None:
    """Test metadata hash processing."""
    meta = {
        "element": {"foo": "bar"},
        "A": 1,
        "B": [2, 3, 4, 5, 6],
        "dependencies": ["numpy"],
    }
    hash1, _, element1 = process_meta(meta)
    assert element1 == {"foo": "bar"}

    meta = {
        "element": {"foo": "baz"},
        "B": [2, 3, 4, 5, 6],
        "A": 1,
        "dependencies": ["numpy"],
    }
    hash2, _, element2 = process_meta(meta)
    assert hash1 == hash2
    assert element2 == {"foo": "baz"}

    meta = {
        "element": {"foo": "bar"},
        "A": 1,
        "B": [2, 3, 1, 5, 6],
        "dependencies": ["numpy"],
    }
    hash3, _, element3 = process_meta(meta)
    assert hash1 != hash3
    assert element3 == element1

    meta4 = {
        "element": {"foo": "bar"},
        "B": {
            "B2": [2, 3, 4, 5, 6],
            "B1": [9.22, 3.14, 1.41, 5.67, 6.28],
            "B3": (1, "car"),
        },
        "A": 1,
        "dependencies": ["numpy"],
    }

    meta5 = {
        "A": 1,
        "B": {
            "B3": (1, "car"),
            "B1": [9.22, 3.14, 1.41, 5.67, 6.28],
            "B2": [2, 3, 4, 5, 6],
        },
        "element": {"foo": "baz"},
        "dependencies": ["numpy"],
    }

    hash4, _, _ = process_meta(meta4)
    hash5, _, _ = process_meta(meta5)
    assert hash4 == hash5

    # Different element keys should give a different hash
    meta6 = {
        "A": 1,
        "B": {
            "B3": (1, "car"),
            "B1": [9.22, 3.14, 1.41, 5.67, 6.28],
            "B2": [2, 3, 4, 5, 6],
        },
        "element": {"bar": "baz"},
        "dependencies": ["numpy"],
    }
    hash6, _, _ = process_meta(meta6)
    assert hash4 != hash6


def test_process_meta_invalid_metadata_key() -> None:
    """Test invalid metadata key check for metadata hash processing."""
    meta = {}
    with pytest.raises(ValueError, match=r"element"):
        process_meta(meta)

    meta = {"element": {}}
    with pytest.raises(ValueError, match=r"dependencies"):
        process_meta(meta)


@pytest.mark.parametrize(
    "meta,elements",
    [
        (
            {
                "element": {"foo": "bar"},
                "A": 1,
                "B": [2, 3, 4, 5, 6],
                "dependencies": ["numpy"],
            },
            ["foo"],
        ),
        (
            {
                "element": {"subject": "foo", "session": "bar"},
                "B": [2, 3, 4, 5, 6],
                "A": 1,
                "dependencies": ["numpy"],
            },
            ["subject", "session"],
        ),
    ],
)
def test_process_meta_element(meta: Dict, elements: List[str]) -> None:
    """Test metadata element after processing.

    Parameters
    ----------
    meta : dict
        The parametrized metadata dictionary.
    elements : list of str
        The parametrized elements to assert against.

    """
    hash1, processed_meta, _ = process_meta(meta)
    assert "_element_keys" in processed_meta
    assert processed_meta["_element_keys"] == elements
    assert "A" in processed_meta
    assert "B" in processed_meta
    assert "element" not in processed_meta


@pytest.mark.parametrize(
    "element,prefix",
    [
        ({"subject": "sub-01"}, "element_sub-01_"),
        ({"subject": 1}, "element_1_"),
        ({"subject": "sub-01", "session": "ses-02"}, "element_sub-01_ses-02_"),
        ({"subject": 1, "session": 2}, "element_1_2_"),
    ],
)
def test_element_to_prefix(
    element: Dict, prefix: str
) -> None:
    """Test converting element to prefix (for file naming).

    Parameters
    ----------
    element : str, int, dict or tuple
        The parameterized element.
    prefix : str
        The parametrized prefix to assert against.

    """
    prefix_generated = element_to_prefix(element)
    assert prefix_generated == prefix


def test_element_to_prefix_invalid_type() -> None:
    """Test element to prefix type checking."""
    element = 2.3
    with pytest.raises(ValueError, match=r"must be a dict"):
        element_to_prefix(element)  # type: ignore
