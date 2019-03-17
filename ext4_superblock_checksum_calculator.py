'''
crc32c package from pip (https://pypi.org/project/crc32c/) copyright:

ICRAR - International Centre for Radio Astronomy Research
(c) UWA - The University of Western Australia, 2017
Copyright by UWA (in the framework of the ICRAR)
'''

##
# This script will read your EXT4 superblock, show you written in it checksum
# and then calculate this checksum by itself.
# You may use it to learn how checksum is calculates in EXT4
##

# pip install crc32c
import crc32c

# my device with ext4
DEVICE="/dev/sda7"

def calculateSuperblockChecksum ( pathToDevice ):
    file=open(pathToDevice,"r")
    # Offset of a superblock
    sb_offset=0x400
    file.seek(sb_offset)
    # superblock has 1024 bytes length
    bytes=file.read(1024)
    file.close()

    print("ORIGINAL SUPERBLOCK:")
    print(bytes.encode('hex'))
    print("")

    # 0x3FC - offset to checksum
    # bytes_nocs - original superblock without checksum (1020 bytes)
    bytes_nocs=bytes[0:0x3FC]

    checksum_raw=crc32c.crc32(bytes_nocs)
    print("ORIGINAL CHECKSUM (not calculated, big endian!): 0x"+rev(bytes[0x3FC:0x3FC+4]).encode('hex'))
    print("RAW SUPERBLOCK CRC32C CHECKSUM WITHOUT CHECKSUM FIELDS (1020 bytes): "+hex(checksum_raw))

    inverter=0xFFFFFFFF
    checksum_final=inverter-crc32c.crc32(bytes_nocs)
    print("INVERTED (0xFFFFFFFF-previous field): "+hex(checksum_final))

# simple arrays reverser, LE to BE and back
def rev ( array ):
    array=array[::-1]
    return array

calculateSuperblockChecksum(DEVICE)
