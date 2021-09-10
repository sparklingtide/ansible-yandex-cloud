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

from plugins.module_utils.yc import YC  # pylint: disable=E0611, E0401
from google.protobuf.json_format import MessageToDict
from grpc import StatusCode
from grpc._channel import _InactiveRpcError
from yandex.cloud.compute.v1.disk_service_pb2 import GetDiskRequest
from yandex.cloud.compute.v1.disk_service_pb2_grpc import DiskServiceStub

DISK_OPERATIONS = ["get_info"]


def disk_argument_spec():
    return dict(
        id=dict(type="str", required=True),
        operation=dict(choices=DISK_OPERATIONS, required=True),
    )


class YccDisk(YC):
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
    argument_spec = disk_argument_spec()
    module = YccDisk(argument_spec=argument_spec)
    response = dict()

    try:
        if module.params.get("operation"):
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
