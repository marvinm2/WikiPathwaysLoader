#!/usr/bin/env python3
"""
WikiPathways Data Count Collection Script

This script executes SPARQL queries against the WikiPathways SPARQL endpoint
and updates the WikiPathwayscounts.tsv file with the latest statistics.
"""

import requests
import sys
from datetime import datetime
from pathlib import Path

# Configuration
SPARQL_ENDPOINT = "https://sparql.wikipathways.org/sparql"
QUERIES_DIR = Path(__file__).parent.parent / "queries"
TSV_FILE = Path(__file__).parent.parent / "WikiPathwayscounts.tsv"

# Query mappings: (query_file, result_variable)
QUERY_MAPPINGS = [
    ("count-pathways.rq", "PathwayCount"),
    ("count-datanodes.rq", "DataNodeCount"),
    ("count-geneproducts.rq", "GeneProductCount"),
    ("count-proteins.rq", "ProteinCount"),
    ("count-metabolites.rq", "MetaboliteCount"),
    ("count-interactions.rq", "InteractionCount"),
    ("count-signaling-pathways.rq", "pathwaycount"),
]


def execute_sparql_query(query):
    """Execute a SPARQL query and return the result."""
    headers = {
        "Accept": "application/sparql-results+json",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    response = requests.post(
        SPARQL_ENDPOINT,
        data={"query": query},
        headers=headers,
        timeout=60
    )

    response.raise_for_status()
    return response.json()


def get_count_from_result(result_json, variable_name):
    """Extract the count value from SPARQL JSON result."""
    try:
        bindings = result_json["results"]["bindings"]
        if bindings:
            # Handle different variable name formats (with or without capitalization)
            for binding in bindings:
                for key in binding:
                    if key.lower() == variable_name.lower():
                        return int(binding[key]["value"])
        return 0
    except (KeyError, ValueError, IndexError) as e:
        print(f"Error parsing result for {variable_name}: {e}", file=sys.stderr)
        return 0


def collect_all_counts():
    """Execute all queries and collect counts."""
    print("Collecting WikiPathways statistics...")
    counts = {}

    for query_file, var_name in QUERY_MAPPINGS:
        query_path = QUERIES_DIR / query_file

        if not query_path.exists():
            print(f"Warning: Query file not found: {query_path}", file=sys.stderr)
            counts[query_file] = 0
            continue

        print(f"  Executing {query_file}...")

        try:
            with open(query_path, 'r') as f:
                query = f.read()

            result = execute_sparql_query(query)
            count = get_count_from_result(result, var_name)
            counts[query_file] = count
            print(f"    Result: {count}")

        except Exception as e:
            print(f"Error executing {query_file}: {e}", file=sys.stderr)
            counts[query_file] = 0

    return counts


def get_release_date():
    """Get the release date from metadata query."""
    metadata_path = QUERIES_DIR / "metadata.rq"

    if not metadata_path.exists():
        # Fallback to current date
        return datetime.now().strftime("%Y-%m")

    try:
        with open(metadata_path, 'r') as f:
            query = f.read()

        result = execute_sparql_query(query)
        bindings = result["results"]["bindings"]

        if bindings:
            # Extract date from result
            date_str = bindings[0]["date"]["value"]
            # Parse ISO date and format as YYYY-MM
            date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return date_obj.strftime("%Y-%m")

    except Exception as e:
        print(f"Error getting release date: {e}", file=sys.stderr)

    # Fallback to current date
    return datetime.now().strftime("%Y-%m")


def update_tsv_file(date, counts):
    """Update the WikiPathwayscounts.tsv file with new data."""
    print(f"\nUpdating {TSV_FILE} for date {date}...")

    # Read existing file
    if not TSV_FILE.exists():
        print(f"Error: TSV file not found: {TSV_FILE}", file=sys.stderr)
        sys.exit(1)

    with open(TSV_FILE, 'r') as f:
        lines = f.readlines()

    # Parse header
    header = lines[0].strip()

    # Create new data row
    new_row = f"{date}\t{counts['count-pathways.rq']}\t{counts['count-datanodes.rq']}\t{counts['count-geneproducts.rq']}\t{counts['count-proteins.rq']}\t{counts['count-metabolites.rq']}\t{counts['count-interactions.rq']}\t{counts['count-signaling-pathways.rq']}\n"

    # Check if date already exists
    date_found = False
    for i, line in enumerate(lines[1:], start=1):
        if line.startswith(date + "\t"):
            # Replace existing row
            lines[i] = new_row
            date_found = True
            print(f"  Updated existing row for {date}")
            break

    if not date_found:
        # Find correct position to insert (maintain chronological order)
        insert_pos = len(lines)
        for i, line in enumerate(lines[1:], start=1):
            row_date = line.split("\t")[0]
            if row_date > date:
                insert_pos = i
                break
            elif not row_date.strip():  # Empty row
                continue

        lines.insert(insert_pos, new_row)
        print(f"  Added new row for {date}")

    # Write back to file
    with open(TSV_FILE, 'w') as f:
        f.writelines(lines)

    print("TSV file updated successfully!")


def main():
    """Main execution function."""
    print("=" * 60)
    print("WikiPathways Data Count Collection")
    print("=" * 60)

    # Get release date
    date = get_release_date()
    print(f"\nRelease date: {date}")

    # Collect counts
    counts = collect_all_counts()

    # Update TSV
    update_tsv_file(date, counts)

    print("\n" + "=" * 60)
    print("Collection complete!")
    print("=" * 60)

    # Print summary
    print("\nSummary:")
    print(f"  Date: {date}")
    print(f"  Pathways: {counts['count-pathways.rq']}")
    print(f"  DataNodes: {counts['count-datanodes.rq']}")
    print(f"  GeneProducts: {counts['count-geneproducts.rq']}")
    print(f"  Proteins: {counts['count-proteins.rq']}")
    print(f"  Metabolites: {counts['count-metabolites.rq']}")
    print(f"  Interactions: {counts['count-interactions.rq']}")
    print(f"  SignalingPathways: {counts['count-signaling-pathways.rq']}")


if __name__ == "__main__":
    main()
