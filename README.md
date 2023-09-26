# Using Globus Flows

This repository demonstrates how to create Python-based, native applications for interacting with the Globus APIs and for automating tasks using Globus Flows.

It will require the following:

* Python 3.11
* [Globus Python SDK v3](https://globus-sdk-python.readthedocs.io/en/stable/)
* An existing Globus collection to which you have access
* [Globus Connect Personal](https://www.globus.org/globus-connect-personal)


## Install `pyenv` and Python Build Dependencies

### Red Hat(ish) Linux

```bash
# Install pre-reqs

# CentOS 7 and < Fedora 22
sudo yum -y install git make gcc patch \
  zlib-devel bzip2 bzip2-devel \
  readline-devel sqlite sqlite-devel \
  openssl-devel tk-devel libffi-devel \
  xz-devel libuuid-devel gdbm-devel \
  libnsl2-devel

# > Fedora 22
sudo dnf -y install git make gcc patch \
  zlib-devel bzip2 bzip2-devel \
  readline-devel sqlite sqlite-devel \
  openssl-devel tk-devel libffi-devel \
  xz-devel libuuid-devel gdbm-devel \
  libnsl2-devel

# AlmaLinux 8
sudo dnf -y config-manager --set-enabled powertools
sudo yum -y install git make gcc patch \
  zlib-devel bzip2 bzip2-devel \
  readline-devel sqlite sqlite-devel \
  openssl-devel tk-devel libffi-devel \
  xz-devel libuuid-devel gdbm-devel \
  libnsl2-devel

# AlmaLinux 9
sudo dnf -y config-manager --set-enabled crb
sudo yum -y install git make gcc patch \
  zlib-devel bzip2 bzip2-devel \
  readline-devel sqlite sqlite-devel \
  openssl-devel tk-devel libffi-devel \
  xz-devel libuuid-devel gdbm-devel \
  libnsl2-devel

# Install pyenv in your home folder
git clone https://github.com/pyenv/pyenv.git ~/.pyenv

pushd ~/.pyenv && src/configure && make -C src
popd
```

### OSX via HomeBrew

```zsh
brew update
brew install pyenv

brew install openssl readline sqlite3 xz zlib tcl-tk
```

## Configure Shell

### Linux

```bash
target=${HOME}/.bashrc

echo 'export PYENV_ROOT="$HOME/.pyenv"' >> "$target"
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> "$target"
echo 'eval "$(pyenv init -)"' >> "$target"
```

If your `${HOME}/.bash_profile` script does not source `${HOME}/.bashrc`, add the previous lines to it by `target=${HOME}/.bash_profile` and repeat execution of the `echo` commands above.

Make pyenv available by executing:

```bash
source ${HOME}/.bashrc
```

### OSX and Zsh

Newer versions of OSX use Zsh instead of Bash. OSX uses `.zprofile` for both new Terminal windows and shells invoked from an existing Terminal window.

```zsh
target=${HOME}/.zprofile

echo 'export PYENV_ROOT="$HOME/.pyenv"' >> "$target"
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> "$target"
echo 'eval "$(pyenv init -)"' >> "$target"

source "$target"
```

## Install Globus Connect Personal and Commandline

Download and install the [Globus Connect Personal](https://www.globus.org/globus-connect-personal) appropriate for your OS.

The command line tool `globus` is available as a `pipx` package.
First, install [`pipx`](https://pypa.github.io/pipx/).
Then, install the `globus` command line tool using these [directions](https://docs.globus.org/cli/#installation).

N.B., alternatively, you may install the `pipx` package into the Python virtual environment you create and activate in the next section.

## Fetch File Transfer Code

```bash
git clone git@github.com:WrightLaboratory/dt5202_DataTransfer.git

git fetch origin

# If using development code, create new local dev branch based on the remote dev
git switch -c dev origin/dev
```

## Running Code

### Create New Python Virtual Environment

```bash

cd dt5202_DataTransfer

# Build Install Python 3.x.x
pyenv install $(cat ./.python-version)

# Create Python virtual environment
python -m venv ./.venv

# Activate virtual enviroment
source ./.venv/bin/activate

# Install module dependencies into virtual environment
pip install -U pip
pip install -r requirements.txt

```

---

### Special Note for PyYAML Package

There is a bug for installing PyYAML.
You must build and cache PyYAML constrained to `Cython < 3.0`, prior to running `pip install -r requirements.txt`.
The workaround is detailed in [#736](https://github.com/yaml/pyyaml/issues/736):

```bash
# create a constraint file that limits the Cython version to one that should work
echo 'Cython < 3.0' > /tmp/constraint.txt

# seed pip's local wheel cache with a PyYAML wheel
pip wheel -c /tmp/constraint.txt -w ${HOME}/.cache/pip PyYAML


# install PyYAML itself, or any other package(s) that ask for the PyYAML version you just built
pip install ${HOME}/.cache/pip/PyYAML*.whl
```

---

## Deploying and Managing Globus Flows

We will be using a Python-based Globus native application, `manage_flow.py`, to deploy and manage our flows.
The code is based on the [Create and Delete Hello World Flow](https://globus-sdk-python.readthedocs.io/en/stable/examples/create_and_run_flow/index.html#create-and-delete-hello-world-flow) example given in the [Globus SDK for Python](https://globus-sdk-python.readthedocs.io/en/stable/index.html).
It replaces the `deploy_flow.py` script provided in [globus-flows-trigger-examples](https://github.com/globus/globus-flows-trigger-examples), which used the deprecated `globus_automate_client` package.

It should be noted that this script duplicates the functionality given in `globus flows` cli.
This script is included to demonstrate how a python native app is created.
It forms the basis of the `trigger_transfer_flow.py` script in the following section.

First we must populate the environment with values that will be needed to login and authorize `manage_flows.py`:

```bash
export GLOBUS_SUBSCRIPTION_ID="< UUID_FROM_ADMIN >"
export GLOBUS_CLIENT_NAME="< CLIENT_NAME_REGISTERED_TO_APP >"
export GLOBUS_CLIENT_ID="<  CLIENT_ID_REGISTERED_TO_APP >"
export GLOBUS_DEFAULT_TOKEN_STORE="~/.config/globus/.sdk-flow.json"
```

Next, we can run `manage_flow.py`.

```bash
chmod +x ./manage_flow.py

./manage_flow.py list
```

This will present you with a login URL:

```bash
Please go to this URL and login:

https://auth.globus.org/v2/oauth2/authorize?client_id=< client_uuid >&redirect_uri=https%3A%2F%2Fauth.globus.org%2Fv2%2Fweb%2Fauth-code&scope=https%3A%2F%2Fauth.globus.org%2Fscopes%2< scopes_uuid >%2Fmanage_flows&state=_default&response_type=code&code_challenge=< code_challenge>&code_challenge_method=S256&access_type=offline

Please enter the code here: 
```

Since we do not have any flows deployed, we should expect the following output:

```bash
+---------+-------+
| flow_id | title |
+---------+-------+
+---------+-------+
```

You may get help for the script at any time:

```bash
./manage_flow.py --help
usage: manage_flow.py [-h] [-f FLOW_ID] [-t TITLE] [-d FLOW_DEFINITION] [-s INPUT_SCHEMA] {create,delete,list}

positional arguments:
  {create,delete,list}

options:
  -h, --help            show this help message and exit
  -f FLOW_ID, --flow-id FLOW_ID
                        Flow ID for delete
  -t TITLE, --title TITLE
                        Name for create
  -d FLOW_DEFINITION, --flow-definition FLOW_DEFINITION
                        JSON file or inline JSON definition to create flow
  -s INPUT_SCHEMA, --input-schema INPUT_SCHEMA
                        JSON file or inline JSON input schema to create flow
```

## Example File Transfer Flow

This code has been adapted from the example provided at [d](https://globus.net).

It watches the specified folder for changes (in this case, the creation of a new file) and triggers execution of a Globus Flow to transfer the file to a Globus guest collection.

### Deploy File Transfer Flow

This flow is defined in `./flows/transfer_flow_definition.json`.
Its accompanying `transfer_flow_input_schema.json`, contains information used by the Globus API to validate input parameters to the flow and to display help when the flow is invoked interactively at in the Globus [Flows](https://app.globus.org/flows/library) page.

Deploy the flow:

```bash
./manage_flow.py create --title 'Transfer Flow Demo' \
  -d ./flows/transfer_flow_definition.json \
  -s ./flows/transfer_flow_input_schema.json
```

This will result in the following log entries emitted to standard output:

```bash
{"message": "Creating flow: Transfer Flow Demo", "logger": "__main__", "level": "info", "timestamp": "2023-09-25T15:42:56Z"}
{"message": "Created flow id: 01234567-0123-0123-0123-01234567abcef", "logger": "__main__", "level": "info", "timestamp": "2023-09-25T15:42:58Z"}
```

Take note of the `flow id` value.
(This will differ for your particular invocation of `manage_flow.py`)
Export it to your environment:

```bash
# This will differ for your particular invocation
export GLOBUS_FLOW_ID="01234567-0123-0123-0123-01234567abcef"
```

### Configure Globus Transfer Trigger (`trigger_transfer_flow.py`)

```bash
export GLOBUS_LOCAL_ID="$(globus endpoint local-id)"
export GLOBUS_REMOTE_ID="< UUID_FROM_ADMIN >"
export GLOBUS_SRC_BASEPATH="< /path/to/watched/folder/ >"
export GLOBUS_DST_BASEPATH="< /basepath/ >"
```

Obtain the UUID of the Globus guest collection from the adminstrator of the guest collection.
This will be the `destination_endpoint_id`.

N.B., if you are satisfied with your current environment settings you may cache them by executing the following:

```bash
python settings.py -e ~/.config/globus/flow/.flow.yaml 
```

`manage_flow.py` and `transfer_flow.py` will load these settings upon launch.
You also may override the settings in `~/.config/globus/flow/.flow.yaml` with any of the `export` commands in the previous sections.

### Initialize Watcher

```bash
mkdir -p "${HOME}/instrument_data"
python ./trigger_transfer_flow.py --watchdir "${HOME}/instrument_data"
```

### Simulate Data Acquisition

Open another terminal.
Create a new data file.

```bash
tee "${HOME}/instrument_data/$(date +%s).txt"<<'EOF'
"x","y"
0,0
1,1
2,4
3,9
EOF
```
