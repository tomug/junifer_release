import os
from itertools import product
from pathlib import Path
from ..datagrabber import DataladDataGrabber
from ..api.decorators import register_datagrabber


@register_datagrabber
class JuselessUKBVBM(DataladDataGrabber):
    """Juseless UKB VMG DataGrabber class.

    Implements a DataGrabber to access the UKB VBM data in Juseless.

    """

    def __init__(self, datadir=None):
        """Initialize a JuselessUKBVBM object.

        Parameters
        ----------
        datadir : str or Path
            That directory where the datalad dataset will be cloned. If None,
            (default), the datalad dataset will be cloned into a temporary
            directory.
        """
        uri = 'ria+http://ukb.ds.inm7.de#~cat_m0wp1'
        rootdir = 'm0wp1'
        types = ['VBM_GM']
        super().__init__(
            types=types, datadir=datadir, uri=uri, rootdir=rootdir)

    def get_elements(self):
        """Get the list of subjects in the dataset.

        Returns
        -------
        elements : list[str]
            The list of subjects in the dataset.
        """
        elems = []
        for x in self.datadir.glob('*._T1w.nii.gz'):
            sub, ses = x.name.split('_')
            sub = sub.replace('m0wp1', '')
            ses = ses[:5]
            elems.append((sub, ses))
        return elems

    def __getitem__(self, element):
        """Index one element in the dataset.

        Parameters
        ----------
        element : tuple[str, str]
            The element to be indexed. First element in the tuple is the
            subject, second element is the session.

        Returns
        -------
        out : dict[str -> Path]
            Dictionary of paths for each type of data required for the
            specified element.
        """
        sub, ses = element
        out = {}

        out['VBM_GM'] = self.datadir / f'm0wp1{sub}_{ses}_T1w.nii.gz'
        out['meta'] = dict(datagrabber=self.get_meta())
        self._dataset_get(out)
        out['meta']['element'] = dict(subject=sub, session=ses)
        return out


@register_datagrabber
class HCP1200(DataladDataGrabber):
    """ Human Connectome Project Datalad DataGrabber class

    Implements a DataGrabber to access the Human Connectome Project

    """

    def __init__(
        self, datadir=None, subjects=None, tasks=None, phase_encodings=None
    ):
        """Initialize a HCP object.

        Parameters
        ----------
        datadir : str or Path
            That directory where the datalad dataset will be cloned. If None,
            (default), the datalad dataset will be cloned into a temporary
            directory.
        subjects : str or list of strings
            HCP subject ID's. If 'None' (default), all available subjects are
            selected
        tasks : str or list of strings
            HCP task sessions. If 'None' (default), all available task
            sessions are selected. Can be 'REST1', 'REST2', 'SOCIAL', 'WM',
            'RELATIONAL', 'EMOTION', 'LANGUAGE', 'GAMBLING', 'MOTOR', or a
            list consisting of these names.
        phase_encoding : str or list of strings
            HCP phase encoding directions. Can be 'LR' or 'RL'. If 'None'
            (default) both will be used.

        """
        uri = (
            'https://github.com/datalad-datasets/'
            'human-connectome-project-openaccess.git'
        )
        rootdir = 'HCP1200'
        types = ['BOLD']
        super().__init__(
            types=types, datadir=datadir, uri=uri, rootdir=rootdir
        )

        self.subjects = subjects
        self.tasks = tasks
        self.phase_encodings = phase_encodings

        if isinstance(self.subjects, str):
            self.subjects = [self.subjects]
        if isinstance(self.tasks, str):
            self.tasks = [self.tasks]
        if isinstance(self.phase_encodings, str):
            self.phase_encodings = [self.phase_encodings]

        if self.tasks is None:
            self.tasks = [
                'REST1',
                'REST2',
                'SOCIAL',
                'WM',
                'RELATIONAL',
                'EMOTION',
                'LANGUAGE',
                'GAMBLING',
                'MOTOR',
            ]

        if self.phase_encodings is None:
            self.phase_encodings = ["LR", "RL"]

    def get_elements(self):
        """Get the list of subjects in the dataset.

        Returns
        -------
        elements : list[str]
            The list of subjects in the dataset.
        """
        elems = []

        if self.subjects is None:
            self.subjects = os.listdir(self.datadir)

        for subject, task, phase_encoding in product(
            self.subjects, self.tasks, self.phase_encodings
        ):
            elems.append((subject, task, phase_encoding))

        return elems

    def __getitem__(self, element):
        """Index one element in the dataset.

        Parameters
        ----------
        element : tuple[str, str]
            The element to be indexed. First element in the tuple is the
            subject, second element is the task, third element is the
            phase encoding direction.

        Returns
        -------
        out : dict[str -> Path]
            Dictionary of paths for each type of data required for the
            specified element.
        """
        sub, task, phase_encoding = element
        out = {}

        if 'REST' in task:
            task_name = f'rfMRI_{task}'
        else:
            task_name = f'tfMRI_{task}'

        out['BOLD'] = dict(
            path=self.datadir / sub / 'MNINonLinear' / 'Results' /
            f'{task_name}_{phase_encoding}' /
            f'{task_name}_{phase_encoding}_hp2000_clean.nii.gz'
        )

        conf_dir = (
            Path('/data') / 'group' / 'appliedml' /
            'data' / 'HCP1200_Confounds_tsv'
        )
        out['BOLD']['confounds'] = (
            conf_dir / sub / 'MNINonLinear' / 'Results' /
            f'{task_name}_{phase_encoding}' / f'Confounds_{sub}.tsv'
        )

        out['meta'] = dict(datagrabber=self.get_meta())
        self._dataset_get(out)

        out['meta']['element'] = dict(
            subject=sub, task=task, phase_encoding=phase_encoding
        )

        return out
