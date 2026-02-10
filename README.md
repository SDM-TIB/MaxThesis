# Inputs:

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
"mine_negative_rules": leave empty for False --> positiv rules, put anything for True
