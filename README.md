# Plinux

Cross-platform tool to work with remote Linux OS.

Plinux based on paramiko project. It can establish ssh connection to a remote server, execute command as user or with sudo rights. Plinux returns object with exit code, sent command, stdout/sdtderr response.

## Installation
For most users, the recommended method to install is via pip:
```
pip install plinux
```

## Usage

```
client = Plinux(host='172.16.0.124', username='bobby', password='qawsedrf')
response = client.run_cmd('hostname')
print(response.stdout)  # WebServer
print(response.ok)  # True
```
