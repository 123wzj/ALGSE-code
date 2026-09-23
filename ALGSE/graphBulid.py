'''
Description: build the snapshots
Usage:
Parameters:  xxxx-preprocess.txt
Return:
Author: Ying Jie
LastEditTime: 2023-09-17 13:53:46
'''
import os
import networkx as nx
import pickle
from config import *
"""
Read the parsed events, build the snapshot graphs and return their number.
"""
graphName = 'Graph'
G = nx.Graph(name=graphName, data=True, align='vertical')  # undirected
GraphSeq = {}


def createGraph(self, filename):
    file = open(filename, 'r')

    for line in file.readlines():
        nodes = line.split()
        edge = (int(nodes[0]), int(nodes[2]))
        self.graph.add_edge(*edge)

    return self.graph
def graphBuild(readFilepath,graph_node_num,writeFillpath):
    graph_id = 0
    n = graph_node_num

    with open(readFilepath) as f:
        while True:
            line = f.readline().strip()
            # print(line)
            if not line: break
            splits = line.split(' ')
            subUUID,  eventType, objUUID,  timeStamp = splits[0], splits[1], splits[2], splits[3],
            # print(eventType, subType, objType)


            if not G.has_node(subUUID):
                # G.add_node(subUUID, type=subType, time=timeStamp)
                G.add_node(subUUID)
            if not G.has_node(objUUID):
                # G.add_node(objUUID, type=objType, time=timeStamp)
                G.add_node((objUUID))
            if not G.has_edge(subUUID, objUUID):
                # G.add_edge(subUUID, objUUID, time=timeStamp, key=eventType)
                G.add_edge(subUUID, objUUID,weight = 1)
            else:
                G[subUUID][objUUID]['weight'] += 1
            # G.nodes()[subUUID]['time'], G.nodes()[objUUID]['time'] = timeStamp, timeStamp  # update node timestamps

            if len(G.nodes()) >= n:
                GraphSeq[graph_id] = G.copy()
                graph_id += 1
                G.clear()
    ## flush the remaining events
    GraphSeq[graph_id] = G.copy()
    graph_id += 1
    G.clear()
    os.makedirs(os.path.dirname(writeFillpath),exist_ok=True)
    # specificSnapshotFile = r"ProcessedData/drapra3/theia/train/graph/graph.pkl"
    # specificSnapshotFile = r"ProcessedData/drapra3/theia/test/data/graph.pkl"
    # create_folder_for_file(specificSnapshotFile)
    # with open(os.getcwd() + os.path.join(SnapshotDir,  '22_test_ext.pkl'), 'wb') as fs:
    with open(writeFillpath, 'wb') as fs:
        pickle.dump(GraphSeq, fs)
    return graph_id

# graphnumber = 3000
# readpath = medium_file_path+"event.txt"
# writepath = medium_file_path+"graph.pkl"
# file_train_num = graphBuild(readpath, graphnumber, writepath)
# print("file-train-num",file_train_num)














