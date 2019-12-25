import json
import logging
import os
import platform
import socket
import warnings
from dataclasses import dataclass
from subprocess import Popen, PIPE, TimeoutExpired
from typing import Any

from paramiko import SSHClient, ssh_exception, AutoAddPolicy

warnings.filterwarnings(action='ignore', module='.*paramiko.*')


@dataclass
class Logger:
    name: str
    console: bool = True
    file: bool = False
    date_format: str = '%Y-%m-%d %H:%M:%S'
    format: str = '%(asctime)-15s [%(name)s] [LINE:%(lineno)d] [%(levelname)s] %(message)s'

    def __post_init__(self):
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.INFO)
        self.formatter = logging.Formatter(fmt=self.format, datefmt=self.date_format)

        # Console handler with a INFO log level
        if self.console:
            ch = logging.StreamHandler()  # use param stream=sys.stdout for stdout printing
            ch.setLevel(logging.INFO)
            ch.setFormatter(self.formatter)  # Add the formatter
            self.logger.addHandler(ch)  # Add the handlers to the logger

        # File handler which logs debug messages
        if self.file:
            fh = logging.FileHandler(f'{self.name}.log', mode='w')
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(self.formatter)  # Add the formatter
            self.logger.addHandler(fh)  # Add the handlers to the logger


@dataclass()
class ResponseParser:
    """Bash response parser"""

    response: Any

    @property
    def stdout(self) -> list:
        return self.response[1]

    @property
    def stderr(self) -> list:
        return self.response[2]

    @property
    def exited(self) -> int:
        return self.response[0]

    @property
    def ok(self):
        return self.response[0] == 0

    @property
    def command(self):
        return self.response[3]


