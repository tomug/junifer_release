"""Provide tests for confound removal."""

# Authors: Federico Raimondo <f.raimondo@fz-juelich.de>
#          Leonard Sasse <l.sasse@fz-juelich.de>
#          Synchon Mandal <s.mandal@fz-juelich.de>
# License: AGPL

import typing
from numpy.testing import assert_array_equal, assert_raises
import pytest
import pandas as pd
from pandas.testing import assert_frame_equal
import numpy as np

import nibabel as nib
from nilearn._utils.exceptions import DimensionError

from junifer.preprocess.confounds import FMRIPrepConfoundRemover
from junifer.testing.datagrabbers import (
    OasisVBMTestingDatagrabber,
    PartlyCloudyTestingDataGrabber,
)
from junifer.datareader import DefaultDataReader

# Set RNG seed for reproducibility
# np.random.seed(1234567)


# def generate_conf_name(
#     size: int = 6, chars: str = string.ascii_uppercase + string.digits
# ) -> str:
#     """Generate configuration name."""
#     return "".join(random.choice(chars) for _ in range(size))


# def _simu_img() -> Tuple[Nifti1Image, Nifti1Image]:
#     # Random 4D volume with 100 time points
#     vol = 100 + 10 * np.random.randn(5, 5, 2, 100)
#     img = Nifti1Image(vol, np.eye(4))
#     # Create an nifti image with the data, and corresponding mask
#     mask = Nifti1Image(np.ones([5, 5, 2]), np.eye(4))
#     return img, mask


def test_FMRIPrepConfoundRemover_init() -> None:
    """Test FMRIPrepConfoundRemover init."""

    with pytest.raises(ValueError, match="keys must be strings"):
        FMRIPrepConfoundRemover(strategy={1: "full"})  # type: ignore

    with pytest.raises(ValueError, match="values must be strings"):
        FMRIPrepConfoundRemover(strategy={"motion": 1})  # type: ignore

    with pytest.raises(ValueError, match="component names"):
        FMRIPrepConfoundRemover(strategy={"wrong": "full"})

    with pytest.raises(ValueError, match="confound types"):
        FMRIPrepConfoundRemover(strategy={"motion": "wrong"})


def test_FMRIPrepConfoundRemover_validate_input() -> None:
    """Test FMRIPrepConfoundRemover validate_input."""
    confound_remover = FMRIPrepConfoundRemover()

    # Input is valid when both BOLD and BOLD_confounds are present

    input = ["T1w"]
    with pytest.raises(ValueError, match="not have the required data"):
        confound_remover.validate_input(input)

    input = ["BOLD"]
    with pytest.raises(ValueError, match="not have the required data"):
        confound_remover.validate_input(input)

    input = ["BOLD", "T1w"]
    with pytest.raises(ValueError, match="not have the required data"):
        confound_remover.validate_input(input)

    input = ["BOLD", "T1w", "BOLD_confounds"]
    confound_remover.validate_input(input)


def test_FMRIPrepConfoundRemover_get_output_kind() -> None:
    """Test FMRIPrepConfoundRemover validate_input."""
    confound_remover = FMRIPrepConfoundRemover()
    inputs = [
        ["BOLD", "T1w", "BOLD_confounds"],
        ["BOLD", "VBM_GM", "BOLD_confounds"],
        ["BOLD", "BOLD_confounds"],
    ]
    # Confound remover works in place
    for input in inputs:
        assert confound_remover.get_output_kind(input) == input


def test_FMRIPrepConfoundRemover__map_adhoc_to_fmriprep() -> None:
    """Test FMRIPrepConfoundRemover adhoc to fmriprep spec mapping."""
    confound_remover = FMRIPrepConfoundRemover()
    # Use non fmriprep variable names
    adhoc_names = [f"var{i}" for i in range(6)]
    adhoc_df = pd.DataFrame(np.random.randn(10, 6), columns=adhoc_names)

    # map them to valid variable names
    fmriprep_names = [
        "trans_x",
        "trans_y",
        "trans_z",
        "rot_x",
        "rot_y",
        "rot_z",
    ]

    # Build mappings dictionary
    mappings = {x: y for x, y in zip(adhoc_names, fmriprep_names)}
    input = {
        "mappings": {"fmriprep": mappings},
        "data": adhoc_df,
    }

    confound_remover._map_adhoc_to_fmriprep(input)
    # This should work in-place
    assert adhoc_df.columns.tolist() == fmriprep_names


