# Loading and configuring the WikiPathways SPARQL endpoint

This repository contains files for the monthly update of the [WikiPathways SPARQL endpoint](sparql.wikipathways.org), which is deployed using the base [ammar257ammar/Snorql-UI](https://github.com/ammar257ammar/Snorql-UI) Docker image. The instructions below are for loading new data in the SPARQL endpoint.

<img src="https://github.com/marvinm2/WikiPathwaysloader/blob/master/WikiPathwaysLOGO.png" width="214" height="194"><img src="https://github.com/marvinm2/WikiPathwaysloader/blob/master/BiGCaTLOGO.png" width="194" height="194">

Every month there is a new data release by WikiPathways, all of which are stored in [data.wikipathways.org](http://data.wikipathways.org/). The protocol for getting the data in the Virtuoso SPARQL endpoint will be described step by step.

## Step 1 - Check if the RDF generation was done correctly
Check the sizes of the files in the RDF folder of the new set on [data.wikipathways.org/current/rdf](http://data.wikipathways.org/current/rdf/) and whether they are of similar size, or slightly larger than the sizes shown in the screenshot below.

<img src="https://github.com/marvinm2/WikiPathwaysloader/blob/master/datawikipathways.png">

## Step 2 - Access the server and check which of the two instances is live
Currently, the service runs on `Strato1`. If this is incorrect, check the BiGCaT Service spreadsheet. Access the server with your credentials.

There are 2 instances of the WikiPathways snorql UI, one of which is live through [WikiPathways SPARQL endpoint](sparql.wikipathways.org) and the other one is for testing before going live. The loading protocol below should be done on the instance that is not live. After loading, the URL proxy is switched between the two instances. To check the current live instance, inspect the file `/etc/nginx/sites-enabled/wikipathways` and take note of the two ports that are indicated. 

Next, use the following to identify which of the instances is live:

    sudo docker ps | grep -w wikipathways

If the current live instance is `wikipathways-snorql` and `wikipathways-virtuoso`, navigate to the folder `/home/MarvinMartens/WikiPathways-EP2` for the loading of data. If the current live instance is `wikipathways-snorql2` and `wikipathways-virtuoso2`, navigate to the folder `/home/MarvinMartens/WikiPathways-EP2`.

## Step 3 - Enter the folder called 'import'
Within the `/home/MarvinMartens/WikiPathways-EP` or `/home/MarvinMartens/WikiPathways-EP2` folder, you can find the `db` folder. The `db/data/` folder will be used to store all Turtle files and create the main WikiPathways.ttl. Move to that folder:

    cd db/data

If the folder is not empty (for example, it has data from last month), empty the folder.

    rm -r *

To download the data, go directly to [data.wikipathways.org/current/rdf](http://data.wikipathways.org/current/rdf/) or use the following commands, in which the date (in the example below the date was 2020-10-10) should be adapted to match the latest datasets:

    wget http://data.wikipathways.org/current/rdf/wikipathways-20240410-rdf-gpml.zip
    wget http://data.wikipathways.org/current/rdf/wikipathways-20240410-rdf-wp.zip
    wget http://data.wikipathways.org/current/rdf/wikipathways-20240410-rdf-authors.zip
    wget http://data.wikipathways.org/current/rdf/wikipathways-rdf-void.ttl
    wget -O wpvocab.ttl https://raw.githubusercontent.com/marvinm2/WikiPathwaysLoader/master/data/wpvocab.ttl
    wget -O gpmlvocab.ttl https://raw.githubusercontent.com/marvinm2/WikiPathwaysLoader/master/data/gpmlvocab.ttl
    wget -O PathwayOntology.ttl https://raw.githubusercontent.com/marvinm2/WikiPathwaysLoader/master/data/PathwayOntology.ttl
    wget -O DiseaseOntology.ttl https://raw.githubusercontent.com/marvinm2/WikiPathwaysLoader/master/data/DiseaseOntology.ttl
    wget -O CellOntology.ttl https://jenkins.bigcat.unimaas.nl/job/Ontology%20conversion%20-%20CL/lastSuccessfulBuild/artifact/cl.ttl
    wget -O chebi-slim.ttl https://raw.githubusercontent.com/marvinm2/WikiPathwaysLoader/master/data/chebi-slim.ttl

## Step 3 - Unzip and concatenate all files

After downloading and copying all zip files into the `import` folder, the `.zip` files should be unzipped with the command:

    unzip \*.zip
    
The remaining `wpvocab.ttl`, `gpmlvocab.ttl`, `chebi-slim.ttl`, and `...rdf-void.ttl` files should be moved into one of the created folders. 

    mv *.ttl wp

Combine all separate `.ttl` files in one single file by entering the following:

    find . -name *.ttl -exec cat > ../WikiPathways.ttl {} \;
    mv ../WikiPathways.ttl .

Also, be sure to copy the `ServiceDescription.ttl` in the folder and download the most recent VoID file separately, naming it `void`:
``` 
cp ../../ServiceDescription.ttl .
```
```
wget -O void http://data.wikipathways.org/current/rdf/wikipathways-rdf-void.ttl
```

## Step 4 - Enter SQL and reset the Virtuoso service
Enter the OpenLink Virtuoso Interactive SQL of the instance (be sure to replace `wikipathways-virtuoso` with `wikipathways-virtuoso2` to enter the right one):

    sudo docker exec -i wikipathways-virtuoso isql 1111

Prior to loading the new data, the Virtuoso server has to be restarted and the old data has to be removed. This is done with the following commands and could take some time:

    RDF_GLOBAL_RESET();

    DELETE FROM load_list WHERE ll_graph = 'http://rdf.wikipathways.org/';
    DELETE FROM load_list WHERE ll_graph = 'servicedescription';
    
To check if the files are removed from the `load_list`, enter:

    select * from DB.DBA.load_list;

## Step 5 - Loading the prefixes and permissions
While in the SQL, define the namespace prefixes by entering the following commands:

    log_enable(2);
    DB.DBA.XML_SET_NS_DECL ('dc', 'http://purl.org/dc/elements/1.1/',2);
    DB.DBA.XML_SET_NS_DECL ('cas', 'https://identifiers.org/cas/',2);
    DB.DBA.XML_SET_NS_DECL ('wprdf', 'http://rdf.wikipathways.org/',2);
    DB.DBA.XML_SET_NS_DECL ('prov', 'http://www.w3.org/ns/prov#',2);
    DB.DBA.XML_SET_NS_DECL ('foaf', 'http://xmlns.com/foaf/0.1/',2);
    DB.DBA.XML_SET_NS_DECL ('hmdb', 'https://identifiers.org/hmdb/',2);
    DB.DBA.XML_SET_NS_DECL ('freq', 'http://purl.org/cld/freq/',2);
    DB.DBA.XML_SET_NS_DECL ('pubmed', 'http://www.ncbi.nlm.nih.gov/pubmed/',2);
    DB.DBA.XML_SET_NS_DECL ('wp', 'http://vocabularies.wikipathways.org/wp#',2);
    DB.DBA.XML_SET_NS_DECL ('void', 'http://rdfs.org/ns/void#',2);
    DB.DBA.XML_SET_NS_DECL ('biopax', 'http://www.biopax.org/release/biopax-level3.owl#',2);
    DB.DBA.XML_SET_NS_DECL ('dcterms', 'http://purl.org/dc/terms/',2);
    DB.DBA.XML_SET_NS_DECL ('rdfs', 'http://www.w3.org/2000/01/rdf-schema#',2);
    DB.DBA.XML_SET_NS_DECL ('pav', 'http://purl.org/pav/',2);
    DB.DBA.XML_SET_NS_DECL ('ncbigene', 'https://identifiers.org/ncbigene/',2);
    DB.DBA.XML_SET_NS_DECL ('xsd', 'http://www.w3.org/2001/XMLSchema#',2);
    DB.DBA.XML_SET_NS_DECL ('rdf', 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',2);
    DB.DBA.XML_SET_NS_DECL ('gpml', 'http://vocabularies.wikipathways.org/gpml#',2);
    DB.DBA.XML_SET_NS_DECL ('skos', 'http://www.w3.org/2004/02/skos/core#',2);
    DB.DBA.XML_SET_NS_DECL ('owl', 'http://www.w3.org/2002/07/owl#',2);
    DB.DBA.XML_SET_NS_DECL ('efo', 'http://www.ebi.ac.uk/efo/',2);
    DB.DBA.XML_SET_NS_DECL ('xml', 'http://www.w3.org/XML/1998/namespace',2);
    DB.DBA.XML_SET_NS_DECL ('wiki', 'http://sparql.wikipathways.org/',2);
    DB.DBA.XML_SET_NS_DECL ('cur', 'http://vocabularies.wikipathways.org/wp#Curation:',2);
    
Define the permissions to use the SPARQL endpoint with:

    log_enable(1);
    grant select on "DB.DBA.SPARQL_SINV_2" to "SPARQL";
    grant execute on "DB.DBA.SPARQL_SINV_IMP" to "SPARQL";

## Step 6 - Load the data and run the RDF loader
To load the `WikiPathways.ttl` file and run the RDF loader, execute the following commands (this might take a while):

    ld_dir('data', 'WikiPathways.ttl', 'http://rdf.wikipathways.org/');
    ld_dir('data', 'ServiceDescription.ttl', 'servicedescription');
    rdf_loader_run();

To check the status of the loaded data, the `ll_status` in the `load_list` should be 2. This step will also indicate whether the Turtle file is correct or causes an error in Virtuoso. Do this using:

    select * from DB.DBA.load_list;

## Step 7 - Quit the SQL
To quit the SQL:

    quit;

## Step 8 - Move the void file to ./well-known
Move the void file to the `.well-known` folder:

    cp db/data/void snorql-extended/.well-known/

Quit the exec mode:
    
    exit

## Step 9 - Test if everything went well

The last step of this protocol is testing whether the loading of new data worked. For that, visit the [WikiPathways SPARQL endpoint](http://sparql.wikipathways.org) and force refresh the page (Ctrl + F5). Next, run the SPARQL queries from the metadata folder in the Query panel. Click the `.rq` files and click `Run query`. The testing comprises three steps:

#### Metadata 

Use the next query to validate that the right dataset is loaded. It should normally indicate the 10th of the current month, assuming this protocol is executed after the 10th day of the month. For that, select the `A. Metadata/metadata.rq` query from the Query panel and run it.

### Counts of data

The following set of SPARQL queries involves the counts of the dataset for various entities. To compare with previous versions, be sure to add the resulting counts in the [WikiPathwayscounts.tsv](https://github.com/marvinm2/WikiPathwaysloader/blob/master/WikiPathwayscounts.tsv) spreadsheet by adding a new line to it. Note when the numbers go down, or are drastically different from the previous months. That could indicate potential issues in the RDF. These SPARQL queries are located in the `A. Metadata/datacounts` folder in the Query panel

- Count of Pathways Loaded 
- Count total amount of DataNodes 
- Count of GeneProduct Nodes 
- Count of Protein Nodes 
- Count of Metabolites 
- Count of all Interactions in WikiPathways 
- Count of all signaling pathways in WikiPathways 


### Federated SPARQL query 
Make sure to test a federated SPARQL query to make sure federated queries are running. This one takes slightly longer than the other test queries. For example, with the following query:

```sparql
PREFIX aopo:	<http://aopkb.org/aop_ontology#> 
PREFIX cheminf:	<http://semanticscience.org/resource/CHEMINF_> 

SELECT DISTINCT (str(?title) as ?pathwayName) ?chemical ?ChEBI ?ChemicalName  ?mappedid ?LinkedStressor 

WHERE {
   ?pathway a wp:Pathway ; wp:organismName "Homo sapiens"; dcterms:identifier ?WPID ; dc:title ?title . 
   ?chemical a wp:Metabolite; dcterms:isPartOf ?pathway; wp:bdbChEBI ?mappedid . 
   SERVICE <https://aopwiki.rdf.bigcat-bioinformatics.org/sparql/>{
    ?mappedid a cheminf:000407; cheminf:000407 ?ChEBI .
    ?cheLook a cheminf:000000; dc:title ?ChemicalName ; dcterms:isPartOf ?LinkedStressor ;  skos:exactMatch ?mappedid .
   }}
limit 1
```

Also accessible with [this permalink](https://bit.ly/443CJBl)

If the SNORQL UI does not work directly with the federated query, try in the SPARQL endpoint [sparql.wikipathways.org/sparql/](sparql.wikipathways.org/sparql/)

### Final step: change the live instance to the right ports and restart nginx
Update the `/etc/nginx/sites-enabled/wikipathways` file to have the correct ports of the updated instance:

    sudo nano /etc/nginx/sites-enabled/wikipathways

Then, restart nginx

    sudo service nginx restart

## In case of SPARQL endpoint down

In case the SPARQL endpoint is down, perform the following steps:
### Log into the server and check which of the instances should be active
See Step 2
### Check if the docker container with the Virtuoso Endpoint is running or has stopped. 
The Docker container should be called `wikipathways-virtuoso`. To check for running containers:

    sudo docker ps | grep -w wikipathways

To check for a stopped container:

    sudo docker ps -a | grep -w wikipathways

### If the container is not running
Enter the correct folder (`/home/MarvinMartens/WikiPathways-EP` or `/home/MarvinMartens/WikiPathways-EP2`). Launch the service with:

    sudo docker-compose up -d

### If the container is running
Try to log into the container in the exec mode (Step 4). If you get the following error message `'*** Error S2801: [Virtuoso Driver]CL033: Connect failed to 1111 = 1111. at line 0 of Top-Level:'`, do the following: Enter the correct folder (`/home/MarvinMartens/WikiPathways-EP` or `/home/MarvinMartens/WikiPathways-EP2`). Restart the docker container with the commands:
```
sudo docker-compose down
```
```
sudo docker compose up -d
```
This should resolve the issue. 
