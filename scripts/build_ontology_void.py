#!/usr/bin/env python3
"""Generate data/ontology-void.ttl from the ontology Turtle files in data/.

The VoID description of the imported ontologies used to be maintained by hand. It
drifted badly: it still pointed at Jenkins jobs that no longer exist, claimed
Pathway Ontology 7.52 while the endpoint served 7.56, and never mentioned the
ChEBI slim at all. This script derives the description from the files that are
actually loaded, so it cannot drift again.

The output is a pure function of the input files -- no wall-clock timestamps --
so re-running it without an ontology change produces a byte-identical file and
the workflow's "commit only if something changed" guard keeps working. When an
import happened is recorded precisely by this file's git history.

Usage:
    python3 scripts/build_ontology_void.py [--data-dir data] [--check]

    --check  exit 1 if the generated content differs from the file on disk
             (does not write); intended for CI.
"""

import argparse
import re
import sys
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS

OBO = "http://purl.obolibrary.org/obo/"
DC11 = Namespace("http://purl.org/dc/elements/1.1/")
OBOINOWL = Namespace("http://www.geneontology.org/formats/oboInOwl#")

RAW_BASE = "https://raw.githubusercontent.com/marvinm2/WikiPathwaysLoader/master/data"
WORKFLOW = ("https://github.com/marvinm2/WikiPathwaysLoader/blob/master/"
            ".github/workflows/build-imports.yml")
ROBOT = "https://github.com/ontodev/robot/releases/tag/v1.9.0"
SLIMMER = "https://github.com/enanomapper/slimmer/releases/tag/v1.0.1"

# Per-file facts that are not discoverable from the ontology header: where the
# workflow fetches it and what it uses to convert it. Keep in step with
# .github/workflows/build-imports.yml.
ONTOLOGIES = [
    {
        "file": "PathwayOntology.ttl",
        "title": "Pathway Ontology",
        "imported_from": "http://purl.obolibrary.org/obo/pw.owl",
        "created_with": [ROBOT],
        "landing_page": "https://obofoundry.org/ontology/pw.html",
        "uri_space": OBO + "PW_",
        # The PW header carries no description of its own.
        "description": ("The Pathway Ontology, a controlled vocabulary of "
                        "pathway types, converted to RDF from the OWL release "
                        "published at the OBO PURL."),
    },
    {
        "file": "DiseaseOntology.ttl",
        "title": "Human Disease Ontology",
        "imported_from": "http://purl.obolibrary.org/obo/doid.owl",
        "created_with": [ROBOT],
        "landing_page": "https://obofoundry.org/ontology/doid.html",
        "uri_space": OBO + "DOID_",
    },
    {
        "file": "CellOntology.ttl",
        "title": "Cell Ontology",
        "imported_from": "http://purl.obolibrary.org/obo/cl.owl",
        "created_with": [ROBOT],
        "landing_page": "https://obofoundry.org/ontology/cl.html",
        "uri_space": OBO + "CL_",
        "note": ("The release merges its imports, so the class count covers the "
                 "GO, UBERON, PATO and PR terms CL reuses as well as CL's own."),
    },
    {
        "file": "chebi-slim.ttl",
        "title": "ChEBI Ontology (WikiPathways slim)",
        "imported_from": "http://ftp.ebi.ac.uk/pub/databases/chebi/ontology/chebi_lite.obo",
        "created_with": [SLIMMER, ROBOT],
        "landing_page": "https://www.ebi.ac.uk/chebi/",
        "uri_space": OBO + "CHEBI_",
        "note": ("Slimmed with the eNanoMapper Slimmer to the ChEBI terms that "
                 "WikiPathways actually annotates with, queried live from the "
                 "endpoint (wp:bdbChEBI), rather than the full ChEBI release."),
    },
]

TITLE_PREDS = [DCTERMS.title, DC11.title, URIRef(OBO + "terms_title")]
DESC_PREDS = [DCTERMS.description, DC11.description, URIRef(OBO + "terms_description")]
LICENSE_PREDS = [DCTERMS.license, URIRef(OBO + "terms_license")]
CREATOR_PREDS = [DCTERMS.creator, DC11.creator, URIRef(OBO + "dc_creator")]
VERSION_PREDS = [OWL.versionInfo, URIRef(OBO + "owl_versionInfo")]

VERSION_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}|\d+(\.\d+)*)$")
VERSION_IRI_DATE_RE = re.compile(r"/releases/(\d{4}-\d{2}-\d{2})/")
OBO_DATE_RE = re.compile(r"^(\d{2}):(\d{2}):(\d{4})\b")
TERM_RE = re.compile(r"^" + re.escape(OBO) + r"([A-Za-z]+)_(\d+)$")