def test_FMRIPrepConfoundRemover__process_fmriprep_spec() -> None:
    """Test FMRIPrepConfoundRemover fmriprep spec processing."""

    # Test one strategy, full, no spike
    confound_remover = FMRIPrepConfoundRemover(strategy={"wm_csf": "full"})

    var_names = [
        "csf",
        "white_matter",
        "csf_power2",
        "white_matter_power2",
        "csf_derivative1",
        "white_matter_derivative1",
        "csf_derivative1_power2",
        "white_matter_derivative1_power2",
    ]

    confounds_df = pd.DataFrame(
        np.random.randn(7, len(var_names)), columns=var_names
    )

    out = confound_remover._process_fmriprep_spec({"data": confounds_df})
    to_select, sq_to_compute, der_to_compute, spike_name = out
    assert set(to_select) == set(var_names)
    assert len(sq_to_compute) == 0
    assert len(der_to_compute) == 0
    assert spike_name == "framewise_displacement"

    # Same strategy, but derivatives are not present
    var_names = ["csf", "white_matter", "csf_power2", "white_matter_power2"]
    missing_der_names = ["csf_derivative1", "white_matter_derivative1"]
    missing_sq_names = [
        "csf_derivative1_power2",
        "white_matter_derivative1_power2",
    ]

    all_names = var_names + missing_der_names + missing_sq_names

    confounds_df = pd.DataFrame(
        np.random.randn(7, len(var_names)), columns=var_names
    )
    out = confound_remover._process_fmriprep_spec({"data": confounds_df})
    to_select, sq_to_compute, der_to_compute, spike_name = out
    assert set(to_select) == set(all_names)
    assert set(sq_to_compute) == set(missing_sq_names)
    assert set(der_to_compute) == set(missing_der_names)
    assert spike_name == "framewise_displacement"

    # Same strategy, with spike, only basics are present
    confound_remover = FMRIPrepConfoundRemover(
        strategy={"wm_csf": "full"}, spike=0.2
    )

    var_names = ["csf", "white_matter"]
    missing_der_names = ["csf_derivative1", "white_matter_derivative1"]
    missing_sq_names = [
        "csf_power2",
        "white_matter_power2",
        "csf_derivative1_power2",
        "white_matter_derivative1_power2",
    ]

    all_names = var_names + missing_der_names + missing_sq_names

    confounds_df = pd.DataFrame(
        np.random.randn(7, len(var_names) + 1),
        columns=var_names + ["framewise_displacement"],
    )
    out = confound_remover._process_fmriprep_spec({"data": confounds_df})
    to_select, sq_to_compute, der_to_compute, spike_name = out
    assert set(to_select) == set(all_names)
    assert set(sq_to_compute) == set(missing_sq_names)
    assert set(der_to_compute) == set(missing_der_names)
    assert spike_name == "framewise_displacement"

    # Two component strategy, mixed confounds, no spike
    confound_remover = FMRIPrepConfoundRemover(
        strategy={"wm_csf": "power2", "global_signal": "full"}
    )

    var_names = ["csf", "white_matter", "global_signal"]
    missing_der_names = ["global_signal_derivative1"]
    missing_sq_names = [
        "csf_power2",
        "white_matter_power2",
        "global_signal_power2",
        "global_signal_derivative1_power2",
    ]

    all_names = var_names + missing_der_names + missing_sq_names

    confounds_df = pd.DataFrame(
        np.random.randn(7, len(var_names)), columns=var_names
    )
    out = confound_remover._process_fmriprep_spec({"data": confounds_df})
    to_select, sq_to_compute, der_to_compute, spike_name = out
    assert set(to_select) == set(all_names)
    assert set(sq_to_compute) == set(missing_sq_names)
    assert set(der_to_compute) == set(missing_der_names)
    assert spike_name == "framewise_displacement"

    # Test for wrong columns/strategy pairs

    confound_remover = FMRIPrepConfoundRemover(
        strategy={"wm_csf": "full"}, spike=0.2
    )
    var_names = ["csf"]
    confounds_df = pd.DataFrame(
        np.random.randn(7, len(var_names)), columns=var_names
    )

    msg = r"Missing basic confounds: \['white_matter'\]"
    with pytest.raises(ValueError, match=msg):
        confound_remover._process_fmriprep_spec({"data": confounds_df})

    var_names = ["csf", "white_matter"]
    confounds_df = pd.DataFrame(
        np.random.randn(7, len(var_names)), columns=var_names
    )

    msg = r"Missing framewise_displacement"
    with pytest.raises(ValueError, match=msg):
        confound_remover._process_fmriprep_spec({"data": confounds_df})


