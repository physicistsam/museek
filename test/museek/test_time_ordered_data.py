import unittest
from unittest.mock import patch, Mock, MagicMock, call

import numpy as np

from museek.receiver import Receiver, Polarisation
from museek.time_ordered_data import TimeOrderedData, ScanStateEnum, ScanTuple


class TestTimeOrderedData(unittest.TestCase):

    @patch.object(TimeOrderedData, '_set_scan_state_dumps')
    @patch.object(TimeOrderedData, '_correlator_products_indices')
    @patch.object(TimeOrderedData, 'load_data')
    def setUp(self, mock_load_data, mock_correlator_products_indices, mock_set_scan_state_dumps):
        self.mock_katdal_data = MagicMock()
        self.mock_correlator_products_indices = mock_correlator_products_indices
        mock_load_data.return_value = self.mock_katdal_data
        mock_block_name = Mock()
        mock_receiver_list = [Mock(), Mock()]
        mock_data_folder = Mock()

        self.time_ordered_data = TimeOrderedData(block_name=mock_block_name,
                                                 receivers=mock_receiver_list,
                                                 token=None,
                                                 data_folder=mock_data_folder)

    def test_init(self):
        self.mock_katdal_data.select.assert_called_once_with(
            corrprods=self.mock_correlator_products_indices.return_value
        )
        self.assertIsNone(self.time_ordered_data.scan_dumps)
        self.assertIsNone(self.time_ordered_data.track_dumps)
        self.assertIsNone(self.time_ordered_data.slew_dumps)
        self.assertIsNone(self.time_ordered_data.stop_dumps)

    def test_str(self):
        expect = str(self.mock_katdal_data)
        self.assertEqual(str(self.time_ordered_data), expect)

    @patch('museek.time_ordered_data.katdal.open')
    def test_load_data_when_data_folder(self, mock_open):
        block_name = 'block'
        self.time_ordered_data.load_data(block_name=block_name, token=None, data_folder='')
        mock_open.assert_called_once_with(f'{block_name}/{block_name}/{block_name}_sdp_l0.full.rdb')

    @patch('museek.time_ordered_data.katdal.open')
    def test_load_data_when_token(self, mock_open):
        block_name = 'block'
        token = 'token'
        self.time_ordered_data.load_data(block_name=block_name, token=token, data_folder=None)
        mock_open.assert_called_once_with(
            f'https://archive-gw-1.kat.ac.za/{block_name}/{block_name}_sdp_l0.full.rdb?{token}'
        )

    def test_antenna(self):
        mock_receiver = MagicMock()
        mock_antenna_name_list = MagicMock()
        self.time_ordered_data._antenna_name_list = mock_antenna_name_list
        antenna = self.time_ordered_data.antenna(receiver=mock_receiver)
        mock_antenna_name_list.index.assert_called_once_with(mock_receiver.antenna_name)
        self.assertEqual(self.time_ordered_data.antennas.__getitem__.return_value, antenna)

    def test_antenna_when_explicit(self):
        self.time_ordered_data._antenna_name_list = ['m000', 'm001']
        self.time_ordered_data.antennas = ['antenna0', 'antenna1']
        antenna = self.time_ordered_data.antenna(receiver=Receiver(antenna_number=1, polarisation=Polarisation.v))
        self.assertEqual('antenna1', antenna)

    @patch.object(TimeOrderedData, '__setattr__')
    @patch.object(TimeOrderedData, '_dumps_of_scan_state')
    def test_set_scan_state_dumps(self, mock_dumps_of_scan_state, mock_setattr):
        self.time_ordered_data._set_scan_state_dumps()
        mock_dumps_of_scan_state.assert_has_calls(calls=[call(scan_state=ScanStateEnum.SCAN),
                                                         call(scan_state=ScanStateEnum.TRACK),
                                                         call(scan_state=ScanStateEnum.SLEW),
                                                         call(scan_state=ScanStateEnum.STOP)])
        mock_setattr.assert_has_calls(
            calls=[call('scan_dumps', mock_dumps_of_scan_state.return_value),
                   call('track_dumps', mock_dumps_of_scan_state.return_value),
                   call('slew_dumps', mock_dumps_of_scan_state.return_value),
                   call('stop_dumps', mock_dumps_of_scan_state.return_value)]
        )

    def test_correlator_products_indices(self):
        all_correlator_products = np.asarray([('a', 'a'), ('b', 'b'), ('c', 'c'), ('d', 'd')])
        self.time_ordered_data.correlator_products = np.asarray([('c', 'c'), ('a', 'a')])
        expect = [2, 0]
        indices = self.time_ordered_data._correlator_products_indices(all_correlator_products=all_correlator_products)
        self.assertListEqual(expect, indices)

    def test_correlator_products_indices_when_all_missing_expect_raise(self):
        all_correlator_products = np.asarray([('a', 'a'), ('b', 'b'), ('c', 'c'), ('d', 'd')])
        self.time_ordered_data.correlator_products = np.asarray([('e', 'e'), ('f', 'f')])
        self.assertRaises(ValueError,
                          self.time_ordered_data._correlator_products_indices,
                          all_correlator_products=all_correlator_products)

    def test_correlator_products_indices_when_one_missing_expect_raise(self):
        all_correlator_products = np.asarray([('a', 'a'), ('b', 'b'), ('c', 'c'), ('d', 'd')])
        self.time_ordered_data.correlator_products = np.asarray([('a', 'a'), ('f', 'f')])
        self.assertRaises(ValueError,
                          self.time_ordered_data._correlator_products_indices,
                          all_correlator_products=all_correlator_products)

    def test_dumps_of_scan_state(self):
        self.time_ordered_data._scan_tuple_list = [ScanTuple(dumps=[0], state='scan', index=0, target=Mock()),
                                                   ScanTuple(dumps=[1], state='track', index=1, target=Mock())]
        self.assertEqual([0], self.time_ordered_data._dumps_of_scan_state(scan_state=ScanStateEnum.SCAN))
        self.assertEqual([1], self.time_ordered_data._dumps_of_scan_state(scan_state=ScanStateEnum.TRACK))

    def test_get_scan_tuple_list(self):
        mock_target = Mock()
        mock_scans = MagicMock(return_value=[(0, 'scan', mock_target),
                                             (1, 'track', mock_target)])
        mock_data = MagicMock(scans=mock_scans)
        scan_tuple_list = self.time_ordered_data._get_scan_tuple_list(data=mock_data)
        expect_list = [ScanTuple(dumps=mock_data.dumps, state='scan', index=0, target=mock_target),
                       ScanTuple(dumps=mock_data.dumps, state='track', index=1, target=mock_target)]
        for expect, scan_tuple in zip(expect_list, scan_tuple_list):
            self.assertTupleEqual(expect, scan_tuple)

    def test_get_correlator_products(self):
        self.time_ordered_data.receivers = [Receiver(antenna_number=0, polarisation=Polarisation.v),
                                            Receiver(antenna_number=0, polarisation=Polarisation.h),
                                            Receiver(antenna_number=200, polarisation=Polarisation.h)]
        expect_list = [['m000v', 'm000v'], ['m000h', 'm000h'], ['m200h', 'm200h']]
        for expect, correlator_product in zip(expect_list, self.time_ordered_data._get_correlator_products()):
            self.assertListEqual(expect, correlator_product)
