from copy import deepcopy
from ansible_collections.sparklingtide.yandex_cloud.plugins.module_utils.yc import response_error_check, YC
from google.protobuf.json_format import MessageToDict
from yandex.cloud.vpc.v1.subnet_service_pb2_grpc import SubnetServiceStub
from yandex.cloud.vpc.v1.subnet_service_pb2 import CreateSubnetRequest, ListSubnetsRequest, DeleteSubnetRequest
from yandex.cloud.vpc.v1.subnet_service_pb2 import CreateNetworkRequest, ListNetworksRequest, DeleteNetworkRequest
import traceback


def vpc_subnet_argument_spec():
    return dict(
        name=dict(type="str", required=True),
        folder_id=dict(type="str", required=True),
        network_id=dict(type="str", required=True),
        v4_cidr_blocks=dict(type="list", required=True),
        state=dict(choices=["present", "absent"], required=False),
    )

class YccVPCSubnet(YC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.subnet_service = self.sdk.client(SubnetServiceStub)
    
    def _translate(self):
        params = dict()
        for key in self.params:
            if key in ("folder_id", "network_id", "v4_cidr_blocks", "name"):
                params[key] = self.params[key]

        return params

    def add_subnet(self):
        response = dict()
        spec = self._translate()
        cloud_response = self.waiter(self.subnet_service.Create(CreateSubnetRequest(**spec)))
        response.update(MessageToDict(cloud_response))
        response = response_error_check(response)       
        return response
    
    def delete_subnet(self):
        response = dict()
        spec = self._translate()
        networks = self.subnet_service.List(ListNetworksRequest(folder_id=spec["folder_id"], filter="name = \"{}\"".format(spec["name"])))
        network_id = networks.networks[0].id
        cloud_response = self.waiter(self.subnet_service.Delete(DeleteNetworkRequest(network_id=network_id)))
        response.update(MessageToDict(cloud_response))
        response = response_error_check(response)       
        return response

    def manage_states(self):
        sw = {
            "present": self.add_subnet,
            "absent": self.delete_subnet,
        }
        return sw[self.params.get("state")]()

def main():
    argument_spec = vpc_subnet_argument_spec()
    module = YccVPCSubnet(
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