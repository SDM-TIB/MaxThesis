from hashlib import sha256

""" represents a path in the graph"""
class Path:
    def __init__(self, head, body):
        self.head = head
        self.body = body
        return
    def __repr__(self):
        return f"Path:\nhead: {self.head},\nbody: {self.body}.\n"

""" represents a (sub)rule"""
class Rule:
    def __init__(self, head=(), body=[], connections=[]):
        self.head = head
        self.body = body
        self.connections = connections
    def __key(self):
        return (self.head, self.body, self.connections)
    def __hash__(self):
        print(sha256(self.__repr__().encode('utf-8')).hexdigest()[:16])
        return int(sha256(self.__repr__().encode('utf-8')).hexdigest(), 16)
    def __eq__(self, other):
        if isinstance(other, Rule):
            return self.__key() == other.__key()
        return
    def __repr__(self):
        return f"Rule:\nhead: {self.head},\nbody: {self.body},\nconnections: {self.connections}.\n"


"""incidence list represemting a graph"""
class IncidenceList:
    def __init__(self, edges:dict=dict(), nodes:dict=dict()):
        self.edges = edges
        self.nodes = nodes

    def __repr__(self):
        return f"Graph:\nedges: {self.edges},\nnodes: {self.nodes}.\n"


    def addNode(self, n, edges=set()):
        if not n in self.nodes:
            self.nodes[n] = edges
        else:
            for e in edges:
                self.nodes[n].add(e) 

    def deleteNode(self, n):
        for l in self.nodes[n]:
            self.delete(l)
        del self.nodes[n]

    def add(self, l, x, y):
        if not l in self.edges:
            self.edges[l] = {(x,y)}
        else:
            if (x,y) in self.edges[l]:
                return
            self.edges[l].add((x,y))
        self.addNode(x, {l})
        self.addNode(y, {l})
            
        
    def delete(self, l):
        del self.edges[l]
        return
    
    def neighbours(self, n):
        return {(l, self.edges[l]) for l in self.nodes[n]}


"""represents information from an ontology.
   namely the class hierarchy and domain and range for properties."""
class Ontology:
    def __init__(self, classes=dict[list](), properties=dict()):
        self.classes = classes
        self.properties = properties

    def __repr__(self):
        return f"Ontology:\nclasses: {self.classes},\nproperties: {self.properties}.\n"

    def addClass(self, prefix, c:str, super:str=""):
            classname = removePrefix(c, prefix)
            if not classname in self.classes:
                if super:
                    self.classes[classname] = {super}
                else:
                    self.classes[classname] = set()
            else:
                print(f"helloooooooooooooooo\n{super}")
                self.classes[classname].add(super) 

    def addProperty(self, prefix, p, d=set(), r=set()):
        self.properties[removePrefix(p, prefix)] = (d, r)
 

"""class that holds all information on predicate mappings for a kg and specific target"""
class P_map:
    def __init__(self, target, predicates, neg_predicates, predicate_mappings, neg_predicate_mappings):
        self.target = target
        self.predicates = predicates
        self.neg_predicates = neg_predicates
        self.predicate_mappings = predicate_mappings
        self.neg_predicate_mappings = neg_predicate_mappings

    def __repr__(self) -> str:
        return f"{type(self).__name__}(target={self.target}, predicates={self.predicates}, neg_predicates={self.neg_predicates}, predicate_mappings={self.predicate_mappings}, neg_predicate_mappings={self.neg_predicate_mappings})"

    def addPrefix(self, prefix):
        self.target = addPrefix(self.target, prefix)
        s = set()
        for p in self.predicates:
            s.add(addPrefix(p, prefix))
        self.predicates = s
        s = set()
        for p in self.neg_predicates:
            s.add(addPrefix(p, prefix))
        self.neg_predicates = s

        for p in self.predicate_mappings:
            pass # TODO
        for p in self.neg_predicate_mappings:
            pass # TODO
    
    def removePrefix(self, prefix):
        self.target = removePrefix(self.target, prefix)
        s = set()
        for p in self.predicates:
            s.add(removePrefix(p, prefix))
        self.predicates = s
        s = set()
        for p in self.neg_predicates:
            s.add(removePrefix(p, prefix))
        self.neg_predicates = s
            
        for p in self.predicate_mappings:
            pass
        for p in self.neg_predicate_mappings:
            pass # TODO

"""add prefix to element"""
def addPrefix(element:str, prefix:str):
    return f"<{prefix}{element}>"
"""remove prefix from element"""
def removePrefix(element:str, prefix:str):
    return element.removeprefix("<").removeprefix(f"{prefix}").removesuffix(">")
