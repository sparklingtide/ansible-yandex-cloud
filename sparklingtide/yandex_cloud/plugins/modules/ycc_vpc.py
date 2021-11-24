from copy import deepcopy
from ansible_collections.sparklingtide.yandex_cloud.plugins.module_utils.yc import response_error_check, YC
from google.protobuf.json_format import MessageToDict
from yandex.cloud.vpc.v1.network_service_pb2_grpc import NetworkServiceStub
from yandex.cloud.vpc.v1.network_service_pb2 import CreateNetworkRequest, ListNetworksRequest, DeleteNetworkRequest
import traceback


def vpc_argument_spec():
    return dict(
        name=dict(type="str", required=True),
        folder_id=dict(type="str", required=True),
        state=dict(choices=["present", "absent"], required=False),
    )

class YccVPC(YC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.network_service = self.sdk.client(NetworkServiceStub)
    
    def _translate(self):
        params = dict()
        for key in self.params:
            if key == "folder_id" or key == "name":
                params[key] = self.params[key]

        return params

    def _list_by_name(self, folder_id, name):
        networks = self.network_service.List(ListNetworksRequest(folder_id=folder_id, filter='name="%s"' % name))
        return MessageToDict(networks)

    def _get_network(self, name, folder_id):
        networks = self._list_by_name(name, folder_id)    
        return networks.get("networks", (None,))[0]


    def add_vpc(self):
        response = dict()
        spec = self._translate()
        vpc = self._get_network(spec["folder_id"], spec["name"])
        if not vpc:
            cloud_response = self.waiter(self.network_service.Create(CreateNetworkRequest(**spec)))
            response.update(MessageToDict(cloud_response))
            response = response_error_check(response)
        else:
            response = vpc       
        return response
    
    def delete_vpc(self):
        response = dict()
        spec = self._translate()
        networks = self.network_service.List(ListNetworksRequest(folder_id=spec["folder_id"], filter="name = \"{}\"".format(spec["name"])))
        network_id = networks.networks[0].id
        cloud_response = self.waiter(self.network_service.Delete(DeleteNetworkRequest(network_id=network_id)))
        response.update(MessageToDict(cloud_response))
        response = response_error_check(response)       
        return response

    def manage_states(self):
        sw = {
            "present": self.add_vpc,
            "absent": self.delete_vpc,
        }
        return sw[self.params.get("state")]()

def main():
    argument_spec = vpc_argument_spec()
    module = YccVPC(
        argument_spec=argument_spec,
    )
    response = dict()
    # if the user is working with this module in only check mode we do not
    # want to make any changes to the environment, just return the current
    # state with no modifications

    try:
        if module.params.get("state"):
            response = module.manage_states()
        else:
            raise Exception("One of the state/operation should be provided.")

    except Exception as error:  # pylint: disable=broad-except
        if hasattr(error, "details"):
            response["msg"] = getattr(error, "details")()
            response["exception"] = traceback.format_exc()
        else:
            response["msg"] = "Error during runtime occurred"
            response["exception"] = traceback.format_exc()
        module.fail_json(**response)

    module.exit_json(**response)


if __name__ == "__main__":
    main()