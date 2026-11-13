# Security

## Reporting a problem

Please don't report a security problem in a public issue. Write to
[easimov@iai.kit.edu](mailto:easimov@iai.kit.edu) instead, with what is affected and how to
reproduce it. We answer as soon as we can and tell you when a fix is out.

## Supported versions

Fixes go into the latest version only.

## Running eCoSim safely

The server and the clients talk without a login and without encryption, so anyone who can reach
the server port can join a run or send it messages. By default the server only listens on
`localhost`. When you set another host, run eCoSim only in a network you trust, for example inside
a cluster job or behind a firewall. The same goes for the port of a Pyro5 model.

With PostgreSQL, use a database user with a password and only the rights eCoSim needs. The HPC job
scripts start their own PostgreSQL with a password login.
