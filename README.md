# notes

- cwd should be src/

- rule output: first atom is head, rest is body

# add data

In ./Data/KG add a folder containing an .nt file with the same name as the folder.

In src/Data/Constraints add a folder containing a .ttl file containing SHACL-constraints both with the same name as used before. If there are SPARQL querys in the constraints please use "$this" when referencing the target node. Also requires writing "SELECT ($this AS ?this)". This is needed for error free validation with TravSHACL.

In ./Data/Constraints add a .ttl file containing the ontology. Here the name doesn't matter.

# input.json:

"KG": name of KG
"prefix": namespace prefix
"rules_file": rule file to write to (will be generated if not exists)
"rdf_file": .nt file in KG folder, must be same name as KG,
"constraints_folder": also same name as KG,
"ontology_file": name of ontology file .ttl,
"max_body_length": leave empty for default of 3,
"example_set_size": num of pos/ neg examples per target predicate, leave empty for default 15
"type_predicate": leave empty for default of 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
"alpha": alpha used in weight formula, leave empty for default 0.5,
"mine_negative_rules": leave empty for False --> will mine positive rules, put anything for True,
"onto-valid": wether the whole graph is validated against the ontology in the beginning:leave empty for False, put anything for True

# example input

use this as input.json for testing

{
"KG": "musicKG",
"prefix": "http://example.org/",
"rules_file": "musicKG.csv",
"rdf_file": "musicKG.nt",
"constraints_folder": "musicKG",
"ontology_file": "musicKGOntology.ttl",
"max_body_length": "",
"example_set_size": "",
"type_predicate": "",
"alpha": "",
"mine_negative_rules": "",
"onto-valid": ""
}
