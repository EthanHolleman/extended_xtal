from schema.utils import *
import pprint
import matplotlib.pyplot as plt
from networkx.drawing.nx_agraph import graphviz_layout
import networkx as nx


def main():
    json_dir = '/home/ethan/Documents/github/extended_xtal/schemas/'
    # change above to cmd line argument
    json_files = collect_jsons(json_dir, string=True)
    objs = [obj.init_from_json(p) for p in json_files]
    spliced_objects = splice_objects(objs)
    g = make_graph(spliced_objects)
    g.render()

   
    



if __name__ == "__main__":
    main()