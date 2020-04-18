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

`git clone http://github.com/marvinm2/WikiPathwaysloader.git`

## Step 3 - Create a folder, enter it, and store the data
This folder is best to create in the same directory as all files from this GitHub repository. 

`mkdir data`

`cd data`

To download the data, go directly to [data.wikipathways.org/current/rdf](http://data.wikipathways.org/current/rdf/) or use the following commands, in which the date (in the example below the date was 2020-04-10) should be adapted to match the latest datasets:

`wget http://data.wikipathways.org/current/rdf/wikipathways-20200410-rdf-gpml.zip`

`wget http://data.wikipathways.org/current/rdf/wikipathways-20200410-rdf-wp.zip`

`wget http://data.wikipathways.org/current/rdf/wikipathways-20200410-rdf-void.ttl`

`wget http://data.wikipathways.org/current/rdf/wikipathways-20200410-rdf-authors.zip`

After downloading, the three `.zip` files should be unzipped, and the remaining `void.ttl` file should be stored in one of the created folders. Can be done with the command:

`unzip \*.zip`

## Step 4 - Concatenate all files
Connect all separate `.ttl` files in one single file by entering the following:

`find . -name *.ttl -exec cat > ../WikiPathways.ttl {} \;`

Afterwards, move back up one folder

`cd ../`

## Step 5 - Build the Docker image
To build the Docker image, use the following command from within the folder that contains the `Dockerfile`, `docker-entrypoint.sh`, and the newly created `WikiPathways.ttl`:

`sudo docker build .`

## Step 6 - Tag and push the created Docker image
The created Docker image will have a randomly generated `IMAGE ID`, which can be found using:

`sudo docker images`

The created Docker image should be tagged in two ways:
- one that has a tag with the version
- one that has the `latest` tag

Copy the `IMAGE ID` of the created Docker image, and use it to replace the `[IMAGE ID]` in tag commands. The version of the image is the date on which this protocol is executed (in this example, the date is `2020-04-17`)

`sudo docker tag [IMAGE ID] bigcatum/wploader:latest`

`sudo docker tag [IMAGE ID] bigcatum/wploader:2020-04-17`





