#!/usr/bin/env python

import argparse
import globus_sdk
import os

# This could go into a different file and be invoked without the file watcher
from globus_sdk.tokenstorage import SimpleJSONFileAdapter
from watch import FileTrigger, translate_local_path_to_globus_path

from settings import LOGGER, GLOBUS_CONFIG


SUBSCRIPTION_ID = GLOBUS_CONFIG['subscription']['id']
NATIVE_APP_CLIENT_ID = GLOBUS_CONFIG['native_app']['id']
DEFAULT_TOKEN_STORE=GLOBUS_CONFIG['token_store']

FLOW_ID = GLOBUS_CONFIG['flow']['id']
RESOURCE_SERVER = globus_sdk.FlowsClient.resource_server


def do_login_flow(native_client, scopes):
    native_client.oauth2_start_flow(requested_scopes=scopes, refresh_tokens=True)
    authorize_url = native_client.oauth2_get_authorize_url()
    print(f"Please go to this URL and login:\n\n{authorize_url}\n")
    auth_code = input("Please enter the code here: ").strip()
    tokens = native_client.oauth2_exchange_code_for_tokens(auth_code)
    return tokens


def get_authorizer(native_client, resource_server, scopes, file_adapter):
    # try to load the tokens from the file, possibly returning None
    if file_adapter.file_exists():
        tokens = file_adapter.get_token_data(resource_server)
    else:
        tokens = None

    if tokens is None:
        # do a login flow, getting back initial tokens
        response = do_login_flow(native_client=native_client, scopes=scopes)
        # now store the tokens and pull out the correct token
        file_adapter.store(response)
        tokens = response.by_resource_server[resource_server]

    return globus_sdk.RefreshTokenAuthorizer(
        tokens["refresh_token"],
        native_client,
        access_token=tokens["access_token"],
        expires_at=tokens["expires_at_seconds"],
        on_refresh=file_adapter.on_refresh,
    )


def run_flow(event_file):
    flow_label = f"Trigger transfer: {os.path.basename(event_file)}" if (l := GLOBUS_CONFIG['flow']['label']) is None else l

    # source_id = GLOBUS_CONFIG['flow']['input']['source']['id']
    # destination_id = GLOBUS_CONFIG['flow']['input']['destination']['id']
    destination_base_path = f"/{FLOW_ID.split('-')[0]}/" if (p := GLOBUS_CONFIG['flow']['destination_base_path']) is None else p

    # Get the Globus-compatible directory name where the triggering file is stored.
    event_folder = os.path.dirname(event_file)
    source_path = translate_local_path_to_globus_path(event_file)

    # Get name of monitored folder to use as destination path
    # and for setting permissions
    event_folder_name = os.path.basename(event_folder)

    # Add a trailing '/' to meet Transfer requirements for directory transfer
    destination_path = os.path.join(
        destination_base_path, event_folder_name, os.path.basename(event_file))
    # Convert Windows path separators to forward slashes.
    destination_path = destination_path.replace("\\", "/")

    LOGGER.info(f"source_path: {source_path}")
    LOGGER.info(f"destination_path: {destination_path}")

    # Modify initial values read from configuration with watchdog event paths
    # These modified values are not cached in `~/.config/globs/flow/.flow.yaml` configuration file
    GLOBUS_CONFIG['flow']['input']['source']['path'] = source_path
    GLOBUS_CONFIG['flow']['input']['destination']['path'] = destination_path

    # Inputs to the flow
    req_body = {
        "input": GLOBUS_CONFIG['flow']['input']
    }

    response = specific_flow_client.run_flow(
        body=req_body,
        label=flow_label,
        tags=["Trigger_Tutorial"]
    )
    LOGGER.info(f"Transferring {event_file}")
    LOGGER.info(f"View status at https://app.globus.org/runs/{response['run_id']}/logs")


# Parse input arguments
def parse_args():
    parser = argparse.ArgumentParser(
        description="""
        Watch a directory and trigger a simple transfer flow."""
    )
    parser.add_argument(
        "--watchdir",
        type=str,
        default=os.path.abspath(".") if (p := GLOBUS_CONFIG['flow']['input']['source']['path']) is None else p,
        help=f"Directory path to watch. [default: current directory]",
    )
    parser.add_argument(
        "--extensions",
        type=str,
        default="",
        nargs="*",
        help='Filename extension(s) that will trigger the flow. [default: ""]',
    )
    parser.set_defaults(verbose=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # Creates and starts the watcher
    native_client = globus_sdk.NativeAppAuthClient(NATIVE_APP_CLIENT_ID)
    file_adapter = SimpleJSONFileAdapter(
        os.path.abspath(os.path.expanduser(DEFAULT_TOKEN_STORE)))
    flow_scope = globus_sdk.SpecificFlowClient(FLOW_ID).scopes.user

    specific_flow_client = globus_sdk.SpecificFlowClient(
        flow_id=FLOW_ID, authorizer=get_authorizer(
            native_client=native_client,resource_server=FLOW_ID,
            scopes=flow_scope, file_adapter=file_adapter))
    
    trigger = FileTrigger(
        watch_dir=os.path.expanduser(args.watchdir), patterns=args.extensions, FlowRunner=run_flow,)
    trigger.run()

