"""Provide class for regional homogeneity (ReHo) on parcels."""

# Authors: Synchon Mandal <s.mandal@fz-juelich.de>
# License: AGPL


from typing import TYPE_CHECKING, Any, Dict, List, Optional

import numpy as np

from ..api.decorators import register_marker
from ..utils import logger
from .base import BaseMarker
from .parcel_aggregation import ParcelAggregation


if TYPE_CHECKING:
    from junifer.storage import BaseFeatureStorage


@register_marker
class ReHoParcels(BaseMarker):
    """Class for regional homogeneity on parcels.

    Parameters
    ----------
    parcellation : str
        The name of the parcellation. Check valid options by calling
        :func:`junifer.data.parcellations.list_parcellations`.
    name : str, optional
        The name of the marker. If None, it will use the class name
        (default None).

    """

    def __init__(
        self,
        parcellation: str,
        name: Optional[str] = None,
    ) -> None:
        self.parcellation = parcellation
        super().__init__(name=name)

    def get_valid_inputs(self) -> List[str]:
        """Get valid data types for input.

        Returns
        -------
        list of str
            The list of data types that can be used as input for this marker.

        """
        return ["BOLD"]

    def get_output_kind(self, input: List[str]) -> List[str]:
        """Get output kind.

        Parameters
        ----------
        input : list of str
            The input to the marker. The list must contain the
            available Junifer Data dictionary keys.

        Returns
        -------
        list of str
            The updated list of output kinds, as storage possibilities.

        """
        return ["table"]

    def store(
        self,
        kind: str,
        out: Dict[str, Any],
        storage: "BaseFeatureStorage",
    ) -> None:
        """Store.

        Parameters
        ----------
        kind : {"BOLD"}
            The data kind to store.
        out : dict
            The computed result as a dictionary to store.
        storage : storage-like
            The storage class, for example, SQLiteFeatureStorage.

        """
        logger.debug(f"Storing {kind} in {storage}")
        storage.store(kind="table", **out)

    def compute(
        self,
        input: Dict[str, Any],
        extra_input: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Compute.

        For a given voxel, identifies the set of neighbours within a certain
        radius and then calculates Kendall's W for the voxel and its
        neighbours for the timepoints in the BOLD signal. For more
        information about the method, please check [1]_.

        Parameters
        ----------
        input : dict
            The BOLD data as dictionary.
        extra_input : dict, optional
            The other fields in the pipeline data object (default None).

        Returns
        -------
        dict
            The computed result as dictionary. The dictionary has the following
            keys:

            * ``data`` : the actual computed values as a 1D numpy.ndarray
            * ``columns`` : the column labels for the parcels as a list
            * ``row_names`` : ``None``

        References
        ----------
        .. [1] Jiang, L., & Zuo, X. N. (2016).
               Regional Homogeneity: A Multimodal, Multiscale Neuroimaging
               Marker of the Human Connectome.
               The Neuroscientist, Volume 22(5), Pages 486–505.
               https://doi.org/10.1177/1073858415595004

        """
        logger.debug("Calculating ReHO for parcels.")
        # Initialize parcel aggregation
        parcel_aggregation = ParcelAggregation(
            parcellation=self.parcellation,
            method="kendall_w",
            on="BOLD",
        )
        # Perform aggregation
        output = parcel_aggregation.compute(
            input=input, extra_input=extra_input
        )
        # Expand row dimension
        output["data"] = output["data"][np.newaxis, :]
        # Delete row_names
        del output["row_names"]
        # Set row_cols_name to None
        output["rows_col_name"] = None
        return output
