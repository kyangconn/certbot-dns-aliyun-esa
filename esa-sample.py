# -*- coding: utf-8 -*-
# This file is auto-generated, don't edit it. Thanks.
from __future__ import annotations

import logging
import os
import sys

from typing import List

from alibabacloud_credentials.client import Client
from alibabacloud_esa20240910 import models as esa20240910_models
from alibabacloud_esa20240910.client import Client as ESA20240910Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util.client import Client as UtilClient
from darabonba.core import DaraCore as DaraCore
from darabonba.exceptions import DaraException



class Sample:
    def __init__(self):
        pass

    @staticmethod
    def create_esa20240910client() -> ESA20240910Client:
        config = open_api_models.Config()
        config.credential = Client(None)
        # Endpoint please refer to https://api.aliyun.com/product/ESA
        config.endpoint = 'esa.cn-hangzhou.aliyuncs.com'
        return ESA20240910Client(config)

    @staticmethod
    def rate_plan_inst_cert(
        client: ESA20240910Client,
    ) -> esa20240910_models.PurchaseRatePlanResponseBody:
        logging.log(logging.INFO, 'Begin Call PurchaseRatePlan to create resource')
        purchase_rate_plan_request = esa20240910_models.PurchaseRatePlanRequest(
            type = 'NS',
            charge_type = 'PREPAY',
            auto_renew = False,
            period = 1,
            coverage = 'overseas',
            auto_pay = True,
            plan_name = 'high'
        )
        purchase_rate_plan_response = client.purchase_rate_plan(purchase_rate_plan_request)
        describe_rate_plan_instance_status_request = esa20240910_models.DescribeRatePlanInstanceStatusRequest(
            instance_id = purchase_rate_plan_response.body.instance_id
        )
        current_retry = 0
        delayed_time = 10000
        interval = 10000
        while current_retry < 10:
            try :
                sleep_time = 0
                if current_retry == 0:
                    sleep_time = delayed_time
                else:
                    sleep_time = interval

                logging.log(logging.INFO, 'Polling for asynchronous results...')
                DaraCore.sleep(sleep_time)
            except Exception as error :
                raise DaraException({
                    'message': error.message
                })
            
            describe_rate_plan_instance_status_response = client.describe_rate_plan_instance_status(describe_rate_plan_instance_status_request)
            instance_status = describe_rate_plan_instance_status_response.body.instance_status
            if instance_status == 'running':
                logging.log(logging.INFO, 'Call PurchaseRatePlan success, response: ')
                logging.log(logging.INFO, UtilClient.to_jsonstring(purchase_rate_plan_response))
                return purchase_rate_plan_response.body
            current_retry+= 1
        raise DaraException({
            'message': 'Asynchronous check failed'
        })

    @staticmethod
    async def rate_plan_inst_cert_async(
        client: ESA20240910Client,
    ) -> esa20240910_models.PurchaseRatePlanResponseBody:
        logging.log(logging.INFO, 'Begin Call PurchaseRatePlan to create resource')
        purchase_rate_plan_request = esa20240910_models.PurchaseRatePlanRequest(
            type = 'NS',
            charge_type = 'PREPAY',
            auto_renew = False,
            period = 1,
            coverage = 'overseas',
            auto_pay = True,
            plan_name = 'high'
        )
        purchase_rate_plan_response = await client.purchase_rate_plan_async(purchase_rate_plan_request)
        describe_rate_plan_instance_status_request = esa20240910_models.DescribeRatePlanInstanceStatusRequest(
            instance_id = purchase_rate_plan_response.body.instance_id
        )
        current_retry = 0
        delayed_time = 10000
        interval = 10000
        while current_retry < 10:
            try :
                sleep_time = 0
                if current_retry == 0:
                    sleep_time = delayed_time
                else:
                    sleep_time = interval

                logging.log(logging.INFO, 'Polling for asynchronous results...')
                await DaraCore.sleep_async(sleep_time)
            except Exception as error :
                raise DaraException({
                    'message': error.message
                })
            
            describe_rate_plan_instance_status_response = await client.describe_rate_plan_instance_status_async(describe_rate_plan_instance_status_request)
            instance_status = describe_rate_plan_instance_status_response.body.instance_status
            if instance_status == 'running':
                logging.log(logging.INFO, 'Call PurchaseRatePlan success, response: ')
                logging.log(logging.INFO, UtilClient.to_jsonstring(purchase_rate_plan_response))
                return purchase_rate_plan_response.body
            current_retry+= 1
        raise DaraException({
            'message': 'Asynchronous check failed'
        })

    @staticmethod
    def site_cert(
        rate_plan_inst_cert_response_body: esa20240910_models.PurchaseRatePlanResponseBody,
        client: ESA20240910Client,
    ) -> esa20240910_models.CreateSiteResponseBody:
        logging.log(logging.INFO, 'Begin Call CreateSite to create resource')
        create_site_request = esa20240910_models.CreateSiteRequest(
            site_name = 'gositecdn.cn',
            instance_id = rate_plan_inst_cert_response_body.instance_id,
            coverage = 'overseas',
            access_type = 'NS'
        )
        create_site_response = client.create_site(create_site_request)
        get_site_request = esa20240910_models.GetSiteRequest(
            site_id = create_site_response.body.site_id
        )
        current_retry = 0
        delayed_time = 60000
        interval = 10000
        while current_retry < 5:
            try :
                sleep_time = 0
                if current_retry == 0:
                    sleep_time = delayed_time
                else:
                    sleep_time = interval

                logging.log(logging.INFO, 'Polling for asynchronous results...')
                DaraCore.sleep(sleep_time)
            except Exception as error :
                raise DaraException({
                    'message': error.message
                })
            
            get_site_response = client.get_site(get_site_request)
            status = get_site_response.body.site_model.status
            if status == 'pending':
                logging.log(logging.INFO, 'Call CreateSite success, response: ')
                logging.log(logging.INFO, UtilClient.to_jsonstring(create_site_response))
                return create_site_response.body
            current_retry+= 1
        raise DaraException({
            'message': 'Asynchronous check failed'
        })

    @staticmethod
    async def site_cert_async(
        rate_plan_inst_cert_response_body: esa20240910_models.PurchaseRatePlanResponseBody,
        client: ESA20240910Client,
    ) -> esa20240910_models.CreateSiteResponseBody:
        logging.log(logging.INFO, 'Begin Call CreateSite to create resource')
        create_site_request = esa20240910_models.CreateSiteRequest(
            site_name = 'gositecdn.cn',
            instance_id = rate_plan_inst_cert_response_body.instance_id,
            coverage = 'overseas',
            access_type = 'NS'
        )
        create_site_response = await client.create_site_async(create_site_request)
        get_site_request = esa20240910_models.GetSiteRequest(
            site_id = create_site_response.body.site_id
        )
        current_retry = 0
        delayed_time = 60000
        interval = 10000
        while current_retry < 5:
            try :
                sleep_time = 0
                if current_retry == 0:
                    sleep_time = delayed_time
                else:
                    sleep_time = interval

                logging.log(logging.INFO, 'Polling for asynchronous results...')
                await DaraCore.sleep_async(sleep_time)
            except Exception as error :
                raise DaraException({
                    'message': error.message
                })
            
            get_site_response = await client.get_site_async(get_site_request)
            status = get_site_response.body.site_model.status
            if status == 'pending':
                logging.log(logging.INFO, 'Call CreateSite success, response: ')
                logging.log(logging.INFO, UtilClient.to_jsonstring(create_site_response))
                return create_site_response.body
            current_retry+= 1
        raise DaraException({
            'message': 'Asynchronous check failed'
        })

    @staticmethod
    def record_cert(
        site_cert_response_body: esa20240910_models.CreateSiteResponseBody,
        client: ESA20240910Client,
    ) -> esa20240910_models.CreateRecordResponseBody:
        logging.log(logging.INFO, 'Begin Call CreateRecord to create resource')
        data = esa20240910_models.CreateRecordRequestData(
            type = 111,
            key_tag = 11,
            algorithm = 11,
            certificate = 'eGVzdGFsbWNkbg=='
        )
        create_record_request = esa20240910_models.CreateRecordRequest(
            record_name = 'www.gositecdn.cn',
            comment = 'This is a remark',
            site_id = site_cert_response_body.site_id,
            type = 'CERT',
            data = data,
            ttl = 100
        )
        create_record_response = Sample.create_record_with_retry(client, create_record_request)
        logging.log(logging.INFO, 'Call CreateRecord success, response: ')
        logging.log(logging.INFO, UtilClient.to_jsonstring(create_record_response))
        return create_record_response.body

    @staticmethod
    async def record_cert_async(
        site_cert_response_body: esa20240910_models.CreateSiteResponseBody,
        client: ESA20240910Client,
    ) -> esa20240910_models.CreateRecordResponseBody:
        logging.log(logging.INFO, 'Begin Call CreateRecord to create resource')
        data = esa20240910_models.CreateRecordRequestData(
            type = 111,
            key_tag = 11,
            algorithm = 11,
            certificate = 'eGVzdGFsbWNkbg=='
        )
        create_record_request = esa20240910_models.CreateRecordRequest(
            record_name = 'www.gositecdn.cn',
            comment = 'This is a remark',
            site_id = site_cert_response_body.site_id,
            type = 'CERT',
            data = data,
            ttl = 100
        )
        create_record_response = await Sample.create_record_with_retry_async(client, create_record_request)
        logging.log(logging.INFO, 'Call CreateRecord success, response: ')
        logging.log(logging.INFO, UtilClient.to_jsonstring(create_record_response))
        return create_record_response.body

    @staticmethod
    def create_record_with_retry(
        client: ESA20240910Client,
        create_record_request: esa20240910_models.CreateRecordRequest,
    ) -> esa20240910_models.CreateRecordResponse:
        error_code = ''
        retry_1 = 0
        interval_1 = 5000
        retry_2 = 0
        interval_2 = 5000
        while (retry_1 < 10) or (retry_2 < 20):
            try :
                create_record_response = client.create_record(create_record_request)
                logging.log(logging.INFO, 'Call CreateRecord success, response: ')
                logging.log(logging.INFO, UtilClient.to_jsonstring(create_record_response))
                return create_record_response
            except Exception as error :
                error_code = error.code
            
            if error_code == 'Site.ServiceBusy':
                logging.log(logging.INFO, 'Call CreateRecord failed, errorCode: Site.ServiceBusy, please retry')
                DaraCore.sleep(interval_1)
                retry_1+= 1
            if error_code == 'TooManyRequests':
                logging.log(logging.INFO, 'Call CreateRecord failed, errorCode: TooManyRequests, please retry')
                DaraCore.sleep(interval_2)
                retry_2+= 1
        raise DaraException({
            'message': 'Call CreateRecord failed'
        })

    @staticmethod
    async def create_record_with_retry_async(
        client: ESA20240910Client,
        create_record_request: esa20240910_models.CreateRecordRequest,
    ) -> esa20240910_models.CreateRecordResponse:
        error_code = ''
        retry_1 = 0
        interval_1 = 5000
        retry_2 = 0
        interval_2 = 5000
        while (retry_1 < 10) or (retry_2 < 20):
            try :
                create_record_response = await client.create_record_async(create_record_request)
                logging.log(logging.INFO, 'Call CreateRecord success, response: ')
                logging.log(logging.INFO, UtilClient.to_jsonstring(create_record_response))
                return create_record_response
            except Exception as error :
                error_code = error.code
            
            if error_code == 'Site.ServiceBusy':
                logging.log(logging.INFO, 'Call CreateRecord failed, errorCode: Site.ServiceBusy, please retry')
                await DaraCore.sleep_async(interval_1)
                retry_1+= 1
            if error_code == 'TooManyRequests':
                logging.log(logging.INFO, 'Call CreateRecord failed, errorCode: TooManyRequests, please retry')
                await DaraCore.sleep_async(interval_2)
                retry_2+= 1
        raise DaraException({
            'message': 'Call CreateRecord failed'
        })

    @staticmethod
    def update_record_cert(
        create_record_response_body: esa20240910_models.CreateRecordResponseBody,
        client: ESA20240910Client,
    ) -> None:
        logging.log(logging.INFO, 'Begin Call UpdateRecord to update resource')
        data = esa20240910_models.UpdateRecordRequestData(
            type = 222,
            key_tag = 22,
            algorithm = 22,
            certificate = 'bGVzdGGsbWNkbg=='
        )
        update_record_request = esa20240910_models.UpdateRecordRequest(
            comment = 'test_record_comment',
            data = data,
            ttl = 86400,
            record_id = create_record_response_body.record_id
        )
        update_record_response = Sample.update_record_with_retry(client, update_record_request)
        logging.log(logging.INFO, 'Call UpdateRecord success, response: ')
        logging.log(logging.INFO, UtilClient.to_jsonstring(update_record_response))

    @staticmethod
    async def update_record_cert_async(
        create_record_response_body: esa20240910_models.CreateRecordResponseBody,
        client: ESA20240910Client,
    ) -> None:
        logging.log(logging.INFO, 'Begin Call UpdateRecord to update resource')
        data = esa20240910_models.UpdateRecordRequestData(
            type = 222,
            key_tag = 22,
            algorithm = 22,
            certificate = 'bGVzdGGsbWNkbg=='
        )
        update_record_request = esa20240910_models.UpdateRecordRequest(
            comment = 'test_record_comment',
            data = data,
            ttl = 86400,
            record_id = create_record_response_body.record_id
        )
        update_record_response = await Sample.update_record_with_retry_async(client, update_record_request)
        logging.log(logging.INFO, 'Call UpdateRecord success, response: ')
        logging.log(logging.INFO, UtilClient.to_jsonstring(update_record_response))

    @staticmethod
    def update_record_with_retry(
        client: ESA20240910Client,
        update_record_request: esa20240910_models.UpdateRecordRequest,
    ) -> esa20240910_models.UpdateRecordResponse:
        error_code = ''
        retry_1 = 0
        interval_1 = 5000
        retry_2 = 0
        interval_2 = 3000
        while (retry_1 < 20) or (retry_2 < 10):
            try :
                update_record_response = client.update_record(update_record_request)
                logging.log(logging.INFO, 'Call UpdateRecord success, response: ')
                logging.log(logging.INFO, UtilClient.to_jsonstring(update_record_response))
                return update_record_response
            except Exception as error :
                error_code = error.code
            
            if error_code == 'TooManyRequests':
                logging.log(logging.INFO, 'Call UpdateRecord failed, errorCode: TooManyRequests, please retry')
                DaraCore.sleep(interval_1)
                retry_1+= 1
            if error_code == 'Record.ServiceBusy':
                logging.log(logging.INFO, 'Call UpdateRecord failed, errorCode: Record.ServiceBusy, please retry')
                DaraCore.sleep(interval_2)
                retry_2+= 1
        raise DaraException({
            'message': 'Call UpdateRecord failed'
        })

    @staticmethod
    async def update_record_with_retry_async(
        client: ESA20240910Client,
        update_record_request: esa20240910_models.UpdateRecordRequest,
    ) -> esa20240910_models.UpdateRecordResponse:
        error_code = ''
        retry_1 = 0
        interval_1 = 5000
        retry_2 = 0
        interval_2 = 3000
        while (retry_1 < 20) or (retry_2 < 10):
            try :
                update_record_response = await client.update_record_async(update_record_request)
                logging.log(logging.INFO, 'Call UpdateRecord success, response: ')
                logging.log(logging.INFO, UtilClient.to_jsonstring(update_record_response))
                return update_record_response
            except Exception as error :
                error_code = error.code
            
            if error_code == 'TooManyRequests':
                logging.log(logging.INFO, 'Call UpdateRecord failed, errorCode: TooManyRequests, please retry')
                await DaraCore.sleep_async(interval_1)
                retry_1+= 1
            if error_code == 'Record.ServiceBusy':
                logging.log(logging.INFO, 'Call UpdateRecord failed, errorCode: Record.ServiceBusy, please retry')
                await DaraCore.sleep_async(interval_2)
                retry_2+= 1
        raise DaraException({
            'message': 'Call UpdateRecord failed'
        })

    @staticmethod
    def destroy_record_cert(
        create_record_response_body: esa20240910_models.CreateRecordResponseBody,
        client: ESA20240910Client,
    ) -> None:
        logging.log(logging.INFO, 'Begin Call DeleteRecord to destroy resource')
        delete_record_request = esa20240910_models.DeleteRecordRequest(
            record_id = create_record_response_body.record_id
        )
        delete_record_response = Sample.delete_record_with_retry(client, delete_record_request)
        logging.log(logging.INFO, 'Call DeleteRecord success, response: ')
        logging.log(logging.INFO, UtilClient.to_jsonstring(delete_record_response))

    @staticmethod
    async def destroy_record_cert_async(
        create_record_response_body: esa20240910_models.CreateRecordResponseBody,
        client: ESA20240910Client,
    ) -> None:
        logging.log(logging.INFO, 'Begin Call DeleteRecord to destroy resource')
        delete_record_request = esa20240910_models.DeleteRecordRequest(
            record_id = create_record_response_body.record_id
        )
        delete_record_response = await Sample.delete_record_with_retry_async(client, delete_record_request)
        logging.log(logging.INFO, 'Call DeleteRecord success, response: ')
        logging.log(logging.INFO, UtilClient.to_jsonstring(delete_record_response))

    @staticmethod
    def delete_record_with_retry(
        client: ESA20240910Client,
        delete_record_request: esa20240910_models.DeleteRecordRequest,
    ) -> esa20240910_models.DeleteRecordResponse:
        error_code = ''
        retry_1 = 0
        interval_1 = 5000
        retry_2 = 0
        interval_2 = 1000
        while (retry_1 < 20) or (retry_2 < 10):
            try :
                delete_record_response = client.delete_record(delete_record_request)
                logging.log(logging.INFO, 'Call DeleteRecord success, response: ')
                logging.log(logging.INFO, UtilClient.to_jsonstring(delete_record_response))
                return delete_record_response
            except Exception as error :
                error_code = error.code
            
            if error_code == 'TooManyRequests':
                logging.log(logging.INFO, 'Call DeleteRecord failed, errorCode: TooManyRequests, please retry')
                DaraCore.sleep(interval_1)
                retry_1+= 1
            if error_code == 'Record.ServiceBusy':
                logging.log(logging.INFO, 'Call DeleteRecord failed, errorCode: Record.ServiceBusy, please retry')
                DaraCore.sleep(interval_2)
                retry_2+= 1
        raise DaraException({
            'message': 'Call DeleteRecord failed'
        })

    @staticmethod
    async def delete_record_with_retry_async(
        client: ESA20240910Client,
        delete_record_request: esa20240910_models.DeleteRecordRequest,
    ) -> esa20240910_models.DeleteRecordResponse:
        error_code = ''
        retry_1 = 0
        interval_1 = 5000
        retry_2 = 0
        interval_2 = 1000
        while (retry_1 < 20) or (retry_2 < 10):
            try :
                delete_record_response = await client.delete_record_async(delete_record_request)
                logging.log(logging.INFO, 'Call DeleteRecord success, response: ')
                logging.log(logging.INFO, UtilClient.to_jsonstring(delete_record_response))
                return delete_record_response
            except Exception as error :
                error_code = error.code
            
            if error_code == 'TooManyRequests':
                logging.log(logging.INFO, 'Call DeleteRecord failed, errorCode: TooManyRequests, please retry')
                await DaraCore.sleep_async(interval_1)
                retry_1+= 1
            if error_code == 'Record.ServiceBusy':
                logging.log(logging.INFO, 'Call DeleteRecord failed, errorCode: Record.ServiceBusy, please retry')
                await DaraCore.sleep_async(interval_2)
                retry_2+= 1
        raise DaraException({
            'message': 'Call DeleteRecord failed'
        })

    @staticmethod
    def main(
        args: List[str],
    ) -> None:
        # The code may contain api calls involving fees. Please ensure that you fully understand the charging methods and prices before running.
        # Set the environment variable COST_ACK to true or delete the following judgment to run the sample code.
        cost_acknowledged = os.environ.get('COST_ACK')
        if DaraCore.is_null(cost_acknowledged) or not cost_acknowledged == 'true':
            logging.log(logging.WARNING, 'Running code may affect the online resources of the current account, please proceed with caution!')
            return
        # Init client
        esa_20240910client = Sample.create_esa20240910client()
        # Init resource
        rate_plan_inst_cert_resp_body = Sample.rate_plan_inst_cert(esa_20240910client)
        site_cert_resp_body = Sample.site_cert(rate_plan_inst_cert_resp_body, esa_20240910client)
        record_cert_resp_body = Sample.record_cert(site_cert_resp_body, esa_20240910client)
        # update resource
        Sample.update_record_cert(record_cert_resp_body, esa_20240910client)
        # destroy resource
        Sample.destroy_record_cert(record_cert_resp_body, esa_20240910client)

    @staticmethod
    async def main_async(
        args: List[str],
    ) -> None:
        # The code may contain api calls involving fees. Please ensure that you fully understand the charging methods and prices before running.
        # Set the environment variable COST_ACK to true or delete the following judgment to run the sample code.
        cost_acknowledged = os.environ.get('COST_ACK')
        if DaraCore.is_null(cost_acknowledged) or not cost_acknowledged == 'true':
            logging.log(logging.WARNING, 'Running code may affect the online resources of the current account, please proceed with caution!')
            return
        # Init client
        esa_20240910client = Sample.create_esa20240910client()
        # Init resource
        rate_plan_inst_cert_resp_body = await Sample.rate_plan_inst_cert_async(esa_20240910client)
        site_cert_resp_body = await Sample.site_cert_async(rate_plan_inst_cert_resp_body, esa_20240910client)
        record_cert_resp_body = await Sample.record_cert_async(site_cert_resp_body, esa_20240910client)
        # update resource
        await Sample.update_record_cert_async(record_cert_resp_body, esa_20240910client)
        # destroy resource
        await Sample.destroy_record_cert_async(record_cert_resp_body, esa_20240910client)


if __name__ == '__main__':
    Sample.main(sys.argv[1:])