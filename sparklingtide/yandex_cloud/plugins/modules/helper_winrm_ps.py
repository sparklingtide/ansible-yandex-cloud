from copy import deepcopy
from ansible_collections.sparklingtide.yandex_cloud.plugins.module_utils.yc import response_error_check, YC
from google.protobuf.json_format import MessageToDict
from ansible.module_utils.basic import AnsibleModule

import winrm
import traceback


def vpc_argument_spec():
    return dict(
        url=dict(type="str", required=True),
        user=dict(type="str", required=True),
        password=dict(type="str", required=True),
        script=dict(type="str", required=True),
        state=dict(choices=["present", "absent"], required=False),
    )

class HelperWinRMPs(AnsibleModule):
    def _translate(self):
        params = dict()
        for key in self.params:
            if key in ("url", "script", "user", "password"):
                params[key] = self.params[key]

        return params

    def run_script(self):
        spec = self._translate()
        session = winrm.Session(spec["url"], auth=(spec["user"], spec["password"]), server_cert_validation='ignore', transport='ntlm')
        r = session.run_ps(spec["script"])
        return {
            "std_out": r.std_out,
            "status_code": r.status_code,
            "std_err": r.std_err
        }

def main():
    argument_spec = vpc_argument_spec()
    module = HelperWinRMPs(
        argument_spec=argument_spec,
    )
    response = dict()
    # if the user is working with this module in only check mode we do not
    # want to make any changes to the environment, just return the current
    # state with no modifications

    try:
        response = module.run_script()

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