# Copyright VyOS maintainers and contributors <maintainers@vyos.io>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 or later as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from dataclasses import dataclass

from build.lib.vyos.utils.network import check_port_availability, is_loopback_addr
from vyos.utils.network import (
    bgp_as_get_integer_value,
    bgp_format_asdot,
    bgp_format_asdot_plus,
    bgp_format_asplain,
    bgp_parse_as_number,
    bgp_parse_asdot_plus,
    bgp_parse_asplain,
    is_addr_assigned,
    is_ipv6_link_local,
)
from unittest import TestCase

class TestVyOSUtilsNetwork(TestCase):
    def setUp(self):
        pass

    def test_is_addr_assigned(self):
        self.assertTrue(is_addr_assigned('127.0.0.1'))
        self.assertTrue(is_addr_assigned('::1'))
        self.assertFalse(is_addr_assigned('127.251.255.123'))

    def test_is_ipv6_link_local(self):
        self.assertFalse(is_ipv6_link_local('169.254.0.1'))
        self.assertTrue(is_ipv6_link_local('fe80::'))
        self.assertTrue(is_ipv6_link_local('fe80::affe:1'))
        self.assertTrue(is_ipv6_link_local('fe80::affe:1%eth0'))
        self.assertFalse(is_ipv6_link_local('2001:db8::'))
        self.assertFalse(is_ipv6_link_local('2001:db8::%eth0'))
        self.assertFalse(is_ipv6_link_local('VyOS'))
        self.assertFalse(is_ipv6_link_local('::1'))
        self.assertFalse(is_ipv6_link_local('::1%lo'))

    def test_is_loopback_addr(self):
        self.assertTrue(is_loopback_addr('127.0.0.1'))
        self.assertTrue(is_loopback_addr('127.0.1.1'))
        self.assertTrue(is_loopback_addr('127.1.1.1'))
        self.assertTrue(is_loopback_addr('::1'))

        self.assertFalse(is_loopback_addr('::2'))
        self.assertFalse(is_loopback_addr('192.0.2.1'))

    def test_check_port_availability(self):
        self.assertTrue(check_port_availability('::1', 8080))
        self.assertTrue(check_port_availability('127.0.0.1', 8080))
        self.assertTrue(check_port_availability(None, 8080, protocol='udp'))
        # We do not have 192.0.2.1 configured on this system
        self.assertFalse(check_port_availability('192.0.2.1', 443))
        # We do not have 2001:db8::1 configured on this system
        self.assertFalse(check_port_availability('2001:db8::1', 80, protocol='udp'))


# BGP AS number test helper and test database
@dataclass
class ValidASNumber:
    """A valid BGP AS number in all its equivalent representations."""

    integer: int
    asplain: str  # plain decimal,  e.g. "65536"
    asdot_plus: str  # always X.Y,     e.g. "1.0"
    asdot: str  # asplain ≤65535, asdot+ otherwise

    @property
    def all_formats(self) -> list[str]:
        return [self.asplain, self.asdot_plus, self.asdot]


VALID_AS_NUMBERS: list[ValidASNumber] = [
    #                     integer       asplain   asdot_plus          asdot
    # smallest valid
    ValidASNumber(1, '1', '0.1', '1'),
    # typical 16-bit private
    ValidASNumber(65000, '65000', '0.65000', '65000'),
    # last 16-bit
    ValidASNumber(65535, '65535', '0.65535', '65535'),
    # first 32-bit
    ValidASNumber(65536, '65536', '1.0', '1.0'),
    # second 32-bit block
    ValidASNumber(131072, '131072', '2.0', '2.0'),
    # typical 32-bit private
    ValidASNumber(4202377273, '4202377273', '64123.12345', '64123.12345'),
    # largest valid
    ValidASNumber(4294967294, '4294967294', '65535.65534', '65535.65534'),
]


INVALID_AS_NUMBERS: list[str] = [
    '0',  # AS 0 is reserved
    '4294967295',  # AS 4294967295 is reserved (2^32 - 2)
    '4294967296',  # AS 4294967296 is invalid (greater than 2^32 - 2)
    '9999999999',  # AS 999999999 is invalid (greater than 2^32 - 2)
    '-1',  # negative numbers are not valid
    '0.0',  # asdot+ 0.0 resolves to AS 0 (reserved)
    '65535.65535',  # asdot+ resolves to AS 4294967295 (reserved)
    '65536.0',  # left part of asdot+ must be ≤ 65535
    '0.65536',  # right part of asdot+ must be ≤ 65535
    '1.2.3',  # two dots
    'a.b',  # non-numeric asdot+ parts
    'abc',  # non-numeric asplain
    '',  # empty string
]
INVALID_AS_NUMBERS_INT: list[int] = [
    0,  # AS 0 is reserved
    4294967295,  # AS 4294967295 is reserved (2^32 - 2)
    4294967296,  # AS 4294967296 is invalid (greater than 2^32 - 2)
    9999999999,  # AS 999999999 is invalid (greater than 2^32 - 2)
    -1,  # negative numbers are not valid
]


