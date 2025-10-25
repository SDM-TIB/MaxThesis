""" 
represents a path in the graph
"""
class Path:
    def __init__():
        return
""" 
represents a (sub)rule
"""
class Rule:
    def __init__():
        return


"""class that holds all information on predicate mappings for a kg and specific target"""
class P_map:
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

    def __init__(self, target, predicates, neg_predicates, predicate_mappings, neg_predicate_mappings):
        self.target = target
        self.predicates = predicates
        self.neg_predicates = neg_predicates
        self.predicate_mappings = predicate_mappings
        self.neg_predicate_mappings = neg_predicate_mappings

    def __repr__(self) -> str:
        return f"{type(self).__name__}(target={self.target}, predicates={self.predicates}, neg_predicates={self.neg_predicates}, predicate_mappings={self.predicate_mappings}, neg_predicate_mappings={self.neg_predicate_mappings})"

