#NOTE: on a local fedora machine debian images are not working with the FMUs libraries (e.g. SMDTest_Sub2.so) and
#      the following error occurs:
#      Exception in thread "main" java.lang.UnsatisfiedLinkError:
#            Unable to load library '/tmp/fmu_3b427ad0_d902_458c_a67a_c19da75bae82Sub2_Linux/binaries/linux64/SMDTest_Sub2.so':
#                    Native library (tmp/fmu_3b427ad0_d902_458c_a67a_c19da75bae82Sub2_Linux/binaries/linux64/SMDTest_Sub2.so)
#                    not found in resource path (FmuVariation-0.0.1-SNAPSHOT-shaded.jar)
FROM fedora:42

####################
## Prerequisites
####################
USER root
# Update apt
RUN dnf update -y
# Install Java, Python and other prerequistes
RUN dnf install -y \
    gnupg \
    apt-transport-https \
    lsb-release \
    wget \
    python3 \
    java-21-openjdk \
    vim \
    nc

## add postgres repository
#RUN dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/F-$(rpm -E %{fedora})-x86_64/pgdg-fedora-repo-latest.noarch.rpm
##   postgresql16: client programs to access the DBMS
#RUN dnf install -y \
#    postgresql16 \
#    postgresql16-server \
## init postgresql
#RUN /usr/pgsql-16/bin/postgresql-16-setup initdb


####################
## Add TimescaleDB
####################
# Steps are taken from here: https://docs.timescale.com/self-hosted/latest/install/installation-linux/
# Set up package repo
RUN dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/F-$(rpm -E %{fedora})-x86_64/pgdg-fedora-repo-latest.noarch.rpm
COPY timescale_timescaledb.repo /etc/yum.repos.d/timescale_timescaledb.repo
## Update packages
RUN dnf update -y
## Install TimescaleDB and PostgreSQL
RUN dnf install -y \
    timescaledb-2-postgresql-16 \
    postgresql16 \
    postgresql16-server \
    postgresql16-contrib

#####################
## Copy IT dirs
#####################
COPY integration_test /integration_test
RUN mkdir /builds
RUN chown -R postgres:postgres /integration_test
RUN chmod +x /integration_test/*.sh
RUN chown -R postgres:postgres /builds

#####################
## Set up entrypoint
#####################
ENV PATH $PATH:/usr/pgsql-16/bin
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

USER postgres
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