def first(graph, subject, predicates):
    """First value for the first predicate that has one, in listed order."""
    for pred in predicates:
        for value in graph.objects(subject, pred):
            return value
    return None


def all_values(graph, subject, predicates):
    out = []
    for pred in predicates:
        for value in graph.objects(subject, pred):
            if value not in out:
                out.append(value)
    return out


def pick_version(graph, subject):
    """Prefer a value that looks like a version.

    The ChEBI slim puts a paragraph of prose in owl:versionInfo and the real
    ChEBI release number in obo:owl_versionInfo, so taking the first hit blindly
    would record the prose as the version.
    """
    candidates = all_values(graph, subject, VERSION_PREDS)
    for value in candidates:
        if VERSION_RE.match(str(value).strip()):
            return str(value).strip()
    return None


def pick_release_date(graph, subject, version_iri):
    """Upstream release date as an xsd:date.

    The versionIRI is the most reliable source. Failing that, oboInOwl:date in
    DD:MM:YYYY form -- the ChEBI slim also carries a YYYY-MM-DD stamp for when
    the slim itself was built, which is not what we want here.
    """
    if version_iri:
        match = VERSION_IRI_DATE_RE.search(str(version_iri))
        if match:
            return match.group(1)
    for value in graph.objects(subject, OBOINOWL.date):
        match = OBO_DATE_RE.match(str(value).strip())
        if match:
            day, month, year = match.groups()
            return f"{year}-{month}-{day}"
    return None


def analyse(path, uri_space):
    """Parse one ontology file and pull out everything the VoID needs."""
    graph = Graph()
    graph.parse(str(path), format="turtle")

    ontology = None
    for subject in graph.subjects(RDF.type, OWL.Ontology):
        ontology = subject
        break
    if ontology is None:
        raise SystemExit(f"{path.name}: no owl:Ontology header found")

    classes = set(graph.subjects(RDF.type, OWL.Class))
    named = [str(c) for c in classes if isinstance(c, URIRef)]

    own_terms = [i for i in named if i.startswith(uri_space)]
    if not own_terms:
        raise SystemExit(f"{path.name}: no classes found under {uri_space}")

    # Example resource: the ontology's declared root term if it names one,
    # otherwise its lowest-numbered own term, for a stable pick across releases.
    # Keep the IRI exactly as written -- OBO local IDs are not consistently
    # zero-padded (CHEBI_90 is real, CHEBI_0000090 is not).
    example = first(graph, ontology, [URIRef(OBO + "IAO_0000700")])
    if example is None:
        example = URIRef(min(own_terms, key=lambda i: int(TERM_RE.match(i).group(2))))

    version_iri = first(graph, ontology, [OWL.versionIRI])
    return {
        "ontology_iri": str(ontology),
        "version_iri": str(version_iri) if version_iri else None,
        "version": pick_version(graph, ontology),
        "released": pick_release_date(graph, ontology, version_iri),
        "title": first(graph, ontology, TITLE_PREDS),
        "description": first(graph, ontology, DESC_PREDS),
        "license": first(graph, ontology, LICENSE_PREDS),
        "creators": all_values(graph, ontology, CREATOR_PREDS),
        "comment": first(graph, ontology, [RDFS.comment]),
        "triples": len(graph),
        "classes": len(classes),
        "own_classes": len(own_terms),
        "uri_space": uri_space,
        "example": str(example),
    }


def escape(text):
    text = str(text)
    for old, new in (("\\", "\\\\"), ('"', '\\"'), ("\n", "\\n"), ("\r", "\\r"), ("\t", "\\t")):
        text = text.replace(old, new)
    return text


