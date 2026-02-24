import csv
import re
from rdflib import Graph


def load_knowledge_graph(nt_file):
    """Load the knowledge graph from .nt file"""
    print(f"Loading knowledge graph from {nt_file}...")
    g = Graph()
    g.parse(nt_file, format='nt')
    print(f"Loaded {len(g)} triples")
    return g


def parse_rule(body, head):
    """
    Parse body and head into structured format
    Returns: (body_patterns, head_pattern, head_vars)
    """

    def parse_triple(triple_str):
        """Parse 's  p  o' format into (subject, predicate, object)"""
        temp = triple_str.split("(")
        p = temp[0]
        vars = temp[1].removesuffix(")")
        s = vars.split(",")[0]
        o = vars.split(",")[1]

        return s,p,o

    # Parse body (multiple patterns separated by '   ')
    body_patterns = []
    if body:
        body_triples = body.split(';')
        for triple_str in body_triples:
            pattern = parse_triple(triple_str)
            if pattern:
                body_patterns.append(pattern)

    # Parse head (single pattern)
    head_pattern = parse_triple(head)

    # Extract variables from head
    head_vars = []
    if head_pattern:
        for item in head_pattern:
            if item.startswith('?'):
                head_vars.append(item)

    return body_patterns, head_pattern, head_vars


def build_sparql_patterns(patterns, namespace_prefix='ex', namespace_uri='http://example.org/'):
    """Convert parsed patterns to SPARQL triple patterns"""
    sparql_lines = []
    for subj, pred, obj in patterns:
        # Add namespace to predicate
        pred_uri = f"{namespace_prefix}:{pred}"

        # Handle subject
        if subj.startswith('?'):
            subj_sparql = subj
        else:
            subj_sparql = f"{namespace_prefix}:{subj}"

        # Handle object
        if obj.startswith('?'):
            obj_sparql = obj
        else:
            obj_sparql = f"{namespace_prefix}:{obj}"

        sparql_lines.append(f"            {subj_sparql} {pred_uri} {obj_sparql} .")

    return '\n'.join(sparql_lines)


def calculate_std_confidence(g, body, head, namespace_prefix='ex', namespace_uri='http://example.org/'):
    """
    Calculate Standard Confidence using the template:
    SELECT (xsd:float(?PEHead)/xsd:float(?PFHead) AS ?Confidence) WHERE {
        {SELECT (COUNT(DISTINCT *) AS ?PEHead) WHERE {
            SELECT VarsInHead WHERE {
                BodyTriplePatterns.
                HeadTriplePattern
            }
        }}
        {SELECT (COUNT(DISTINCT *) AS ?PFHead) WHERE {
            HeadTriplePattern
        }}
    }
    """
    body_patterns, head_pattern, head_vars = parse_rule(body, head)
    if not head_pattern or not body_patterns:
        return None

    # Build SPARQL patterns
    body_sparql = build_sparql_patterns(body_patterns, namespace_prefix, namespace_uri)
    head_sparql = build_sparql_patterns([head_pattern], namespace_prefix, namespace_uri)
    vars_str = ' '.join(head_vars) if head_vars else '*'

    try:
        # Step 1: Calculate PEHead (support) - count where both body and head are true
        query_pe_head = f"""
PREFIX {namespace_prefix}: <{namespace_uri}>
SELECT (COUNT(*) AS ?PEHead) WHERE {{
    SELECT DISTINCT {vars_str} WHERE {{
{body_sparql}
{head_sparql}
    }}
}}
"""
        result_pe = list(g.query(query_pe_head))
        pe_head = int(result_pe[0][0]) if result_pe and result_pe[0][0] else 0

        # Step 2: Calculate PFHead (head coverage) - count where head is true
        query_pf_head = f"""
PREFIX {namespace_prefix}: <{namespace_uri}>
SELECT (COUNT(*) AS ?PFHead) WHERE {{
    SELECT DISTINCT {vars_str} WHERE {{
{head_sparql}
    }}
}}
"""
        result_pf = list(g.query(query_pf_head))
        pf_head = int(result_pf[0][0]) if result_pf and result_pf[0][0] else 0

        # Calculate confidence
        if pf_head > 0:
            confidence = pe_head / pf_head
            return confidence, pe_head, pf_head
        else:
            return 0.0, pe_head, pf_head

    except Exception as e:
        print(f"  Error calculating std confidence: {e}")
        return None


