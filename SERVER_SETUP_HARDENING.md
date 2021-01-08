# Monero Server Setup and Hardening

## Introduction

The following document outlines the technical setup of a number of hosted sites for the Monero community, namely:

- A reverse proxy
- The getmonero.org website
- The downloads sub-site
- The CCS sub-site

Each of these systems is hosted in a secure container with respective controls for identifying and detecting vulnerabilities, attacks and anomalies as well as providing for post incident analysis. This document is intended to be a living document to be updated as and when new controls or enhancements are identified to replace the existing ones.

## Attribution and thanks

This document, and the Monero server infrastructure itself, has only been possible thanks to the work and effort of Gus from [Tari Labs](https://tarilabs.com), Dan from [GloBee](https://globee.com), and others. In addition, the Monero community is extremely grateful for the ongoing sponsorship of server infrastructure by [GloBee](https://globee.com) and the global CDN by [Tari Labs](https://tarilabs.com).

## Contributing

Anyone can contribute to this living document, particularly if they find aspects of the security hardening that can and should be improved. Feel free to open a pull-request or issue for the change, and after discussion and acceptance by those in the Monero ecosystem who are familiar with infosec (particularly those in the Monero VRP workgroup) changes can be implemented in the live infrastructure and in this document.

## Container configuration


### Auditing

Firstly, as well as auditing normal Linux file system and system calls, we also audit all Docker related files and directories. The Docker daemon runs with root privileges and its behavior depends on some key files and directories. To enable auditing for docker we add the following lines to "/etc/audit/audit.rules"

```
-w /usr/lib/systemd/system/docker.service -k docker
-w /usr/lib/systemd/system/docker.socket -k dockerDo 
-w /etc/default/docker -k docker
-w /etc/sysconfig/docker -k docker
-w /etc/docker/daemon.json -k docker
-w /usr/bin/containerd -k docker
-w /usr/sbin/runc -k docker
```

and restart the daemon.

```
~$ sudo service auditd restart
```

### Restrict container network traffic

By default, unrestricted network traffic is enabled between all containers on the same host on the default network bridge. Because of this each container has the potential of reading all packets across the container network on the same host. This might lead to an unintended and unwanted disclosure of information to other containers. Therefore we need to restrict this. We edit the Docker daemon configuration file to ensure that ICC is disabled. It should contain the following setting:

```
"icc": false
```

*\* The database the CCS app uses listens on the host loopback adapter.

*\* The Monero wallet for the CCS app listens on the host loopback adapter.

### Change ulimit

"ulimit" provides control over the resources available to the shell and to processes which it starts. Setting system resource limits judiciously can save us from disasters such as a fork bomb. Setting the default ulimit for the Docker daemon enforces the ulimit for all container instances. To have proper control over system resources we define a default ulimit as is needed in the environment. For this we ensure "---default-ulimit" is added to /etc/docker/daemon.json.

### Namespace support

The Linux kernel \"user namespace\" support within the Docker daemon provides additional security for the Docker host system. It allows a container to have a unique range of user and group IDs which are outside the traditional user and group range utilized by the host system. For example, the root user can have the expected administrative privileges inside the container but can effectively be mapped to an unprivileged UID on the host system. We enable user namespace support in Docker daemon to utilize container user to host user re-mapping. We create two files and restart the daemon with the "---userns-remap" flag.

```
~$ touch /etc/subuid /etc/subgid

~$ dockerd --userns-remap=default
```



### Centralized and remote logging

Centralized and remote logging ensures that all important log records are safe even in the event of a major data availability issue. For our configuration we utilise both and start the docker daemon with the following logging driver:

```
~$ dockerd --log-driver=syslog --log-opt syslog-address=tcp://x.x.x.x
```

### Live restore

By setting the "---live-restore\" flag within the Docker daemon we ensure that container execution is not interrupted when it is not available. This also makes it easier to update and patch the Docker daemon without application downtime. To enable this we add this setting to the "/etc/docker/daemon.json" file.

### Disable userland proxy

The Docker engine provides two mechanisms for forwarding ports from the host to containers, hairpin NAT, and the use of a userland proxy. In most circumstances, the hairpin NAT mode is preferred as it improves performance and makes use of native Linux iptables functionality instead of using an additional component. To enable this we add set "---userland-proxy" to *false* in the "/etc/docker/daemon.json" file.

### Restrict containers

A process can set the no\_new\_priv bit in the kernel and this persists across forks, clones and execve. The no\_new\_priv bit ensures that the process and its child processes do not gain any additional privileges via suid or sgid bits. This reduces the security risks associated with many dangerous operations because there is a much reduced ability to subvert privileged binaries. Setting this at the daemon level ensures that by default all new containers are restricted from acquiring new privileges. To do this we add the "---no-new-privileges\" parameter to the "/etc/docker/daemon.json" file.

### Container user

It's generally good practice to run the container as a non-root user, where possible. This can be done either via the USER directive in the Dockerfile or through gosu or similar where used as part of the CMD or ENTRYPOINT directives. Each container used for Monero services is run as a non-root user.

### Content trust

Content trust provides the ability to use digital signatures for data sent to and received from remote Docker registries. These signatures allow client-side verification of the identity and the publisher of specific image tags and ensures the provenance of container images. To enable content trust in a shell we run the following command:

```
export DOCKER_CONTENT_TRUST=1
```

### HEALTHCHECK instruction

An important security control is that of availability. Adding the HEALTHCHECK instruction to the container image ensures that the Docker engine periodically checks the running container instances against that instruction to ensure that containers are still operational. Based on the results of the health check, the Docker engine could terminate containers which are not responding correctly, and instantiate new ones. HEALTHCHECK is enabled for each image.

### SELinux security

SELinux provides a Mandatory Access Control (MAC) system that greatly augments the default Discretionary Access Control (DAC) model. We add an extra layer of safety to the containers by enabling SELinux on the Linux host. To enable SELinux for containers we start the service with the "---selinux-enabled" parameter.

### Limit memory usage

By default a container can use all of the memory on the host. A memory limit mechanism is used to prevent a denial of service occurring where one container consumes all of the host's resources and other containers on the same host are therefore not able to function. All containers are run with limited memory.

### CPU priority

CPU time is divided between containers equally. We control available CPU resources amongst container instances by using the CPU sharing feature. CPU sharing allows us to prioritize one container over others and prevents lower priority containers from absorbing CPU resources which may be required by other processes. This ensures that high priority containers are able to claim the CPU runtime they require. To do this we run each container with the "---cpu-shares" parameter.

### Read only filesystem

We enable an option that forces containers at runtime to explicitly define their data writing strategy to persist or not persist their data. This also reduces security attack vectors since the container instance\'s filesystem cannot be tampered with or written to unless it has explicit read-write permissions on its filesystem folder and directories. We add the "---read-only" flag at container runtime to enforce the container's root filesystem being mounted as read only.

### Bind incoming container traffic

As the system hosting these containers has multiple network interfaces the container can accept connections on exposed ports on any network interface. The containers do not accept incoming connections on any random interface, but only the one designated for their respective type of traffic. The exception here is with the web server reverse proxy which is bound to 0.0.0.0

### Container restart policy

To avoid a potential denial of service through container restarts we restrict the number restarts to a maximum of "5". We enable this with the "\--detach ---restart=on-failure:5" parameter.

### Using latest versions

Multiple Docker commands such as docker pull, docker run etc. are known to have an issue where by default, they extract the local copy of the image, if present, even though there is an updated version of the image with the same tag in the upstream repository. This could lead to using older images containing known vulnerabilites. Image versions are checked regularly to ensure they are up to date.

### PIDs limit

Attackers could launch a fork bomb with a single command inside a container. This fork bomb could crash the entire system and would require a restart of the host to make the system functional again. Using the PIDs cgroup parameter \--pids-limit prevents this kind of attack by restricting the number of forks that can happen inside a container within a specified time frame. To enable this we "---pids-limit" parameter when launching the containers.

### Avoiding image sprawl

Tagged images are useful if you need to fall back from the \"latest\" version to a specific version of an image in production. Images with unused or old tags may contain vulnerabilities that might be exploited if instantiated. This process is performed manually with the following commands:

For removing exited containers:

```
~$ docker ps --filter status=dead --filter status=exited -aq | xargs -r docker rm -v
```

For removing unused images:

```
~$ docker images --no-trunc | grep '<none>' | awk '{ print $3 }' | xargs -r docker rmi
```

For removing unused volumes:

```
~$ docker volume ls -qf dangling=true | xargs -r docker volume rm
```



## Container Monitoring


Container monitoring is the process of implementing security tools and policies that will give you the assurance that everything in your container is running as intended, and only as intended. This includes protecting the infrastructure, the software supply chain, runtime, and everything in between. With this in mind, the process of securing and monitoring containers is continuous. As we are using docker for containerisation it's important that we don't introduce any vulnerabilities through this party libraries as well as scan continuously for any changes to our images.

The [Anchore Engine](https://github.com/anchore/anchore-engine) is an open-source tool for scanning and analyzing container images for security vulnerabilities and policy issues. It is available as a Docker container image that can run within an orchestration platform, or as a standalone installation.

To install we create the working directory, download the docker-compose.yaml and start:

```
~$ mkdir anchore && cd anchore

~/anchore$ curl https://docs.anchore.com/current/docs/engine/quickstart/docker-compose.yaml > docker-compose.yaml
```

### Verify Service Availability

After a few moments (depending on system speed), your Anchore Engine services should be up and running, ready to use. You can verify the containers are running with docker-compose:

```
~/achore$ docker-compose ps
```

```
Name					Command							State	Ports
------------------------------------------------------------------------------------------
anchor_analyzer_1		docker-entrypoint.sh anch ...	Up		8228/tcp	
anchor_api_1			docker-entrypoint.sh anch ...	Up		0.0.0.0:8228->8228/tcp	
anchor_catalog_1		docker-entrypoint.sh anch ...	Up		8228/tcp	
anchordb_1				docker-entrypoit.sh postgres	Up		5432/tcp	
anchor_policy-engine_1	docker-entrypoint.sh anch ...	Up		8228/tcp	
anchor_queue_1			docker-entrypoint.sh anch ...	Up		8228/tcp
```

Once up Anchor will need some time to for the engine to sync all vulnerability data. We can check this using the following command:

```
~/anchore$ docker-compose exec api anchore-cli system feeds list
```

```
Feed                    Group           LastSyn RecordCount     
github                  github:composer pending None  
github                  github:gem      pending None    
github                  github:java     pending None    
github                  github:npm      pending None    
github                  github:nuget    pending None    
github                  github:python   pending None    
nvdv2                   nvdv2:cves      pending 75000   
Vulnerabilities         alpine:3.10     2020-06-18T09:04:24.097825      1725    
vulnerabilities         alpine:3.11     2020-06-18T09:04:54.6675558     1904    
vulnerabilities         alpine:3.3      2020-06-18T09:05:27.880919      457     
vulnerabilities         alpine:3.4      2020-06-18T09:05:35.968058      681     
vulnerabilities         alpine:3.5      2020-06-18T09:05:47.839692      875     
vulnerabilities         alpine:3.6      2020-06-18T09:06:03.175967      1051    
vulnerabilities         alpine:3.7      2020-06-18T09:06:21.220216      1395    
vulnerabilities         alpine:3.8      2020-06-18T09:06:44.989782      1486    
vulnerabilities         alpine:3.9      2020-06-18T09:07:10.199129      1558    
vulnerabilities         amzn:2          2020-06-18T09:07:36.529917      371     
vulnerabilities         centos:5        2020-06-18T09:08:00.023036      1347    
vulnerabilities         centos:6        2020-06-18T09:08:50.5450995     1414    
vulnerabilities         centos:7        2020-06-18T09:09:47.668024      1079    
vulnerabilities         centos:8        2020-06-18T09:10:51.897518      293    
vulnerabilities         debian:10       2020-06-18T09:11:17.521461      22987   
vulnerabilities         debian:11       2020-06-18T09:17:06.693053      20132   
vulnerabilities         debian:7        2020-06-18T09:22:28.995214      20455   
vulnerabilities         debian:8        2020-06-18T09:27:56.393597      23959   
vulnerabilities         debian:9        2020-06-18T09:34:20.024352      23057   
vulnerabilities         debian:unstable 2020-06-18T09:40:30.568618      24383   
vulnerabilities         ol:5            2020-06-18T09:46:44.468378      1248    
vulnerabilities         ol:6            2020-06-18T09:47:36.301448      1528    
vulnerabilities         ol:7            2020-06-18T09:48:46.926634      1213    
vulnerabilities         ol:8            2020-06-18T09:49:58.987848      243     
vulnerabilities         rhel:5          2020-06-18T09:50:18.132817      7297    
vulnerabilities         rhel:6          2020-06-18T09:52:36.401724      6916    
vulnerabilities         rhel:7          2020-06-18T09:54:41.226131      6198    
vulnerabilities         rhel:8          2020-06-18T09:56:43.155089      1762    
vulnerabilities         ubuntu:12.04    2020-06-18T09:57:18.428255      14959   
vulnerabilities         ubuntu:12.10    2020-06-18T10:01:04.079754      5652    
vulnerabilities         ubuntu:13.04    2020-06-18T10:02:28.484830      4127    
vulnerabilities         ubuntu:14.04    2020-06-18T10:03:26.829261      21951   
vulnerabilities         ubuntu:14.10    2020-06-18T10:08:42.606760      4456    
vulnerabilities         ubuntu:15.04    2020-06-18T10:09:52.995509      5912    
vulnerabilities         ubuntu:15.10    2020-06-18T10:11:19.476645      6513    
vulnerabilities         ubuntu:16.04    2020-06-18T10:12:58.910023      19063   
vulnerabilities         ubuntu:16.10    2020-06-18T10:17:52.827455      8647    
vulnerabilities         ubuntu:17.04    2020-06-18T10:19:51.583886      9157    
vulnerabilities         ubuntu:17.10    2020-06-18T10:21:54.662854      7941    
vulnerabilities         ubuntu:18.04    2020-06-18T10:23:43.183380      13322   
vulnerabilities         ubuntu:18.10    2020-06-18T10:27:04.729094      8397    
vulnerabilities         ubuntu:19.04    2020-06-18T10:28:52.670142      8665    
vulnerabilities         ubuntu:19.10    2020-06-18T10:30:49.078677      8106    
vulnerabilities         ubuntu:20.04    2020-06-18T10:32:32.430732      7149
```

All the feeds will need to be completed before you can start using Anchore. A good indication is if all the feed counts are above 0.

### Analysing Images

Once all feeds are completed we add our images for analysis. Image analysis is performed as a distinct, asynchronous, and scheduled task driven by queues that analyser workers periodically poll. As we built the dockers images ourselves the Dockerfile used to build the image needs to be passed to Anchore Engine at the time of image addition. This is performed with the following command example:

```
anchore-cli image add myrepo.com:5000/app/webapp:latest --dockerfile=/path/to/Dockerfile
```

 

## Remote Access


There are a number of hardening changes made to the default SSH setup on the server. The first few being fairly obvious and then some additional to further enhance security on the protocol. The SSH port currently in use has been removed for obvious reasons and 'Protocol 2' is not necessary to be enforced for newer versions of SSH.

### Root Login Disabled

Remote login as root is disallowed. Any users who require root privileges are added to the group for sudo users.

```
PermitRootLogin no
```

### Idle Session Timeout

"ClientAliveInterval" sets a timeout interval in seconds after which if no data has been received from the client. "ClientAliveCountMax" sets the number of client alive messages which may be sent without sshd receiving any messages back from the client.

The following setting will check the client after 10 minutes of inactivity three times and then disconnect.

```
ClientAliveInterval 600
ClientAliveCountMax 3
Disable X11Forwarding
X11Forwarding is disabled as it is not required.
X11Forwarding no
```

### Detailed Logging

Verbose system logging is enabled to include detailed information such as an event source, date, user, timestamp, source addresses, destination addresses, and other useful elements.

```
LogLevel VERBOSE
```

### Ignore RHOSTS

The IgnoreRhosts parameter specifies that .rhosts and .shosts files will not be used in RhostsRSAAuthentication or HostbasedAuthentication.

```
IgnoreRhosts yes
```

### Disable GSSAPI Authentication

GSSAPI authentication is used to provide additional authentication mechanisms to applications. Allowing GSSAPI authentication through SSH exposes the system\'s GSSAPI to remote hosts, increasing the attack surface of the system. GSSAPI authentication must be disabled unless needed.

```
GSSAPIAuthentication no
```

### 2-Factor Authentication

To prevent against potential password attacks or in the event of a password compromise we enable Google Authenticator's TOTP (Time Based One Time Passwords). As part of the [Authenticator project](https://code.google.com/p/google-authenticator/) Google released a PAM (Pluggable Authentication Module) implementation of a 2-factor system. We enable this by installing the libpam module and enrolling users.

```
~$ sudo apt-get install libpam-google-authenticator
~$ google-authenticator
```

The enrolment process presents the user with a QR code to be scanned by the mobile google authenticator application and asks a number of questions:

```
Do you want authentication tokens to be time-based (y/n) y

Do you want to disallow multiple uses of the same authentication

token? This restricts you to one login about every 30s, but it increases your chances to notice or even prevent man-in-the-middle attacks (y/n) y

By default, tokens are good for 30 seconds and in order to compensate for possible time-skew between the client and the server, we allow an extra token before and after the current time. If you experience problems with poor time synchronization, you can increase the window from its default size of 1:30min to about 4min. Do you want to do so (y/n) y

If the computer that you are logging into isn\'t hardened against brute-force login attempts, you can enable rate-limiting for the authentication module. By default, this limits attackers to no more than 3 login attempts every 30s. Do you want to enable rate-limiting (y/n) y
```

Then we edit the PAM rule file /etc/pam.d/sshd by adding the follow at the end:

```
auth required pam_google_authenticator.so
```

Lastly, we add PAM authentication and challenge/response within the sshd\_config and restart the SSH server.

```
UsePAM yes
ChallengeResponseAuthentication yes
```

### User Whitelisting

We enable this feature to allow only authorised users to authenticate via SSH.

```
AllowUsers ***,***,***
```

### Changing Default Ciphers and Algorithms

By default SSH comes bundled with a number of insecure key exchange algorithms, symmetric ciphers and message authentication codes. It's important that these are removed to prevent passive collection and potential key recovery at a later stage.

We add the following to the SSH configuration file:

```
KexAlgorithms curve25519-sha256@libSSH.org
Ciphers chacha20-poly1305@openSSH.com
MACs hmac-sha2-512-etm@openSSH.com
```

### Regenerate Moduli

The use of multiple moduli inhibits a determined attacker from pre-calculating moduli exchange values, and discourages dedication of resources for analysis of any particular modulus. The /etc/ssh/moduli file that is installed with OpenSSH is identical to other new system installs of SSH. This does not necessarily mean they are insecure however it is generally good practice to regen these and strip small Diffie-Hellman moduli. We run the following commands:

```
~$ rm /etc/ssh/ssh_host_*
~$ ssh-keygen -t rsa -b 4096 -f /etc/ssh/ssh_host_rsa_key -N ""
~$ ssh-keygen -t ed25519 -f /etc/ssh/ssh_host_ed25519_key -N “"
~$ awk '$5 >= 3071' /etc/ssh/moduli > /etc/ssh/moduli.safe
~$ mv /etc/ssh/moduli.safe /etc/ssh/moduli
```

Restart SSH service and download and run [ssh-audit](https://github.com/arthepsy/ssh-audit):

```
# general       
(gen) banner: SSH-2.0-OpenSSHL7.6p1 Ubuntu-4ubuntu0.3
(gen) software: 0penSSH 7.6p1
(gen) compatibility: OpenSSH 7.2+, Dropbear SSH 2013.62+-
(gen) compression : enabled (zlib@openssh.com)  

# key exchange algorithms
(kex) curve25519-sha256@l ibssh.org [info] available since 0penSSH 6.5, Dropbear SSH 2013.62

# host-key algorithms
(key) ssh-ed25519                       -- [info] available since OpenSSH 6.5
(key) ssh-rsa                           -- [info] available since OpenSSH 2.5.0, Dropbear SSH 0.28
(key) rsa-sha2-512                      -- [info] available since OpenSSH 7.2
(key) rsa-sha2-256                      -- [info] available since OpenSSH 7.2

# encryption algorithms (ciphers)
(enc) chacha20-poly1305@openssh.com     -- [info] available since OpenSSH 6.5
                                        -- [info] default cipher since OpenSSH 6.9.

# message authenti.cation code algorithms
(mac) hmac-sha2-512-etm@openssh.comi    -- [info] available since OpenSSH 6.2

# algorithm recommendations (for OpenSSH 7.6)
(rec) +di ffie-hellman-group18- sha512  -- kex algorithm to append      
(rec) +diffie-hellman-group14-sha256    -- kex algorithm to append
(rec) +diffie-hel lman-group16-sha512   -- kex algorithm to append
(rec) +aes256-ctr                       -- enc algorithm to append
(rec) +aes192- ctr                      -- enc algorithm to append
(rec) +aes128-ctr                       -- enc algorithm to append
(rec) +aes128-gcm@openssh.com           -- enc algorithm to append     
(rec) +aes256-gcm@openssh.com           -- enc algorithm to append      
(rec) +hmac-sha2-256-etm@openssh.com    -- mac algorithm to append
(rec) +umac-128-etm@openssh.com         -- mac algorithm to append
```



### Fail2ban

Fail2ban is a log-parsing application that monitors system logs for indicators of automated attacks. When an attempted compromise is located, using the defined parameters, fail2ban will add a new rule to iptables to block the IP address of the attacker, either for a set amount of time or permanently. To enable we run the following commands:

```
~$ apt-get install fail2ban

~$ cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
```

Open the /etc/fail2ban/jail.d/defaults-debian.conf files and enable it for ssh, then restart:

```
[sshd]
enabled = true
service fail2ban restart
Config File
```

The resulting /etc/ssh/sshd\_config file will look like this:

```
Port ***
SyslogFacility AUTH
HostKey /etc/ssh/ssh_host_ed25519_key
HostKey /etc/ssh/ssh_host_rsa_key
KexAlgorithms curve25519-sha256@libssh.org
Ciphers chacha20-poly1305@openssh.com
MACs hmac-sha2-512-etm@openssh.com
GSSAPIAuthentication no
LogLevel VERBOSE
PermitRootLogin no
MaxAuthTries 5
IgnoreRhosts yes
PasswordAuthentication no
PermitEmptyPasswords no
UsePAM yes
ChallengeResponseAuthentication yes
X11Forwarding no
PrintMotd no
ClientAliveInterval 600
ClientAliveCountMax 3
PrintLastLog yes
TCPKeepAlive yes
UseDNS yes
AcceptEnv LANG LC_*
Subsystem sftp /usr/lib/ssh/sftp-server -f AUTHPRIV -l INFO
AllowUsers ***
AuthenticationMethods publickey,keyboard-interactive
```



## Operating System Compliance and Vulnerability Scans

There are two open source tools currently available that will ensure a secure system setup and identify any areas of weakness for further hardening. These tools are OpenScapand Lynis. We begin by installing OpenSCAP. Since we\'re working from the command line, we\'re going to only install the OpenSCAP base (which is a command line-only tool):

```
~$ sudo apt-get install libopenscap8 -y
```

Next we download the OVAL definitions specific to our OS that the OpenSCAP command will use for the audit:

```
~$ wget https://people.canonical.com/~ubuntu-security/oval/com.ubuntu.xenial.cve.oval.xml
```

Once this is completed we can run the audit:

```
~$ oscap oval eval --results /tmp/oscap_results.xml --report /tmp/oscap_report.html com.ubuntu.xenial.cve.oval.xml
```

** If we open the resulting html file it will highlight any areas of concern in red. 

To install Lynis we need to clone the repo from their website as the package installation will be out of date:

```
~$ git clone https://github.com/CISOfy/Lynis
```

Once completed we can audit the system:

```
~$ cd Lynis; ./lynis audit system
```

 

## Remote Monitoring


Remote monitoring of the server requires a combination of Wazuh and Osquery (Wazuh is an open-source intrusion detection system and Osquery is an endpoint threat hunting and incident response tool). The Wazuh server decodes and analyzes incoming information and passes the results along to an Elasticsearch cluster for indexing and storage. The agent/server authentication method is certificate based.

***Wazuh*** uses Elastic stack as a backend, which reads, parses, indexes and stores data generated by the Wazuh manager. The Wazuh agent collects system and Osquery logs, and proactively detects intrusions. The collected information is sent to the Wazuh manger using the ossec-remoted protocol, which encrypts data between the agent and the server. The Wazuh server (deployed on the internet) runs the Wazuh manager and API which collects and analysis data from the deployed agents. The server instance is deployed as a docker instance.

***Osquery*** is deployed on the Monero server and configured to work with Wazuh. All data from the Osquery logs are collected by the Wazuh agent (every 30 minutes) and gets pushed to the Wazuh manager for analysis. Osquery exposes an operating system as a relational database, which makes it easier to write and use basic SQL commands to search the operating system data. The basic architecture looks as such:

The Wazuh agent use the OSSEC message protocol to send collected events to the Wazuh server over port 1514 (UDP or TCP). The Wazuh server then decodes and rule-checks the received events with the analysis engine. Events that trip a rule are augmented with alert data such as rule id and rule name. Events can be spooled to one or both of the following files, depending on whether or not a rule is tripped:

1. The file /var/ossec/logs/archives/archives.json contains all events whether they tripped a rule or not.

2. The file /var/ossec/logs/alerts/alerts.json contains only events that tripped a rule.


\* The Wazuh message protocol uses AES encryption with 128 bits per block and 256-bit keys.

### Wazuh / Elastic Communication

Wazuh server uses Filebeat to send alert and event data to Elasticsearch server using TLS encryption. Filebeat formats the incoming data and optionally enriches it with GeoIP information before sending it to Elasticsearch (port 9200/TCP). Once the data is indexed into Elasticsearch, Kibana (port 5601/TCP) is used to mine and visualize the information.

The Wazuh App runs inside Kibana constantly querying the RESTful API (port 55000/TCP on the Wazuh manager) in order to display configuration and status related information of the server and agents, as well to restart agents when desired. This communication is encrypted with TLS and authenticated with username and password.

### Wazuh Server Installation

Firstly, we install docker and docker compose.

```
~$ curl -sSL https://get.docker.com/ | sh
```

Then we add our user to the docker group and add the execute permission.

```
~$ usermod -aG docker $USER

~$ chmod +x /usr/local/bin/docker-compose
```

Elastic stack can use a fair amount of memory when in use. The default memory allocation is insufficient and we need to increase this.

```
~$ sysctl -w vm.max_map_count**=**262144
```

We're ready to download the Wazuh docker compose file and start the Wazuh server components.

```
~$ curl -sSL https://get.docker.com/ | sh

~$ curl -L "https://github.com/docker/compose/releases/download/{ver}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
```

If we run a *netstat -plunt* the following ports should be exposed after a successful installation:

------- -----------------------------
```
  1514    Wazuh UDP
  1515    Wazuh TCP
  514     Wazuh UDP
  55000   Wazuh API
  5000    Logstash TCP input
  9200    Elasticsearch HTTP
  9300    Elasticsearch TCP transport
  5601    Kibana
  80      Nginx http
  443     Nginx https
```


------- -----------------------------

### Wazuh Agent Installation

Download the latest package from the Wazuh download site and install it.

```
~$ wget https://packages.wazuh.com/x.x/osx/wazuh-agent-{ver}.pkg

~$ installer -pkg wazuh-agent-{ver}.pkg -target /
```

Once installed the agent files will be located at the following locations /Library/Ossec/

### Connecting the Agent

We need to create a certificate in order for the agent to authenticate with the server.

```
~$ openssl req -x509 -batch -nodes -days 365 -newkey rsa:2048 -out 

~$ /var/ossec/etc/sslmanager.cert -keyout /var/ossec/etc/sslmanager.key
```

And then issue and sign the certificate for the agent.

```
~$ openssl req -new -nodes -newkey rsa:2048 -keyout sslagent.key -out sslagent.csr -batch

~$ openssl x509 -req -days 365 -in sslagent.csr -CA rootCA.pem -CAkey rootCA.key -out sslagent.cert -CAcreateserial
```

Copy the CA key to the /var/ossec/etc folder on the Wazuh server and start the service.

```
~$ cp rootCA.pem /var/ossec/etc

~$ /var/ossec/bin/ossec-authd -v /var/ossec/etc/rootCA.pem
```

Distribute the keys to the agent and connect to the Wazuh manager

```
~$ cp sslagent.cert sslagent.key /var/ossec/etc

~$ /var/ossec/bin/agent-auth -m {ip} -x 

~$ /var/ossec/etc/sslagent.cert -k /var/ossec/etc/sslagent.key
```

To test, logging into the interface and check how many clients are connected to the manager. As it the service listens locally access to the Wazuh management interface can only be accessed through a SSH tunnel.
