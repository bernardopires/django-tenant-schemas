# Docker Tutorial
## Requirements
- Docker
- Docker Compose

## HowTo

1. Change `HOST` to `tenant_tutorial_db` in **settings.py**.

1. `cd django-tenant-schemas/examples`

1. Run `docker-compose up --build` to start server.

1. Go to [localhost:8000](http://localhost:8000/) and fallow the instruction.

1. Execute `docker exec -it tenant_tutorial_app sh`. Do steps from tutorial here.

1. You can open **pgadmin4** on [localhost:5050](http://localhost:5050/).

pgadmin4 credentials:

- user: `pgadmin4@pgadmin.org`

- password: `admin`

database credentials:

- user: `postgres`

- password: `root`

- host: `tenant_tutorial_db`

## NB
If you want to save database after docker shutdown man [volumes in docker-compose](https://docs.docker.com/compose/compose-file/#volume-configuration-reference) and uncomment *volumes* in **tenant_tutorial_db** section in **docker-compose.yml**.
