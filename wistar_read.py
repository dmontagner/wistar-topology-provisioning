#!/usr/bin/env python
 
import sqlite3
from sqlite3 import Error
import json
import graphviz as gv
import pprint
from collections import defaultdict
import yaml
from yaml.representer import Representer
import logging

# setting logging capabilities
log = logging.getLogger() # 'root' Logger
console = logging.StreamHandler()
format_str = '%(asctime)s\t%(levelname)s -- %(funcName)s %(filename)s:%(lineno)s -- %(message)s'
console.setFormatter(logging.Formatter(format_str))
log.addHandler(console) # prints to console.

# set the log level here
log.setLevel(logging.DEBUG) 
#log.setLevel(logging.ERROR) 

# adjusting the yaml representation for defaultdict
yaml.add_representer(defaultdict, Representer.represent_dict)
 
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by the db_file
    :param db_file: database file
    :return: Connection object or None
    """
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)
 
    return None
 
 
def select_all_topologies(conn):
    """
    Query all rows in the tasks table
    :param conn: the Connection object
    :return:
    """
    cur = conn.cursor()
    cur.execute("SELECT * FROM topologies_topology")
 
    rows = cur.fetchall()
 
    for row in rows:
        print(row)
 
 
def select_topology(conn, topology_name):
    """
    Query tasks by priority
    :param conn: the Connection object
    :param priority:
    :return:
    """
    cur = conn.cursor()
    cur.execute("SELECT * FROM topologies_topology WHERE name=?", (topology_name,))
 
    rows = cur.fetchall()
 
    #for row in rows:
    #    print(row)

    return rows
 
def generate_empty_yaml_var_file(dev_list, conn_list):
    # dmontagner@quanta5:~/scripts/wistar$ cat example_of_cfg_yaml.yaml
    # igp: ospf # ospf or isis
    # ibgp_asn: 65000 # internal iBGP
    # routers:
    #     pe1:
    #         role: pe           # p, pe, rr, ce
    #         interfaces:
    #             lo0:
    #                 area:      # isis or ospf area
    #                 level:     # isis level. if ospf, then set to None
    #                 passive:   # isis or ospf passive interface True or False
    #                 address:   # cidr of the interface
    #                 mpls:      # enable mpls on interface - True or False
    #                 remote:    # remote node:interface where this interface connect. If lo0, set to None. Informational only

    nested_dict = lambda: defaultdict(nested_dict)
    yaml_cfg = nested_dict()
    
    # igp defaults to ospf
    yaml_cfg['igp'] = "ospf"

    # ibgp_asn defaults to 65000
    yaml_cfg['ibgp_asn'] = 65000

    # sort the dev_list
    dev_list.sort()

    # iterate through routers
    for rtr in dev_list:
        
        # router hierarchy
        #yaml_cfg['routers'][rtr] = ""

        # role defaults to pe
        yaml_cfg['routers'][rtr]['role'] = "pe"

        # interfaces hierarchy
        #yaml_cfg['routers'][rtr]['interfaces'] = ""

        # iterate through the interfaces
        # the connection list is a list of dev:int:dev:int (src_dev:src_int:tgt_dev:tgt_int)
        #   hence, we need to check for all interfaces in both src and tgt dev
        for connection in conn_list:
            
            src_dev, src_int, tgt_dev, tgt_int = connection.split(":")

            if ( rtr in src_dev ):

                log.debug("router = %s / interface = %s", rtr, connection)

                # we will use src_int
                
                # defaults to 0.0.0.0
                yaml_cfg['routers'][rtr]['interfaces'][src_int]['area'] = "0.0.0.0"
                
                # ISIS Level defaults to 2
                yaml_cfg['routers'][rtr]['interfaces'][src_int]['level'] = 2

                # Passive defaults to false
                yaml_cfg['routers'][rtr]['interfaces'][src_int]['passive'] = False

                # Address defaults to ""
                yaml_cfg['routers'][rtr]['interfaces'][src_int]['address'] = ""

                # mpls defaults to True
                yaml_cfg['routers'][rtr]['interfaces'][src_int]['mpls'] = True

                # mpls defaults to True
                yaml_cfg['routers'][rtr]['interfaces'][src_int]['mpls'] = True

                # remote: if this is src, we fill up with tgt
                # remote: if this is tgt, we fill up with src
                yaml_cfg['routers'][rtr]['interfaces'][src_int]['remote'] = tgt_dev + ":" + tgt_int

                log.debug("info for routers|%s|interfaces|%s| has been added!", rtr, src_int)

            elif ( rtr in tgt_dev ):

                log.debug("router = %s / interface = %s", rtr, connection)

                # we will use tgt_int 
                
                # defaults to 0.0.0.0
                yaml_cfg['routers'][rtr]['interfaces'][tgt_int]['area'] = "0.0.0.0"
                
                # ISIS Level defaults to 2
                yaml_cfg['routers'][rtr]['interfaces'][tgt_int]['level'] = 2

                # Passive defaults to false
                yaml_cfg['routers'][rtr]['interfaces'][tgt_int]['passive'] = False

                # Address defaults to ""
                yaml_cfg['routers'][rtr]['interfaces'][tgt_int]['address'] = ""

                # mpls defaults to True
                yaml_cfg['routers'][rtr]['interfaces'][tgt_int]['mpls'] = True

                # mpls defaults to True
                yaml_cfg['routers'][rtr]['interfaces'][tgt_int]['mpls'] = True

                # remote: if this is src, we fill up with tgt
                # remote: if this is tgt, we fill up with src
                yaml_cfg['routers'][rtr]['interfaces'][src_int]['remote'] = tgt_dev + ":" + tgt_int

                log.debug("info for routers|%s|interfaces|%s| has been added!", rtr, tgt_int)

    pprint.pprint(yaml_cfg)
    output_yaml_file = open("result.yml", "w")
    yaml.dump(yaml_cfg, output_yaml_file, default_flow_style=False)
    output_yaml_file.close()


def main():
    database = "db.sqlite3"
    my_topology = None
    my_graph = gv.Graph(format='svg')
    connection_list = []
    node_list = []
 
    # create a database connection
    conn = create_connection(database)
    conn.row_factory = dict_factory
    node_name_id = dict()

    dev_int_map = dict()
    # pe1 : 0
    # left1 : 0
    # p1 : 0    
    
    device_interfaces_mapping = dict()
    node_id_type = dict()

    with conn:
        # print("1. Selecting topology by name (core_mpls):")
        my_topology = select_topology(conn,"core_mpls")
        
        # print("my_topology = %s" % my_topology)

        my_topo_json = my_topology[0]["json"]
        my_topo_load = json.loads(my_topo_json)

        TOPO_ITEM_TYPE_FLAG = None # VCP, VFP, VM or Connection

        for topo_item in my_topo_load:
            topo_item_type = topo_item["type"]
            # it means I found one topo obj that is either a VM, VCP or VFP
            if "vpfe" in topo_item_type:
                TOPO_ITEM_TYPE_FLAG="VFP"
            elif "vrf" in topo_item_type:
                TOPO_ITEM_TYPE_FLAG="VCP"
            elif "ubuntu" in topo_item_type:
                TOPO_ITEM_TYPE_FLAG="VM"
            elif "Connection" in topo_item_type:
                TOPO_ITEM_TYPE_FLAG="Connection"

            if ( TOPO_ITEM_TYPE_FLAG == "VFP" or TOPO_ITEM_TYPE_FLAG == "VCP" or TOPO_ITEM_TYPE_FLAG == "VM" ):
                topo_item_id = topo_item["id"].rstrip()
                topo_item_name = topo_item["userData"]["name"].rstrip()
                node_name_id[topo_item_id] = topo_item_name
                my_graph.node(node_name_id[topo_item_id])
                dev_int_map[node_name_id[topo_item_id]] = 0
                node_id_type[node_name_id[topo_item_id]] = TOPO_ITEM_TYPE_FLAG
                print("\n\n===================================")
                print("Node ID.....: %s" % topo_item_id)
                print("Node Name...: %s" % topo_item_name)
                print("Node Type...: %s" % TOPO_ITEM_TYPE_FLAG)
                print("===================================")

                # updating the node_list for further yaml generation
                node_list.append(topo_item_name.encode("ascii"))

            elif ( TOPO_ITEM_TYPE_FLAG == "Connection" ):
                topo_item_id = topo_item["id"].rstrip()
                topo_item_source = topo_item["source"]["node"].rstrip()
                topo_item_target = topo_item["target"]["node"].rstrip()
                my_graph.edge(node_name_id[topo_item_source], node_name_id[topo_item_target])

                # add the mapping based on both source and targets
                # the interface mapping in wistar is bidir

                # first, identify the type of node for both src and target
                src_node_type = node_id_type[node_name_id[topo_item_source]]
                tgt_node_type = node_id_type[node_name_id[topo_item_target]]

                # second, identify the prefix of the src and tgt node interfaces based on their type
                src_node_prefix_int = None
                tgt_node_prefix_int = None
                src_offset = 0
                tgt_offset = 0
                if ( src_node_type == "VFP" ):
                    src_node_prefix_int = "ge-0/0/"
                    src_offset = 0
                elif ( src_node_type == "VM" ):
                    src_node_prefix_int = "ens"
                    src_offset = 4

                if ( tgt_node_type == "VFP" ):
                    tgt_node_prefix_int = "ge-0/0/"
                    tgt_offset = 0
                elif ( tgt_node_type == "VM" ):
                    tgt_node_prefix_int = "ens"
                    tgt_offset = 4

                # third, calculate the interface number based on the offset
                # VMX offset is 0
                # Ubuntu offset is 4
                src_int_number = dev_int_map[node_name_id[topo_item_source]] + src_offset
                tgt_int_number = dev_int_map[node_name_id[topo_item_target]] + tgt_offset

                # fourth, define the actual interface name for both source and target nodes
                src_int_name = src_node_prefix_int + str(src_int_number)
                tgt_int_name = tgt_node_prefix_int + str(tgt_int_number)

                print("\n\n-----------------------------------")
                print("Node ID......: %s" % topo_item_id)
                print("Node Source..: %s-%s (id = %s)" % (node_name_id[topo_item_source], src_int_name, topo_item_source))
                print("Node Target..: %s-%s (id = %s)" % (node_name_id[topo_item_target], tgt_int_name, topo_item_target))
                print("Node Type....: %s" % TOPO_ITEM_TYPE_FLAG)
                print("-----------------------------------")

                # updating the connection_list for further yaml generation
                # connection format is a string: dev:int:dev:int (connections are bidir)
                connection_str = None
                connection_str = node_name_id[topo_item_source].encode("ascii") + ":" + src_int_name.encode("ascii") + ":" + node_name_id[topo_item_target].encode("ascii") + ":" + tgt_int_name.encode("ascii")
                connection_list.append(connection_str.encode("ascii"))

                # updating the counters of the interfaces
                dev_int_map[node_name_id[topo_item_source]] = dev_int_map[node_name_id[topo_item_source]] + 1
                dev_int_map[node_name_id[topo_item_target]] = dev_int_map[node_name_id[topo_item_target]] + 1

            TOPO_ITEM_TYPE_FLAG = None

    # render graph file
    filename = my_graph.render(filename="my_graph.svg")

    # render yaml variable files
    generate_empty_yaml_var_file(node_list, connection_list)
    



# (Pdb) p my_topo_load[0]
# {u'userData': {}, u'angle': 0, u'bgColor': u'none', u'color': u'none', u'dasharray': None, u'height': 55, # u'width': 50, u'stroke': 1, u'radius': 0, u'alpha': 1, u'y': 115, u'x': 667, u'cssClass': 
# u'draw2d_shape_composite_Group', u'type': u'draw2d.shape.composite.Group', u'id': 
# u'46b90879-6cff-3170-3f10-6e1b4b697553', u'ports': []}

# (Pdb) p my_topo_load[0]["height"]
# 55
# (Pdb)

        #print("my_topology = %s" % my_topology)

        # test
 
        # print("2. Query all tasks")
        # select_all_topologies(conn)
 
 
if __name__ == '__main__':
    main()
