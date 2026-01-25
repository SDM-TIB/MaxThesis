from hashlib import sha256
from copy import deepcopy


###############################################
# Classes
###############################################

"""incidence list represemting a graph"""
class IncidenceList:
    def __init__(self, edges=None, nodes=None):
        if edges == None:
            edges = {}
        if nodes == None:
            nodes = {}
        self.edges = edges
        self.nodes = nodes

    def __repr__(self):
        return f"Graph:\nedges: {self.edges},\nnodes: {self.nodes}.\n"

    def copy(self):
        return IncidenceList(deepcopy(self.edges), deepcopy(self.nodes))


    def addNode(self, n, edges=None):
        if edges == None:
            edges = set()
        if not n in self.nodes:
            self.nodes[n] = edges
        else:
            self.nodes[n].update(edges) 

    def deleteNode(self, n):
        for l in self.nodes[n]:
            self.delete(l)
        del self.nodes[n]

    def add(self, x, l, y):
        self.addNode(x, {l})
        self.addNode(y, {l})
        if not l in self.edges:
            self.edges[l] = {(x,y)}
        else:
            if not (x,y) in self.edges[l]:
                self.edges[l].add((x,y))
        
    def delete(self, l):
        del self.edges[l]
        return
    
    def triples(self):
        return {(pair[0], p, pair[1])  for p in self.edges for pair in self.edges[p]}
    
    def neighbors(self, n):
        neighbors = set()
        edges = self.nodes.get(n)
        if edges:
            for edge in edges:
                for pair in self.edges[edge]:
                    if n in pair:
                        if n in pair[0]:
                            neighbors.add(pair[1])
                        else:
                            neighbors.add(pair[0])
        return neighbors
    



"""class that holds all information on predicate mappings for a kg and specific target"""
class P_map:
    def __init__(self, target, predicates, neg_predicates, predicate_mappings, neg_predicate_mappings):
        self.target = target
        self.predicates = predicates
        self.neg_predicates = neg_predicates
        self.predicate_mappings = predicate_mappings
        self.neg_predicate_mappings = neg_predicate_mappings

    def __repr__(self) -> str:
        return f"{type(self).__name__}(target={self.target},\n\npredicates={self.predicates},\n\nneg_predicates={self.neg_predicates},\n\npredicate_mappings={self.predicate_mappings},\n\nneg_predicate_mappings={self.neg_predicate_mappings})"

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

        d = {}
        for p in self.predicate_mappings:
            p1 = addPrefix(p, prefix)
            d[p1] = set()
            for np in self.predicate_mappings[p]:
                d[p1].add(addPrefix(np, prefix))
        self.predicate_mappings = d

        d = {}
        for p in self.neg_predicate_mappings:
            p1 = addPrefix(p, prefix)
            d[p1] = set()
            for np in self.neg_predicate_mappings[p]:
                d[p1].add(addPrefix(np, prefix))
        self.neg_predicate_mappings = d

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
            
        d = {}
        for p in self.predicate_mappings:
            p1 = removePrefix(p, prefix)
            d[p1] = set()
            for np in self.predicate_mappings[p]:
                d[p1].add(removePrefix(np, prefix))
        self.predicate_mappings = d

        d = {}
        for p in self.neg_predicate_mappings:
            p1 = removePrefix(p, prefix)
            d[p1] = set()
            for np in self.neg_predicate_mappings[p]:
                d[p1].add(removePrefix(np, prefix))
        self.neg_predicate_mappings = d

    """
    get a predicates predecessor, for a negative_pred get post-normalization positive predicate, for that, get original predicate
    """
    def original_pred(self, new_pred:str):
        if new_pred in self.predicate_mappings:
            return self.predicate_mappings[new_pred]
        if new_pred in self.neg_predicate_mappings:
            return self.predicate_mappings[self.neg_predicate_mappings[new_pred]]
        return ""


    """
    get post normalization predicates from their pre-normalization predecessor
    """
    def new_preds(self, original_pred:str):
        return {k for k, v in self.predicate_mappings.items() if v == original_pred}




    """
    get existing negative variants of post-normalization predicates
    """
    def neg_preds(self, new_preds:set):
        return {k for k, v in self.neg_predicate_mappings.items() if v in new_preds}




    


