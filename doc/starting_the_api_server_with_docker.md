## EWXPWS DB documentation

# Launching the EWXPWSDB API server using docker

There is a docker file for building and running the included FastAPI server.     

Here are hints for running this on an ubuntu-based server.   The advantage to using docker for this purpose is that you can run multiple servers in different environments.  

## 1. Install Docker
First install docker on th system 

*(instructions tbd)*

## 2. Launch Docker

After install docker must be started to use it.  Modern systems use systemctl to manage services (which is probably does not even need to be said). 


```
sudo systemctl start docker
```

## 3. Build container

It's far easier to build the container on the system in whic you plan to use it rather than remotely.    This is especially needed if you don't have an account with a build service (typically requires payment) and you are using an ARM-based computer (e.g. Apple Silicon) and want to run on X86 VM.   (there are ways around this but this may be easier).  In addition if you build the image on your local computer, it must be uploaded to the VM. 

*instructions tbd*

## 4. Set up the environment

There are several enviroment variables needed by the system. See the example .env file in this repository and the main readme for details.   You can set these variables in the enviroment before launching docker but an easier way is to create a file with them and tell Docker.  the file does not have to be called `.env` (this is just the convention for when the server is run on the command line without docker using the python dot env library).  Create the file with the appropriate variables (e.g. database connection string needed).   Using a file is potentially more secure as setting them on the command line also enters them into the command history file.     

## 4. Run directly/manually

You can use one of the following commands to start the api.  This assume the file with the environment variables used the system are in a file named `.env` in same directory in which you start the docker image.   Note we are running on ports other than standard http (80) or https (443) as we plan to use a reverse proxy server (such as nginx) to make installing SSL certs easier (e.g. with certbot).  The dockerfile in this project uses gunicorn as a server.   This assume port 8000 is also open 

```
sudo docker run -d  --env-file=.env -p 8000:8000 ewxpwsdb:v0.23 startapi --port 8000 --ssl
```


Additionally if you want to run a temporary dev server on another port you need to 

1. open the port up in the network security settings on the cloud system or with the on-server firewall (in AWS this is the network security group).   
2. start the server using the flag to indicate there is no ssl 
   `sudo docker run -d  --env-file=.env -p 8001:8001 ewxpwsdb:v0.23 startapi --port 80 --no-ssl`

this allows you to test a second, temporary version of the api server on the same system.  this is for development and testing only and hsould not be used on a production system.  

## 5. add system service to run at boot

You need to add a `systemd` service to your system to run the above 