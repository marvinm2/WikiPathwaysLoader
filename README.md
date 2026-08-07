# WikiPathways SPARQL endpoint loader

Vocabularies, ontology imports and loading scripts for the
[WikiPathways SPARQL endpoint](https://sparql.wikipathways.org).

<img src="WikiPathwaysLOGO.png" width="214" height="194"><img src="BiGCaTLOGO.png" width="194" height="194">

WikiPathways publishes a new RDF release every month at
[data.wikipathways.org](https://data.wikipathways.org/current/rdf/). The endpoint is reloaded from
that release, and on every reload the loader also fetches seven Turtle files **from this
repository** and concatenates them into the store alongside the release data.

That is the thing to understand before changing anything here: a stale or broken file in `data/`
is stale or broken data in production. It is not a documentation repository.

## What the endpoint fetches from here

Both loader paths download the same seven files from `master`:

    wpvocab.ttl  gpmlvocab.ttl  PathwayOntology.ttl  DiseaseOntology.ttl
    CellOntology.ttl  chebi-slim.ttl  ontology-void.ttl

They come from a configurable base URL, defaulting to this repository's raw content:

    GITHUB_VOCAB=https://raw.githubusercontent.com/wikipathways/WikiPathwaysLoader/master/data

Two consequences worth stating plainly:

- **The default branch has to stay `master`.** Renaming it to `main` would break every one of those
  URLs, and GitHub does not redirect raw content across a branch rename. The dataset IRIs in
  `ontology-void.ttl` embed the same path.
- Anything merged to `master` reaches production at the next monthly reload without a further step.

## `data/`

| File | What it is |
|---|---|
| `wpvocab.ttl` | The WP vocabulary, `http://vocabularies.wikipathways.org/wp#`. Hand-maintained. |
| `gpmlvocab.ttl` | The GPML vocabulary, `http://vocabularies.wikipathways.org/gpml#`. Hand-maintained. |
| `PathwayOntology.ttl` | Pathway Ontology (RGD), from its OBO PURL, converted with ROBOT. |
| `DiseaseOntology.ttl` | Human Disease Ontology, from its OBO PURL, converted with ROBOT. |
| `CellOntology.ttl` | Cell Ontology, from its OBO PURL, converted with ROBOT. |
| `chebi-slim.ttl` | ChEBI cut down to the terms WikiPathways actually annotates with. |
| `ontology-void.ttl` | VoID description of the four ontologies above. **Generated — do not edit.** |

The four ontology files are loaded so that the ontology tags on pathways resolve to labels. When
one of them is missing or stale the endpoint still answers, and the only visible symptom is tags
with no `rdfs:label` — which is how Cell Ontology managed to be absent entirely for years.

The ChEBI slim is produced by the eNanoMapper Slimmer from the set of ChEBI terms it looks up on
the live endpoint, so it tracks what WikiPathways actually uses rather than all of ChEBI.

## Workflows

`.github/workflows/build-imports.yml` — 03:00 UTC on the 10th of each month, and on manual
dispatch. Downloads the three OBO ontologies from their PURLs, converts them with ROBOT, rebuilds
the ChEBI slim, regenerates `data/ontology-void.ttl`, and commits whatever changed to `master`.
Note it commits most months whether or not an ontology moved, because the Slimmer writes its own
build time into the slim.

`.github/workflows/collect-counts.yml` — 23:00 UTC on the 13th of each month, and on manual
dispatch. Runs the count queries against the live endpoint and appends a row to
[`WikiPathwayscounts.tsv`](WikiPathwayscounts.tsv).

Both push directly to `master` and declare `permissions: contents: write` for that reason.

## `scripts/`

`build_ontology_void.py` — generates `data/ontology-void.ttl` from the ontology Turtle files
themselves: version, release date, licence, upstream source, the tool that converted it, and
triple and class counts. This replaced a hand-maintained file that had drifted badly, still
naming Jenkins jobs that no longer existed. Reading the facts out of the data means it cannot
drift again.

    pip install 'rdflib>=7,<8'
    python3 scripts/build_ontology_void.py

The output is a pure function of its inputs — no wall-clock timestamps — so re-running it without
an ontology change leaves the file byte-identical, which is what makes the workflow's
"commit only if something changed" guard work. `--check` verifies the committed file matches the
data without writing.

`collect_counts.py` — runs the queries in `queries/` against the endpoint and maintains
`WikiPathwayscounts.tsv` in date order. Driven by `collect-counts.yml`.

`void-rewrite.sql` — Virtuoso rewrite rule that serves `/.well-known/void` by CONSTRUCTing the
VoID out of the store, rather than by copying a file into a document root as the pre-2026 hosting
did. Apply it to **both** blue-green instances: the rule lives in Virtuoso's own SQL tables and
survives `RDF_GLOBAL_RESET()` and restarts, but a rule on only one instance silently disappears at
the next cutover. The file's own comments carry the rest, including two traps that cost a day.

## `queries/`

The count and metadata queries used to sanity-check a load: pathways, data nodes, gene products,
proteins, metabolites, interactions, signalling pathways, and the dataset metadata. They carry no
`PREFIX` lines because the endpoint declares its namespaces server-side.

`metadata.rq` should report the current month's release. A sharp drop in any count, or a number
that moves when it should not, means look at the RDF before switching the endpoint over.

Worth also running a federated query by hand after a load, since nothing else exercises that path:

```sparql
SELECT DISTINCT (str(?title) as ?pathwayName) ?ChEBI ?ChemicalName ?LinkedStressor
WHERE {
  ?pathway a wp:Pathway ; wp:organismName "Homo sapiens" ; dc:title ?title .
  ?chemical a wp:Metabolite ; dcterms:isPartOf ?pathway ; wp:bdbChEBI ?mappedid .
  SERVICE <https://aopwiki.rdf.bigcat-bioinformatics.org/sparql/> {
    ?mappedid a cheminf:000407 ; cheminf:000407 ?ChEBI .
    ?cheLook a cheminf:000000 ; dc:title ?ChemicalName ;
             dcterms:isPartOf ?LinkedStressor ; skos:exactMatch ?mappedid .
  }
} LIMIT 1
```

## How a monthly load runs

The endpoint runs on the Translational Genomics Docker Swarm cluster, in a blue-green pair of
Virtuoso instances behind Traefik. A load never touches the live instance: it fills the offline
one, verifies it, and an operator flips which instance serves once the numbers look right. Rolling
back is flipping it the other way, and the previous release stays loaded until the next cycle
overwrites it.

There is a scheduled path — a monthly cron job on the cluster that does the whole load and then
stops short of the switch — and a manual path for one-off loads. Both read this repository's
`data/` directory, and both concatenate it with the release zips into a single Turtle file loaded
into the graph `http://rdf.wikipathways.org/`.

The operational detail — host names, service names, the switch script, the rewrite rules, storage
paths — lives in the cluster's own documentation, which is maintained alongside the running
services and is the authoritative source. It is deliberately not duplicated here, because a
second copy would drift and there would be no way to tell which was right.

Before 2026 the endpoint ran on a single host with nginx and docker-compose, and earlier still on
OpenShift. Both arrangements are gone; the instructions for them are in this file's git history if
anyone ever needs them.
