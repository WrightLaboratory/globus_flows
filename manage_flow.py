#!/usr/bin/env python
import argparse
import globus_sdk
import json
import os
import sys


from globus_sdk.tokenstorage import SimpleJSONFileAdapter
from pathlib import Path
from tabulate import tabulate

from settings import LOGGER, GLOBUS_CONFIG


SUBSCRIPTION_ID = GLOBUS_CONFIG['subscription']['id']
NATIVE_APP_CLIENT_ID = GLOBUS_CONFIG['native_app']['id']
DEFAULT_TOKEN_STORE=GLOBUS_CONFIG['token_store']


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


def get_flows_client(native_client, resource_server, scopes, file_adapter):
    return globus_sdk.FlowsClient(
        authorizer=get_authorizer(native_client=native_client,resource_server=resource_server,
        scopes=scopes,
        file_adapter=file_adapter))


def create_flow(flows_client,
                title='',
                subtitle='',
                definition={},
                input_schema={}):
    LOGGER.info(f"Creating flow: {title}")
    globus_http_response = flows_client.create_flow(
        title=title,
        definition=definition,
        input_schema=input_schema,
        subtitle=subtitle)
    return globus_http_response


def delete_flow(flows_client, flow_id):
    LOGGER.info(f'Deleting flow id: {flow_id}')
    globus_http_response = flows_client.delete_flow(flow_id)
    return globus_http_response 


def list_flows(flows_client):
    globus_http_response = flows_client.list_flows(filter_role="flow_owner")
    return globus_http_response


def dict_from(json_str_or_file:'str'='') -> 'dict':
    try:
        if (p := Path(json_str_or_file)).is_file():
            with open(p, 'r') as stream:
                return json.load(stream)
    except:
        LOGGER.error(f'Cannot load JSON: {str(json_str_or_file)}')
        return None
    
    try:
        return json.loads(json_str_or_file)
    except:
        LOGGER.error(f'Cannot load JSON: {str(json_str_or_file)}')
        return None



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["create", "delete", "list"])
    parser.add_argument("-f", "--flow-id", help="Flow ID for delete")
    parser.add_argument("-t", "--title", help="Name for create")
    parser.add_argument("-d", "--flow-definition", help="JSON file or inline JSON definition to create flow")
    parser.add_argument("-s", "--input-schema", help="JSON file or inline JSON input schema to create flow")
    args = parser.parse_args()


    try:
        native_client = globus_sdk.NativeAppAuthClient(NATIVE_APP_CLIENT_ID)
        file_adapter = SimpleJSONFileAdapter(
            os.path.abspath(os.path.expanduser(DEFAULT_TOKEN_STORE)))
        
        flow_client_scopes = [globus_sdk.FlowsClient.scopes.manage_flows]
        resource_server = globus_sdk.FlowsClient.resource_server


        fc = get_flows_client(
            native_client=native_client,
            resource_server=resource_server,
            scopes=flow_client_scopes,
            file_adapter=file_adapter)
        
        if (command := args.action) == "create":
            if (t := args.title) is None:
                parser.error("create requires --title")
            if (d := args.flow_definition) is None:
                parser.error("create requires --flow-definition")
            flow_definition = dict_from(json_str_or_file=d)
            input_schema = dict_from(json_str_or_file=args.input_schema)
            LOGGER.debug(f"flow definition: {flow_definition}")
            LOGGER.debug(f"flow input schema: {input_schema}")
            response = create_flow(
                flows_client=fc, title=t, definition=flow_definition,
                input_schema=input_schema)
            if not (d := response.data)['id'] is None:
                LOGGER.info(f"Created flow id: {d['id']}")
        elif command == "delete":
            if (id := args.flow_id) is None:
                parser.error("delete requires --flow-id")
            response = delete_flow(flows_client=fc, flow_id=id)
            if (d := response.data)['DELETED']:
                LOGGER.info(f"Deleted flow id: {d['id']}")
        elif command == "list":
            response = list_flows(fc)
            flows = [ [f['id'], f['title']] for f in response.data['flows']]
            print("\n")
            print(tabulate(tabular_data=flows, headers=['flow_id', 'title'], tablefmt='pretty'))
            print("\n")
        else:
            raise NotImplementedError()
    except globus_sdk.FlowsAPIError as e:
        #LOGGER.error(f"{e.code} {e.message}")
        LOGGER.error(f"{e.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()