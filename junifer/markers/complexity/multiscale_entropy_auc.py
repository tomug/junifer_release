"""Provide class for the AUC of multiscale entropy of a time series."""

# Authors: Amir Omidvarnia <a.omidvarnia@fz-juelich.de>
#          Leonard Sasse <l.sasse@fz-juelich.de>
# License: AGPL

from typing import Dict, List, Optional, Union

from ...api.decorators import register_marker
from ...utils import logger
from ..utils import _multiscale_entropy_auc
from .complexity_base import ComplexityBase


@register_marker
class MultiscaleEntropyAUC(ComplexityBase):
    """Class for AUC of multiscale entropy of a time series.

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
        Parameters to pass to the AUC of multiscale entropy calculation
        function. For more information, check out
        :func:`junfier.markers.utils._multiscale_entropy_auc`. If None, value
        is set to {"m": 2, "tol": 0.5, "scale": 10} (default None).
    name : str, optional
        The name of the marker. If None, it will use the class name
        (default None).

    """

    def __init__(
        self,
        parcellation: Union[str, List[str]],
        agg_method: str = "mean",
        agg_method_params: Optional[Dict] = None,
        mask: Optional[str] = None,
        params: Optional[Dict] = None,
        name: Optional[str] = None,
    ) -> None:
        # from ptpython.repl import embed
        # print('Stop: __init__')
        # embed(globals(), locals())
        super().__init__(
            parcellation=parcellation,
            agg_method=agg_method,
            agg_method_params=agg_method_params,
            mask=mask,
            name=name,
        )
        if params is None:
            self.params = {"m": 2, "tol": 0.5, "scale": 10}
        else:
            self.params = params

    def compute(self, input: Dict, extra_input: Optional[Dict] = None) -> Dict:
        """Compute.

        Take a timeseries of brain areas, and calculate the AUC of
        multiscale entropy [1].

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
            * ``row_names`` : row names as a list
            * ``col_names`` : column names as a list
            * ``matrix_kind`` : the kind of matrix (tril, triu or full)

        References
        ----------
        .. [1] Costa, M., Goldberger, A. L., & Peng, C. K.
               Multiscale entropy analysis of complex physiologic time series.
               Physical review letters, 89(6), 068102, 2002.

        See also
        ---------
        https://neuropsychology.github.io/NeuroKit/functions/complexity.html

        """
        # Extract aggregated BOLD timeseries
        bold_timeseries = self._extract_bold_timeseries(input=input)

        # Calculate AUC of multiscale entropy
        logger.info("Calculating AUC of multiscale entropy.")
        feature_map = _multiscale_entropy_auc(
            bold_timeseries["data"], self.params
        )  # n_roi X 1
        # Initialize output
        output = {}
        output["data"] = feature_map
        output["col_names"] = "multiscale_entropy_auc"
        output["row_names"] = bold_timeseries["columns"]
        return output
