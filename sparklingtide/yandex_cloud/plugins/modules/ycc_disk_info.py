#!/usr/bin/python

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

RETURN = """
'disk':
    createdAt: ''
    folderId: ''
    id: ''
    instanceIds: []
    productIds: []
    size: ''
    sourceImageId: ''
    status: ''
    typeId: 'network-hdd'
    zoneId: 'ru-central1-c'
"""

import traceback

from ansible_collections.sparklingtide.yandex_cloud.plugins.module_utils.yc import YC, response_error_check  # pylint: disable=E0611, E0401
from google.protobuf.json_format import MessageToDict
from grpc import StatusCode
from grpc._channel import _InactiveRpcError
from yandex.cloud.compute.v1.disk_service_pb2 import GetDiskRequest, CreateDiskRequest, ListDisksRequest, DeleteDiskRequest
from yandex.cloud.compute.v1.disk_service_pb2_grpc import DiskServiceStub

def disk_info_argument_spec():
    return dict(
        name=dict(type="str", required=True),
        folder_id=dict(type="str", required=True),
    )


class YccDiskInfo(YC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.disk_service = self.sdk.client(DiskServiceStub)

    def _get_disk(self, disk_id):
        try:
            return MessageToDict(self.disk_service.Get(GetDiskRequest(disk_id=disk_id)))
        except _InactiveRpcError as err:
            if err._state.code is StatusCode.INVALID_ARGUMENT:  # pylint: disable=W0212
                return dict()
            else:
                raise err
    
    def _translate(self):
        params = dict()
        for key in self.params:
            if key != "auth" and key != "state" and key != "operation":
                params[key] = self.params[key]

        return params

    def add_disk(self):
        response = dict()
        spec = self._translate()
        cloud_response = self.waiter(self.disk_service.Create(CreateDiskRequest(**spec)))
        response.update(MessageToDict(cloud_response))
        response = response_error_check(response)       
        return response

    def delete_disk(self):
        response = dict()
        spec = self._translate()
        disks = self.disk_service.List(ListDisksRequest(folder_id=spec["folder_id"], filter="name = \"{}\"".format(spec["name"])))
        disk_id = disks.disks[0].id
        cloud_response = self.waiter(self.disk_service.Delete(DeleteDiskRequest(disk_id=disk_id)))
        response.update(MessageToDict(cloud_response))
        response = response_error_check(response)       
        return response

    def manage_states(self):
        sw = {
            "present": self.add_disk,
            "absent": self.delete_disk,
        }
        return sw[self.params.get("state")]()

    def manage_operations(self):  # pylint: disable=inconsistent-return-statements
        operation = self.params.get("operation")

        if operation == "get_info":
            return self.get_info()

    def get_info(self):
        response = dict()
        id = self.params.get("id")
        disk = self._get_disk(id)
        if not disk:
            response["msg"] = "No such disk"
            return response
        response["disk"] = disk
        return response


def main():
    argument_spec = disk_info_argument_spec()
    module = YccDiskInfo(argument_spec=argument_spec)
    response = dict()

    try:
        if module.params.get("state"):
            response = module.manage_states()
        elif module.params.get("operation"):
            response = module.manage_operations()
        else:
            raise Exception("One of the operation should be provided.")

    except Exception as error:  # pylint: disable=broad-except
        if hasattr(error, "details"):
            response["msg"] = getattr(error, "details")()
            response["exception"] = traceback.format_exc()
        else:
            response["msg"] = "Error during runtime ocurred"
            response["exception"] = traceback.format_exc()
        module.fail_json(**response)

    module.exit_json(**response)


if __name__ == "__main__":
    main()
