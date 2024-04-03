import os
import struct
import tempfile

from assemblyline_v4_service.common.base import ServiceBase
from assemblyline_v4_service.common.result import Result, ResultSection
from assemblyline_v4_service.common.request import ServiceRequest


class DefenderQuarantine(ServiceBase):

    def execute(self, request: ServiceRequest):
        result = Result()
        request.result = result

        text_section = ResultSection('Windows Defender Quarantine Results', parent=request.result)

        decoded_file = self.mse_unquarantine(request)
        if decoded_file:
            text_section.set_heuristic(1)
            text_section.add_line("Succesfully decoded file from Windows Defender Quarantine file")
            text_section.add_line(decoded_file)
            text_section.add_tag("file.name.decoded", decoded_file)

    # MS SCEP & SE quarantined files decrypter
    # This script is a fork from quarantine.py from the cuckoosandbox project.
    # Also thanks to Jon Glass (https://jon.glass/quarantines-junk/)
    #
    # Copyright (C) 2015 KillerInstinct, Optiv, Inc. (brad.spengler@optiv.com)
    # This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
    # See the file 'docs/LICENSE' for copying permission.

    #
    # Credit: https://raw.githubusercontent.com/brad-accuvant/cuckoo-modified/00ad13c94cc7453c40ed6152d16009ca1c8ed6f2/lib/cuckoo/common/quarantine.py
    # Link to license: https://github.com/brad-accuvant/cuckoo-modified/blob/master/docs/LICENSE
    #
    def mse_unquarantine(self, request: ServiceRequest):
        with open(request.file_path, "rb") as quarfile:
            data = bytearray(quarfile.read())

        fsize = len(data)
        if fsize < 12 or data[0] != 0x0B or data[1] != 0xad or data[2] != 0x00:
            return None

        with tempfile.TemporaryDirectory() as temp_dir:
            # TODO: Validate that using a temp folder to write the resulting decodedfile is not a problem
            # I would believe the file may disappear before the service finishes
            sbox = self.mse_ksa()
            outdata = self.rc4_decrypt(sbox, data)

            with open(os.path.join(temp_dir, f"{request.file_name}_decoded_meta.bin"), "wb") as f:
                f.write(outdata)

            headerlen = 0x28 + struct.unpack("<I", outdata[8:12])[0]
            origlen = struct.unpack("<I", outdata[headerlen - 12:headerlen - 8])[0]

            filename = f"{request.file_name}_decoded.bin"
            decodedfile = os.path.join(temp_dir, filename)

            if origlen + headerlen == fsize:
                with open(decodedfile, "wb") as f:
                    f.write(outdata[headerlen:])

            # TODO: This and returning the decodedfile should only happen if the previous condition was true
            request.add_extracted(decodedfile, filename, "mse unquarantine file")
        return decodedfile

    def mse_ksa(self):
        # hardcoded key obtained from mpengine.dll
        key = [0x1E, 0x87, 0x78, 0x1B, 0x8D, 0xBA, 0xA8, 0x44, 0xCE, 0x69,
               0x70, 0x2C, 0x0C, 0x78, 0xB7, 0x86, 0xA3, 0xF6, 0x23, 0xB7,
               0x38, 0xF5, 0xED, 0xF9, 0xAF, 0x83, 0x53, 0x0F, 0xB3, 0xFC,
               0x54, 0xFA, 0xA2, 0x1E, 0xB9, 0xCF, 0x13, 0x31, 0xFD, 0x0F,
               0x0D, 0xA9, 0x54, 0xF6, 0x87, 0xCB, 0x9E, 0x18, 0x27, 0x96,
               0x97, 0x90, 0x0E, 0x53, 0xFB, 0x31, 0x7C, 0x9C, 0xBC, 0xE4,
               0x8E, 0x23, 0xD0, 0x53, 0x71, 0xEC, 0xC1, 0x59, 0x51, 0xB8,
               0xF3, 0x64, 0x9D, 0x7C, 0xA3, 0x3E, 0xD6, 0x8D, 0xC9, 0x04,
               0x7E, 0x82, 0xC9, 0xBA, 0xAD, 0x97, 0x99, 0xD0, 0xD4, 0x58,
               0xCB, 0x84, 0x7C, 0xA9, 0xFF, 0xBE, 0x3C, 0x8A, 0x77, 0x52,
               0x33, 0x55, 0x7D, 0xDE, 0x13, 0xA8, 0xB1, 0x40, 0x87, 0xCC,
               0x1B, 0xC8, 0xF1, 0x0F, 0x6E, 0xCD, 0xD0, 0x83, 0xA9, 0x59,
               0xCF, 0xF8, 0x4A, 0x9D, 0x1D, 0x50, 0x75, 0x5E, 0x3E, 0x19,
               0x18, 0x18, 0xAF, 0x23, 0xE2, 0x29, 0x35, 0x58, 0x76, 0x6D,
               0x2C, 0x07, 0xE2, 0x57, 0x12, 0xB2, 0xCA, 0x0B, 0x53, 0x5E,
               0xD8, 0xF6, 0xC5, 0x6C, 0xE7, 0x3D, 0x24, 0xBD, 0xD0, 0x29,
               0x17, 0x71, 0x86, 0x1A, 0x54, 0xB4, 0xC2, 0x85, 0xA9, 0xA3,
               0xDB, 0x7A, 0xCA, 0x6D, 0x22, 0x4A, 0xEA, 0xCD, 0x62, 0x1D,
               0xB9, 0xF2, 0xA2, 0x2E, 0xD1, 0xE9, 0xE1, 0x1D, 0x75, 0xBE,
               0xD7, 0xDC, 0x0E, 0xCB, 0x0A, 0x8E, 0x68, 0xA2, 0xFF, 0x12,
               0x63, 0x40, 0x8D, 0xC8, 0x08, 0xDF, 0xFD, 0x16, 0x4B, 0x11,
               0x67, 0x74, 0xCD, 0x0B, 0x9B, 0x8D, 0x05, 0x41, 0x1E, 0xD6,
               0x26, 0x2E, 0x42, 0x9B, 0xA4, 0x95, 0x67, 0x6B, 0x83, 0x98,
               0xDB, 0x2F, 0x35, 0xD3, 0xC1, 0xB9, 0xCE, 0xD5, 0x26, 0x36,
               0xF2, 0x76, 0x5E, 0x1A, 0x95, 0xCB, 0x7C, 0xA4, 0xC3, 0xDD,
               0xAB, 0xDD, 0xBF, 0xF3, 0x82, 0x53
        ]
        sbox = list(range(256))
        j = 0
        for i in range(256):
            j = (j + sbox[i] + key[i]) % 256
            tmp = sbox[i]
            sbox[i] = sbox[j]
            sbox[j] = tmp
        return sbox

    def rc4_decrypt(self, sbox, data):
        out = bytearray(len(data))
        i = 0
        j = 0
        for k in range(len(data)):
            i = (i + 1) % 256
            j = (j + sbox[i]) % 256
            tmp = sbox[i]
            sbox[i] = sbox[j]
            sbox[j] = tmp
            val = sbox[(sbox[i] + sbox[j]) % 256]
            out[k] = val ^ data[k]

        return out
