from hashlib import sha256

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

    def triples(self):
        return {(pair[0], p, pair[1])  for p in self.edges for pair in self.edges[p]}


""" represents a path in the graph"""
class Path:
    def __init__(self, head=(), graph=IncidenceList()):
        self.graph = graph
        self.head = head
        return
    def __repr__(self):
        return f"Path spanning the subgraph: {self.graph}\nhead: {self.head}.\n"
    
    def rule(self): 
        entities = set(self.graph.nodes.keys())
        name_dict = {}
        p_count = 0
        rule = Rule()
        triple_queue = []



        # make working copies
        nodes = self.graph.nodes.copy()
        edges = self.graph.edges.copy()
        head = self.head

        current_entity = self.head[0]
        current_triple = self.head

        while entities:
            entities.remove(current_entity)
            current_triple, current_entity, p_count, head, triple_queue = handle_current_and_get_next(current_triple, current_entity, name_dict, p_count, triple_queue, entities, nodes, edges, head)

            edges["2"] = ("hello", "bye")
            print(self.graph.edges)

            print(triple_queue)
            # queue is done
            if current_triple == ("","",""):
                if not entities:
                    break
                if len(entities) == 1:
                    if entities.pop() == self.head[2]:
                        # head triple must be the one left , head subject always renamed first, thus generate_var(0)
                        s, _ = generate_var(0)
                        print((s, self.head[1], self.head[2]))

                        _,head,_ = rename_triple((s, self.head[1], self.head[2]), self.head[2], edges, head,  name_dict, p_count)
                # there must be an error, because there are entities in the path unconnected to head, only head object is allowed to remain
                else:
                    raise RuntimeError("invalid path, the path contains unconnected triples.")
                    

        connections = {tuple(name_dict[key]) for key in name_dict if len(name_dict[key]) > 1}    


        graph = IncidenceList()
        graph.nodes = nodes
        graph.edges = edges

        print(graph.triples())

        rule.head = head        
        rule.body = graph.triples()
        rule.body.remove(head)
        rule.connections = connections

        print(f"rule {rule}")    
        return  rule
    
def rename_triple(triple, current_entity, edges, head, name_dict, p_count):

    print(f"\nCalled rename triple with triple = {triple}, current_entity = {current_entity}, \n edges = {edges}\n head = {head} \n namedict = {name_dict} \n pcount = {p_count}\n")

    s,p,o = triple
    
    is_head = False
    if (s,p,o) == head:
        is_head = True
    # renaming of triple in working copy ( + entry in name dict)
    edges[p].remove((s, o))


    # it is known that at least one of s and o matches current entity

    # special case if subject and object are the same
    if s == o:
        s, p_count = generate_var(p_count)
        o, p_count = generate_var(p_count)
        edges[triple[1]].add((s, o))
        add_to_set_dict(name_dict, current_entity, s)
        add_to_set_dict(name_dict, current_entity, o)
        if is_head:
            head = (s, head[1], o)
 
    # current entity is subject
    elif triple.index(current_entity) == 0:
        s , p_count= generate_var(p_count)
        edges[triple[1]].add((s, o))
        add_to_set_dict(name_dict, current_entity, s)
        if is_head:
            head = (s, head[1], head[2])
    # current entity is object
    else:
        o, p_count = generate_var(p_count)
        edges[triple[1]].add((s, o))
        add_to_set_dict(name_dict, current_entity, o)
        if is_head:
            head = (head[0], head[1], o)
            
    return p_count, head, (s, p, o)



def handle_current_and_get_next(current_triple, current_entity, name_dict, p_count, triple_queue, entities, nodes, edges, head, top_lvl_call=True):

    print(f"\nCalled handle current and get next with: current_triple = {current_triple}, current_entity = {current_entity},\n name_dict = {name_dict},\n p_count = {p_count},\n triple_queue = {triple_queue},\n entities = { entities},\n nodes = {nodes},\n edges = {edges},\n head = {head},\n top_lvl_call = {top_lvl_call} ")

    if top_lvl_call:
        # rename current entity in current triple
        p_count, head, _ = rename_triple(current_triple, current_entity, edges, head, name_dict, p_count)
        
    # get the predicates involving current entity
    connecting_predicates = nodes[current_entity].copy()

    while connecting_predicates:
        # start with smallest predicate (uniqueness is guaranteed here)
        p = min(connecting_predicates)
        connecting_predicates.remove(p)

        if top_lvl_call:
            # get the entities connected to current entity via the predicate, current triple is disregarded, b/c alraedy renamed
            connections = {t for t in edges[p] if current_entity in t }

            # in recursing comparison runs, theres no previous renaming of current predicate, exclude manually
        else:
            connections = {t for t in edges[p] if current_entity in t if t[0] != current_triple[0] or t[1] != current_triple[2]}


        l = len(connections)
        # one connection
        if l == 1:
            # add the one connection to the queue
            entity_pair = connections.pop()
            if top_lvl_call:
                p_count, head, triple = rename_triple((entity_pair[0], p, entity_pair[1]), current_entity, edges, head, name_dict, p_count)
                triple_queue.append(triple)
            else:
                triple_queue.append((entity_pair[0], p, entity_pair[1]))

        # multiple connections, need to be sorted
        if l >= 2:
            # TODO compare multiple connections
            pairs = []
            for tuple in connections:
                if tuple[0] == current_entity:
                    c = tuple[1]
                else: 
                    c = tuple[0]
                
                t_next = handle_current_and_get_next((tuple[0], p, tuple[1]), c, name_dict, p_count, [], entities, nodes, edges, head, False) 
                pairs.append((tuple, t_next))
            
            

            if top_lvl_call:
                # found the order of same predicate instances, rename and add to queue
                while pairs:
                    pair = min(pairs, key=lambda element: element[1][1])
                    p_count, head, triple = rename_triple((pair[0][0], p, pair[0][1]), current_entity, edges, head, name_dict, p_count)
                    pairs.remove(pair)
                    triple_queue.append(triple)

            # get the triple with lowest following path
            else:
                pair = min(pairs, key=lambda element: element[1][1])
                triple_queue.append((pair[0][0], p, pair[0][1]))


    # get next triple, if there are no unhandled entities, get the next one
    while True:
        # if queue is empty return recognizable output
        if not triple_queue:
            next_triple = ("","","")
            break
        else:
            next_triple = triple_queue.pop(0)
        if next_triple[0] in entities or next_triple[2] in entities:
            break

    return next_triple, next_triple[0] if next_triple[0] in entities else next_triple[2], p_count, head, triple_queue


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

def add_to_count_dict(d, key):
    if key in d:
        d[key]+= 1
    else:
        d[key] = 0

""" represents a (sub)rule"""
class Rule:
    def __init__(self, head=(), body=set(), connections=set()):
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






###############################
# util
###############################


"""add prefix to element"""
def addPrefix(element:str, prefix:str):
    return f"<{prefix}{element}>"
"""remove prefix from element"""
def removePrefix(element:str, prefix:str):
    return element.removeprefix("<").removeprefix(f"{prefix}").removesuffix(">")