class TestBGPASNumber(TestCase):
    """Tests for BGP AS number parsing and formatting helpers."""

    def test_bgp_parse_asplain_valid(self):
        for asn in VALID_AS_NUMBERS:
            with self.subTest(asplain=asn.asplain):
                self.assertEqual(bgp_parse_asplain(asn.asplain), asn.integer)

    def test_bgp_parse_asdot_plus_valid(self):
        for asn in VALID_AS_NUMBERS:
            with self.subTest(asdot_plus=asn.asdot_plus):
                self.assertEqual(bgp_parse_asdot_plus(asn.asdot_plus), asn.integer)

    def test_bgp_parse_as_number_valid(self):
        for asn in VALID_AS_NUMBERS:
            for fmt in asn.all_formats:
                with self.subTest(input=fmt, expected=asn.integer):
                    self.assertEqual(bgp_parse_as_number(fmt), asn.integer)

    def test_bgp_parse_as_number_invalid(self):
        for inv in INVALID_AS_NUMBERS:
            with self.subTest(value=inv):
                with self.assertRaises(ValueError):
                    bgp_parse_as_number(inv)

    # bgp_as_get_integer_value
    def test_bgp_as_get_integer_value_from_string(self):
        for asn in VALID_AS_NUMBERS:
            for fmt in asn.all_formats:
                with self.subTest(input=fmt, expected=asn.integer):
                    self.assertEqual(bgp_as_get_integer_value(fmt), asn.integer)

    def test_bgp_as_get_integer_value_from_integer(self):
        for asn in VALID_AS_NUMBERS:
            with self.subTest(integer=asn.integer):
                self.assertEqual(bgp_as_get_integer_value(asn.integer), asn.integer)

    def test_bgp_as_get_integer_value_invalid_string_raises(self):
        for inv in INVALID_AS_NUMBERS:
            with self.subTest(value=inv):
                with self.assertRaises(ValueError):
                    bgp_as_get_integer_value(inv)

    def test_bgp_as_get_integer_value_invalid_integer_raises(self):
        for bad_int in INVALID_AS_NUMBERS_INT:
            with self.subTest(value=bad_int):
                with self.assertRaises(ValueError):
                    bgp_as_get_integer_value(bad_int)

    # bgp_format_asplain
    def test_bgp_format_asplain_valid_all_formats(self):
        for asn in VALID_AS_NUMBERS:
            for fmt in asn.all_formats:
                with self.subTest(input=fmt, expected=asn.asplain):
                    self.assertEqual(bgp_format_asplain(fmt), asn.asplain)

    def test_bgp_format_asplain_from_integer(self):
        for asn in VALID_AS_NUMBERS:
            with self.subTest(integer=asn.integer):
                self.assertEqual(bgp_format_asplain(asn.integer), asn.asplain)

    def test_bgp_format_asplain_invalid_raises(self):
        for inv in INVALID_AS_NUMBERS:
            with self.subTest(value=inv):
                with self.assertRaises(ValueError):
                    bgp_format_asplain(inv)

    # bgp_format_asdot_plus
    def test_bgp_format_asdot_plus_valid_all_formats(self):
        for asn in VALID_AS_NUMBERS:
            for fmt in asn.all_formats:
                with self.subTest(input=fmt, expected=asn.asdot_plus):
                    self.assertEqual(bgp_format_asdot_plus(fmt), asn.asdot_plus)

    def test_bgp_format_asdot_plus_from_integer(self):
        for asn in VALID_AS_NUMBERS:
            with self.subTest(integer=asn.integer):
                self.assertEqual(bgp_format_asdot_plus(asn.integer), asn.asdot_plus)

    def test_bgp_format_asdot_plus_invalid_raises(self):
        for inv in INVALID_AS_NUMBERS:
            with self.subTest(value=inv):
                with self.assertRaises(ValueError):
                    bgp_format_asdot_plus(inv)

    # bgp_format_asdot
    def test_bgp_format_asdot_valid_all_formats(self):
        for asn in VALID_AS_NUMBERS:
            for fmt in asn.all_formats:
                with self.subTest(input=fmt, expected=asn.asdot):
                    self.assertEqual(bgp_format_asdot(fmt), asn.asdot)

    def test_bgp_format_asdot_from_integer(self):
        for asn in VALID_AS_NUMBERS:
            with self.subTest(integer=asn.integer):
                self.assertEqual(bgp_format_asdot(asn.integer), asn.asdot)

    def test_bgp_format_asdot_invalid_raises(self):
        for inv in INVALID_AS_NUMBERS:
            with self.subTest(value=inv):
                with self.assertRaises(ValueError):
                    bgp_format_asdot(inv)