def test_FMRIPrepConfoundRemover__pick_confounds_adhoc() -> None:
    """Test FMRIPrepConfoundRemover pick confounds on adhoc confounds."""
    confound_remover = FMRIPrepConfoundRemover(strategy={"wm_csf": "full"})
    # Use non fmriprep variable names
    adhoc_names = [f"var{i}" for i in range(2)]
    adhoc_df = pd.DataFrame(np.random.randn(10, 2), columns=adhoc_names)

    # map them to valid variable names
    fmriprep_names = ["csf", "white_matter"]
    fmriprep_all_vars = [
        "csf",
        "white_matter",
        "csf_power2",
        "white_matter_power2",
        "csf_derivative1",
        "white_matter_derivative1",
        "csf_derivative1_power2",
        "white_matter_derivative1_power2",
    ]

    # Build mappings dictionary
    mappings = {x: y for x, y in zip(adhoc_names, fmriprep_names)}
    input = {
        "mappings": {"fmriprep": mappings},
        "data": adhoc_df,
        "format": "adhoc",
    }

    out = confound_remover._pick_confounds(input)
    assert set(out.columns) == set(fmriprep_all_vars)


def test_FMRIPRepConfoundRemover__pick_confounds_fmriprep() -> None:
    """Test FMRIPrepConfoundRemover pick confounds on fmriprep confounds."""
    confound_remover = FMRIPrepConfoundRemover(
        strategy={"wm_csf": "full"}, spike=0.2
    )
    fmriprep_all_vars = [
        "csf",
        "white_matter",
        "csf_power2",
        "white_matter_power2",
        "csf_derivative1",
        "white_matter_derivative1",
        "csf_derivative1_power2",
        "white_matter_derivative1_power2",
    ]

    reader = DefaultDataReader()
    out1, out2 = None, None
    with PartlyCloudyTestingDataGrabber() as dg:
        input = dg["sub-01"]
        input = reader.fit_transform(input)
        out1 = confound_remover._pick_confounds(input["BOLD_confounds"])
        assert set(out1.columns) == set(fmriprep_all_vars + ["spike"])

    with PartlyCloudyTestingDataGrabber(reduce_confounds=False) as dg:
        input = dg["sub-01"]
        input = reader.fit_transform(input)
        out2 = confound_remover._pick_confounds(input["BOLD_confounds"])
        assert set(out2.columns) == set(fmriprep_all_vars + ["spike"])

    assert_frame_equal(out1, out2)
    # TODO: Test if fmriprep returns the same derivatives/power2 as we compute


def test_FMRIPrepConfoundRemover__validate_data() -> None:
    """Test FMRIPrepConfoundRemover validate data."""
    confound_remover = FMRIPrepConfoundRemover(strategy={"wm_csf": "full"})
    reader = DefaultDataReader()
    with OasisVBMTestingDatagrabber() as dg:
        input = dg["sub-01"]
        input = reader.fit_transform(input)
        new_input = input["VBM_GM"]
        with pytest.raises(
            DimensionError, match="incompatible dimensionality"
        ):
            confound_remover._validate_data(new_input, None)

    with PartlyCloudyTestingDataGrabber(reduce_confounds=False) as dg:
        input = dg["sub-01"]
        input = reader.fit_transform(input)
        new_input = input["BOLD"]

        with pytest.raises(ValueError, match="No extra input"):
            confound_remover._validate_data(new_input, None)
        with pytest.raises(ValueError, match="No BOLD_confounds provided"):
            confound_remover._validate_data(new_input, {})
        with pytest.raises(
            ValueError, match="No BOLD_confounds data provided"
        ):
            confound_remover._validate_data(new_input, {"BOLD_confounds": {}})

        extra_input = {
            "BOLD_confounds": {"data": "wrong"},
        }
        msg = "must be a pandas dataframe"
        with pytest.raises(ValueError, match=msg):
            confound_remover._validate_data(new_input, extra_input)

        extra_input = {"BOLD_confounds": {"data": pd.DataFrame()}}
        with pytest.raises(ValueError, match="Image time series and"):
            confound_remover._validate_data(new_input, extra_input)

        extra_input = {
            "BOLD_confounds": {"data": input["BOLD_confounds"]["data"]}
        }
        with pytest.raises(ValueError, match="format must be specified"):
            confound_remover._validate_data(new_input, extra_input)

        extra_input = {
            "BOLD_confounds": {
                "data": input["BOLD_confounds"]["data"],
                "format": "wrong",
            }
        }
        with pytest.raises(ValueError, match="Invalid confounds format wrong"):
            confound_remover._validate_data(new_input, extra_input)

        extra_input = {
            "BOLD_confounds": {
                "data": input["BOLD_confounds"]["data"],
                "format": "adhoc",
            }
        }
        with pytest.raises(ValueError, match="variables names mappings"):
            confound_remover._validate_data(new_input, extra_input)

        extra_input = {
            "BOLD_confounds": {
                "data": input["BOLD_confounds"]["data"],
                "format": "adhoc",
                "mappings": {},
            }
        }
        with pytest.raises(ValueError, match="mappings to fmriprep"):
            confound_remover._validate_data(new_input, extra_input)

        extra_input = {
            "BOLD_confounds": {
                "data": input["BOLD_confounds"]["data"],
                "format": "adhoc",
                "mappings": {
                    "fmriprep": {
                        "rot_x": "wrong",
                        "rot_y": "rot_z",
                        "rot_z": "rot_y",
                    }
                },
            }
        }
        with pytest.raises(ValueError, match=r"names: \['wrong'\]"):
            confound_remover._validate_data(new_input, extra_input)

        extra_input = {
            "BOLD_confounds": {
                "data": input["BOLD_confounds"]["data"],
                "format": "adhoc",
                "mappings": {
                    "fmriprep": {
                        "wrong": "rot_x",
                        "rot_y": "rot_z",
                        "rot_z": "rot_y",
                    }
                },
            }
        }
        with pytest.raises(ValueError, match=r"Missing columns: \['wrong'\]"):
            confound_remover._validate_data(new_input, extra_input)