def render(entries):
    lines = [
        "# Generated by scripts/build_ontology_void.py -- do not edit by hand.",
        "#",
        "# VoID description of the ontology imports loaded into the WikiPathways",
        "# SPARQL endpoint alongside the WikiPathways RDF. Regenerated by the",
        "# 'Build imports' workflow whenever an ontology is rebuilt, so the versions",
        "# below always match the Turtle files in this directory.",
        "",
        "@prefix dcat:    <http://www.w3.org/ns/dcat#> .",
        "@prefix dcterms: <http://purl.org/dc/terms/> .",
        "@prefix foaf:    <http://xmlns.com/foaf/0.1/> .",
        "@prefix freq:    <http://purl.org/cld/freq/> .",
        "@prefix owl:     <http://www.w3.org/2002/07/owl#> .",
        "@prefix pav:     <http://purl.org/pav/> .",
        "@prefix void:    <http://rdfs.org/ns/void#> .",
        "@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .",
        "",
        f"<{RAW_BASE}/ontology-void.ttl>",
        "        a                  void:DatasetDescription ;",
        '        dcterms:title      "VoID description of the ontologies imported into the '
        'WikiPathways SPARQL endpoint"^^xsd:string ;',
        f"        dcterms:source     <{WORKFLOW}> ;",
    ]
    topics = [f"<{RAW_BASE}/{entry['file']}>" for entry, _ in entries]
    lines.append("        foaf:topic         " + " ,\n                           ".join(topics) + " .")
    lines.append("")

    for config, facts in entries:
        iri = f"{RAW_BASE}/{config['file']}"
        title = config.get("title") or facts["title"]
        description = config.get("description") or facts["description"]
        if config.get("note"):
            description = f"{description} {config['note']}" if description else config["note"]

        block = [f"<{iri}>", "        a                           void:Dataset ;"]
        block.append(f'        dcterms:title               "{escape(title)}"^^xsd:string ;')
        if description:
            block.append(f'        dcterms:description         "{escape(description)}"^^xsd:string ;')
        block.append("        dcterms:accrualPeriodicity  freq:monthly ;")
        if facts["license"]:
            block.append(f"        dcterms:license             <{facts['license']}> ;")
        if facts["released"]:
            block.append(f'        dcterms:issued              "{facts["released"]}"^^xsd:date ;')
        for creator in facts["creators"]:
            if isinstance(creator, URIRef):
                block.append(f"        dcterms:creator             <{creator}> ;")
            else:
                block.append(f'        dcterms:creator             "{escape(creator)}"^^xsd:string ;')
        if facts["version"]:
            block.append(f'        pav:version                 "{escape(facts["version"])}"^^xsd:string ;')
        if facts["version_iri"]:
            block.append(f"        owl:versionIRI              <{facts['version_iri']}> ;")
        block.append(f"        pav:importedFrom            <{config['imported_from']}> ;")
        block.append(f"        pav:importedBy              <{WORKFLOW}> ;")
        block.append(f"        pav:createdBy               <{WORKFLOW}> ;")
        for tool in config["created_with"]:
            block.append(f"        pav:createdWith             <{tool}> ;")
        # Only worth stating when the conversion started from something other
        # than the URL we fetched -- true for the ChEBI slim, not for the OBO
        # releases, whose ontology IRI is the PURL we downloaded.
        if facts["ontology_iri"] != config["imported_from"]:
            block.append(f"        pav:derivedFrom             <{facts['ontology_iri']}> ;")
        block.append(f"        void:dataDump               <{iri}> ;")
        block.append("        void:feature                <http://www.w3.org/ns/formats/Turtle> ;")
        block.append(f'        void:triples                {facts["triples"]} ;')
        block.append(f'        void:classes                {facts["classes"]} ;')
        block.append(f'        void:uriSpace               "{facts["uri_space"]}"^^xsd:string ;')
        block.append(f"        void:exampleResource        <{facts['example']}> ;")
        block.append("        void:vocabulary             <http://www.w3.org/2002/07/owl#> ;")
        block.append(f"        dcat:landingPage            <{config['landing_page']}> ;")
        block.append(f"        foaf:homepage               <{config['landing_page']}> .")
        lines.extend(block)
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data", type=Path)
    parser.add_argument("--check", action="store_true",
                        help="compare against the file on disk instead of writing")
    args = parser.parse_args()

    entries = []
    for config in ONTOLOGIES:
        path = args.data_dir / config["file"]
        if not path.exists():
            raise SystemExit(f"missing {path} -- run the ontology build jobs first")
        print(f"reading {path.name} ...", file=sys.stderr, flush=True)
        facts = analyse(path, config["uri_space"])
        print(f"  {facts['triples']} triples, {facts['classes']} classes "
              f"({facts['own_classes']} under {facts['uri_space']}), "
              f"version {facts['version']}", file=sys.stderr)
        entries.append((config, facts))

    content = render(entries)
    target = args.data_dir / "ontology-void.ttl"

    if args.check:
        current = target.read_text() if target.exists() else ""
        if current != content:
            print(f"{target} is out of date -- regenerate with "
                  f"scripts/build_ontology_void.py", file=sys.stderr)
            return 1
        print(f"{target} is up to date", file=sys.stderr)
        return 0

    # Parse what we just produced, so a malformed template fails here and not in
    # Virtuoso halfway through a monthly load.
    Graph().parse(data=content, format="turtle")
    target.write_text(content)
    print(f"wrote {target}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
