## EWXPWS DB documentation

# Launching the EWXPWSDB API server using docker

There is a docker file for building and running the included FastAPI server.  
The docker file is really very simple in that it installs this as a  

Here are hints for running this on an ubuntu-based server.   The advantage to 
using docker for this purpose is that you can run multiple servers in different
environments.  

## 1. Install Docker
First install docker on the system if it's not present already.   These
instructions are generic and depends upon which operating system you are 
using (Windows, MacOS, Ubuntu, AmazonLinux, etc)

Many of the Amazon Linux 2023 AMIs (images used to create VMs) include
docker already. 

## 2. Launch Docker

After install docker must be started to use it.  Modern systems use systemctl to
manage services (which is probably does not even need to be said) and if docker 
is installed it should automatically start.  If it's not started, use this:

`sudo systemctl start docker`

## 3. Build container

It may be easier to build the container on the system in whic you plan to use it
rather than remotely.    This is especially needed if you don't have an account
with a build service (typically requires payment) and you are using an 
ARM-based computer (e.g. Apple Silicon) and want to run on X86 VM.   
(there are ways around this but this may be easier).  In addition if you build
the image on your local computer, it must be uploaded to the VM which may 
take just as long as building on a build-VM. 

Requires sudo privileges on the build machine

Example build command, tagged v0.21. Replace the tag with `latest` or the 
version number

```
TAG=v0.21
sudo docker buildx build  -t ewxpwsdb:$TAG -f Dockerfile .
```

## 4. Set up the environment

There are several enviroment variables needed by the system. See the example
.env file in this repository and the main readme for details.   You can set
these variables in the enviroment before launching docker but an easier way is
to create a file with them and tell Docker.  the file does not have to be called
`.env` (this is just the convention for when the server is run on the command
line without docker using the python dot env library).  Create the file with the
appropriate variables (e.g. database connection string needed).   Using a file
is potentially more secure as setting them on the command line also enters them
into the command history file. 

One option to create a system-useable environment file is to add it to /etc, eg

`/etc/.pwsapienv`  

set permissions to read-only for pwsapi user

## 4. Run directly/manually

You can use one of the following commands to start the api.  This assume the
file with the environment variables used the system are in a file named `.env`
in same directory in which you start the docker image.   Note we are running on
ports other than standard http (80) or https (443) as we plan to use a reverse
proxy server (such as nginx) to make installing SSL certs easier (e.g. with
certbot).  The dockerfile in this project uses gunicorn as a server.   This
assume port 8000 is also open.   

as mentioned above, the Docker image for this package simply exposes the CLI
that is created by the package (in `src/ewxpwsdb/api/cli.py`)

```
docker run -d --rm --name pwsapi --env-file=/etc/.pwsapienv -p 8000:8000 \
      ewxpwsdb:v0.23 \
      startapi --port 8000 --no-ssl
```

This will run the server in the background and remove the container when it 
exits so you can re-use the container name.  Again this uses no ssl so that we
can use a reverse proxy on port 443 like nginx. 

Additionally if you want to run a temporary dev server on another port you need
to: 

1. open the port up in the network security settings on the cloud system or with
   the on-server firewall (in AWS this is the network security group).   
2. start the server using the flag to indicate there is no ssl 
   `sudo docker run -d  --env-file=.env -p 8001:8001 ewxpwsdb:v0.23 startapi --port 80 --no-ssl`

this allows you to test a second, temporary version of the api server on the
same system.  this is for development and testing only and hsould not be used on
a production system.  

## 5. add system service to run at boot

You need to add a `systemd` service to your system to run the above 
automatically when the system reboots.   

*Note this current does not work correctly and is a work in progress*


Example `pwsapi.service` file saved in `/etc/systemd/system/`:

```
[Unit]
Description=PWS API Server Docker
After=docker.service
Requires=docker.service

[Service]
Restart=always
StartLimitInterval=30
# ensure the server is stopped before attempting to start it
ExecStartPre=-/usr/bin/docker stop %n
# set the container name the same as this service
# --rm remove container when it's exited so we can re-use this name
ExecStart=/usr/bin/docker run -d --rm --name %n --env-file=/etc/.pwsapienv -p 8000:8000 ewxpwsdb:v0.23 startapi --port 8000 --no-ssl

[Install]
WantedBy=multi-user.target
```
