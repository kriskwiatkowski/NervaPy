import unittest


class FileHeaderSize(unittest.TestCase):
    def runTest(self):
        import nervapy.arm.abi
        from nervapy.formats.elf.file import FileHeader
        file_header = FileHeader(nervapy.arm.abi.arm_gnueabi)
        file_header_bytes = file_header.as_bytearray
        self.assertEqual(len(file_header_bytes), file_header.file_header_size,
                         "ELF header size must match the value specified in the ELF header")
