# django-core

This repository is a generic docker based django project that is being used in all of my backend projects 

## Some features:
* Generic intergration of heavy independant third party apps, like **Machine Learning** applications, to backend dashboard
* Account and team management with invitiation + api key authentication and permissions
* Extra modules based on django-restframework, e.g. **GenericSerializer**(inspired by the concept of GraphQL), filtersets, expiring tokens, ...
* Efficient querysets for heavy calculations, like **statistics pages**. Extra generic expressions for querysets are implemented.
* basic configurations for firewall and nginx image

## How to use:

1) customize src/.env file
2) django and nginx docker images must be created: ```docker-compose up --build```