class Plinux(Logger):
    """Base class to work with linux"""

    _URL = 'https://confluence.starwind.com:8444/display/QA/LinuxTool'

    def __init__(
            self, host, username, password, port: int = 22, logger_enabled: bool = True, *args, **kwargs):
        super().__init__(name=self.__class__.__name__, *args, **kwargs)
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.logger.disabled = not logger_enabled

    def __str__(self):
        return f'Local host: {self.get_current_os_name()}\n' \
               f'Remote IP: {self.host}\n' \
               f'Username: {self.username}\n' \
               f'Password: {self.password}\n' \
               f'Host availability: {self.is_host_available()}\n' \
               f'Credentials are correct: {self.is_credentials_valid()}\n\n' \
               f'RTFM: {Plinux._URL}\n'

    def is_host_available(self, port: int = 0, timeout: int = 5):
        """Check remote host is available using specified port"""

        # return self._client().get_transport().is_active()
        port_ = port or self.port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((self.host, port_))
            return False if result else True

    def list_all_methods(self):
        """Returns all available public methods"""
        return [method for method in dir(self) if not method.startswith('_')]

    def run_cmd_local(self, cmd, timeout=60):
        """Main function to send commands using subprocess

        :param cmd: string, command
        :param timeout: timeout for command
        :return: Decoded response

        """

        with Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE) as process:
            # process.wait(timeout)
            try:
                self.logger.info(f'COMMAND: "{cmd}"')
                stdout, stderr = process.communicate(timeout=timeout)
                data = (stdout + stderr).decode().strip()
                self.logger.info(f'RESULT: "{data}"')
                return data
            except TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                data = stdout + stderr
                return data.decode()

    def _client(self, sftp=False, timeout=15):
        """http://www.paramiko.org/"""

        client = SSHClient()
        client.set_missing_host_key_policy(AutoAddPolicy())

        try:
            client.connect(self.host, username=self.username, password=self.password, timeout=timeout)

            if sftp:
                return client.open_sftp()
            return client
        except ssh_exception.AuthenticationException as e:
            self.logger.error(e.args)
            raise ssh_exception.AuthenticationException
        except ssh_exception.NoValidConnectionsError as e:
            self.logger.error(e.strerror)
            raise ssh_exception.NoValidConnectionsError
        except TimeoutError as e:
            self.logger.error('Timeout exceeded.' + e.strerror)
            raise TimeoutError

    def run_cmd(self, cmd: str, sudo: bool = False, timeout: int = 30) -> ResponseParser:
        """Base method to execute SSH command on remote server

        :param cmd: SSH command
        :param sudo: Execute specified command as sudo user
        :param timeout: Execution timeout
        :return: ResponseParser class
        """

        client = self._client()

        try:
            command = f"sudo -S -p '' -- sh -c '{cmd}'" if sudo else cmd
            self.logger.info(command)

            stdin, stdout, stderr = client.exec_command(command, timeout=timeout)

            if sudo:
                stdin.write(self.password + '\n')
                stdin.flush()

            # Get exit code
            exited = stdout.channel.recv_exit_status()

            # Get STDOUT
            stdout = stdout.read().decode().strip()
            out = stdout if stdout else None
            self.logger.info(f'{exited}: {out}')

            # Get STDERR
            stderr = stderr.read().decode().strip()
            err = stderr if stderr else None
            if err:
                self.logger.error(err)

            response = exited, out, err, command
            return ResponseParser(response)
        finally:
            client.close()

    @staticmethod
    def get_current_os_name():
        return platform.system()

    @property
    def __sudo_cmd(self):
        return f'sudo -S <<< {self.password}'

    def send_cmd(self, cmd: str, sudo: bool = False):
        """Base method to execute SSH command on remote server

        :param cmd: SSH command
        :param sudo: Execute specified command as sudo user
        :return: Decoded command result
        """

        warnings.warn('"send_cmd" is deprecated and will be removed. Use "run_cmd" method instead', DeprecationWarning)

        client = self._client()

        try:
            cmd_ = f'sudo -S <<< "{self.password}" {cmd}' if sudo else cmd

            self.logger.info(f'[{self.host}] [{self.username}@{self.password}] "{cmd_}"')

            stdin, stdout, stderr = client.exec_command(cmd_)
            data = (stdout.read() + stderr.read()).decode().strip()

            self.logger.info(f'[RESULT] "{data}"')

            # pretty print - remove sudo prompt
            sudo_prompt = '[sudo] password for user:'
            if sudo_prompt in data:
                if sudo_prompt == data:
                    return None
                return data.split('[sudo] password for user: ')[1]

            return data
        finally:
            client.close()

    def is_credentials_valid(self):
        try:
            self.run_cmd('whoami')
            return True
        except ssh_exception.AuthenticationException:
            return False

    def get_os_version(self):
        return self.run_cmd('lsb_release -a')

    def get_ip(self):
        return self.run_cmd('hostname -I')

    def get_hostname(self):
        return self.run_cmd('hostname')

    # FIXME
    def change_hostname(self, name):
        cmd = f'{self.__sudo_cmd} -- sh -c "echo {name} > /etc/hostname; hostname -F /etc/hostname"'
        self.run_cmd(cmd)
        cmd = f"""{self.__sudo_cmd} -- sh -c 
        'sed -i "/127.0.1.1.*/d" /etc/hosts; echo "127.0.1.1 {name}" >> /etc/hosts'"""
        return self.run_cmd(cmd)

    def get_date(self):
        return self.run_cmd('date')

    # ---------- Service management ----------
    def get_service(self, name):
        """Get whole service info"""

        return self.run_cmd(f'systemctl status {name}')

    def get_service_status(self, name):
        """Get service status"""
        return self.run_cmd(f'systemctl is-active {name}')

    def stop_service(self, name):
        return self.run_cmd(f'systemctl stop {name}', sudo=True)

    def kill_service(self, name):
        return self.run_cmd(f'systemctl kill {name}', sudo=True)

    def start_service(self, name):
        return self.run_cmd(f'systemctl start {name}', sudo=True)

    def restart_service(self, name):
        return self.run_cmd(f'systemctl restart {name}', sudo=True)

    def get_service_journal(self, name):
        return self.run_cmd(f'journalctl -u {name}', sudo=True)

    def list_active_services(self, no_legend: bool = True, all_services: bool = False):
        """
        List all active services and it's status

        :param no_legend:
        :param all_services: To see loaded but inactive units, too
        :return:
        """

        cmd = 'systemctl list-units -t service'
        if no_legend:
            cmd += ' --no-legend'
        if all_services:
            cmd += ' --all'
        return self.run_cmd(cmd)

    def enable(self, name):
        return self.run_cmd(f'systemctl enable {name}', sudo=True)

    def disable(self, name):
        return self.run_cmd(f'systemctl disable {name}', sudo=True)

    def is_enabled(self, name):
        return self.run_cmd(f'systemctl is-enabled {name}')

    def get_netstat_info(self, params=''):
        """Get netstat info

        Necessary to install net-tool: "yum -y install net-tools"

        :param params: "ltpu" - Active Internet connections (only servers)
        :return:
        """

        cmd_ = 'netstat' if not params else f'netstat -{params}'
        return self.run_cmd(cmd_)

    # ----------- File and directory management ----------
    def check_exists(self, path):
        r"""Check file and directory exists.

        For windows path: specify network path in row format or use escape symbol.
        You must be connected to the remote host.
        Usage: check_exists('\\\\172.16.0.25\\d$\\New Text Document.txt')

        For linux path: linux style path.
        Usage: check_exists('/home/veeam/WebConsole_891_441_1003_2_0_2416.zip')

        :param path: Full path to file/directory
        :return: Bool
        """

        # Linux
        if '/' in path:
            cmd = f'test -e {path}'
            response = self.run_cmd(cmd)
            return response.ok
        # Windows
        elif '\\' in path:
            return os.path.exists(path)
        raise SyntaxError('Incorrect method usage. Check specified path.')

    def cat_file(self, path):
        return self.run_cmd(f'cat {path}')

    def get_json(self, path, pprint: bool = False) -> dict:
        """Read JSON file as string and pretty print it into console"""

        file = self.cat_file(path)
        jsoned = json.loads(file.stdout)
        if pprint:
            print(json.dumps(jsoned, indent=4), sep='')
        return jsoned

    def create_file(self, path):
        return self.run_cmd(f'touch {path}', sudo=True)

    def get_file_permissions(self, path):
        return self.run_cmd(f'stat -c "%A" {path}')

    def get_file_size(self, path):
        """Get file size

        :param path: File path
        :return: size in bytes
        """

        return self.run_cmd(f'stat -c "%s" {path}')

    def grep_line_in_file(self, path, string, directory: bool = False):
        """Grep line in file or directory

        :param path: File/directory path
        :param string: string pattern to grep
        :param directory: If True - grep in directory with files
        :return:
        """

        if directory:
            return self.run_cmd(f'grep -rn "{string}" {path}')
        return self.run_cmd(f'grep -n "{string}" {path}')

    def change_line_in_file(self, path, old, new):
        """Replace line and save file.

        :param path: File path
        :param old: String to replace
        :param new: New string
        :return:
        """

        return self.run_cmd(f'sed -i "s!{old}!{new}!" {path}', sudo=True)

    def delete_line_from_file(self, path, string):
        return self.run_cmd(f"sed -i '/{string}/d' {path}", sudo=True)

    def get_last_file(self, directory='', name=''):
        """Get last modified file in a directory

        :param name: Filename to grep
        :param directory: Directory path to precess. Home by default
        :return:
        """

        directory_ = directory or f'/home/{self.username}'
        cmd = f'ls {directory_} -Art| grep {name} | tail -n 1' if name else f'ls {directory} -Art | tail -n 1'
        return self.run_cmd(cmd)

    def remove(self, path):
        """Remove file(s) and directories

        Usage:\n
        path=/opt/1 remove the directory\n
        path=/opt/1/* remove all file in the directory\n
        path=/opt/1/file.txt remove specified file in the directory\n

        :param path: Path to a file or directory.
        """

        return self.run_cmd(f'for file in {path}; do rm -rf "$file"; done', sudo=True)

    def extract_files(self, src, dst, mode='tar', quite=True):
        """Extract file to specified directory

        :param src: Full path to archive (with extension)
        :param dst:
        :param mode: "tar", "zip"
        :param quite: Suppress list of unpacked files
        :return:
        """

        unzip_cmd = f'unzip -q {src} -d {dst}' if quite else f'unzip {src} -d {dst}'
        tar_cmd = f'tar -xzvf {src}.tar.gz -C {dst}'

        cmd = tar_cmd if mode == 'tar' else unzip_cmd

        return self.run_cmd(cmd)

    def copy_file(self, src, dst):
        """

        :param src:
        :param dst:
        :return:
        """

        return self.run_cmd(f'cp {src} {dst}', sudo=True)

    def get_processes(self):
        return self.run_cmd(f'ps -aux')

    #  ----------- Power management -----------
    def reboot(self):
        return self.run_cmd('shutdown -r now', sudo=True)

    def shutdown(self):
        return self.run_cmd('shutdown -h now', True)

    #  ----------- Directory management -----------
    def create_directory(self, path):
        return self.run_cmd(f'mkdir {path}', sudo=True)

    def list_dir(self, path, params=None):
        """List directory

        :param path: Directory path
        :param params: Additional params. For example: "la"
        :return:
        """

        cmd = f'ls {path} -{params}' if params else f'ls {path}'
        return self.run_cmd(cmd)

    def count_files(self, path):
        return self.run_cmd(f'ls {path} | wc -l')

    #  ----------- File transfer -----------
    def upload(self, local, remote):
        r"""Upload file/dir to the host and check exists after.

        Usage: tool.upload(r'd:\python_tutorial.pdf', '/home/user/python_tutorial.pdf'')

        :param local: Source full path
        :param remote: Destination full path
        :return: bool
        """

        self._client(sftp=True).put(local, remote, confirm=True)
        self.logger.info(f'Uploaded {local} to {remote}')
        return self.exists(remote)

    def download(self, remote, local) -> bool:
        r"""Download a file from the current connection to the local filesystem and check exists after.

        Usage: tool.download('/home/user/python_tutorial.pdf', 'd:\dust\python_tutorial.pdf')

        :param remote: Remote file to download. May be absolute, or relative to the remote working directory.
        :param local: Local path to store downloaded file in, or a file-like object
        :return: bool
        """

        self._client(sftp=True).get(remote, local)
        self.logger.info(f'Downloaded {remote} to {local}')
        return self.exists(local)

    def change_password(self, new_password):
        """Change password

        BEWARE USING! You'll lost connection to a server after completion.

        echo username:new_password | sudo chpasswd

        :param new_password: New password with no complex check.
        :return:
        """

        return self.run_cmd(f'sudo -S <<< {self.password} -- sh -c "echo {self.username}:{new_password} | chpasswd"')

    # ---------- Disk ----------
    def get_disk_usage(self):
        return self.run_cmd('df -h ')

    def get_free_space(self):
        return self.run_cmd('df -h / | tail -n1 | awk "{print $5}"')

    def debug_info(self):
        """Show debug log. Logger must be enabled"""

        self.logger.info('Linux client created.')
        self.logger.info(f'Local host: {self.get_current_os_name()}')
        self.logger.info(f'Remote IP: {self.host}')
        self.logger.info(f'Username: {self.username}')
        self.logger.info(f'Password: {self.password}')
        self.logger.info(f'Available: {self.is_host_available()}')
        self.logger.info(f'Available: {self.is_host_available()}')
        self.logger.info(f'RTFM: {Plinux._URL}')

    # Aliases
    ps = get_processes
    ls = list_dir
    cp = copy_file
    date = get_date
    os = get_os_version
    exists = check_exists
    netstat = get_netstat_info
    start = start_service
    stop = stop_service
    status = get_service_status
    restart = restart_service
    version = get_os_version
    rm = remove
    chpasswd = change_password
    count = count_files