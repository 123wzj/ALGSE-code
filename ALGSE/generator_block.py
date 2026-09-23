import os
import pickle

import networkx as nx
import numpy as np
from scipy.sparse import coo_matrix, csr_matrix
from utils import verbose_matrix, reorder_matrix, slashburn
from scipy.sparse import save_npz,load_npz,csc_matrix
from config import *
import json
"""
Block generation: takes the community graphs as input and writes the block files, storing only the non-zero blocks.
"""

def load_graph(path):
    allGraph = {}
    with open(path, 'rb') as f:
        graphSeq = pickle.load(f)
    for index, graph in graphSeq.items():
        allGraph[index] = graph
    return allGraph

"""Load blocks from JSON."""
def load_block_matrix_from_json(filename):
    with open(filename, "r") as f:
        block_info = json.load(f)

    block_matrix = {}
    for key, block_filename in block_info.items():
        # convert the string keys back to tuples
        i, j = map(int, key.split(","))
        if block_filename is None:
            block_matrix[(i, j)] = csr_matrix((0, 0), dtype='float32')  # create an empty sparse matrix
        else:
            try:
                block_matrix[(i, j)] = load_npz(block_filename)
            except FileNotFoundError:
                print(f"Warning: Block file {block_filename} not found. Using zero block.")
                block_matrix[(i, j)] = csr_matrix((0, 0), dtype='float32')  # create an empty sparse matrix
    return block_matrix

"""Store blocks as JSON."""
def save_block_matrix_to_json(filepath,block_matrix, filename):
    block_info = {}
    for (i, j), block in block_matrix.items():
        if block.nnz == 0:
            block_info[f"{i},{j}"] = None
        else:
            block_filename = filepath+f"block_{i}_{j}.npz"
            save_npz(block_filename, block)
            block_info[f"{i},{j}"] = block_filename

    with open(filename, "w") as f:
        json.dump(block_info, f)
        # print(f"wrote {filename}")

"""Block storage."""
# def block_matrix_storage(A, block_size):
#     """
#     Split the matrix into blocks and store the non-zero blocks with their positions.
#     """
#     num_rows, num_cols = A.shape
#     num_blocks_row = (num_rows + block_size - 1) // block_size
#     num_blocks_col = (num_cols + block_size - 1) // block_size
#
#     block_matrix = {}
#     for i in range(num_blocks_row):
#         for j in range(num_blocks_col):
#             block = A[i * block_size:(i + 1) * block_size, j * block_size:(j + 1) * block_size]
#             if block.nnz > 0:  # non-zero block
#                 block_matrix[(i, j)] = block
#
#
#     return block_matrix
## encode a block as a string


def block_to_string(block, block_size, position):
    """
    Encode the content and the position of a block as one string.

    Args:
    block (numpy.ndarray): block content.
    block_size (int): block size.
    position (tuple): block position (i, j).

    Returns:
    str: the encoded string.
    """
    # block content as a string
    # block_str = ''.join(str(int(x)) for row in block for x in row)
    block_str = ''.join(str(int(x)) for row in block for x in row.toarray().flatten())
    # block position as a string, zero-padded to two digits
    position_str = f"{position[0]}{position[1]}"

    # concatenate content and position
    result_str = f"{block_str}{position_str}"
    return result_str


def block_matrix_storage(A, block_size, f):
    """
    Split the matrix into blocks and store the non-zero blocks with their positions.

    Args:
    A (numpy.ndarray): input matrix.
    block_size (int): block size.
    filename (str): output file name.
    """
    num_rows, num_cols = A.shape
    num_blocks_row = (num_rows + block_size - 1) // block_size
    num_blocks_col = (num_cols + block_size - 1) // block_size
    # block_matrix = {}
    for i in range(num_blocks_row):
        for j in range(num_blocks_col):
            block = A[i * block_size:(i + 1) * block_size, j * block_size:(j + 1) * block_size]
            if block.nnz > 0:  # non-zero block
                block_str = block_to_string(block, block_size, (i, j))
                f.write(block_str)
                # block_matrix[(i, j)] = block_str

    # write the block records to the file
    # with open(filename, 'w') as f:
    #     for (i, j), block_str in block_matrix.items():
    #         f.write(block_str + '\n')

def load_files_from_directory(directory):
    # list everything in the directory
    files_and_folders = os.listdir(directory)
    # keep only files
    files = [os.path.join(directory, f) for f in files_and_folders if os.path.isfile(os.path.join(directory, f))]
    return files

"""Save the node mapping."""
def save_node_mapping_to_json(filepath, node_mapping, filename):
    with open(os.path.join(filepath, filename), "w") as f:
        json.dump(node_mapping, f, indent=4)
    # print(f"node mapping saved to {os.path.join(filepath, filename)}")

def generator_to_block(community_graph_file_path,block_number):
    file_path = community_graph_file_path
    files = load_files_from_directory(file_path)

    for file in files:
        ## one graph (snapshot) holds several communities
        allGraph = load_graph(file)
        n = len(allGraph)
        base_path = community_to_block + file.split("/")[-1].split(".")[0] + "/"

        if not os.path.exists(base_path):
            os.makedirs(base_path)

        graph_to_community_to_block = base_path+file.split("/")[-1].split(".")[0]+".txt"
        ## each community is a set of blocks; the adjacency of one community is written as one line
        f = open(graph_to_community_to_block, "w")
        for index in range(n):
            f.write(str(index) + " ")
            A = nx.to_numpy_array(allGraph[index])
            ### record the source file position and its id
            original_nodes = list(allGraph[index].nodes())
            original_nodes_to_index = {node: i for i, node in enumerate(original_nodes)}
            A = coo_matrix(A)

            perm, wing = slashburn(A)
            A_reordered = reorder_matrix(A, perm)
            # mapping from original node id to reordered index
            reordered_to_original = {new_idx: original_nodes[old_idx] for new_idx, old_idx in enumerate(perm)}
            node_mapping = {
                "reordered_to_original": reordered_to_original
            }
            # save the mapping
            # save_node_mapping_to_json(base_path, node_mapping, f"community_node_mapping_{index}.json")
            A_csr = A_reordered.tocsc()
            # # block size
            block_size = int(block_number)
            block_matrix_storage(A_csr, block_size,f)
        f.close()
            # save_block_matrix_to_json(block_out_file_path,block_matrix_A, block_out_file_path+"block_matrix_info.json")





