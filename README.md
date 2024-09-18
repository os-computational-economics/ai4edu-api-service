# AI 4 EDU Backend API containers

## This is the repo for the AI4EDU experimental project.
- The main entry point is main.py. This is the fastapi app that serves the API.
- To run a local instance of the app, run "run_server_local.py"
- In the cloud deployment environment, the app is run as a docker container. The docker image is built using the Dockerfile in the root directory of this repo. The docker image is then pushed to the GitHub container registry (https://ghcr.io). The docker image is then pulled from the registry and run as a container in the cloud deployment environment.
- The "admin" folder contains the admin service code.
- The "user" folder contains the end user code.
- The "common" folder contains common classes.

## Config files
There are two config files maintained in this repo:
- the docker_compose_cloud folder contains the docker compose file for the cloud deployment environment
- the nginx_conf folder contains the nginx configuration file for the cloud deployment environment. In the cloud deployment environment, the nginx server (running as a docker container) is used as a reverse proxy server to the fastapi app.

## Database connection and migration
The database connection and migration is handled by 3 packages:
- alembic: database migration
- sqlalchemy: ORM (Object Relational Mapping)
- psycopg: database connection
The alembic configuration file is maintained in the root directory of this repo. The database migration scripts are maintained in the "migrations" folder in the root directory of this repo.
Alembic is used to generate the migration scripts. The migration scripts are then run in the cloud deployment environment to update the database schema.
All database models are maintained in the "models.py" file in the "migration" folder.

## Setup

### Required Software

- Docker
- docker-compose
- Postgresql (optional)
- Python (version 3.11.0)

### Local Database without docker-compose

For security reasons we cannot just connect to the live database so instead we use a local postgresql database

To set this up start by running pgadmin4 (should have came with postgresql). If it is your first time running postgresql it will ask you to set up a password, this will be used later. Once in pgadmin, create a new database called `ai4edu_local` or uncommend the database creation comment in the init script. Afterwards right click the database and hit create script. Run the initialization script that may be found in `db/init.sql`.

If using docker-compose, configuring the postgresql database is completely automatic when the compose is started. If the structure of the database changes, be sure to reset the container or run relevant init scripts to migrate.

### Using Nix

A few useful development tools are provided through the `nix` package manager

#### Shells

You may enter the repo's development shell with the `nix develop` command. This will automatically provide you with all necessary dependencies for this project (minus a docker server).

You may visit `flake.nix` to see the full list of provided dependencies.

The nix development shell is also compatible with direnv, so be sure to enable direnv for this project if you are using direnv.

#### Scripts

Using `nix run .#init-repo` will automatically create all necessary SSL and JWT keys for the project. Remember to copy JWT keys into your .env file however.

Using `nix run .#pgadmin` or just `nix run` will begin the pgadmin client for you interact with the current postgres server (whether it be in docker-compose or local). The interface is accessible through `localhost:5050`

All scripts may be found within the `flake.nix`, including starting docker-compose

### .env

The .env file contains sensitive information such as API keys and is thus not kept in the repo. Create a new file named `.env` and copy in the keys (it should be on slack but if you cant find just ask).

An example `.env` file may be found in `.env.template`. Be sure to edit the postgres config if not using the docker-compose provided. The `POSTGRES_PASSWORD` is auto-propagated to the container to update the password. It is recommended to not leave the default password as "password"

JWT keys may be generated with the example commands provided in the template. Multi-line strings are supported within the .env file with double quotes ("). Be sure to run the second command on a `privateKey.pem` that contains the output of the first command.

### Local SSL certificates

Local SSL certificates should be placed into a folder called `ssl`, which should be ignored by git. The following command should generate self-signed certificates which are satisfactory for local testing and to satisfy Case SSO.

Run this command within a folder called `ssl`:
> `openssl req -newkey rsa:4096 -x509 -sha512 -days 365 -nodes -out localhost_bundle.crt -keyout localhost.key -subj "/C=US/ST=Ohio/L=Cleveland /O=AI4EDU/OU=dev/CN=au4edudev/emailAddress=."`

## Run the backend

In order to start the backend make sure you have Docker running and use the command `docker-compose up --build`

Alternatively if you want to run the backend outside of docker you can use `python run_server_local.py` or `python3 run_server_local.py` (the command depends on how python is setup on your machine). Note that if you run it outside of Docker you need to change the DB_URI in the .env file to `postgresql+psycopg://postgres:your_postgresql_password@localhost:5432/ai4edu_local`