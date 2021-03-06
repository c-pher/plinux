[![PyPI version](https://badge.fury.io/py/plinux.svg)](https://badge.fury.io/py/plinux)
[![Build Status](https://travis-ci.org/c-pher/plinux.svg?branch=master)](https://travis-ci.org/c-pher/plinux)

# Plinux

Cross-platform tool to work with remote Linux OS.

Plinux based on paramiko project. It can establish ssh connection to a remote server, execute command as user or with sudo rights. Plinux returns object with exit code, sent command, stdout/sdtderr response.

## Installation
For most users, the recommended method to install is via pip:
```cmd
pip install plinux
```
## Import
```python
from plinux import Plinux
```
---
## Usage
#### Command from usual user:
```python
from plinux import Plinux

client = Plinux(host="172.16.0.124", username="bobby", password="qawsedrf")
response = client.run_cmd("hostname")
print(response.stdout)  # WebServer
print(response.ok)  # True
```

#### Command using sudo:
```python
from plinux import Plinux

client = Plinux(host="172.16.0.124", username="bobby", password="qawsedrf", logger_enabled=True)
response = client.run_cmd("systemctl stop myservicename.service", sudo=True)

print(response)  # ResponseParser(response=(0, None, None, "sudo -S -p '' -- sh -c 'systemctl stop myservicename.service'"))
print(response.command)  # sudo -S -p '' -- sh -c 'systemctl stop myservicename.service'
print(response.exited)  # 0
```

#### SFTP usage:
```python
from plinux import Plinux

tool = Plinux(host="ftp.test.local", username="bobby", password="qawsedrf")
sftp = tool.sftp
print(sftp.listdir())
```

#### SQLite3 usage:
```python
from plinux import Plinux

client = Plinux(host="cdn1.test.local", username="bobby", password="qawsedrf")

db_path = '/opt/ProductName/nxdb/StorageConfig.db'
sql = 'select Data from DtoDataContainer'
db = client.sqlite3(db_path, sql).json()
print(db)  # {"Settings1": 1, "Settings2": 2...,"Settings10": 10}
print(db['Setting1'])  # {"Settings1": 1}
```

#### Aliases
Some methods have "human commands" and aliases:

* client.run_cmd("ls /home/bobby")
* client.list_dir("/home/bobby")
* client.ls("/home/bobby")

---

## Changelog
##### 1.1.6 (29.11.2020)
sqlite3 method updated to accept external parameters like "-line -header"

##### 1.1.5 (07.11.2020)
sqlite3 method added

##### 1.1.4 (06.11.2020)
- added 'sftp' property explicitly
- 'cat', 'check_exists', 'get_json' now support sudo usage

##### 1.1.3 (08.08.2020)
get_pid method added

##### 1.1.2 (25.04.2020)
- send_cmd deprecated
- fix password prompt in stderr


##### 1.1.1 (29.03.2020)
get_md5 method added

##### 1.1.0 (19.03.2020)
ResponseParser extended with json()


##### 1.0.9 (28.02.2020)
Log filehandler writes in utf8 from now

##### 1.0.8 (06.02.2020)
get_file_permission extended:
- added faq
- added "human=False" param returns access rights in human readable form otherwise in in octal
- added alias "stat"

##### 1.0.7 (30.01.2020)
- ResponseParser methods notation changed.
    - stdout -> str
    - stderr -> str
    - exited -> int
    - ok -> bool
    - command -> str

##### 1.0.6 (29.01.2020)
- kill_user_session method added

##### 1.0.5 (26.01.2020)
- logging refactored to avoid multiple log entries