# WikiPathwaysloader

This repository contains files for the monthly update of the [WikiPathways SPARQL endpoint](sparql.wikipathways.org), which is deployed in Openshift using the base [openlink/virtuoso-opensource-7](https://hub.docker.com/r/openlink/virtuoso-opensource-7/) Docker image. In order to load the data into the Virtuoso service, a loader Docker image is built and pushed to DockerHub in the [bigcatum/wploader](https://hub.docker.com/r/bigcatum/wploader) repository.

<img src="https://github.com/marvinm2/WikiPathwaysloader/blob/master/WikiPathwaysLOGO.png" width="214" height="194"><img src="https://github.com/marvinm2/WikiPathwaysloader/blob/master/BiGCaTLOGO.png" width="194" height="194">

Every month there is a new data release by WikiPathways, all of which are stored in [data.wikipathways.org](http://data.wikipathways.org/). The protocol for getting the data in the Virtuoso SPARQL endpoint will be described step by step, containing commands used in Linux terminal.

## Step 1 - Check if the RDF generation was done correctly
Check the sizes of the files in the RDF folder of the new set on [data.wikipathways.org/current/rdf](http://data.wikipathways.org/current/rdf/) and whether they are of similar size, or slightly larger than the sizes shown in the screenshot below.

<img src="https://github.com/marvinm2/WikiPathwaysloader/blob/master/WikiPathwaysLOGO.png" width="214" height="194">

## Step 2 - Clone this repository or download the necessary files
For this process of creating the Docker image and using it in Openshift, the following files are required:
- [Dockerfile]()
- [docker-entrypoint.sh]()
- [wikipathwaysloader.yaml]()

Download these files or clone this repository with the following command:

    git clone http://github.com/marvinm2/WikiPathwaysloader.git

## Step 3 - Create a folder, enter it, and store the data
This folder is best to create in the same directory as all files from this GitHub repository. 

    mkdir data
    cd data

To download the data, go directly to [data.wikipathways.org/current/rdf](http://data.wikipathways.org/current/rdf/) or use the following commands, in which the date (in the example below the date was 2020-04-10) should be adapted to match the latest datasets:

    wget http://data.wikipathways.org/current/rdf/wikipathways-20200410-rdf-gpml.zip
    wget http://data.wikipathways.org/current/rdf/wikipathways-20200410-rdf-wp.zip
    wget http://data.wikipathways.org/current/rdf/wikipathways-20200410-rdf-void.ttl
    wget http://data.wikipathways.org/current/rdf/wikipathways-20200410-rdf-authors.zip

After downloading, the three `.zip` files should be unzipped, and the remaining `void.ttl` file should be stored in one of the created folders. Can be done with the command:

    unzip \*.zip

## Step 4 - Concatenate all files
Connect all separate `.ttl` files in one single file by entering the following:

    find . -name *.ttl -exec cat > ../WikiPathways.ttl {} \;

Afterwards, move back up one folder

    cd ../

## Step 5 - Build the Docker image
To build the Docker image, use the following command from within the folder that contains the `Dockerfile`, `docker-entrypoint.sh`, and the newly created `WikiPathways.ttl`:

    sudo docker build .

## Step 6 - Tag and push the created Docker image
The created Docker image will have a randomly generated `IMAGE ID`, which can be found using:

    sudo docker images

The created Docker image should be tagged in two ways:
- one that has a tag with the version
- one that has the `latest` tag

Copy the `IMAGE ID` of the created Docker image, and use it to replace the `[IMAGE ID]` in tag commands. The version of the image is the date on which this protocol is executed (in this example, the date is `2020-04-17`). The version is stored to create an archive of older versions of the data.

    sudo docker tag [IMAGE ID] bigcatum/wploader:2020-04-17
    sudo docker tag [IMAGE ID] bigcatum/wploader:latest

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
    
    DELETE FROM load_list WHERE ll_graph = 'wikipathways.org';

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
    
Define the permissions to use the SPARQL endpoint with:

    log_enable(1);
    grant select on "DB.DBA.SPARQL_SINV_2" to "SPARQL";
    grant execute on "DB.DBA.SPARQL_SINV_IMP" to "SPARQL";

## Step 14 - Load the data and run the RDF loader
To load the `WikiPathways.ttl` file and run the RDF loader, execute the following commands (this might take a while):

    ld_dir('.', 'WikiPathways.ttl', 'wikipathways.org');
    rdf_loader_run();

To check the status of the loaded data, the `ll_status` in the `load_list` should be 2. Do this using:

    select * from DB.DBA.load_list;

## Step 15 - Quit the SQL and pod

    quit;
    
    exit



