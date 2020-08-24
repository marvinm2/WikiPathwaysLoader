# WikiPathwaysloader

This repository contains files for the monthly update of the [WikiPathways SPARQL endpoint](sparql.wikipathways.org), which is deployed in Openshift using the base [openlink/virtuoso-opensource-7](https://hub.docker.com/r/openlink/virtuoso-opensource-7/) Docker image. In order to load the data into the Virtuoso service, a loader Docker image is built and pushed to DockerHub in the [bigcatum/wploader](https://hub.docker.com/r/bigcatum/wploader) repository.

<img src="https://github.com/marvinm2/WikiPathwaysloader/blob/master/WikiPathwaysLOGO.png" width="214" height="194"><img src="https://github.com/marvinm2/WikiPathwaysloader/blob/master/BiGCaTLOGO.png" width="194" height="194">

Every month there is a new data release by WikiPathways, all of which are stored in [data.wikipathways.org](http://data.wikipathways.org/). The protocol for getting the data in the Virtuoso SPARQL endpoint will be described step by step.

The requirements for updating the WikiPathwys SPARQL endpoint with this protocol:
- Ability to use [Docker](https://docs.docker.com/get-docker/) on your system
- Atherization to push Docker images to the [bigcatum/wploader](https://hub.docker.com/r/bigcatum/wploader) repository
- Ability to use [OpenShift Container Platform command-line interface (CLI)](https://docs.openshift.com/container-platform/4.2/cli_reference/openshift_cli/getting-started-cli.html) on your system
- Access to the Openshift project on the OpenRiskNet infrastructure that runs the WikiPathways Virtuoso service

## Step 1 - Check if the RDF generation was done correctly
Check the sizes of the files in the RDF folder of the new set on [data.wikipathways.org/current/rdf](http://data.wikipathways.org/current/rdf/) and whether they are of similar size, or slightly larger than the sizes shown in the screenshot below.

<img src="https://github.com/marvinm2/WikiPathwaysloader/blob/master/datawikipathways.png">


## Step 2 - Clone this repository or download the necessary files
For this process of creating the Docker image and using it in Openshift, the following files are required:
- [Dockerfile](https://github.com/marvinm2/WikiPathwaysloader/blob/master/Dockerfile)
- [docker-entrypoint.sh](https://github.com/marvinm2/WikiPathwaysloader/blob/master/docker-entrypoint.sh)
- [wikipathwaysloader.yaml](https://github.com/marvinm2/WikiPathwaysloader/blob/master/wikipathwaysloader.yaml)
- [/data/PathwayOntology.ttl](https://github.com/marvinm2/WikiPathwaysLoader/blob/master/data/PathwayOntology.ttl)

Download these files or clone this repository with the following command:

    git clone http://github.com/marvinm2/WikiPathwaysloader.git

## Step 3 - Enter the folder called 'data'
This folder will be used to store all Turtle files, and already includes the `PathwayOntology.ttl` file. The folder should be located in the same location as the other required files mentioned in step 2.

    cd data

To download the data, go directly to [data.wikipathways.org/current/rdf](http://data.wikipathways.org/current/rdf/) or use the following commands, in which the date (in the example below the date was 2020-04-10) should be adapted to match the latest datasets:

    wget http://data.wikipathways.org/current/rdf/wikipathways-20200810-rdf-gpml.zip
    wget http://data.wikipathways.org/current/rdf/wikipathways-20200810-rdf-wp.zip
    wget http://data.wikipathways.org/current/rdf/wikipathways-20200810-rdf-authors.zip
    wget http://data.wikipathways.org/current/rdf/wikipathways-20200810-rdf-void.ttl
    wget -O wpvocab.ttl https://www.w3.org/2012/pyRdfa/extract?uri=http://vocabularies.wikipathways.org/wp#
    wget -O gpmlvocab.ttl https://www.w3.org/2012/pyRdfa/extract?uri=http://vocabularies.wikipathways.org/gpml#
    wget https://raw.githubusercontent.com/marvinm2/WikiPathwaysLoader/master/data/PathwayOntology.ttl

After downloading, the three `.zip` files should be unzipped with the command:

    unzip \*.zip
    
The remaining `wpvocab.ttl`, `gpmlvocab.ttl` and `...rdf-void.ttl` files should be moved into one of the created folders. 

    mv *.ttl wp

## Step 4 - Concatenate all files
Connect all separate `.ttl` files in one single file by entering the following:

    find . -name *.ttl -exec cat > ../WikiPathways.ttl {} \;

Afterwards, move back up one folder

    cd ../

## Step 5 - Build the Docker image
To build the Docker image, use the following command from within the folder that contains the `Dockerfile`, `docker-entrypoint.sh`, and the newly created `WikiPathways.ttl`:

    sudo docker build -t wploader .

## Step 6 - Tag and push the created Docker image
The created Docker image should be tagged in two ways:
- one that has a tag with the version
- one that has the `latest` tag

The version of the image is the date on which this protocol is executed (in this example, the date is `2020-04-17`). The version is stored to create an archive of older versions of the data.

    sudo docker tag wploader bigcatum/wploader:2020-04-17
    sudo docker tag wploader bigcatum/wploader:latest

## Step 7 - Push the tagged Docker images to DockerHub
For this step, it is necessary to login with a DockerHub account, and have permission to push images to the repository, which is in our case [bigcatum/wploader](https://hub.docker.com/r/bigcatum/wploader).

    sudo docker push bigcatum/wploader:2020-04-17
    sudo docker push bigcatum/wploader:latest

This might take a while, depending on your internet speed. When it is finished, the Docker images will appear in the `tags` tab of [bigcatum/wploader](https://hub.docker.com/r/bigcatum/wploader/tags?page=1) repository.

## Step 8 - Using the created loader Docker image in Openshift
Assuming you have access to the Openshift project that has the running Virtuoso service (in our case, in the OpenRiskNet e-infrastructure), you can login using the [OpenShift Container Platform command-line interface (CLI)](https://docs.openshift.com/container-platform/4.2/cli_reference/openshift_cli/getting-started-cli.html). For easy access to the login command, log in on the [Openshift console of OpenRisknet](https://prod.openrisknet.org/console/), end use the `Copy Login Command` in the top-right of the screen for your authorization token. If you have login details, use the following command, after which you enter your authentication details:

    oc login https://prod.openrisknet.org:443

## Step 9 - Removing the old wikipathwaysloader job, and starting the new one
After you logged in, you want to remove the old `wikipathwaysloader` job by entering:

    oc delete job --selector template=wikipathwaysloader

Next, a new job can be started which will use the [bigcatum/wploader:latest](https://hub.docker.com/r/bigcatum/wploader/tags?page=1) Docker image. Be sure to be located in the folder that has the `wikipathwaysloader.yaml` file.

    oc process -f wikipathwaysloader.yaml | oc create -f -

This job will pull the [bigcatum/wploader:latest](https://hub.docker.com/r/bigcatum/wploader/tags?page=1) Docker image and execute the `docker-entrypoint.sh` file which copies the `WikiPathways.ttl` file into the mounted folder of the Virtuoso service.

## Step 10 - Entering the Virtuoso pod
To enter the Virtuoso pod, the name of the pod is required, which you can list using:

    oc get pods

Copy the name of the correct pod, and use it in the following command to replace `[POD NAME]`:

    oc rsh [POD NAME]

## Step 11 - Move the WikiPathways.ttl to the right folder and retrieve the DBA password
A simple step, moving the `WikiPathways.ttl` file from the mounted folder into the one you are in when you enter the pod.

    mv ../../../wikipathwaysdata/WikiPathways.ttl .

Next, look up the DBA password using:

    head -n3 ../../../settings/dba_password

## Step 12 - Enter SQL and reset the Virtuoso service
To enter the OpenLink Virtuoso Interactive SQL, enter:

    isql

Prior to loading the new data, the Virtuoso server has to be restarted and the old data has to be removed. This is done with the following commands and could take some time and requires you to enter the DBA password:

    RDF_GLOBAL_RESET();

    DELETE FROM load_list WHERE ll_graph = 'http://rdf.wikipathways.org/';

## Step 13 - Loading the prefixes and permissions
While in the ISQL, define the namespace prefixes by entering the following commands:

    log_enable(2);
    DB.DBA.XML_SET_NS_DECL ('dc', 'http://purl.org/dc/elements/1.1/',2);
    DB.DBA.XML_SET_NS_DECL ('cas', 'http://identifiers.org/cas/',2);
    DB.DBA.XML_SET_NS_DECL ('wprdf', 'http://rdf.wikipathways.org/',2);
    DB.DBA.XML_SET_NS_DECL ('prov', 'http://www.w3.org/ns/prov#',2);
    DB.DBA.XML_SET_NS_DECL ('foaf', 'http://xmlns.com/foaf/0.1/',2);
    DB.DBA.XML_SET_NS_DECL ('hmdb', 'http://identifiers.org/hmdb/',2);
    DB.DBA.XML_SET_NS_DECL ('freq', 'http://purl.org/cld/freq/',2);
    DB.DBA.XML_SET_NS_DECL ('pubmed', 'http://www.ncbi.nlm.nih.gov/pubmed/',2);
    DB.DBA.XML_SET_NS_DECL ('wp', 'http://vocabularies.wikipathways.org/wp#',2);
    DB.DBA.XML_SET_NS_DECL ('void', 'http://rdfs.org/ns/void#',2);
    DB.DBA.XML_SET_NS_DECL ('biopax', 'http://www.biopax.org/release/biopax-level3.owl#',2);
    DB.DBA.XML_SET_NS_DECL ('dcterms', 'http://purl.org/dc/terms/',2);
    DB.DBA.XML_SET_NS_DECL ('rdfs', 'http://www.w3.org/2000/01/rdf-schema#',2);
    DB.DBA.XML_SET_NS_DECL ('pav', 'http://purl.org/pav/',2);
    DB.DBA.XML_SET_NS_DECL ('ncbigene', 'http://identifiers.org/ncbigene/',2);
    DB.DBA.XML_SET_NS_DECL ('xsd', 'http://www.w3.org/2001/XMLSchema#',2);
    DB.DBA.XML_SET_NS_DECL ('rdf', 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',2);
    DB.DBA.XML_SET_NS_DECL ('gpml', 'http://vocabularies.wikipathways.org/gpml#',2);
    DB.DBA.XML_SET_NS_DECL ('skos', 'http://www.w3.org/2004/02/skos/core#',2);
    DB.DBA.XML_SET_NS_DECL ('owl', 'http://www.w3.org/2002/07/owl#',2);
    DB.DBA.XML_SET_NS_DECL ('ns1', 'http://purl.obolibrary.org/obo/',2);
    DB.DBA.XML_SET_NS_DECL ('ns2', 'http://data.bioontology.org/metadata/',2);
    DB.DBA.XML_SET_NS_DECL ('ns3', 'http://data.bioontology.org/metadata/obo/',2);
    DB.DBA.XML_SET_NS_DECL ('ns4', 'http://purl.obolibrary.org/obo/pw#',2);
    DB.DBA.XML_SET_NS_DECL ('efo', 'http://www.ebi.ac.uk/efo/',2);
    DB.DBA.XML_SET_NS_DECL ('xml', 'http://www.w3.org/XML/1998/namespace',2);
    DB.DBA.XML_SET_NS_DECL ('wiki', 'http://sparql.wikipathways.org/',2);
    
Define the permissions to use the SPARQL endpoint with:

    log_enable(1);
    grant select on "DB.DBA.SPARQL_SINV_2" to "SPARQL";
    grant execute on "DB.DBA.SPARQL_SINV_IMP" to "SPARQL";

## Step 14 - Load the data and run the RDF loader
To load the `WikiPathways.ttl` file and run the RDF loader, execute the following commands (this might take a while):

    ld_dir('.', 'WikiPathways.ttl', 'http://rdf.wikipathways.org/');
    rdf_loader_run();

To check the status of the loaded data, the `ll_status` in the `load_list` should be 2. Do this using:

    select * from DB.DBA.load_list;

## Step 15 - Quit the SQL and pod
To quit the SQL:

    quit;

To exit the pod:

    exit

## Step 16 - Test if everything went well

The last step of this protocol is the testing whether the loading of new data worked. For that, visit the [WikiPathways SPARQL endpoint](http://sparql.wikipathways.org) and force refresh the page (Ctrl + F5). Next, run the SPARQL queries by pasting the queries below in the SPARQL endpoint and click `Run query`. The testing comprises of two steps:

### Step 16A - Perform SPARQL queries
Run the SPARQL queries below to count the content of the RDF and check if the data loaded is consistent with previous releases. 

#### Query #1 - Metadata 
Use the next query to validate that the right dataset is loaded. It should normally indicate the 10th of the current month, assuming this protocol is executed after the 10th day of the month.

```sparql
SELECT DISTINCT ?dataset (str(?titleLit) as ?title) ?date ?license 
WHERE {
   ?dataset a void:Dataset ;
   dcterms:title ?titleLit ;
   dcterms:license ?license ;
   pav:createdOn ?date .
 }
 ```

The following SPARQL queries involve the counts of the dataset for various entities. To compare with previous versions, be sure to add the resulting counts in the [WikiPathwayscounts.tsv](https://github.com/marvinm2/WikiPathwaysloader/blob/master/WikiPathwayscounts.tsv) spreadsheet by adding a new line to it. Note when the numbers go down, or are drastically different from the previous months. That could indicate potential issues in the RDF.

#### Query #2 - Count of Pathways Loaded 

```sparql
SELECT DISTINCT count(?pathwayRDF) as ?pathwayCount
WHERE {
    ?pathwayRDF a wp:Pathway .
} 
```

#### Query #3 - Count total amount of DataNodes 

```sparql
SELECT DISTINCT count(?dataNodes) as ?DataNodeCount
WHERE {
    ?dataNodes a wp:DataNode .
}
```

#### Query #4 - Count of GeneProduct Nodes 

```sparql
SELECT DISTINCT count(?geneProduct) as ?GeneProductCount
WHERE {
    ?geneProduct a wp:GeneProduct .
}
```

#### Query #5 - Count of Protein Nodes 

```sparql
SELECT DISTINCT count(?protein) as ?ProteinCount
WHERE {
    ?protein a wp:Protein .
}
```

#### Query #6 - Count of Metabolites 

```sparql
SELECT DISTINCT count(?Metabolite) as ?MetaboliteCount
WHERE {
    ?Metabolite a wp:Metabolite .
}
```

#### Query #7 - Count of all Interactions in WikiPathways 

```sparql
SELECT DISTINCT count(?Interaction) as ?InteractionCount
WHERE {
    ?Interaction a wp:Interaction .
}
```

#### Query #8 - Count of all signaling pathways in WikiPathways 

```sparql
SELECT count(distinct ?pathway) as ?pathwaycount
WHERE {
  ?tag1 a owl:Class ;
  rdfs:label ?label .
  ?tag rdfs:subClassOf* ?tag1.
  ?pathway a wp:Pathway; wp:ontologyTag ?tag.
FILTER regex(str(?label), "signaling pathway")
}
```

### Step 16B - Test federated SPARQL query 
Make sure to test a federated SPARQL query to make sure federated queries are running. This one takes slightly longer than the other test queries.

```sparql
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX up:<http://purl.uniprot.org/core/>
PREFIX rdf:<http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX cco: <http://rdf.ebi.ac.uk/terms/chembl#>
PREFIX rdfs:<http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?drugMechanism ?ChEMBLTarget
WHERE {
SERVICE <https://www.ebi.ac.uk/rdf/services/chembl/sparql>{
    ?drugMechanism a cco:Mechanism ;
    cco:hasMolecule ?ChEMBLCompound ;
    cco:hasTarget ?ChEMBLTarget .
}} LIMIT 100
```

