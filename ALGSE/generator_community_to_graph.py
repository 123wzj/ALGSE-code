
import collections

import random
import time
import networkx as nx
import matplotlib.pyplot as plt
from config import *
import pickle
"""
Louvain community detection adapted to the DARPA TC data; the detected communities can be written out as graphs.
"""



def load_graph(path):
    allGraph = {}
    with open(path, 'rb') as f:
        graphSeq = pickle.load(f)
    for index, graph in graphSeq.items():
        allGraph[index] = graph
    # G = collections.defaultdict(dict)
    # with open(path) as text:
    #     for line in text:
    #         vertices = line.strip().split()
    #         v_i = int(vertices[0])
    #         v_j = int(vertices[3])
    #         w = 1.0  # use the dataset's weight if it has one
    #         G[v_i][v_j] = w
    #         G[v_j][v_i] = w
    return allGraph


# vertex class: holds the node id and its community id
class Vertex:
    def __init__(self, vid, cid, nodes, k_in=0):
        # node id
        self._vid = vid
        # community id
        self._cid = cid
        self._nodes = nodes
        self._kin = k_in  # weight of the edges inside the node


class Louvain:
    ### initially every node is its own community
    def __init__(self, G):
        ## self._G holds the connections between communities
        self._G = G
        ## self._nodeG holds the connections between the original nodes
        self._nodeG = G
        # self._m = 0  # edge count; changes as the graph is aggregated
        self._m = G.edges().__len__()
        self._cid_vertices = {}  # community id -> set of node ids
        self._vid_vertex = {}  # node id -> Vertex instance
        for vid in self._G.nodes():
            # every node starts as its own community
            self._cid_vertices[vid] = {vid}
            # the initial community id is the node id
            self._vid_vertex[vid] = Vertex(vid, vid, {vid})
            # count edges; one edge per node pair
            # self._m += sum([1 for neighbor in self._G[vid].keys()
            #                if neighbor > vid])

    # modularity optimisation phase
    def first_stage(self):
        mod_inc = False  # whether the algorithm can stop
        visit_sequence = self._G.nodes()
        # visit order
        random.shuffle(list(visit_sequence))
        while True:
            can_stop = True  # whether the first phase can stop
            # iterate over all nodes
            for v_vid in visit_sequence:
                # community id of the node
                v_cid = self._vid_vertex[v_vid]._cid
                # k_v: weighted degree of the node, inner plus outer edge weights


                k_v = sum(edge[2]['weight'] for edge in self._G.edges(v_vid, data=True)) +self._vid_vertex[v_vid]._kin
                # k_v = sum(self._G[v_vid].values()) + \
                #     self._vid_vertex[v_vid]._kin
                # community ids with a positive modularity gain
                cid_Q = {}
                # iterate over the neighbours
                for z,w_vid in self._G.edges(v_vid):
                # for w_vid in self._G[v_vid].keys():
                    # community id of the neighbour
                    w_cid = self._vid_vertex[w_vid]._cid
                    if w_cid in cid_Q:
                        continue
                    else:
                        # tot: total weight of the links incident to nodes in community C
                        # tot = sum(
                        #     [sum(self._G[k].values()) + self._vid_vertex[k]._kin for k in self._cid_vertices[w_cid]])
                        tot = 0
                        for k in self._cid_vertices[w_cid]:
                          tot += sum(edge[2]['weight'] for edge in self._G.edges(k, data=True)) + self._vid_vertex[k]._kin

                        if w_cid == v_cid:
                            tot -= k_v
                        # k_v_in: total weight of the links from node i to nodes in C
                        # k_v_in = sum(
                        #     [v for k, v in self._G[v_vid].items() if k in self._cid_vertices[w_cid]])
                        k_v_in = sum(
                            [v['weight'] for x, k, v in self._G.edges(v_vid,data=True) if k in self._cid_vertices[w_cid]])
                        # only the sign of delta_Q matters, so the factor 1/(2*self._m) is dropped
                        delta_Q = k_v_in - k_v * tot / self._m
                        cid_Q[w_cid] = delta_Q

                # community with the largest gain
                cid, max_delta_Q = sorted(
                    cid_Q.items(), key=lambda item: item[1], reverse=True)[0]
                if max_delta_Q > 0.0 and cid != v_cid:
                    # move the node to the community with the largest gain
                    self._vid_vertex[v_vid]._cid = cid
                    # add the node to that community
                    self._cid_vertices[cid].add(v_vid)
                    # remove the node from its previous community
                    self._cid_vertices[v_cid].remove(v_vid)
                    # modularity can still increase; keep iterating
                    can_stop = False
                    mod_inc = True
            if can_stop:
                break
        return mod_inc

    # aggregation phase
    def second_stage(self):
        cid_vertices = {}
        vid_vertex = {}
        # iterate over communities and their nodes
        for cid, vertices in self._cid_vertices.items():
            if len(vertices) == 0:
                continue
            new_vertex = Vertex(cid, cid, set())
            # collapse the community into one node
            for vid in vertices:
                new_vertex._nodes.update(self._vid_vertex[vid]._nodes)
                new_vertex._kin += self._vid_vertex[vid]._kin
                # k, v: neighbour and edge weight; sum the intra-community weight k_in; each edge is seen from both ends so the weight is halved
                for x, k, v in self._G.edges(vid,data=True):
                # for k, v in self._G[vid].items():
                    if k in vertices:
                        new_vertex._kin += v['weight']/ 2.0
                        # new_vertex._kin += v / 2.0
            # new community and node ids
            cid_vertices[cid] = {cid}
            vid_vertex[cid] = new_vertex
        G = nx.Graph(name="new_Grapher", data=True, align='vertical')
        # G = collections.defaultdict(dict)
        # for every non-empty community, compute the weight of the edges to the other communities
        for cid1, vertices1 in self._cid_vertices.items():
            if len(vertices1) == 0:
                continue
            for cid2, vertices2 in self._cid_vertices.items():
                # the next non-empty community after cid
                if cid2 <= cid1 or len(vertices2) == 0:
                    continue
                edge_weight = 0.0
                # iterate over the nodes of cid1
                for vid in vertices1:
                    # sum the weights of the node's edges into cid2 (total inter-community weight; parallel edges count as one)
                    for a,k,v in self._G.edges(vid,data=True):
                    # for k, v in self._G[vid].items():
                        if k in vertices2:
                            edge_weight += v['weight']
                if edge_weight != 0:
                    # G[cid1][cid2] = edge_weight
                    # G[cid2][cid1] = edge_weight
                    G.add_edge(cid1, cid2, weight=edge_weight)
        # update communities and nodes; each community becomes one node
        self._cid_vertices = cid_vertices
        self._vid_vertex = vid_vertex
        self._G = G
    def get_communities_with_connections(self):
        communities = {}
        community_connections = {}

        for cid, vertices in self._cid_vertices.items():
            if len(vertices) != 0:
                c = set()
                for vid in vertices:
                    c.update(self._vid_vertex[vid]._nodes)
                if cid not in communities:
                    communities[cid] = []
                communities[cid]=list(c)


        for cid1, vertices1 in self._cid_vertices.items():
            if len(vertices1) == 0:
                continue
            for cid2, vertices2 in self._cid_vertices.items():
                ## make sure the two communities differ
                if cid2 <= cid1 or len(vertices2) == 0:
                    continue

                ## iterate over the nodes of cid1
                for nid in self._vid_vertex[cid1]._nodes:
                    ## iterate over the neighbours of each node in cid
                    for u,k,v in self._G.edges(nid,data=True):
                    # for k, v in self._nodeG[nid].items():
                        ### a neighbour in cid2 makes both nodes boundary nodes
                        ## stored as: community 1, community 2, (node id in community 1, node ids in community 2)
                        if k in self._vid_vertex[cid1]._nodes:
                            continue
                        if k in self._vid_vertex[cid2]._nodes:
                            if (cid1,cid2) not in community_connections and (cid2,cid1) not in community_connections:
                                community_connections[(cid1,cid2)]={}
                            if (cid1,cid2) in community_connections.keys():
                                if nid not in community_connections[((cid1,cid2))]:
                                    community_connections[((cid1,cid2))][nid]=set()
                                community_connections[((cid1,cid2))][nid].add(k)
                            else:
                                if nid not in community_connections[((cid2, cid1))]:
                                    community_connections[((cid2, cid1))][nid] = set()
                                community_connections[((cid2, cid1))][nid].add(k)

        return communities, community_connections

    def get_communities(self):
        communities = []
        for vertices in self._cid_vertices.values():
            if len(vertices) != 0:
                c = set()
                for vid in vertices:
                    c.update(self._vid_vertex[vid]._nodes)
                communities.append(list(c))
        return communities
    def save_communities_to_graph(self, communities, save_path):
        """
               Convert every community to a graph and save it as a .pkl file.
               :param communities: the partition (dict or list)
               :param output_dir: output directory
               """
        if isinstance(communities, dict):
            communities = communities.values()  # dict form: take the node lists
        GraphSeq = {}

        for idx, community in enumerate(communities):
            # build the community graph
            community_graph = nx.Graph()
            # add nodes
            community_graph.add_nodes_from(community)
            # add edges (intra-community only)
            for node in community:
                for neighbor in self._nodeG[node]:
                    if neighbor in community:
                        community_graph.add_edge(node, neighbor)
            GraphSeq[idx] = community_graph
        with open(save_path,'wb') as fs:
            pickle.dump(GraphSeq,fs)
            # print("community graph saved")
    # def execute(self):
    #     iter_time = 1
    #     while True:
    #         iter_time += 1
    #         # iterate until no node move improves the modularity
    #         mod_inc = self.first_stage()
    #         if mod_inc:
    #             self.second_stage()
    #         else:
    #             break
    #     return self.get_communities()
    def execute(self):
        iter_time = 1
        while True:
            iter_time += 1
            mod_inc = self.first_stage()
            if mod_inc:
                self.second_stage()
            else:
                break
        communities, community_connections = self.get_communities_with_connections()
        return communities, community_connections


