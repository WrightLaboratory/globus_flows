#! /usr/bin/env python
import argparse
import os
import sys
import yaml

import json
import logging
import logging.config
import structlog

from shutil import copy as cp
from pathlib import Path


from jinja2 import Environment, FileSystemLoader


DEFAULT_CONIFG_DIR = Path(os.path.expanduser("~/.config"))
GLOBUS_CONFIG_DIR = DEFAULT_CONIFG_DIR.joinpath('globus')
MYFLOW_CONFIG_DIR = GLOBUS_CONFIG_DIR.joinpath('flow')

MYFLOW_CONFIG_FILE = MYFLOW_CONFIG_DIR.joinpath('.flow.yaml')
LOGGING_CONFIG_FILE = MYFLOW_CONFIG_DIR.joinpath('.logging.yaml')


__CONFIGS__ = {
    'client_name' : os.getenv('GLOBUS_CLIENT_NAME', ''),
    'client_id' : os.getenv('GLOBUS_CLIENT_ID', ''),
    'subscription_id' : os.getenv('GLOBUS_SUBSCRIPTION_ID', ''),
    'token_store' :  os.getenv('GLOBUS_DEFAULT_TOKEN_STORE', ''),
    'flow_id' : os.getenv('GLOBUS_FLOW_ID', ''),
    'source_endpoint_id' : os.getenv('GLOBUS_LOCAL_ID', ''),
    'source_base_path' : os.getenv('GLOBUS_SRC_BASEPATH', ''),
    'destination_endpoint_id' : os.getenv('GLOBUS_REMOTE_ID', ''),
    'destination_base_path' : os.getenv('GLOBUS_DST_BASEPATH', '')
}


def export(config_file: 'str|Path'=None, template_file: 'str'=None, configs: 'dict'=None) -> None:
    # Default Values
    config_file = config_file if config_file is not None else MYFLOW_CONFIG_FILE
    template_file = template_file if template_file is not None else 'conf/flow.yaml.j2'
    configs = configs if configs is not None else __CONFIGS__
    
    p = Path(template_file).absolute()
    environment = Environment(loader=FileSystemLoader(p.parent))
    template = environment.get_template(p.name)
    cfg = template.render(configs)
    with open(config_file, mode='w', encoding='utf-8') as stream:
        stream.write(cfg)
    return


for p in [GLOBUS_CONFIG_DIR, MYFLOW_CONFIG_DIR]:
    if not p.exists():
        os.makedirs(p)


if not (f := LOGGING_CONFIG_FILE).exists():
    cp(Path('conf/logging.yaml'), f)


if not (f := MYFLOW_CONFIG_FILE).exists():
    # Render flow configuration file with values from the environment or set them to None
    # Users may edit the resulting config file
    export()


LOGGING_CONFIG = {}
with open(LOGGING_CONFIG_FILE, 'r') as stream:
    LOGGING_CONFIG = yaml.safe_load(stream)

GLOBUS_CONFIG = {}
with open(MYFLOW_CONFIG_FILE, 'r') as stream:
    GLOBUS_CONFIG = yaml.safe_load(stream)

# Override with values from environment

# Logging level
if (setting := os.getenv('LOGLEVEL')) is not None:
    setting = setting.upper()
    setting = setting if setting in ['INFO', 'DEBUG', 'WARNING', 'ERROR', 'CRITICAL'] else 'INFO'
    LOGGING_CONFIG['root']['level'] = setting

# Globus
if (setting := os.getenv('GLOBUS_CLIENT_NAME')) is not None:
    GLOBUS_CONFIG['native_app']['name'] = setting

if (setting := os.getenv('GLOBUS_SUBSCRIPTION_ID')) is not None:
    GLOBUS_CONFIG['subscription']['id'] = setting

if (setting := os.getenv('GLOBUS_CLIENT_ID')) is not None:
    GLOBUS_CONFIG['native_app']['id'] = setting

if (setting := os.getenv('GLOBUS_DEFAULT_TOKEN_STORE')) is not None:
    GLOBUS_CONFIG['token_store'] = setting

# Globus Flow Settings
if (setting := os.getenv('GLOBUS_FLOW_ID')) is not None:
    GLOBUS_CONFIG['flow']['id'] = setting

# Globus Flow tasks

# Globus transfer_files action input values
if (setting := os.getenv('GLOBUS_LOCAL_ID')) is not None:
    GLOBUS_CONFIG['flow']['input']['source']['id'] = setting

if (setting := os.getenv('GLOBUS_SRC_BASEPATH')) is not None:
    GLOBUS_CONFIG['flow']['input']['source']['path'] = setting

if (setting := os.getenv('GLOBUS_REMOTE_ID')) is not None:
    GLOBUS_CONFIG['flow']['input']['destination']['id'] = setting

if (setting := os.getenv('GLOBUS_DST_BASEPATH')) is not None:
    GLOBUS_CONFIG['flow']['input']['destination']['path'] = setting

# Initilialize logger

# Expand any ~ components in path
if not (logfile := Path(LOGGING_CONFIG['handlers']['file']['filename']).expanduser()).parent.exists():
    logfile.parent.mkdir(parents=True)
LOGGING_CONFIG['handlers']['file']['filename'] = str(Path(logfile))

logging.config.dictConfig(LOGGING_CONFIG)

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        #YYYY-MM-DD'T'HH:mm:ssZ
        structlog.processors.TimeStamper(fmt="%Y-%m-%dT%H:%M:%SZ"),
        structlog.stdlib.render_to_log_kwargs
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

LOGGER = structlog.get_logger()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--export-to-file", help="File path to export environment configuration")
    args = parser.parse_args()

    try:
        if (f := args.export_to_file) is not None:
            p = Path(f).expanduser().absolute()
            export(config_file=p)
        sys.exit(0)
    except IOError as e:
        #LOGGER.error(f"{e.code} {e.message}")
        LOGGER.error(f"{e.text}")
        sys.exit(1)

if __name__ == "__main__":
    main()