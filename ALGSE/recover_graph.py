import os
import json
import numpy as np
from config import *
import networkx as nx
from scipy.sparse import load_npz, csr_matrix, coo_matrix
"""Recover the structure graph of a community from its stored blocks."""
def load_block_matrix_from_json(filename):
    """
    Load the block JSON file and return the block matrices.
    """
    with open(filename, "r") as f:
        block_info = json.load(f)

    block_matrix = {}
    for key, block_filename in block_info.items():
        i, j = map(int, key.split(","))
        if block_filename is None:
            block_matrix[(i, j)] = csr_matrix((0, 0), dtype='float32')
        else:
            try:
                block_matrix[(i, j)] = load_npz(block_filename)
            except FileNotFoundError:
                print(f"Warning: Block file {block_filename} not found. Using zero block.")
                block_matrix[(i, j)] = csr_matrix((0, 0), dtype='float32')
    return block_matrix

def load_node_mapping_from_json(filename):
    """
    Load the node mapping JSON file.
    """
    with open(filename, "r") as f:
        node_mapping = json.load(f)
    return node_mapping

def reconstruct_adjacency_matrix(block_matrix, block_size, matrix_shape):
    """
    Rebuild the full adjacency matrix from the blocks.
    """
    num_rows, num_cols = matrix_shape
    num_blocks_row = (num_rows + block_size - 1) // block_size
    num_blocks_col = (num_cols + block_size - 1) // block_size

    # empty sparse matrix
    A = csr_matrix((num_rows, num_cols), dtype='float32')

    for i in range(num_blocks_row):
        for j in range(num_blocks_col):
            if (i, j) in block_matrix:
                block = block_matrix[(i, j)]
                row_start, col_start = i * block_size, j * block_size
                row_end, col_end = min(row_start + block_size, num_rows), min(col_start + block_size, num_cols)
                A[row_start:row_end, col_start:col_end] = block[:row_end - row_start, :col_end - col_start]

    return A

def reconstruct_graph_from_adjacency_matrix(A, node_mapping):
    """
    Rebuild the graph from the adjacency matrix.
    """
    # mapping from reordered index to original node id
    reordered_to_original = node_mapping["reordered_to_original"]
    original_nodes = [reordered_to_original[str(i)] for i in range(A.shape[0])]

    # rebuild the graph
    G = nx.from_scipy_sparse_matrix(A, create_using=nx.Graph())
    mapping = {i: original_nodes[i] for i in range(len(original_nodes))}
    G = nx.relabel_nodes(G, mapping)

    return G

def reconstruct_community_graphs(block_out_file_path, community_node_path, block_size):
    """
    Recover the graph of every community from its blocks and node mapping.
    """
    community_graphs = []
    block_matrix = load_block_matrix_from_json(block_out_file_path)
    # load the node mapping
    node_mapping = load_node_mapping_from_json(community_node_path)

    # rebuild the adjacency matrix
    A = reconstruct_adjacency_matrix(block_matrix, block_size, matrix_shape=(
    len(node_mapping["reordered_to_original"]), len(node_mapping["reordered_to_original"])))

    # rebuild the graph
    G = reconstruct_graph_from_adjacency_matrix(A, node_mapping)
    community_graphs.append(G)

    return community_graphs

if __name__ == '__main__':
    # paths

    block_out_file_path = community_to_block+"community_to_graph_3/block/0/block_matrix_info.json"
    community_node_path = community_to_block+"community_to_graph_3/community_node/community_node_mapping_0.json"
    block_size = 4  # block size

    # recover every community
    community_graphs = reconstruct_community_graphs(block_out_file_path, community_node_path,block_size)

    # print each community
    for index, G in enumerate(community_graphs):
        print(f"community {index}:")
        print(f"nodes: {G.number_of_nodes()}")
        print(f"edges: {G.number_of_edges()}")
        print(f"node list: {list(G.nodes())}")
        print(f"edge list: {list(G.edges())}")