# plot the partition
def showCommunity(G, partition, pos,save_path = "community.png"):
    # one marker per community; inter-community edges in bold black
    cluster = {}
    labels = {}
    for index, item in enumerate(partition):
        for nodeID in item:
            labels[nodeID] = r'$' + str(nodeID) + '$'  # node label
            cluster[nodeID] = index  # partition index of the node

    # draw nodes
    colors = ['r', 'g', 'b', 'y', 'm']
    shapes = ['v', 'D', 'o', '^', '<']
    for index, item in enumerate(partition):
        nx.draw_networkx_nodes(G, pos, nodelist=item,
                               node_color=colors[index%5],
                               node_shape=shapes[index%5],
                               node_size=350,
                               alpha=1)

    # draw edges
    edges = {len(partition): []}
    for link in G.edges():
        # inter-cluster links
        if cluster[link[0]] != cluster[link[1]]:
            edges[len(partition)].append(link)
        else:
            # intra-cluster links
            if cluster[link[0]] not in edges:
                edges[cluster[link[0]]] = [link]
            else:
                edges[cluster[link[0]]].append(link)

    for index, edgelist in enumerate(edges.values()):
        # intra-cluster
        if index < len(partition):
            nx.draw_networkx_edges(G, pos,
                                   edgelist=edgelist,
                                   width=1, alpha=0.8, edge_color=colors[index%5])
        else:
            # inter-cluster
            nx.draw_networkx_edges(G, pos,
                                   edgelist=edgelist,
                                   width=3, alpha=0.8, edge_color=colors[index%5])

    # draw labels
    nx.draw_networkx_labels(G, pos, labels, font_size=12)

    plt.axis('off')
    # save the figure
    plt.savefig(save_path, format='png', dpi=300, bbox_inches='tight')
    # print(f"figure saved to {save_path}")
    plt.close()  # close the figure

