from copy import deepcopy
from typing_extensions import Required
from ansible_collections.sparklingtide.yandex_cloud.plugins.module_utils.yc import response_error_check, YC
from google.protobuf.json_format import MessageToDict
from yandex.cloud.compute.v1.image_service_pb2 import CreateImageRequest, ListImagesRequest, DeleteImageRequest
from yandex.cloud.compute.v1.image_service_pb2_grpc import ImageServiceStub

import traceback


def image_info_argument_spec():
    return dict(
        name=dict(type="str", required=True),
        folder_id=dict(type="str", required=True),
        disk_id=dict(type="str", required=False),
        snapshot_id=dict(type="str", required=False),
        network=dict(type="str", required=False),
        url=dict(type="url", required=False),
        state=dict(choices=["present", "absent"], required=False),
    )

class YccImageInfo(YC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.image_service = self.sdk.client(ImageServiceStub)
    
    def _translate(self):
        params = dict()
        for key in self.params:
            if key not in ('auth', 'state'):
                params[key] = self.params[key]

        return params

    def get_info(self):
        pass
    def add_image(self):
        response = dict()
        spec = self._translate()
        cloud_response = self.waiter(self.image_service.Create(CreateImageRequest(**spec)))
        response.update(MessageToDict(cloud_response))
        response = response_error_check(response)       
        return response
    
    def delete_image(self):
        response = dict()
        spec = self._translate()
        networks = self.image_service.List(ListImagesRequest(folder_id=spec["folder_id"], filter="name = \"{}\"".format(spec["name"])))
        network_id = networks.networks[0].id
        cloud_response = self.waiter(self.image_service.Delete(DeleteImageRequest(image_id=network_id)))
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
    argument_spec = image_info_argument_spec()
    module = YccImageInfo(
        argument_spec=argument_spec,
    )
    response = dict()
    # if the user is working with this module in only check mode we do not
    # want to make any changes to the environment, just return the current
    # state with no modifications

    try:
        response = module.get_info()
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