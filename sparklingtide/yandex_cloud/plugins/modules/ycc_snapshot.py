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
from typing_extensions import Required

from ansible_collections.sparklingtide.yandex_cloud.plugins.module_utils.yc import YC, response_error_check  # pylint: disable=E0611, E0401
from google.protobuf.json_format import MessageToDict
from grpc import StatusCode
from grpc._channel import _InactiveRpcError
from yandex.cloud.compute.v1.snapshot_service_pb2 import CreateSnapshotRequest, DeleteSnapshotRequest, GetSnapshotRequest, ListSnapshotsRequest
from yandex.cloud.compute.v1.snapshot_service_pb2_grpc import SnapshotServiceStub

DISK_OPERATIONS = ["get_info"]


def disk_argument_spec():
    return dict(
        state=dict(choices=["present", "absent"], required=False),
        name=dict(type="str", required=True),
        folder_id=dict(type="str", required=True),
        disk_id=dict(type="str", required=True),
        zone_id=dict(type="str", required=True),
        operation=dict(choices=DISK_OPERATIONS, required=False),
    )


class YccSnapshot(YC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.snapshot_service = self.sdk.client(SnapshotServiceStub)

    def _get_snapshot(self, snapshot_id):
        try:
            return MessageToDict(self.disk_service.Get(GetSnapshotRequest(snapshot_id=snapshot_id)))
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

    def add_snapshot(self):
        response = dict()
        spec = self._translate()
        cloud_response = self.waiter(self.snapshot_service.Create(CreateSnapshotRequest(**spec)))
        response.update(MessageToDict(cloud_response))
        response = response_error_check(response)       
        return response

    def delete_snapshot(self):
        response = dict()
        spec = self._translate()
        disks = self.snapshot_service.List(ListSnapshotsRequest(folder_id=spec["folder_id"], filter="name = \"{}\"".format(spec["name"])))
        disk_id = disks.disks[0].id
        cloud_response = self.waiter(self.snapshot_service.Delete(DeleteSnapshotRequest(disk_id=disk_id)))
        response.update(MessageToDict(cloud_response))
        response = response_error_check(response)       
        return response

    def manage_states(self):
        sw = {
            "present": self.add_snapshot,
            "absent": self.delete_snapshot,
        }
        return sw[self.params.get("state")]()

    def manage_operations(self):  # pylint: disable=inconsistent-return-statements
        operation = self.params.get("operation")

        if operation == "get_info":
            return self.get_info()

    def get_info(self):
        response = dict()
        id = self.params.get("id")
        disk = self._get_snapshot(id)
        if not disk:
            response["msg"] = "No such disk"
            return response
        response["disk"] = disk
        return response


def main():
    argument_spec = disk_argument_spec()
    module = YccSnapshot(argument_spec=argument_spec)
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
