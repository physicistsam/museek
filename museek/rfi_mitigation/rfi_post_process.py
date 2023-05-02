import numpy as np
from scipy import ndimage

from museek.data_element import DataElement
from museek.factory.data_element_factory import DataElementFactory


class RfiPostProcess:
    """ Class to post-process rfi masks. """

    def __init__(self, new_flag: DataElement, initial_flag: DataElement, struct_size: tuple[int, int]):
        """
        Initialise the post-processing of RFI flags.
        :param new_flag: newly generated RFI flag
        :param initial_flag: initial flags the RFI flags were built upon
        :param struct_size: structure size for binary dilation, closing etc
        """
        self._flag = new_flag
        self._initial_flag = initial_flag
        self._struct_size = struct_size
        self._struct = np.ones((self._struct_size[0], self._struct_size[1]), dtype=bool)
        self._factory = DataElementFactory()

    def get_flag(self):
        """ Return the flag. """
        return self._flag

    def binary_mask_dilation(self):
        """ Dilate the mask. """
        dilated = ndimage.binary_dilation(self._flag.squeeze ^ self._initial_flag.squeeze,
                                          structure=self._struct,
                                          iterations=2)
        self._flag = self._factory.create(array=dilated[:, :, np.newaxis])

    def binary_mask_closing(self):
        """ Close the mask. """
        closed = ndimage.binary_closing(self._flag.squeeze, structure=self._struct, iterations=5)
        self._flag = self._factory.create(array=closed[:, :, np.newaxis])

    def flag_all_channels(self, channel_flag_threshold: float):
        """ If the fraction of flagged channels exceeds `channel_flag_threshold`, all channels are flagged. """
        flagged_fraction = self._flag.sum(axis=1).squeeze / self._flag.shape[1]
        timestamps_to_flag = np.where(flagged_fraction > channel_flag_threshold)[0]
        flag = self._flag.squeeze
        flag[timestamps_to_flag, :] = 1
        self._flag = self._factory.create(array=flag[:, :, np.newaxis])