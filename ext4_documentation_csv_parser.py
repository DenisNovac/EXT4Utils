##
# This is the CSV parser for documentation in format:
# Offset, Length, Name [array_length]
# It will process Length of field as Length*array_length
##

# you MUST to prepare your csv first:
# for example, be sure to delete all one-row hints from it
# do not insert in it DESCRIPTIONS, only three field: offset, length and name!

# my prepared file with csv
CSV_PATH="superblock_csv_example.csv"
def parseCSV ( path ):
    offsets = [ ]
    lengths = [ ]
    names = [ ]
    # this is specification of superblock from https://ext4.wiki.kernel.org/index.php/Ext4_Disk_Layout#The_Super_Block
    f=open(path,"r")
    i=0
    for line in f:
        i=i+1
        p=0
        offset=""
        length=""
        name=""
        for c in line:
            if c=='\n': break
            if c==',':
                p=p+1
                continue
            if p==0: offset=offset+c
            if p==1: length=length+c
            if p==2: name=name+c

        #offsets.append(offset.encode('hex'))
        offsets.append(offset)
        if length=="__le64": length=8
        if length=="__le32": length=4
        if length=="__le16": length=2
        if length=="__u8": length=1
        if length=="char": length=1

        new_name=""
        mult_length=""
        if '[' in name:
            isNum=False
            for c in name:
                if c=='[':
                    isNum=True
                    continue
                if c==']': break
                if isNum:
                    mult_length=mult_length+c
                    continue
                new_name=new_name+c
            name=new_name
            length=length*int(mult_length)
        lengths.append(length)
        names.append(name)
    f.close()

    # this will give you a list of names to place it in some array
    '''
    string_variables=""
    for s in names:
        string_variables=string_variables+s+","
    print(string_variables)
    '''

    # this field must give out the size of your block from documentation
    sum=0
    for l in lengths:
        sum=sum+l
    print("PARSED LENGTH: "+str(sum))
    print("")


parseCSV(CSV_PATH)