""" represents a path in the graph"""
class Path:
    def __init__(self, head=(), graph=None):
        if graph == None:
            graph = IncidenceList()
        self.graph = graph
        self.head = head
        return
    def __repr__(self):
        return f"Path with:\n head: {self.head}\n{self.graph}\n"
        
    

    def copy(self):
        return Path(self.head, self.graph.copy())


    
 # calculates a paths frontier in line with rudik
    def frontiers_rudik_old(self):
        
        h1 = self.head[0]
        if h1 not in self.graph.nodes.keys():
            # head subject is leaf
            return h1

        for node, preds in self.graph.nodes.items():
            # if node has more than one predicate, it can't be a leaf
            if node == h1 or len(preds) > 1:
                continue

            # node has only one predicate, count instances of it
            count = 0
            for pair in self.graph.edges[next(p for p in preds)]:
                if node in pair:
                    if count:
                        count += 1
                        break
                    count = 1
            if count == 1:
                return node
        return None

    def frontiers_rudik(self):
        
        h1 = self.head[0]
        if not self.graph.nodes or (len(self.graph.nodes) == 1 and h1 in self.graph.nodes):
            # head subject is leaf
            return h1
        


        for node, preds in self.graph.nodes.items():
            # count occurences of node, 2 is too many, disregard s=o triples
            if node == h1:
                continue
            found = False
            for p in preds:
                for pair in self.graph.edges[p]:
                    if node in pair:
                        if not pair[0] == pair[1]:
                            if found:
                                # found 2nd occurence (node is not frontier)
                                break
                            # found 1st occurence
                            found = True

            if found:
                return node
            
        return None




    def rule_new(self, pmap:P_map):

        def original_triple(triple, pmap:P_map):
            if is_literal_comp(triple[1]):
                return triple
            return((triple[0], pmap.predicate_mappings[triple[1]] ,triple[2]))

        def traverse_dfs(self, pmap, current_node):            
            pass
            # 1. find next p and o, switch to original predicate
            

            # 2. add (current_node, p, o) to result


            # 3. a if single best triple, recurse and queue solution
            # 3. b if multiple options recurse all and only add "best" one



            

        def create_rule(triple_queue:list):
            pass

        # head is a special case, add it first then order the body triples
        triple_queue = [original_triple(self.head, pmap)].extend(traverse_dfs(pmap, self.head[0]))

        return create_rule(triple_queue)









    """returns a rule object corresponding to the paths' structure."""
    def rule(self, pmap:P_map): 

        name_dict = {}
        p_count = 0
        rule = Rule()

        head = self.head

        triple_order = dfs(self.graph.nodes, self.graph.edges, head[0], head)     

        # TODO maybe remove, since we also assume connectedness elsewhere
        if len(triple_order) < sum(len(self.graph.edges[p]) for p in self.graph.edges):
            raise ValueError("The given path is faulty, all triples must be reachable from head subject.")
        
        p_count = 0
        for t in triple_order:
            p_count, head = rename_triple(t, head, name_dict, p_count, rule, pmap)

        rule.connections = {tuple(name_dict[key]) for key in name_dict if len(name_dict[key]) > 1}    

        return  rule
    



"""performs a strictly ordered dfs over an Incidence list, starting at  start entity, returns the traversal order of triples"""
def dfs(nodes, edges, start, triple, visited=None):


    def find_min_key(subpaths, visited):
        # true if path one is more favourable than two
        def subpath_better_than(p1, p2):

            for a, b in zip(p1, p2):
                if a[1] < b[1]:
                    return True
                if a[1] > b[1]:
                    return False

            # same entries but one list might be longer, favour longer list
            if len(p1) < len(p2):
                return False
            else: 
                return True

        
        min_key = None

        for key in subpaths:
            clean_subpath(subpaths, key, visited)
            if min_key is None:
                min_key = key
            else:
                if subpath_better_than(subpaths[key], subpaths[min_key]):
                    min_key = key
        return min_key
        
    # removes a tail from the subpath that is already visited
    def clean_subpath(subpaths, key, visited):
        del_set = set()
        for t in subpaths[key]:
            if t in visited:
                del_set.add(t)
        if del_set:
            for k in del_set:
                subpaths[key].remove(k)


    # TODO there is a mistake here, need to compare original predicates, not the new ones
    if visited == None:
        visited = set()
    order = [triple]

    visited.add(triple)
    connected_predicates = nodes[start].copy()

    while connected_predicates:
        p = min(connected_predicates)
        connected_predicates.remove(p)
        connected_triples = {(e[0], p, e[1]) for e in edges[p] if start in e and (e[0], p, e[1]) not in visited}
        if len(connected_triples) == 1:
            t = connected_triples.pop()
            t_start = t[0] if t[0] != start else t[2]
            subpath = dfs(nodes, edges, t_start, t, visited.copy())
            order.extend(subpath)
            for t in subpath:
                visited.add(t)        
        elif len(connected_triples) > 1:

            # until now look ahead of one: paths seem the same; traverse each path completely, then order
            subpaths = {}
            for t in connected_triples:
                t_start = t[0] if t[0] != start else t[2]
                subpaths[t] = dfs(nodes, edges, t_start, t, visited.copy())

            
            while subpaths:
                min_next = find_min_key(subpaths, visited)
                order.extend(subpaths[min_next])
                for t in subpaths[min_next]:
                    visited.add(t)
                del subpaths[min_next]
            return order

    return order




