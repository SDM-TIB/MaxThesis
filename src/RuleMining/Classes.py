from hashlib import sha256
from copy import deepcopy
import numpy as np


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
        if is_literal_comp(new_pred):
            return new_pred
        return new_pred


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
            found1 = False
            found2 = False
            for p in preds:
                for pair in self.graph.edges[p]:
                    if node in pair:
                        if not pair[0] == pair[1]:
                        # found an occurence of node that isn't a self circle
                            if found1:
                                # found 2nd occurence (node is not frontier)
                                found2 = True
                                break
                            # found 1st occurence
                            found1= True
                if found2:
                    # can't be current node
                    break

            if found1 and not found2:
                return node
            
        return None

    """converts a path into a rule, assusemes the body is a straight path starting from head subject with the the exception of possible reflexive predicates/triples"""
    def rule_rudik(self, pmap:P_map):
        def original_triple(triple, pmap:P_map):
            return((triple[0], pmap.original_pred(triple[1]) ,triple[2]))
        
        def generate_var(count):
            return f"?VAR{count}"
          

        name_dict = {}
        name_dict[self.head[0]] = {generate_var(1)}
        if self.head[0] != self.head[2]:
            name_dict[self.head[2]] = {generate_var(2)}
        else: name_dict[self.head[0]].add(generate_var(2))
        count = 3
    
        triple_set = set()

        nodes = set(self.graph.nodes.keys())
        node = self.head[0]

        # collect reflexive triples, to sort in case there are multiple
        ref_triples = []



        while nodes:
            # single triple that leaves from current node
            next_triple = None 
            nodes.discard(node)
            # get connecting triple(s), instantly add reflexive, then the other one and traverse it

            for p in self.graph.nodes[node]:
                for pair in self.graph.edges[p]:
                    if node in pair:
                        if pair[0] == pair[1]:
                            ref_triples.append(original_triple((node, p, node), pmap))
                        elif pair[0] == node and pair[1] in nodes: 
                            next_triple = original_triple((node, p, pair[1]), pmap)
                            next_node = pair[1]
                        elif pair[1] == node and pair[0] in nodes:
                            next_triple = original_triple((pair[0], p, node),pmap)
                            next_node = pair[0]

            if ref_triples:
                ref_triples.sort()
                for t in ref_triples:
                    var_s = generate_var(count)
                    var_o = generate_var(count +1)
                    count += 2
                    name_dict[t[0]].add(var_s)
                    name_dict[t[2]].add(var_o)
                    triple_set.add((var_s, t[1], var_o))
                ref_triples.clear()

            if next_triple:
                var_s = generate_var(count)
                var_o = generate_var(count +1)
                count += 2
                if next_triple[0] in name_dict:
                    name_dict[next_triple[0]].add(var_s)
                else:
                    name_dict[next_triple[0]] = {var_s}

                if next_triple[2] in name_dict:
                    name_dict[next_triple[2]].add(var_o)
                else:
                    name_dict[next_triple[2]] = {var_o}
                triple_set.add((var_s, next_triple[1], var_o))
            else:
                return Rule(original_triple((generate_var(1), self.head[1], generate_var(2)), pmap), triple_set, {tuple(c) for c in name_dict.values() if len(c) > 1})
            node = next_node

        return Rule(original_triple((generate_var(1), self.head[1], generate_var(2)), pmap), triple_set, {tuple(c) for c in name_dict.values() if len(c) > 1})


    def rule(self, pmap:P_map):
        ###################
        #
        # !!ATTENTION!!
        # has a problem with reflexive predicates, requires fix
        #
        #
        ##################

        def original_triple(triple, pmap:P_map):
            return((triple[0], pmap.original_pred(triple[1]) ,triple[2]))

        def traverse(path:Path, pmap:P_map, current_node:str, visited:list=[]):            
            # initialise
            out = []
            connecting_triples = set()
            p_list = []

            
            # build all unvisited triples connected to current entity
            for edge in path.graph.nodes[current_node]:
                p = pmap.original_pred(edge)
                if p not in p_list:
                    p_list.append(p)
                
                for pair in path.graph.edges[edge]:
                    triple = (pair[0], p, pair[1])
                    if current_node in pair and triple not in visited:
                        # TODO need to filter for self circle at current node and if it exists directly add as next triple
                        if pair[0] == pair[1]:
                            out.append(triple)
                        else:
                            connecting_triples.add(triple)


            if not connecting_triples:
                return []
            
            if len(connecting_triples) == 1:
                # add to queue and recurse
                triple = connecting_triples.pop()
                out.append(triple)

                # prepare visited for recursion
                if out:
                    if visited:
                        visited.extend(out)
                    else:
                        visited = out.copy()
                    visited = out.copy()
                out.extend(traverse(path, pmap, (triple[0] if current_node==triple[2] else triple[2]), visited))

            else:
            # len > 1

            # TODO only needed for non rudik path shape
                raise ValueError( "this shouldn't be reached, there must be a branching path")
                p_list.sort()
                while p_list:
                    min_p = p_list.pop(0)
                    possible_next_triples = {t for t in connecting_triples if t[1] == min_p}

                    if len(possible_next_triples) == 1:
                        # chose the triple as next
                        t = possible_next_triples.pop()
                        out.append(t)

                        # recurse, the new node becomes next current node, the triples already in out are given as visited
                        traverse(path, pmap, {t[0] if current_node==t[2] else t[2]}, out)

                    else:
                        #len > 1, need to decide btw the same-predicate triples
                        pass

            return out


            # increments p counter and generates a unique variable 
        
        def generate_var(count):
            return f"?VAR{count}"
            

        def create_rule(head, triple_queue:list):
            name_dict = {}
            hs = generate_var(1)
            ho = generate_var(2)
            if head[0] == head[2]:
                name_dict[head[0]] = {hs, ho}
            else:
                name_dict[head[0]] = {hs}
                name_dict[head[2]] = {ho}

            head = (hs, head[1], ho)
            body = set()
            count = 3
            for (s,p,o) in triple_queue:
                var_s = generate_var(count)
                if s in name_dict:
                    name_dict[s].add(var_s)
                else:
                    name_dict[s] = {var_s}
                count += 1
                var_o = generate_var(count)
                if o in name_dict:
                    name_dict[o].add(var_o)
                else:
                    name_dict[o] = {var_o}
                count += 1
                body.add((var_s, p, var_o))
                
            return Rule(head, body, {tuple(c) for c in name_dict.values() if len(c) > 1})


        # head is a special case, add it first then order the body triples
        triple_queue = traverse(self, pmap, self.head[0])
        return create_rule(original_triple(self.head, pmap), triple_queue)









    """returns a rule object corresponding to the paths' structure."""
    def rule_old(self, pmap:P_map): 

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

    def get_connections(self, var):
        for con in self.connections:
            if var in con:
                return con
        return ()

    
    def as_csv_row(self, negative_rules):
        def triple_csv(triple, negative=False):
            s,p,o = triple
            if negative:
                return f"NOT{p}({s};{o})"
            return f"{p}({s};{o})"
            
        # TODO refactor, also special case if head s=o should be adressed (no mistake, but inconsistency)
        try:
            name_dict = {}
            non_head_var = 3
            for c in self.connections:
                # head vars are always var1 and var 2, after that, need to ensure that no var is skipped for a more intuitive output (e.g. not V1, V2, and V5 as only vars)
                m = min(c)
                if m >= "?VAR3":
                    # node is not in head
                    m = f"?VAR{non_head_var}"
                    non_head_var += 1
                for var in c: 
                    name_dict[var] = m
                    
            # need to account for leaves
            for triple in self.body:
                if triple[0] not in name_dict:
                    name_dict[triple[0]] = f"?VAR{non_head_var}"
                    non_head_var += 1
                if triple[2] not in name_dict:
                    name_dict[triple[2]] = f"?VAR{non_head_var}"
                    non_head_var += 1
            if negative_rules:
                out = [triple_csv((name_dict[self.head[0]], self.head[1], name_dict[self.head[2]]), negative_rules)]
            else:
                out = [triple_csv((name_dict[self.head[0]], self.head[1], name_dict[self.head[2]]))]
            out.extend(list(triple_csv((name_dict[t[0]], t[1], name_dict[t[2]])) for t in self.body))

            return out
        except:
            print(f"rule {self}, name dict {name_dict}")
            raise ValueError
    

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
