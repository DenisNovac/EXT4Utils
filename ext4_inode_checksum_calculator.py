'''
crc32c package from pip (https://pypi.org/project/crc32c/) copyright:

ICRAR - International Centre for Radio Astronomy Research
(c) UWA - The University of Western Australia, 2017
Copyright by UWA (in the framework of the ICRAR)
'''
# See the https://github.com/DenisNovac/EXT4Utils for License and dependencies
# this program must be execute in python2.7 and by SUPERUSER due to 
# ext4_raw_inode_searcher module

# Documentation https://ext4.wiki.kernel.org/index.php/Ext4_Disk_Layout#Checksums
# inode checksum:
# __le32 UUID + inode number + inode generation + the entire inode
# !!! The checksum field of inode is set to zero !!!
# 0x64 	__le32 	i_generation



import sys, struct
# pip install crc32c
import crc32c
# EXT4Utils DenisNovac repository dependencies:
import ext4_raw_inode_searcher

# return of ext4_raw_inode_searcher:
# [inode_num, s_inode_size, raw_inode, raw_superblock]
INODE_NUM=None
INODE_SIZE=None
RAW_INODE=None
RAW_SUPERBLOCK=None

def calc_inode_checksum():
    inode_hex_number=None
    inode_zero_cs=None
    inode_generation=None
    uuid=None

    uuid=RAW_SUPERBLOCK[0x68:0x68+16]
    print("uuid from superblock: "+uuid.encode('hex'))

    inode_generation=RAW_INODE[0x64:0x64+4]
    print("Inode generation: "+inode_generation.encode('hex'))

    print("Inode number from stat: "+hex(INODE_NUM))
    # to little-endian 4 bytes
    inode_hex_number=struct.pack("<L", INODE_NUM)
    print("Little-endian inode number: "+inode_hex_number.encode('hex'))

    # we need to fill checksum fields with zero first
    i_checksum_hi=RAW_INODE[0x82:0x82+2]
    i_checksum_lo=RAW_INODE[0x74+0x8:0x74+0x8+2]
    print("Checksum hi: "+i_checksum_hi.encode('hex'))
    print("Checksum lo: "+i_checksum_lo.encode('hex'))
    # this is what stat from debugfs gives out:
    print("Checksum from stat: "+i_checksum_hi[::-1].encode('hex')+i_checksum_lo[::-1].encode('hex'))
    inode_zero_cs=list(RAW_INODE)
    inode_zero_cs[0x82]="\x00"
    inode_zero_cs[0x83]="\x00"
    inode_zero_cs[0x74+0x8]="\x00"
    inode_zero_cs[0x75+0x8]="\x00"
    inode_zero_cs="".join(inode_zero_cs)
    print("Inode with zero checksum field: ")
    print(inode_zero_cs.encode('hex'))

    # now our inode is filled with zeroes
    # let's proceed to the formula:
    # UUID + inode number + inode generation + the entire inode

    joined_data=uuid+inode_hex_number+inode_generation+inode_zero_cs
    inode_cs=crc32c.crc32(joined_data)

    inverter=0xFFFFFFFF
    checksum_final=inverter-inode_cs

    print("CHECKSUM FROM INODE: "+hex(inode_cs))
    print("INVERTED (0xFFFFFFFF-previous field) CHECKSUM: "+hex(checksum_final))


# call module ext4_raw_inode_searcher, it will give us a lot of information:
# raw superblock to manipulate with uuid, raw inode
def call_inode_searcher():
    global INODE_NUM
    global INODE_SIZE
    global RAW_INODE
    global RAW_SUPERBLOCK

    crc32c.crc32("heu")
    # we don't want to see print() of the ext4_raw_inode_searcher here
    print("")
    print("========= ext4_raw_inode_searcher output =========")

    print("")
    inode_searcher_output = ext4_raw_inode_searcher.main( sys.argv )
    print("")
    print("==================================================")
    print("")
    INODE_NUM=inode_searcher_output[0]
    INODE_SIZE=inode_searcher_output[1]
    RAW_INODE=inode_searcher_output[2]
    RAW_SUPERBLOCK=inode_searcher_output[3]


def main():
    call_inode_searcher()
    calc_inode_checksum()

main()
