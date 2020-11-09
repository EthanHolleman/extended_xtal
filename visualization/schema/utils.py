import json
import networkx as nx
from pathlib import Path
from graphviz import Digraph


ALL_OBJS = set([])
HTML_FORMAT = '<p><strong>{}</strong></p><em><span style="font-size: 10px;">{}</span></em><strong><br></strong><p><br></p>'
HTML_FORMAT = '''<strong>{}-{}</strong>'''

def collect_jsons(path, string=False):
    # only one layer deep
    json_paths = []
    p = Path(path)
    for subpath in p.iterdir():
        if subpath.is_file() and ".json" in subpath.suffix:
            json_paths.append(subpath)
    if string:
        json_paths = [str(p) for p in json_paths]
    return json_paths

def make_graph(collection):
    G = Digraph(format='png')
    root_id = '0'
    G.node(root_id, "xtal")
    edges = set([])

    def add_obj(root_id, objct):
        objct_id = str(hash(objct.name))
        G.node(objct_id, objct.name, color='red')
        edge = root_id, objct_id
        if edge not in edges:
            G.edge(root_id, objct_id)
        edges.add(edge)
        for each_attr in objct.attributes:
            attr_id = str(hash(each_attr.name + objct.name))
            if isinstance(each_attr.data_type, obj):
                if 'items' in each_attr.__dict__:
                    G.node(attr_id, each_attr.name, color='blue')
                    edge = (objct_id, attr_id)
                    if edge not in edges:
                        G.edge(*edge)
                    edges.add(edge)
                    add_obj(attr_id, each_attr.data_type)
                else:
                    add_obj(objct_id, each_attr.data_type)
            else:
                G.node(attr_id, label=each_attr.name, color='blue')
                edge = (objct_id, attr_id)
                if edge not in edges:
                    G.edge(objct_id, attr_id)
                edges.add(edge)
    
    for objct in collection:
        add_obj(root_id, objct)
    
    return G

def splice_objects(collection):
    obj_type_dict = dict(zip([o.json_ref for o in collection], collection))
    print(obj_type_dict)
    spliced_collection = []
    child_objects = set([])
    for objct in collection:
        for i, each_attr in enumerate(objct.attributes):
            if each_attr.data_type in obj_type_dict:
                objct.attributes[i].data_type = obj_type_dict[each_attr.data_type]
                child_objects.add(each_attr.data_type)  # reference to schema
            elif 'items' in each_attr.__dict__:
                if each_attr.items in obj_type_dict:
                    objct.attributes[i].data_type = obj_type_dict[each_attr.items]
                    child_objects.add(each_attr.items)  # reference to schema

    for objct in collection:
        if objct.json_ref not in child_objects:
            spliced_collection.append(objct)
    print(child_objects)
    return spliced_collection


class attribute():

    def __init__(self, name, data_type, description=None, **kwargs):
        self.name = name
        self.data_type = data_type
        self.description = description
        self.__dict__.update(kwargs)

    @classmethod
    def init_from_dict(cls, prop_name, descrip_dict):
        attr_dict = {}
        if 'type' in descrip_dict:
            attr_dict['data_type'] = descrip_dict.pop('type')
        elif '$ref' in descrip_dict:
            attr_dict['data_type'] = descrip_dict['$ref']
        else:
            raise Exception(
                'Attribute {} has no type and does not reference external schema!')

        if 'items' in descrip_dict:
            attr_dict['items'] = descrip_dict.pop('items')
            if isinstance(attr_dict['items'], dict) and "$ref" in attr_dict['items']:
                attr_dict['items'] = attr_dict['items']['$ref']

        attr_dict['name'] = prop_name
        attr_dict.update(descrip_dict)
        return cls(**attr_dict)

    def splice_objs(self):
        # replace reference to a schema with that obj schema
        json_refs = dict(
            zip([each_obj.json_ref for each_obj in ALL_OBJS], ALL_OBJS))
        if self.data_type in json_refs:
            self.data_type = json_refs[self.data_type]

    def __str__(self):
        return self.name


class obj():

    def __init__(self, name, json_ref, attributes=[], required=[]):
        self.name = name
        self.json_ref = json_ref
        self.attributes = attributes
        self.required = required

    @staticmethod
    def make_graph(obj_collection):
        nodes, edgelist = [], []

        # for each_obj in obj_collection:
        #     # iterate through all object
        #     for each_attr in each_obj.attributes:
        #         print(each_obj.name, each_attr.name)

        label_dict = {}

        for each_obj in obj_collection:
            label_dict[hash(each_obj.name)] = each_obj.name
            #nodes.append(each_obj.name)
            for each_attr in each_obj.attributes:
                #nodes.append(str(each_attr))
                edgelist.append(
                    (hash(each_obj.name), hash(each_obj.name + each_attr.name))
                )
                label_dict[hash(each_obj.name + each_attr.name)] = each_attr.name
                if isinstance(each_attr.data_type, obj):
                    edgelist.append(
                        (hash(each_obj.name + each_attr.name), hash(each_attr.data_type.name))
                    )
                    
        return edgelist, label_dict

    @staticmethod
    def json_ref_resolver(object_name):
        # returns what the json ref should be in other files pointing
        # to this json file. Assumes all files are in the same directory
        jp = Path(object_name)
        return '{}.json#/definitions/{}'.format(*[object_name]*2)
    
    @staticmethod
    def splice_objs_into_attributes():
        obj_type_dict = dict(zip([o.json_ref for o in ALL_OBJS], ALL_OBJS))
        for each_obj in ALL_OBJS:
            for each_attr in each_obj.attributes:
                if each_attr.data_type in obj_type_dict:
                    each_attr.data_type = obj_type_dict[each_attr.data_type]

    @classmethod
    def init_from_json(cls, path):
        # assumes only one definition in this json file
        with open(path) as handle:
            data = None
            data = json.load(handle)
            if "definitions" in data:
                definitions = data['definitions']
                for key, val in definitions.items():
                    if isinstance(val, dict):
                        obj_name = key
                        json_ref = obj.json_ref_resolver(obj_name)
                        break
                
                #obj_properties = definitions[new_obj.name]['properties']
                prop_objects = []
                for prop_name, descrip in definitions[obj_name]['properties'].items():
                    prop_objects.append(
                        attribute.init_from_dict(prop_name, descrip)
                    )
                return cls(key, json_ref, prop_objects)
            else:
                raise Exception('No definitions in {}'.format(path))

    def __hash__(self):
        return hash(self.json_ref + self.name)
    
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return self.name
    

def parse_schema(schema_dict):
    if "definitions" in schema_dict:
        nodes, edgelist, descriptions = [], [], []
        definitions = schema_dict['definitions']
        for obj in definitions:
            nodes.append(obj)
            # usually only one object defined here
            if "properties" in obj:
                properties = obj['properties']

                for obj_prop in properties:
                    nodes.append(obj_prop)
                    edgelist.append(
                        (obj, obj_prop)
                    )

            else:
                raise Exception("No properties in {} definition".format(obj))

    else:
        raise Exception('No definitions in schema dict')
