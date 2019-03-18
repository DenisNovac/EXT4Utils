'''
Copyright (c) 2019 UrFU, Denis Yablochkin (yd.novac@gmail.com), Egor Maximov

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is furnished
to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

# This program is raw inode searcher for any files in EXT4 systems.
# You need to give it two arguments: path to your file and name of your device
# in /dev/ folder (such as /dev/sda1). Then program will search its raw inode
# data in file system ext4.

# This program must be executed by SUPERUSER (due to access to /dev/) and only in Python 2.7
# Documentation: https://ext4.wiki.kernel.org/index.php/Ext4_Disk_Layout


import os,sys,struct,math

INODE="Inode: " # This is how your system calls Inode field in STAT utility
# Change it if your system has translation for this word of something

# This method is just for reading stat utility output. You may comment the call
# from main function and then write your inode number in inodeNum variable
def readInodeNumber ( path ):
    bashCommand = "stat "+path+" > ./stat.txt"
    os.system(bashCommand)
    file=open("./stat.txt","r")
    searchInode=[ ]
    inodeNum=""
    carret=len(INODE)
    carret_i=0
    isInode=False
    for line in file:
        for char in line:
            if not isInode:
                if len(searchInode)==carret:
                    searchInode.pop(0)
                searchInode.append(char)
                if (''.join(searchInode)==INODE): isInode=True
            else:
                if not char.isdigit(): break
                inodeNum=inodeNum+char
    inodeNum=int(inodeNum)
    file.close()
    bashCommand = "rm ./stat.txt"
    os.system(bashCommand)
    return inodeNum


# Reading first block of EXT4 device for usable info
def readSuperblockInfo ( pathToDevice ):
    file=open(pathToDevice,"r")
    # Offset of a superblock
    sb_offset=0x400
    file.seek(sb_offset)

    # whole superblock for ext4_inode_checksum_calculator module
    whole_superblock=file.read(1024)

    # Array with all we need
    file.seek(sb_offset)
    bytes=file.read(0x68+0x10)
    #print(bytes.encode('hex'))
    file.close()

    # we'll need to reverse all bytes since it is in little endian
    s_log_block_size=toNumber(bytes[0x18:0x18+4])
    block_size=pow(2,(10+s_log_block_size))

    s_blocks_per_group=toNumber(bytes[0x20:0x20+4])

    s_inodes_per_group=toNumber(bytes[0x28:0x28+4])

    s_inode_size=toNumber(bytes[0x58:0x58+2])

    # actually, we do not need this to proceed, but you can check if your device
    # is correct by executing ls -l /dev/disk/by-uuid/
    # and also we do not need to reverse it since it is not little endian
    s_uuid=bytes[0x68:0x68+16]

    sb_info=[s_blocks_per_group, s_inodes_per_group, s_inode_size, block_size, whole_superblock]
    return sb_info


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


def findInodeTableOffset ( pathToDevice, inodeNum, sb_info ):
    s_inodes_per_group=sb_info[1]
    block_size=sb_info[3]

    # group number is always lesser integer of the fraction
    groupNumber=(inodeNum-1)/s_inodes_per_group
    groupNumber=int(math.floor(groupNumber))

    # find offset to the group descriptor (size is 64 bytes) of the group
    groupDescriptorOffset=groupNumber*64+block_size

    # now we need to jump to this offset in group descriptor
    # to find the offset with inode table where our inode is stored
    file=open(pathToDevice,"r")
    file.seek(groupDescriptorOffset)

    # inode table offets in group descriptor:
    # 0x8 	__le32 	bg_inode_table_lo
    # 0x28 	__le32 	bg_inode_table_hi
    bytes=file.read(0x28+4) # read all descriptor up to high inode table offset
    file.close()
    #print(bytes.encode('hex'))

    # here we read high and low parts for offset to inode table where
    # our inode stored
    bg_inode_table_lo=bytes[0x8:0x8+4]
    bg_inode_table_hi=bytes[0x28:0x28+4]

    # make one number from parts in BIG ENDIAN (we used reversed)
    bg_inode_table=list(reversed(bg_inode_table_hi))+list(reversed(bg_inode_table_lo))
    inode_table_block_string="".join(bg_inode_table)

    # converting it to integer
    inode_table_block=struct.unpack(">Q",inode_table_block_string)

    # making absolute offset to inode table with needed inode
    inode_table_offset=inode_table_block[0]*block_size

    return inode_table_offset


def readInode ( pathToDevice, sb_info, inodeNum, inode_table_offset ):
    # first of all, we need to find which inode in inode table we need
    # we know it's absolute number and amount of inodes per group:
    s_inodes_per_group=sb_info[1]
    s_inode_size=sb_info[2]

    relInodeNum=(inodeNum-1)%s_inodes_per_group

    # using size of inode find relational offset to inode in table:
    rel_inode_offset=relInodeNum*s_inode_size
    print("Relative inode offset in table: "+str(rel_inode_offset))

    # now we jump to inode table offset, then jump to relational offset of
    # needed inode, then read it in memory
    file=open(pathToDevice,"r")
    file.seek(inode_table_offset+rel_inode_offset)
    bytes=file.read(s_inode_size)
    file.close()
    print("RAW INODE OF FILE: ")
    print(bytes.encode('hex'))

    # writing to binary file for analysis
    f = open("output.bin","w+b")
    f.write(bytes)
    f.close()
    return bytes


# error message if too few arguments given
def errorMsg ( ):
    print("")
    print("TOO FEW ARGUMENTS")
    print("USAGE: sudo python2.7 inode_searcher.py <PATH TO FILE> <PATH TO DEVICE>")
    print("Path to file may be like: /home/user/file1.txt")
    print("Path to device MUST BE like: /dev/sda7")
    exit()
    return -1


def main ( args ):
    pathToFile=args[1]
    pathToDevice=args[2]

    inode_num=readInodeNumber(pathToFile)
    print("Inode number: "+str(inode_num))
    print("")

    sb_info=readSuperblockInfo(pathToDevice)


    print("Superblock info:")
    print("Blocks per group: "+str(sb_info[0]))
    print("Inodes per group: "+str(sb_info[1]))
    print("Inode size: "+str(sb_info[2]))
    print("Block size: "+str(sb_info[3]))
    print("")

    inode_table_offset=findInodeTableOffset(pathToDevice,inode_num,sb_info)
    print("Inode table offset: "+str(inode_table_offset))

    raw_inode=readInode(pathToDevice,sb_info,inode_num,inode_table_offset)
    print("")
    print("SEE THE OUTPUT.BIN FILE FOR ANALYSIS OF YOUR INODE")

    # return for ext4_inode_checksum_calculator module
    raw_superblock = sb_info[4] # for ext4_inode_checksum_calculator
    s_inode_size=sb_info[2]
    return [inode_num, s_inode_size, raw_inode, raw_superblock]


# need this if to not execute code while importing it inside
# ext4_inode_checksum_calculator
if __name__ == "__main__":
    # Start :)
    print("-=Inode Searcher for EXT4=-")
    if (len(sys.argv)<3): errorMsg()
    main(sys.argv)