def calculate_pca_confidence(g, body, head, namespace_prefix='ex', namespace_uri='http://example.org/'):
    """
    Calculate PCA Confidence using the template:
    SELECT (xsd:float(?Support)/xsd:float(?PCABodySize) AS ?PCA) WHERE {
        {SELECT (COUNT(DISTINCT *) AS ?Support) WHERE {
            SELECT VarsInHead WHERE {
                BodyTriplePatterns.
                HeadTriplePattern
            }
        }}
        {SELECT (COUNT(DISTINCT *) AS ?PCABodySize) WHERE {
            SELECT VarsInHead WHERE {
                BodyTriplePatterns.
                PCAHeadTriplePattern
            }
        }}
    }
    """
    body_patterns, head_pattern, head_vars = parse_rule(body, head)

    if not head_pattern or not body_patterns:
        return None

    # Build SPARQL patterns
    body_sparql = build_sparql_patterns(body_patterns, namespace_prefix, namespace_uri)
    head_sparql = build_sparql_patterns([head_pattern], namespace_prefix, namespace_uri)
    vars_str = ' '.join(head_vars) if head_vars else '*'

    # Create PCA head pattern with placeholder variables
    pca_head_subj, pca_head_pred, pca_head_obj = head_pattern

    # Replace non-variables with placeholder variables
    if not pca_head_subj.startswith('?'):
        pca_head_subj = '?pcaVar1'
    pca_head_obj = '?pcaVar2'

    pca_head_pattern = (pca_head_subj, pca_head_pred, pca_head_obj)
    pca_head_sparql = build_sparql_patterns([pca_head_pattern], namespace_prefix, namespace_uri)

    try:
        # Step 1: Calculate Support - count where both body and head are true
        query_support = f"""
PREFIX {namespace_prefix}: <{namespace_uri}>
SELECT (COUNT(*) AS ?Support) WHERE {{
    SELECT DISTINCT {vars_str} WHERE {{
{body_sparql}
{head_sparql}
    }}
}}
"""
        result_support = list(g.query(query_support))
        support = int(result_support[0][0]) if result_support and result_support[0][0] else 0
        print(f"support: {support}")
        # Step 2: Calculate PCA Body Size - count with placeholder head
        query_pca_body = f"""
PREFIX {namespace_prefix}: <{namespace_uri}>
SELECT (COUNT(*) AS ?PCABodySize) WHERE {{
    SELECT DISTINCT {vars_str} WHERE {{
{body_sparql}
{pca_head_sparql}
    }}
}}
"""
        result_pca = list(g.query(query_pca_body))
        pca_body_size = int(result_pca[0][0]) if result_pca and result_pca[0][0] else 0

        # Calculate PCA confidence
        if pca_body_size > 0:
            pca_confidence = support / pca_body_size
            return pca_confidence, support, pca_body_size
        else:
            return 0.0, support, pca_body_size

    except Exception as e:
        print(f"  Error calculating PCA confidence: {e}")
        return None


