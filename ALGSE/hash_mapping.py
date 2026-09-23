from config import *
def replace_strings(read_file_path, mapping,write_file_path):
    wf = open(write_file_path,'w')
    with open(read_file_path, 'r') as file:
        lines = file.readlines()
    for line in lines:
        idx,pro = line.split(":")
        for source, target in mapping.items():
            pro = pro.replace(source, target)
        wf.writelines(idx+":"+pro)

    wf.close()
def read_mapping(file_path):
    mapping = {}
    with open(file_path, 'r') as file:
        for line in file:
            source, target = line.strip().split(':')
            mapping[source] = target
    return mapping

def restore_strings(read_file_path,mapping,write_file_path):
    wf = open(write_file_path,'w')
    with open(read_file_path, 'r') as file:
        lines = file.readlines()
    for line in lines:
        idx, pro = line.split(":")
        for target, source in mapping.items():
            pro = pro.replace(source, target)
        wf.writelines(idx + ":" + pro)
    wf.close()

mapping_file = "map.txt"
mapping_data = read_mapping(mapping_file)
replace_file = medium_file_path+"file.txt"
write_file = medium_file_path+"replace_file.txt"
restore_file = medium_file_path+"restore_file.txt"

# replace the string
replace_strings(replace_file, mapping_data,write_file)
restore_strings(write_file,mapping_data,restore_file)
