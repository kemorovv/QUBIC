"""Pure-Python ISO/IEC 18004 QR Code matrix builder (Versions 1-40, ECC L/M/Q/H).

Used as a seamless fallback when the external `qrcode` package is not installed,
producing identical boolean module matrices to `qrcode.QRCode`.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

ECC_LEVEL_MAP = {
    "L": 1,
    "M": 0,
    "Q": 3,
    "H": 2,
}

MODE_8BIT_BYTE = 4
PAD0 = 0xEC
PAD1 = 0x11

EXP_TABLE: List[int] = [0] * 256
LOG_TABLE: List[int] = [0] * 256

for _i in range(8):
    EXP_TABLE[_i] = 1 << _i
for _i in range(8, 256):
    EXP_TABLE[_i] = (
        EXP_TABLE[_i - 4]
        ^ EXP_TABLE[_i - 5]
        ^ EXP_TABLE[_i - 6]
        ^ EXP_TABLE[_i - 8]
    )
for _i in range(255):
    LOG_TABLE[EXP_TABLE[_i]] = _i


def _glog(n: int) -> int:
    if n < 1:
        raise ValueError(f"glog({n})")
    return LOG_TABLE[n]


def _gexp(n: int) -> int:
    while n < 0:
        n += 255
    while n >= 256:
        n -= 255
    return EXP_TABLE[n]


class _QRPolynomial:
    def __init__(self, num: Sequence[int], shift: int) -> None:
        offset = 0
        while offset < len(num) and num[offset] == 0:
            offset += 1
        self.num: List[int] = [0] * (len(num) - offset + shift)
        for i in range(len(num) - offset):
            self.num[i] = num[i + offset]

    def get(self, index: int) -> int:
        return self.num[index]

    def get_length(self) -> int:
        return len(self.num)

    def multiply(self, other: "_QRPolynomial") -> "_QRPolynomial":
        res = [0] * (self.get_length() + other.get_length() - 1)
        for i in range(self.get_length()):
            for j in range(other.get_length()):
                res[i + j] ^= _gexp(_glog(self.get(i)) + _glog(other.get(j)))
        return _QRPolynomial(res, 0)

    def mod(self, other: "_QRPolynomial") -> "_QRPolynomial":
        if self.get_length() - other.get_length() < 0:
            return self
        ratio = _glog(self.get(0)) - _glog(other.get(0))
        res = list(self.num)
        for i in range(other.get_length()):
            res[i] ^= _gexp(_glog(other.get(i)) + ratio)
        return _QRPolynomial(res, 0).mod(other)


class _QRBitBuffer:
    def __init__(self) -> None:
        self.buffer: List[int] = []
        self.length: int = 0

    def put(self, num: int, length: int) -> None:
        for i in range(length):
            self.put_bit(((num >> (length - i - 1)) & 1) == 1)

    def put_bit(self, bit: bool) -> None:
        buf_index = self.length // 8
        if len(self.buffer) <= buf_index:
            self.buffer.append(0)
        if bit:
            self.buffer[buf_index] |= 0x80 >> (self.length % 8)
        self.length += 1


PATTERN_POSITION_TABLE: List[List[int]] = [
    [],
    [6, 18],
    [6, 22],
    [6, 26],
    [6, 30],
    [6, 34],
    [6, 22, 38],
    [6, 24, 42],
    [6, 26, 46],
    [6, 28, 50],
    [6, 30, 54],
    [6, 32, 58],
    [6, 34, 62],
    [6, 26, 46, 66],
    [6, 26, 48, 70],
    [6, 26, 50, 74],
    [6, 30, 54, 78],
    [6, 30, 56, 82],
    [6, 30, 58, 86],
    [6, 34, 62, 90],
    [6, 28, 50, 72, 94],
    [6, 26, 50, 74, 98],
    [6, 30, 54, 78, 102],
    [6, 28, 54, 80, 106],
    [6, 32, 58, 84, 110],
    [6, 30, 58, 86, 114],
    [6, 34, 62, 90, 118],
    [6, 26, 50, 74, 98, 122],
    [6, 30, 54, 78, 102, 126],
    [6, 26, 52, 78, 104, 130],
    [6, 30, 56, 82, 108, 134],
    [6, 34, 60, 86, 112, 138],
    [6, 30, 58, 86, 114, 142],
    [6, 34, 62, 90, 118, 146],
    [6, 30, 54, 78, 102, 126, 150],
    [6, 24, 50, 76, 102, 128, 154],
    [6, 28, 54, 80, 106, 132, 158],
    [6, 32, 58, 84, 110, 136, 162],
    [6, 26, 54, 82, 110, 138, 166],
    [6, 30, 58, 86, 114, 142, 170],
]

RS_BLOCK_TABLE: List[List[int]] = [
    [1, 26, 19], [1, 26, 16], [1, 26, 13], [1, 26, 9],
    [1, 44, 34], [1, 44, 28], [1, 44, 22], [1, 44, 16],
    [1, 70, 55], [1, 70, 44], [2, 35, 17], [2, 35, 13],
    [1, 100, 80], [2, 50, 32], [2, 50, 24], [4, 25, 9],
    [1, 134, 108], [2, 67, 43], [2, 33, 15, 2, 34, 16], [2, 33, 11, 2, 34, 12],
    [2, 86, 68], [4, 43, 27], [4, 43, 19], [4, 43, 15],
    [2, 98, 78], [4, 49, 31], [2, 32, 14, 4, 33, 15], [4, 39, 13, 1, 40, 14],
    [2, 121, 97], [2, 60, 38, 2, 61, 39], [4, 40, 18, 2, 41, 19], [4, 40, 14, 2, 41, 15],
    [2, 146, 116], [3, 58, 36, 2, 59, 37], [4, 36, 16, 4, 37, 17], [4, 36, 12, 4, 37, 13],
    [2, 86, 68, 2, 87, 69], [4, 69, 43, 1, 70, 44], [6, 43, 19, 2, 44, 20], [6, 43, 15, 2, 44, 16],
    [4, 101, 81], [1, 80, 50, 4, 81, 51], [4, 50, 22, 4, 51, 23], [3, 36, 12, 8, 37, 13],
    [2, 116, 92, 2, 117, 93], [6, 58, 36, 2, 59, 37], [4, 46, 20, 6, 47, 21], [7, 42, 14, 4, 43, 15],
    [4, 133, 107], [8, 59, 37, 1, 60, 38], [8, 44, 20, 4, 45, 21], [12, 33, 11, 4, 34, 12],
    [3, 145, 115, 1, 146, 116], [4, 64, 40, 5, 65, 41], [11, 36, 16, 5, 37, 17], [11, 36, 12, 5, 37, 13],
    [5, 109, 87, 1, 110, 88], [5, 65, 41, 5, 66, 42], [5, 54, 24, 7, 55, 25], [11, 36, 12, 7, 37, 13],
    [5, 122, 98, 1, 123, 99], [7, 73, 45, 3, 74, 46], [15, 43, 19, 2, 44, 20], [3, 45, 15, 13, 46, 16],
    [1, 135, 107, 5, 136, 108], [10, 74, 46, 1, 75, 47], [1, 50, 22, 15, 51, 23], [2, 42, 14, 17, 43, 15],
    [5, 150, 120, 1, 151, 121], [9, 69, 43, 4, 70, 44], [17, 50, 22, 1, 51, 23], [2, 42, 14, 19, 43, 15],
    [3, 141, 113, 4, 142, 114], [3, 70, 44, 11, 71, 45], [17, 47, 21, 4, 48, 22], [9, 39, 13, 16, 40, 14],
    [3, 135, 107, 5, 136, 108], [3, 67, 41, 13, 68, 42], [15, 54, 24, 5, 55, 25], [15, 43, 15, 10, 44, 16],
    [4, 144, 116, 4, 145, 117], [17, 68, 42], [17, 50, 22, 6, 51, 23], [19, 46, 16, 6, 47, 17],
    [2, 139, 111, 7, 140, 112], [17, 74, 46], [7, 54, 24, 16, 55, 25], [34, 37, 13],
    [4, 151, 121, 5, 152, 122], [4, 75, 47, 14, 76, 48], [11, 54, 24, 14, 55, 25], [16, 45, 15, 14, 46, 16],
    [6, 147, 117, 4, 148, 118], [6, 73, 45, 14, 74, 46], [11, 54, 24, 16, 55, 25], [30, 46, 16, 2, 47, 17],
    [8, 132, 106, 4, 133, 107], [8, 75, 47, 13, 76, 48], [7, 54, 24, 22, 55, 25], [22, 45, 15, 13, 46, 16],
    [10, 142, 114, 2, 143, 115], [19, 74, 46, 4, 75, 47], [28, 50, 22, 6, 51, 23], [33, 46, 16, 4, 47, 17],
    [8, 152, 122, 4, 153, 123], [22, 73, 45, 3, 74, 46], [8, 53, 23, 26, 54, 24], [12, 45, 15, 28, 46, 16],
    [3, 147, 117, 10, 148, 118], [3, 73, 45, 23, 74, 46], [4, 54, 24, 31, 55, 25], [11, 45, 15, 31, 46, 16],
    [7, 146, 116, 7, 147, 117], [21, 73, 45, 7, 74, 46], [1, 53, 23, 37, 54, 24], [19, 45, 15, 26, 46, 16],
    [5, 145, 115, 10, 146, 116], [19, 75, 47, 10, 76, 48], [15, 54, 24, 25, 55, 25], [23, 45, 15, 25, 46, 16],
    [13, 145, 115, 3, 146, 116], [2, 74, 46, 29, 75, 47], [42, 54, 24, 1, 55, 25], [23, 45, 15, 28, 46, 16],
    [17, 145, 115], [10, 74, 46, 23, 75, 47], [10, 54, 24, 35, 55, 25], [19, 45, 15, 35, 46, 16],
    [17, 145, 115, 1, 146, 116], [14, 74, 46, 21, 75, 47], [29, 54, 24, 19, 55, 25], [11, 45, 15, 46, 46, 16],
    [13, 145, 115, 6, 146, 116], [14, 74, 46, 23, 75, 47], [44, 54, 24, 7, 55, 25], [59, 46, 16, 1, 47, 17],
    [12, 151, 121, 7, 152, 122], [12, 75, 47, 26, 76, 48], [39, 54, 24, 14, 55, 25], [22, 45, 15, 41, 46, 16],
    [6, 151, 121, 14, 152, 122], [6, 75, 47, 34, 76, 48], [46, 54, 24, 10, 55, 25], [2, 45, 15, 64, 46, 16],
    [17, 152, 122, 4, 153, 123], [29, 74, 46, 14, 75, 47], [49, 54, 24, 10, 55, 25], [24, 45, 15, 46, 46, 16],
    [4, 152, 122, 18, 153, 123], [13, 74, 46, 32, 75, 47], [48, 54, 24, 14, 55, 25], [42, 45, 15, 32, 46, 16],
    [20, 147, 117, 4, 148, 118], [40, 75, 47, 7, 76, 48], [43, 54, 24, 22, 55, 25], [10, 45, 15, 67, 46, 16],
    [19, 148, 118, 6, 149, 119], [18, 75, 47, 31, 76, 48], [34, 54, 24, 34, 55, 25], [20, 45, 15, 61, 46, 16],
]

G15 = (1 << 10) | (1 << 8) | (1 << 5) | (1 << 4) | (1 << 2) | (1 << 1) | (1 << 0)
G18 = (1 << 12) | (1 << 11) | (1 << 10) | (1 << 9) | (1 << 8) | (1 << 5) | (1 << 2) | (1 << 0)
G15_MASK = (1 << 14) | (1 << 12) | (1 << 10) | (1 << 4) | (1 << 1)


def _get_bch_digit(data: int) -> int:
    digit = 0
    while data != 0:
        digit += 1
        data >>= 1
    return digit


def _get_bch_type_info(data: int) -> int:
    d = data << 10
    while _get_bch_digit(d) - _get_bch_digit(G15) >= 0:
        d ^= G15 << (_get_bch_digit(d) - _get_bch_digit(G15))
    return ((data << 10) | d) ^ G15_MASK


def _get_bch_type_number(data: int) -> int:
    d = data << 12
    while _get_bch_digit(d) - _get_bch_digit(G18) >= 0:
        d ^= G18 << (_get_bch_digit(d) - _get_bch_digit(G18))
    return (data << 12) | d


def _get_rs_blocks(type_number: int, ecc_level: int) -> List[Tuple[int, int]]:
    offset_map = {1: 0, 0: 1, 3: 2, 2: 3}
    table_row = RS_BLOCK_TABLE[(type_number - 1) * 4 + offset_map[ecc_level]]
    blocks: List[Tuple[int, int]] = []
    for i in range(0, len(table_row), 3):
        count, total_count, data_count = table_row[i], table_row[i + 1], table_row[i + 2]
        for _ in range(count):
            blocks.append((total_count, data_count))
    return blocks


def _get_length_in_bits(type_number: int) -> int:
    if 1 <= type_number < 10:
        return 8
    return 16


def _get_mask(mask_pattern: int, i: int, j: int) -> bool:
    if mask_pattern == 0:
        return (i + j) % 2 == 0
    if mask_pattern == 1:
        return i % 2 == 0
    if mask_pattern == 2:
        return j % 3 == 0
    if mask_pattern == 3:
        return (i + j) % 3 == 0
    if mask_pattern == 4:
        return ((i // 2) + (j // 3)) % 2 == 0
    if mask_pattern == 5:
        return (i * j) % 2 + (i * j) % 3 == 0
    if mask_pattern == 6:
        return ((i * j) % 2 + (i * j) % 3) % 2 == 0
    if mask_pattern == 7:
        return ((i * j) % 3 + (i + j) % 2) % 2 == 0
    raise ValueError(f"Invalid mask pattern: {mask_pattern}")


def _get_error_correct_polynomial(ec_length: int) -> _QRPolynomial:
    poly = _QRPolynomial([1], 0)
    for i in range(ec_length):
        poly = poly.multiply(_QRPolynomial([1, _gexp(i)], 0))
    return poly


def _create_data(type_number: int, ecc_level: int, data_bytes: bytes) -> List[int]:
    rs_blocks = _get_rs_blocks(type_number, ecc_level)
    buffer = _QRBitBuffer()
    buffer.put(MODE_8BIT_BYTE, 4)
    buffer.put(len(data_bytes), _get_length_in_bits(type_number))
    for b in data_bytes:
        buffer.put(b, 8)

    total_data_count = sum(dc for _, dc in rs_blocks)
    if buffer.length > total_data_count * 8:
        raise ValueError("QR code data length overflow")

    if buffer.length + 4 <= total_data_count * 8:
        buffer.put(0, 4)
    while buffer.length % 8 != 0:
        buffer.put_bit(False)
    while True:
        if buffer.length >= total_data_count * 8:
            break
        buffer.put(PAD0, 8)
        if buffer.length >= total_data_count * 8:
            break
        buffer.put(PAD1, 8)

    offset = 0
    max_dc_count = 0
    max_ec_count = 0
    dcdata: List[List[int]] = []
    ecdata: List[List[int]] = []

    for total_count, dc_count in rs_blocks:
        ec_count = total_count - dc_count
        max_dc_count = max(max_dc_count, dc_count)
        max_ec_count = max(max_ec_count, ec_count)

        dc_block = [0xFF & buffer.buffer[i + offset] for i in range(dc_count)]
        offset += dc_count
        dcdata.append(dc_block)

        rs_poly = _get_error_correct_polynomial(ec_count)
        raw_poly = _QRPolynomial(dc_block, rs_poly.get_length() - 1)
        mod_poly = raw_poly.mod(rs_poly)

        ec_len = rs_poly.get_length() - 1
        ec_block = []
        for x in range(ec_len):
            mod_index = x + mod_poly.get_length() - ec_len
            ec_block.append(mod_poly.get(mod_index) if mod_index >= 0 else 0)
        ecdata.append(ec_block)

    result: List[int] = []
    for z in range(max_dc_count):
        for s in range(len(rs_blocks)):
            if z < len(dcdata[s]):
                result.append(dcdata[s][z])
    for xx in range(max_ec_count):
        for t in range(len(rs_blocks)):
            if xx < len(ecdata[t]):
                result.append(ecdata[t][xx])
    return result


class _ISOQRCodeBuilder:
    def __init__(self, data_str: str, ecc_key: str = "M") -> None:
        self.data_bytes = data_str.encode("utf-8")
        self.ecc_level = ECC_LEVEL_MAP.get(ecc_key.upper(), ECC_LEVEL_MAP["M"])
        self.type_number = self._choose_type_number()
        self.module_count = self.type_number * 4 + 17
        self.modules: List[List[Optional[bool]]] = []
        self.data_cache: Optional[List[int]] = None

    def _choose_type_number(self) -> int:
        for t in range(1, 41):
            rs_blocks = _get_rs_blocks(t, self.ecc_level)
            total_data_bits = sum(dc for _, dc in rs_blocks) * 8
            needed_bits = 4 + _get_length_in_bits(t) + len(self.data_bytes) * 8
            if needed_bits <= total_data_bits:
                return t
        raise ValueError("Payload is too large to fit inside a standard Version 40 QR code.")

    def build(self) -> List[List[bool]]:
        best_pattern = 0
        min_penalty: Optional[float] = None
        for pattern in range(8):
            self._make_impl(test=True, mask_pattern=pattern)
            penalty = self._compute_penalty()
            if min_penalty is None or penalty < min_penalty:
                min_penalty = penalty
                best_pattern = pattern
        self._make_impl(test=False, mask_pattern=best_pattern)
        return [[bool(cell) for cell in row] for row in self.modules]

    def _make_impl(self, test: bool, mask_pattern: int) -> None:
        n = self.module_count
        self.modules = [[None for _ in range(n)] for _ in range(n)]
        self._setup_finder_pattern(0, 0)
        self._setup_finder_pattern(n - 7, 0)
        self._setup_finder_pattern(0, n - 7)
        self._setup_alignment_patterns()
        self._setup_timing_patterns()
        self._setup_type_info(test, mask_pattern)
        if self.type_number >= 7:
            self._setup_type_number(test)
        if self.data_cache is None:
            self.data_cache = _create_data(self.type_number, self.ecc_level, self.data_bytes)
        self._map_data(self.data_cache, mask_pattern)

    def _setup_finder_pattern(self, row: int, col: int) -> None:
        n = self.module_count
        for r in range(-1, 8):
            if row + r < 0 or row + r >= n:
                continue
            for c in range(-1, 8):
                if col + c < 0 or col + c >= n:
                    continue
                if (
                    (0 <= r <= 6 and c in (0, 6))
                    or (0 <= c <= 6 and r in (0, 6))
                    or (2 <= r <= 4 and 2 <= c <= 4)
                ):
                    self.modules[row + r][col + c] = True
                else:
                    self.modules[row + r][col + c] = False

    def _setup_timing_patterns(self) -> None:
        n = self.module_count
        for i in range(8, n - 8):
            if self.modules[i][6] is None:
                self.modules[i][6] = i % 2 == 0
            if self.modules[6][i] is None:
                self.modules[6][i] = i % 2 == 0

    def _setup_alignment_patterns(self) -> None:
        pos = PATTERN_POSITION_TABLE[self.type_number - 1]
        for row in pos:
            for col in pos:
                if self.modules[row][col] is not None:
                    continue
                for r in range(-2, 3):
                    for c in range(-2, 3):
                        if abs(r) == 2 or abs(c) == 2 or (r == 0 and c == 0):
                            self.modules[row + r][col + c] = True
                        else:
                            self.modules[row + r][col + c] = False

    def _setup_type_number(self, test: bool) -> None:
        bits = _get_bch_type_number(self.type_number)
        n = self.module_count
        for i in range(18):
            mod = not test and ((bits >> i) & 1) == 1
            self.modules[i // 3][i % 3 + n - 8 - 3] = mod
            self.modules[i % 3 + n - 8 - 3][i // 3] = mod

    def _setup_type_info(self, test: bool, mask_pattern: int) -> None:
        data = (self.ecc_level << 3) | mask_pattern
        bits = _get_bch_type_info(data)
        n = self.module_count
        for v in range(15):
            mod = not test and ((bits >> v) & 1) == 1
            if v < 6:
                self.modules[v][8] = mod
            elif v < 8:
                self.modules[v + 1][8] = mod
            else:
                self.modules[n - 15 + v][8] = mod
        for h in range(15):
            mod = not test and ((bits >> h) & 1) == 1
            if h < 8:
                self.modules[8][n - h - 1] = mod
            elif h < 9:
                self.modules[8][15 - h - 1 + 1] = mod
            else:
                self.modules[8][15 - h - 1] = mod
        self.modules[n - 8][8] = not test

    def _map_data(self, data: List[int], mask_pattern: int) -> None:
        n = self.module_count
        inc = -1
        row = n - 1
        bit_index = 7
        byte_index = 0
        col = n - 1
        while col > 0:
            if col == 6:
                col -= 1
            while True:
                for c in range(2):
                    if self.modules[row][col - c] is None:
                        dark = False
                        if byte_index < len(data):
                            dark = ((data[byte_index] >> bit_index) & 1) == 1
                        if _get_mask(mask_pattern, row, col - c):
                            dark = not dark
                        self.modules[row][col - c] = dark
                        bit_index -= 1
                        if bit_index == -1:
                            byte_index += 1
                            bit_index = 7
                row += inc
                if row < 0 or row >= n:
                    row -= inc
                    inc = -inc
                    break
            col -= 2

    def _compute_penalty(self) -> float:
        n = self.module_count
        lost_point = 0.0
        # Level 1
        for r in range(n):
            for c in range(n):
                same_count = 0
                dark = bool(self.modules[r][c])
                for dr in (-1, 0, 1):
                    if r + dr < 0 or r + dr >= n:
                        continue
                    for dc in (-1, 0, 1):
                        if c + dc < 0 or c + dc >= n or (dr == 0 and dc == 0):
                            continue
                        if bool(self.modules[r + dr][c + dc]) == dark:
                            same_count += 1
                if same_count > 5:
                    lost_point += 3 + same_count - 5

        # Level 2
        for r in range(n - 1):
            for c in range(n - 1):
                cnt = (
                    int(bool(self.modules[r][c]))
                    + int(bool(self.modules[r + 1][c]))
                    + int(bool(self.modules[r][c + 1]))
                    + int(bool(self.modules[r + 1][c + 1]))
                )
                if cnt in (0, 4):
                    lost_point += 3

        # Level 3 (1:1:3:1:1 finder-like ratio penalty)
        for r in range(n):
            for c in range(n - 6):
                if (
                    bool(self.modules[r][c])
                    and not bool(self.modules[r][c + 1])
                    and bool(self.modules[r][c + 2])
                    and bool(self.modules[r][c + 3])
                    and bool(self.modules[r][c + 4])
                    and not bool(self.modules[r][c + 5])
                    and bool(self.modules[r][c + 6])
                ):
                    lost_point += 40

        for c in range(n):
            for r in range(n - 6):
                if (
                    bool(self.modules[r][c])
                    and not bool(self.modules[r + 1][c])
                    and bool(self.modules[r + 2][c])
                    and bool(self.modules[r + 3][c])
                    and bool(self.modules[r + 4][c])
                    and not bool(self.modules[r + 5][c])
                    and bool(self.modules[r + 6][c])
                ):
                    lost_point += 40

        # Level 4
        dark_count = sum(1 for r in range(n) for c in range(n) if self.modules[r][c])
        ratio = abs(100.0 * dark_count / (n * n) - 50.0) / 5.0
        lost_point += ratio * 10.0
        return lost_point


def build_iso_qr_matrix(data: str, error_correction: str = "M", border: int = 4) -> Tuple[List[List[bool]], List[List[bool]]]:
    """Return (matrix_with_border, raw_matrix_without_border)."""
    builder = _ISOQRCodeBuilder(data, ecc_key=error_correction)
    raw = builder.build()
    if border <= 0:
        return [list(r) for r in raw], raw
    raw_n = len(raw)
    padded_n = raw_n + border * 2
    padded: List[List[bool]] = [[False] * padded_n for _ in range(border)]
    for row in raw:
        padded.append([False] * border + list(row) + [False] * border)
    for _ in range(border):
        padded.append([False] * padded_n)
    return padded, raw
