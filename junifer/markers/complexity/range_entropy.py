"""Provide class for range entropy of a time series."""

# Authors: Amir Omidvarnia <a.omidvarnia@fz-juelich.de>
#          Leonard Sasse <l.sasse@fz-juelich.de>
# License: AGPL

from typing import Dict, List, Optional, Union

from ...api.decorators import register_marker
from ...utils import logger
from ..parcel_aggregation import ParcelAggregation
from ..utils import _range_entropy
from .complexity_base import ComplexityBase


@register_marker
class RangeEntropy(ComplexityBase):
    """Class for range entropy of a time series.

    Parameters
    ----------
    parcellation : str or list of str
        The name(s) of the parcellation(s). Check valid options by calling
        :func:`junifer.data.parcellations.list_parcellations`.
    agg_method : str, optional
        The method to perform aggregation using. Check valid options in
        :func:`junifer.stats.get_aggfunc_by_name` (default "mean").
    agg_method_params : dict, optional
        Parameters to pass to the aggregation function. Check valid options in
        :func:`junifer.stats.get_aggfunc_by_name` (default None).
    mask : str, optional
        The name of the mask to apply to regions before extracting signals.
        Check valid options by calling :func:`junifer.data.masks.list_masks`
        (default None).
    params : dict, optional
        Parameters to pass to the range entropy calculation function. For more
        information, check out ``junifer.markers.utils._range_entropy``.
        If None, value is set to {"m": 2, "tol": 0.5, "delay": 1}
        (default None).
    name : str, optional
        The name of the marker. If None, it will use the class name
        (default None).

    """

    def __init__(
        self,
        parcellation: Union[str, List[str]],
        agg_method: str = "mean",
        agg_method_params: Optional[Dict] = None,
        mask: Union[str, Dict, None] = None,
        params: Optional[Dict] = None,
        name: Optional[str] = None,
    ) -> None:
        super().__init__(
            parcellation=parcellation,
            agg_method=agg_method,
            agg_method_params=agg_method_params,
            mask=mask,
            name=name,
        )
        if params is None:
            self.params = {"m": 2, "tol": 0.5, "delay": 1}
        else:
            self.params = params

    def compute(self, input: Dict, extra_input: Optional[Dict] = None) -> Dict:
        """Compute.

        Take a timeseries of brain areas, and calculate the range entropy[1].

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

            * ``data`` : computed data as a numpy.ndarray.
            * ``col_names`` : column names as a list

        References
        ----------
        .. [1] A. Omidvarnia et al. (2018)
               Range Entropy: A Bridge between Signal Complexity and
               Self-Similarity.
               Entropy, vol. 20, no. 12, p. 962, 2018.

        """
        # Extract aggregated BOLD timeseries
        logger.info("Calculating range entropy.")

        # Calculate range entropy
        parcel_aggregation = ParcelAggregation(
            parcellation=self.parcellation,
            method=self.agg_method,
            method_params=self.agg_method_params,
            mask=self.mask,
        )
        # Compute the parcel aggregation
        output = parcel_aggregation.compute(
            input=input, extra_input=extra_input
        )
        feature_map = _range_entropy(output["data"], self.params)  # 1 X n_roi

        # Initialize output
        out = output.copy()
        out["data"] = feature_map
        out["col_names"] = output["columns"]
        del out["columns"]

        return out
