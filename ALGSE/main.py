from config import *
from parse_theia_e3 import *
from generator_block import *
from generator_community_to_graph import *
from graphBulid import *
from datetime import datetime
import time
import psutil
"""
Write path
1. Parse the raw logs into file.txt, socket.txt, process.txt and event.txt; event.txt holds the event four-tuples.
2. Apply the prefix mapping in map.txt to the entity files to reduce redundancy (file_mapping.txt, socket_mapping.txt, process_mapping.txt, event_mapping.txt). This step is not invoked here.
3. Build the snapshot graphs from event.txt.
4. Partition every snapshot into communities.
5. Reorder the nodes of each community and write the block files, together with the community table (community id, original node id, reordered node id).
"""
if __name__ == '__main__':
    process = psutil.Process()
    initial_memory = process.memory_info().rss / (1024 ** 2)
    print(f"initial memory before parsing: {initial_memory:.2f} MB")
### parsing
    start_time = datetime.now()
    # print("reading and write subject")
    raw_dir = "data/"
    writeSubjectFile = parse_file_path + "subject.txt"
    subjectID, countsubject = store_subject(raw_dir, writeSubjectFile)
    # print("reading and writing file")
    writeFile = parse_file_path + "file.txt"
    fileID, countFile = store_file(raw_dir, writeFile, countsubject)
    # print("reading and writing socket")
    writeNetFile = parse_file_path + "socket.txt"
    netID, countsocket = store_netflow(raw_dir, writeNetFile, countFile)
    # print("the entity num is " + str(countsocket))
    # print("creat edges")
    writeIdtouuid = parse_file_path + "id_to_uuid.txt"
    entity_mapping = writeIdToUid(writeIdtouuid, subjectID, fileID, netID)
    writeEventFile = parse_file_path + "event.txt"
    store_event(raw_dir, subjectID, fileID, netID, writeEventFile)
    end_time = datetime.now()
    print(f"parsing took {end_time-start_time} ({(end_time-start_time).total_seconds()} s)")


    ### graph construction
    start_time = datetime.now()
    graphnumber = 5000
    readpath = parse_file_path+"event.txt"
    writepath = medium_file_path+"graph.pkl"
    file_train_num = graphBuild(readpath, graphnumber, writepath)
    # print("file-train-num",file_train_num)
    end_time = datetime.now()
    print(f"graph construction took {end_time-start_time} ({(end_time-start_time).total_seconds()} s)")


    ### community detection
    start_time = datetime.now()
    allGraph = load_graph(medium_file_path + "graph.pkl")

    obj = Graph()

    ## community file

    community_file_path = medium_file_path + "node_community.txt"

    n = len(allGraph)
    total_community = 0
    for index in range(n):
        pos = nx.spring_layout(allGraph[index])
        algorithm = Louvain(allGraph[index])

        communities, community_connections = algorithm.execute()
        end_time = time.time()
        total_community+=len(communities)

        output_file_path = community_graph_file_path + "graph_to_community_" + str(index) + ".pkl"
        algorithm.save_communities_to_graph(communities, output_file_path)
    end_time = datetime.now()
    print("total communities: " + str(total_community))
    print(f"community detection took {end_time - start_time} ({(end_time - start_time).total_seconds()} s)")


    ## block generation
    start_time = datetime.now()
    file_path = community_graph_file_path
    generator_to_block(file_path,'4')
    end_time = datetime.now()
    print(f"block generation took {end_time - start_time} ({(end_time - start_time).total_seconds()} s)")

    final_memory = process.memory_info().rss / (1024 ** 2)
    print(f"final memory: {final_memory:.2f} MB")

    # memory consumed by the pipeline
    memory_used = final_memory - initial_memory
    print(f"memory consumed: {memory_used:.2f} MB")
"""
Read path
1. Locate the POI: its node type selects the entity table, which gives its community id.
2. Decode the blocks of that community and map the reordered indices back to the original node ids through the community table.
3. Rebuild the community graph and attach the attributes from file.txt, socket.txt, process.txt and event.txt.
4. Find the boundary nodes of the community and the communities they lead to.
5. Repeat steps 1 to 4 on those communities.
"""