""" represents a (sub)rule"""
class Rule:
    def __init__(self, head=(), body=None, connections=None):
        if body == None:
            body = set()
        if connections == None:
            connections = set()
        self.head = head
        self.body = body
        self.connections = connections


    def __key(self):
        return (self.head, self.body, self.connections)
    
    def __hash__(self):
        return int(sha256(str(self.__key()).encode('utf-8')).hexdigest(), 16)
    
    def __eq__(self, other):
        if isinstance(other, Rule):
            return self.__key() == other.__key()
        return
    
    def __repr__(self):
        return f"Rule:\nhead: {self.head},\nbody: {self.body},\nconnections: {self.connections}.\n"
    
    def copy(self):
        r = Rule()
        r.head = self.head
        r.body = self.body.copy()
        r.connections = self.connections.copy()
        return r

    
    def as_csv_row(self):
        def triple_csv(triple):
            s,p,o = triple
            return f"{p}({s};{o})"
        
        out = [triple_csv(self.head)]
        out.extend(list(triple_csv(t) for t in self.body))
        for knot in self.connections:
            out.append("=".join(knot))
        return out
    

"""help function for Path.rule()
renames triple subject and object with unique variables and adds them to name dict."""
def rename_triple(triple, head, name_dict, p_count, rule:Rule, pmap:P_map):

    # increments p counter and generates a unique variable 
    def generate_var(p_count):
        p_count += 1
        return f"?VAR{p_count}", p_count

    # safely add single value to a dict with sets of values
    def add_to_set_dict(d, key:str, value):
        if key in d:
            d[key].add(value)
        else:
            d[key] = {value}

    s,p,o = triple
    
    is_head = False
    if (s,p,o) == head:
        is_head = True

    s_var, p_count = generate_var(p_count)
    o_var, p_count = generate_var(p_count)
    add_to_set_dict(name_dict, s, s_var)
    add_to_set_dict(name_dict, o, o_var)
    
    if is_head:
        head = (s_var, pmap.original_pred(head[1]), o_var)
        rule.head = head
    else:
        if is_literal_comp(p):
            rule.body.add((s_var,p,o_var))

        else:
            rule.body.add((s_var,pmap.original_pred(p),o_var))
    return p_count, head


"""represents information from an ontology.
   namely the class hierarchy and domain and range for properties."""
class Ontology:
    def __init__(self, classes=None, properties=None):
        if classes == None:
            classes = dict()
        if properties == None:
            properties = dict()

        self.classes = classes
        self.properties = properties

        # hierarchy from https://www.w3.org/TR/xmlschema11-2/type-hierarchy-201104.longdesc.html
        self.literal_hierarchy =  {
            "anyType": {"anySimpleType"},
            "anySimpleType": {"anyAtomicType", "ENTITIES", "IDREFS", "NMTOKENS"},
            "anyAtomicType": {
                "anyURI", "base64Binary", "boolean", "date", "dateTime", "decimal",
                "double", "duration", "float", "gDay", "gMonth", "gMonthDay",
                "gYear", "gYearMonth", "hexBinary", "NOTATION", "QName", "string",
                "time"
            },
            "dateTime": {"dateTimeStamp"},
            "decimal": {"integer"},
            "integer": {"long", "nonNegativeInteger", "nonPositiveInteger"},
            "long": {"int"},
            "int": {"short"},
            "short": {"byte"},
            "nonNegativeInteger": {"positiveInteger", "unsignedLong"},
            "unsignedLong": {"unsignedInt"},
            "unsignedInt": {"unsignedShort"},
            "unsignedShort": {"unsignedByte"},
            "nonPositiveInteger": {"negativeInteger"},
            "duration": {"dayTimeDuration", "yearMonthDuration"},
            "string": {"normalizedString"},
            "normalizedString": {"token"},
            "token": {"language", "Name", "NMTOKEN"},
            "Name": {"NCName"},
            "NCName": {"ENTITY", "ID", "IDREF"}
        }

    def __repr__(self):
        return f"Ontology:\nclasses: {self.classes},\nProperties: {self.properties}.\n"

    def addClass(self, prefix, c:str, super:str=""):
            classname = removePrefix(c, prefix)
            if not classname in self.classes:
                if super:
                    self.classes[classname] = {super}
                else:
                    self.classes[classname] = set()
            else:
                if super:
                    self.classes[classname].add(super) 

    def addProperty(self, prefix, p, d=None, r=None):
        if d == None:
            d = set()
        if r == None:
            r = set()

        name = removePrefix(p, prefix)
        if not name in self.properties:
            self.properties[name] = (d, r)
        else:
            self.properties[name][0].update(d)
            self.properties[name][1].update(r)
            




################################################
# util
################################################


"""add prefix to element"""
def addPrefix(element:str, prefix:str):
    if element.__contains__("/"):
        return element
    return f"{prefix}{element}"
"""remove prefix from element"""
def removePrefix(element:str, prefix:str):
    return element.removeprefix("<").removeprefix(f"{prefix}").removesuffix(">")

"""checks if predicate is a literral comparison"""
def is_literal_comp(p):
    if p == "=" or p=="<":
        return True
    return False
