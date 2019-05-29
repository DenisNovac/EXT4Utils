# This program searches file blocks on the disk.
# It is similar to 'sudo debugfs /dev/sdX -R "blocks /X"'


# See the https://github.com/DenisNovac/EXT4Utils for License and dependencies
# this program must be execute in python2.7 and by SUPERUSER due to 
# ext4_raw_inode_searcher module

# Documentation https://ext4.wiki.kernel.org/index.php/Ext4_Disk_Layout#The_Contents_of_inode.i_block


import sys
import struct

# EXT4Utils DenisNovac repository dependencies:
import ext4_raw_inode_searcher

# return of ext4_raw_inode_searcher:
# [inode_num, s_inode_size, raw_inode, raw_superblock]
INODE_NUM=None
INODE_SIZE=None
RAW_INODE=None
RAW_SUPERBLOCK=None
BLOCK_SIZE=None
INODE_OFFSET=None
# inode and data of its file is in one group, so we can use it
GROUP_NUMBER=None
GROUP_DESCRIPTOR_OFFSET=None
BLOCKS_PER_GROUP=None

# copy of function from ext4_raw_inode_searcher
def toNumber ( hexList ):
    # This method is for converting bytes.
    # Letter L stands for unsigned long, H - unsigned short. This is not
    # important for Python (but it is usable for converting from C)
    # The L means 4 bytes, H means 2 bytes.
    # < means converting from little-endian
    if len(hexList)==4:length="L"
    if len(hexList)==2:length="H"
    out=struct.unpack("<"+length,hexList)
    # unpack gives list such as (2,0), we need only first number.
    out=int(out[0])
    return out


def call_inode_searcher():
    global INODE_NUM
    global INODE_SIZE
    global RAW_INODE
    global RAW_SUPERBLOCK
    global BLOCK_SIZE
    global INODE_OFFSET
    global GROUP_NUMBER
    global GROUP_DESCRIPTOR_OFFSET
    global BLOCKS_PER_GROUP

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
    INODE_OFFSET=inode_searcher_output[4]
    GROUP_NUMBER=inode_searcher_output[5]
    GROUP_DESCRIPTOR_OFFSET=inode_searcher_output[6]
    BLOCKS_PER_GROUP=inode_searcher_output[7]

    s_log_block_size=toNumber( RAW_SUPERBLOCK[0x18:0x18+4] )
    BLOCK_SIZE=pow(2,(10+s_log_block_size))



def find_data_blocks():
    data_blocks=[ ]

    s_creator_os=RAW_SUPERBLOCK[0x48:0x48+4]
    if not toNumber(s_creator_os)==0:
        print("This program is only for Linux (s_creator_os=0). Terminating.")
        exit(-1)
    i_blocks_lo=RAW_INODE[0x1C:0x1C+4]
    i_blocks_hi=RAW_INODE[0x74:0x74+2]
    zeroes="\x00\x00"
    i_blocks=zeroes+i_blocks_hi[::-1]+i_blocks_lo[::-1]
    # this variable is 512-byte blocks on the disk, not actual 4096-byte blocks!!!
    i_blocks_amount=struct.unpack(">q",i_blocks)[0]*512/BLOCK_SIZE
    print("Blocks of the file: "+str(i_blocks_amount))



    i_block_table_offset=0x28
    i_block_table_length=60
    print ("Global offset to extent tree for this file: "+str(INODE_OFFSET+i_block_table_offset))

    extent_tree=RAW_INODE[i_block_table_offset:i_block_table_offset+i_block_table_length]
    print("\nExtent tree of file: ")
    print (extent_tree.encode('hex'))
    magic_num=extent_tree[0:2]

    if magic_num.encode('hex')=="0af3":
        print("Magic number correct: 0xF30A. Working with Extent tree.")
    else:
        print("Your file system is not ext4 or not using Extent Tree.\nMagic number (0xF30A) not correct.\nTerminated.")
        exit (-1)
    
    print("\nExtent header:")
    extent_header=extent_tree[0:0x8+4]
    print(extent_header.encode("hex"))
    # amount of blocks used by inode
    eh_entries=toNumber( extent_tree[0x2:0x2+2] )
    print("Valid entries following the header: "+ str(eh_entries)+".")
    # depth = 0 means that this extend node points to data blocks
    eh_depth=toNumber( extent_tree[0x6:0x6+2] )
    print("Extent depth is: "+str(eh_depth)+".")

    if eh_depth==0:
        print("This is a 'leaf node' (extent depth=0). Header is followed by eh.entries of struct ext4_extent.")
        for i in range(1,eh_entries+1):
            print("\nEntry: "+str(i))
            entry=extent_tree[0x8+4+12*(i-1):0x8+4+12*i]
            print("\t"+entry.encode("hex"))
            print("\tee_block (first file block number that this extent covers in little-endian): "+entry[0x0:0x0+4].encode('hex'))
            print("\tee_len (number of block covered by extent in little-endian -> blocks in a row): "+entry[0x4:0x4+2].encode('hex'))
            ee_len=toNumber(entry[0x4:0x4+2])
            print("\tee_len (integer): "+str(ee_len))

            # all in little-endian
            ee_start_hi=entry[0x6:0x6+2]
            ee_start_lo=entry[0x8:0x8+4]
            # high bytes in big-endian goes left
            
            ee_start_sum_little_endian=ee_start_hi+ee_start_lo
            print("\tee_start (lo+hi in little-endian): "+ee_start_sum_little_endian.encode("hex"))
            
            zeroes="\x00\x00"
            ee_start_sum=zeroes+ee_start_hi[::-1]+ee_start_lo[::-1]
            print("\tee_start (0x0000+hi+lo in big-endian): "+ee_start_sum.encode("hex"))
            
            print ("\n\tData blocks of extent:")
            first_block_of_extent=struct.unpack(">q",ee_start_sum)[0]
            for i in range(0,ee_len):
                data_blocks.append(first_block_of_extent+i)
                print("\t"+str(first_block_of_extent+i))

    else: 
        print("This is an 'interior node' (depth>0). Wait for updates.")
        exit (-1)

    if not len(data_blocks)==i_blocks_amount:
        print("WARNING!")
        print("INODE BLOCKS NUMBER IS "+str(i_blocks_amount)+" BUT DETECTED BLOCKS NUMBER IS "+str(len(data_blocks)))
        print("USE sudo debugfs /dev/sdX -R 'blocks /X' TO CHECK THE OUTPUT!")

    print("\nDetected file's data blocks:")
    print (data_blocks)
    print("\n")


    return None






def main():
    call_inode_searcher()
    print ("Global inode offset: "+str(INODE_OFFSET))
    print ("Global group number: "+str(GROUP_NUMBER))
    print ("Global group descriptor offset: "+str(GROUP_DESCRIPTOR_OFFSET))
    find_data_blocks()
    
    #read_direct_address_blocks(sys.argv[2],i_block_array)






main()