def test_FMRIPrepConfoundRemover__remove_confounds() -> None:
    """Test FMRIPrepConfoundRemover remove confounds."""
    confound_remover = FMRIPrepConfoundRemover(
        strategy={"wm_csf": "full"}, spike=0.2
    )
    reader = DefaultDataReader()
    with PartlyCloudyTestingDataGrabber(reduce_confounds=False) as dg:
        input = dg["sub-01"]
        input = reader.fit_transform(input)
        confounds = confound_remover._pick_confounds(input["BOLD_confounds"])
        raw_bold = input["BOLD"]["data"]
        clean_bold = confound_remover._remove_confounds(
            bold_img=raw_bold, confounds_df=confounds
        )
        clean_bold = typing.cast(nib.Nifti1Image, clean_bold)
        # TODO: Find a better way to test functionality here
        assert (
            clean_bold.header.get_zooms()  # type: ignore
            == raw_bold.header.get_zooms()
        )
        assert clean_bold.get_fdata().shape == raw_bold.get_fdata().shape
    # TODO: Test confound remover with mask, needs #79 to be implemented


def test_FMRIPrepConfoundRemover_preprocess() -> None:
    """Test FMRIPrepConfoundRemover with all confounds present."""

    # need reader for the data
    reader = DefaultDataReader()
    # All strategies full, no spike
    confound_remover = FMRIPrepConfoundRemover()

    with PartlyCloudyTestingDataGrabber(reduce_confounds=False) as dg:
        input = dg["sub-01"]
        input = reader.fit_transform(input)
        orig_bold = input["BOLD"]["data"].get_fdata().copy()
        pre_input = input["BOLD"]
        pre_extra_input = {"BOLD_confounds": input["BOLD_confounds"]}
        key, output = confound_remover.preprocess(pre_input, pre_extra_input)
        trans_bold = output["data"].get_fdata()
        # Transformation is in place
        assert_array_equal(trans_bold, input["BOLD"]["data"].get_fdata())

        # Data should have the same shape
        assert orig_bold.shape == trans_bold.shape

        # but be different
        assert_raises(
            AssertionError, assert_array_equal, orig_bold, trans_bold
        )
        assert key == "BOLD"


def test_FMRIPrepConfoundRemover_fit_transform() -> None:
    """Test FMRIPrepConfoundRemover with all confounds present."""

    # need reader for the data
    reader = DefaultDataReader()
    # All strategies full, no spike
    confound_remover = FMRIPrepConfoundRemover()

    with PartlyCloudyTestingDataGrabber(reduce_confounds=False) as dg:
        input = dg["sub-01"]
        input = reader.fit_transform(input)
        orig_bold = input["BOLD"]["data"].get_fdata().copy()
        output = confound_remover.fit_transform(input)
        trans_bold = output["BOLD"]["data"].get_fdata()
        # Transformation is in place
        assert_array_equal(trans_bold, input["BOLD"]["data"].get_fdata())

        # Data should have the same shape
        assert orig_bold.shape == trans_bold.shape

        # but be different
        assert_raises(
            AssertionError, assert_array_equal, orig_bold, trans_bold
        )

        assert output["meta"] == input["meta"]  # general meta does not change
        assert "meta" in output["BOLD"]
        assert "preprocess" in output["BOLD"]["meta"]
        t_meta = output["BOLD"]["meta"]["preprocess"]
        assert t_meta["class"] == "FMRIPrepConfoundRemover"
        # It should have all the default parameters
        assert t_meta["strategy"] == confound_remover.strategy
        assert t_meta["spike"] is None
        assert t_meta["detrend"] is True
        assert t_meta["standardize"] is True
        assert t_meta["low_pass"] is None
        assert t_meta["high_pass"] is None
        assert t_meta["t_r"] is None
        assert t_meta["mask_img"] is None
