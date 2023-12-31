import requests
from ..config.settings import get_settings
from enum import Enum
from ..logging import Logger
from fastapi import HTTPException, status as status_codes


settings = get_settings()
logger = Logger(f"{__package__}.{__name__}")


class Endpoints(str, Enum):
    bvn_verification = "https://api.qoreid.com/v1/ng/identities/bvn-basic"
    nin_verification = "https://api.qoreid.com/v1/ng/identities/nin"
    flutterwave_payments = "https://api.flutterwave.com/v3/payments"
    flutterwave_tx_verification = "https://api.flutterwave.com/v3/transactions"
    flutterwave_get_banks = "https://api.flutterwave.com/v3/banks"
    flutterwave_resolve_bank_account = "https://api.flutterwave.com/v3/accounts/resolve"
    flutterwave_transfers = "https://api.flutterwave.com/v3/transfers"


def handle_response2(ok, status, data, silent=True):
    if not ok:

        if not silent:
            raise HTTPException(500, "External API call failed")

    if not (status >= status_codes.HTTP_200_OK and status < status_codes.HTTP_300_MULTIPLE_CHOICES):

        logger.warn("External API call with unhealthy status - " + str(status))

        if not silent:
            raise HTTPException(500, "External API call error")

        return False

    if status == status_codes.HTTP_401_UNAUTHORIZED:

        logger.warn("External API call with unhealthy status - " + str(status))

        if not silent:
            raise HTTPException(401, "External API call error")

        return False

    return True


def handle_response(ok, status, data, silent=True):
    if not ok:

        if not silent:
            raise HTTPException(500, "External API call failed")

    if not (status >= status_codes.HTTP_200_OK and status < status_codes.HTTP_300_MULTIPLE_CHOICES):

        logger.warn("External API call with unhealthy status - " + str(status))

        if not silent:
            raise HTTPException(500, "External API call error")

        return False

    _api_status = data["status"]

    if _api_status != "success":
        logger.warn("External API call returned no success ")

        if not silent:
            raise HTTPException(500, "External API call error")

        return False

    return True


def make_url(frag, surfix="", skip_base=True):

    base_url = ""

    if skip_base:
        return "{0}{1}".format(frag, surfix)

    return "{0}{1}{2}".format(base_url, frag, surfix)


def make_req(url, method, headers={}, body=None):
    _headers = {
        "accept": "application/json",
        "content-type": "application/json",

    }

    logger.info("Making external API call to " + url + " with method " + method + " and headers " + str(_headers) +
                " and body " + str(body))

    _headers.update(headers)

    response = requests.request(
        method=method, url=url, headers=_headers, json=body)

    status = response.status_code
    ok = response.ok

    if not ok:

        logger.critical("External API Call with url " + url +
                        " Failed with status " + str(status) + " and details " + response.text)

        return ok, status, None

    data = response.json()

    return ok, status, data