def add_confidence_scores(csv_file, nt_file, output_file, namespace_prefix='ex', namespace_uri='http://example.org/'):
    """
    Load rules from CSV, calculate confidence scores, and save updated CSV

    Args:
        csv_file: Path to input CSV file with rules
        nt_file: Path to knowledge graph .nt file
        output_file: Path to output CSV file
        namespace_prefix: Prefix for namespace (e.g., 'ex')
        namespace_uri: Full namespace URI (e.g., 'http://FrenchRoyalty.org/')
    """
    # Load knowledge graph
    g = load_knowledge_graph(nt_file)

    print(f"Using namespace: {namespace_prefix} -> <{namespace_uri}>")

    # Read rules from CSV
    rules = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter="\t")
        rules = list(reader)

    print(f"\nProcessing {len(rules)} rules...")

    # Calculate scores for each rule
    for i, rule in enumerate(rules, 1):
        print(rule)
        body = rule['Body']
        head = rule['Head']

        if i <= 3 or i % 20 == 0:  # Print progress for first 3 and every 20th rule
            print(f"\nRule {i}/{len(rules)}:")
            print(f"  Body: {body[:80]}{'...' if len(body) > 80 else ''}")
            print(f"  Head: {head[:80]}{'...' if len(head) > 80 else ''}")

        # Calculate Std Confidence
        std_result = calculate_std_confidence(g, body, head, namespace_prefix, namespace_uri)
        if std_result:
            std_conf, pe_head, pf_head = std_result
            rule['Std Confidence'] = std_conf
            rule['Positive Examples'] = pe_head
            rule['Head Coverage'] = pf_head
            if i <= 3 or i % 20 == 0:
                print(f"  Std Confidence: {std_conf:.6f} (Support: {pe_head}, Head Coverage: {pf_head})")
        else:
            rule['Std Confidence'] = ''
            rule['Positive Examples'] = ''
            rule['Head Coverage'] = ''
            if i <= 3 or i % 20 == 0:
                print(f"  Std Confidence: Could not calculate")

        # Calculate PCA Confidence
        pca_result = calculate_pca_confidence(g, body, head, namespace_prefix, namespace_uri)
        if pca_result:
            pca_conf, support, pca_body_size = pca_result
            rule['PCA Confidence'] = pca_conf
            rule['Body size'] = len(body.split(';')) if body else 0
            rule['PCA Body size'] = pca_body_size
            if i <= 3 or i % 20 == 0:
                print(f"  PCA Confidence: {pca_conf:.6f} (Support: {support}, PCA Body Size: {pca_body_size})")
        else:
            rule['PCA Confidence'] = ''
            rule['Body size'] = len(body.split(';')) if body else 0
            rule['PCA Body size'] = ''
            if i <= 3 or i % 20 == 0:
                print(f"  PCA Confidence: Could not calculate")

    # Write updated CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['Body', 'Head', 'Head Coverage', 'Std Confidence',
                      'PCA Confidence', 'Positive Examples', 'Body size',
                      'PCA Body size', 'Functional variable']
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rules)

    print(f"\n\nUpdated CSV saved to {output_file}")
    print(f"Successfully processed {len(rules)} rules")


# Example usage
if __name__ == "__main__":
    import sys

    # Check if command line arguments are provided
    if len(sys.argv) >= 5:
        csv_file = sys.argv[1]
        nt_file = sys.argv[2]
        output_file = sys.argv[3]
        namespace_uri = sys.argv[4]
        namespace_prefix = sys.argv[5] if len(sys.argv) > 5 else 'ex'
    else:
        # Interactive input
        print("=== Rule Confidence Calculator ===\n")
        csv_file = input(
            "Enter CSV file path (default: anyburl_converted_to_amie.csv): ").strip() or 'anyburl_converted_to_amie.csv'
        nt_file = input("Enter .nt file path (default: french_royalty.nt): ").strip() or 'french_royalty.nt'
        output_file = input(
            "Enter output file path (default: rules_with_confidence.csv): ").strip() or 'rules_with_confidence.csv'
        namespace_uri = input(
            "Enter namespace URI (e.g., http://FrenchRoyalty.org/): ").strip() or 'http://FrenchRoyalty.org/'
        namespace_prefix = input("Enter namespace prefix (default: ex): ").strip() or 'ex'



        # set input here
        csv_file = "./Data/Rules/musicKG.tsv"
        nt_file = "./Data/KG/musicKG/musicKG.nt"
        output_file = "./Data/Rules/musicKG_PCA.tsv"
        namespace_uri = "http://example.org/"
        namespace_prefix = "ex"

    # Ensure namespace URI ends with / or #
    if not namespace_uri.endswith('/') and not namespace_uri.endswith('#'):
        namespace_uri += '/'

    print(f"\n{'=' * 60}")
    print(f"Configuration:")
    print(f"  Input CSV: {csv_file}")
    print(f"  Knowledge Graph: {nt_file}")
    print(f"  Output CSV: {output_file}")
    print(f"  Namespace: {namespace_prefix} -> <{namespace_uri}>")
    print(f"{'=' * 60}\n")

    add_confidence_scores(csv_file, nt_file, output_file, namespace_prefix, namespace_uri)