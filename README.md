# distributed-systems-group-n

### Getting started

You will need [Docker](https://docker.com/) and [Docker Compose](https://docs.docker.com/compose/) installed to run this project.
Versions 29.x and 5.x are recommended for Docker and Docker Compose respectively.

```shell
## To build the project
$ make build

## To run all the containers in detached mode
$ make up ARGS=-d

## To tear down the containers
$ make down

## To view all logs
$ make logs

## To view logs for a particular service
$ make logs ARGS=kafka
```
