from copy import deepcopy
from ansible_collections.sparklingtide.yandex_cloud.plugins.module_utils.yc import response_error_check, YC
from google.protobuf.json_format import MessageToDict
from yandex.cloud.resourcemanager.v1.folder_service_pb2 import CreateFolderRequest, GetFolderRequest, DeleteFolderRequest, ListFoldersRequest
from yandex.cloud.resourcemanager.v1.folder_service_pb2_grpc import FolderServiceStub

import traceback


def folder_info_argument_spec():
    return dict(
        name=dict(type="str", required=True),
        cloud_id=dict(type="str", required=False),
    )

class YccFolderInfo(YC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.folder_service = self.sdk.client(FolderServiceStub)
    
    def _translate(self):
        params = dict()
        for key in self.params:
            if key == "cloud_id" or key == "name":
                params[key] = self.params[key]

        return params

    def get_info(self):
        spec = self._translate()
        folders = MessageToDict(self.folder_service.List(ListFoldersRequest(
            cloud_id=spec["cloud_id"], filter="name = \"{}\"".format(spec["name"]))))
        try:
            return folders["folders"][0]
        except IndexError:
            return dict()

def main():
    argument_spec = folder_info_argument_spec()
    module = YccFolderInfo(
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