def cal_Q(partition, G):  # modularity Q
    # data=True returns (u, v, ddict) triples, otherwise (u, v) pairs
    m = len(G.edges(None, False))
    # print(G.edges(None,False))
    # print("=======6666666")
    a = []
    e = []
    for key in partition:
        community=partition[key]
    # for community in partition:  # each connected subgraph
        t = 0.0
        for node in community:  # each vertex of the subgraph
            # G.neighbors(node): the neighbours of node
            t += len([x for x in G.neighbors(node)])
        a.append(t / (2 * m))
    #             self.zidian[t/(2*m)]=community
    for key in partition:
        community = partition[key]
        t = 0.0
        for i in range(len(community)):
            for j in range(len(community)):
                if (G.has_edge(community[i], community[j])):
                    t += 1.0
        e.append(t / (2 * m))

    q = 0.0
    for ei, ai in zip(e, a):
        q += (ei - ai ** 2)
    return q

class Graph:
    # graph = nx.DiGraph()

    def __init__(self):
        self.graph = nx.Graph()

    def createGraph(self, filename):
        file = open(filename, 'r')

        for line in file.readlines():
            nodes = line.split()
            edge = (int(nodes[0]), int(nodes[3]))
            self.graph.add_edge(*edge)

        return self.graph


# if __name__ == '__main__':
#     allGraph = load_graph(medium_file_path+"graph.pkl")
#
#     obj = Graph()
#
#     ## community file
#     community_file_path = medium_file_path+"node_community.txt"
#
#     n = len(allGraph)
#     for index in range(n):
#         start_time = time.time()
#         pos = nx.spring_layout(allGraph[index])
#         algorithm = Louvain(allGraph[index])
#
#         communities,community_connections = algorithm.execute()
#         end_time = time.time()
#
#
#         output_file_path = community_graph_file_path+"community_to_graph_"+str(index)+".pkl"
#         algorithm.save_communities_to_graph(communities, output_file_path)
