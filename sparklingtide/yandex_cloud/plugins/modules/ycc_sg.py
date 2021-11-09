from copy import deepcopy
from ansible_collections.sparklingtide.yandex_cloud.plugins.module_utils.yc import response_error_check, YC
from google.protobuf.json_format import MessageToDict
from yandex.cloud.vpc.v1.security_group_service_pb2 import CreateSecurityGroupRequest, DeleteSecurityGroupRequest, \
     UpdateSecurityGroupRuleRequest, UpdateSecurityGroupRulesRequest, ListSecurityGroupsRequest
from yandex.cloud.vpc.v1.security_group_service_pb2_grpc import SecurityGroupServiceStub

import traceback


def sg_argument_spec():
    return dict(
        name=dict(type="str", required=True),
        folder_id=dict(type="str", required=True),
        state=dict(choices=["present", "absent"], required=False),
    )

class YccSG(YC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sg_service = self.sdk.client(SecurityGroupServiceStub)
    
    def _translate(self):
        params = dict()
        for key in self.params:
            if key == "folder_id" or key == "name":
                params[key] = self.params[key]

        return params

    def add_sg(self):
        response = dict()
        spec = self._translate()
        cloud_response = self.waiter(self.sg_service.Create(CreateSecurityGroupRequest(**spec)))
        response.update(MessageToDict(cloud_response))
        response = response_error_check(response)       
        return response
    
    def delete_sg(self):
        response = dict()
        spec = self._translate()
        sgs = self.sg_service.List(ListSecurityGroupsRequest(folder_id=spec["folder_id"], filter="name = \"{}\"".format(spec["name"])))
        sg_id = sgs.networks[0].id
        cloud_response = self.waiter(self.sg_service.Delete(DeleteSecurityGroupRequest(security_group_id=sg_id)))
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
    argument_spec = sg_argument_spec()
    module = YccSG(
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