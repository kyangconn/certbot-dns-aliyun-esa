"""
阿里云ESA API客户端
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from alibabacloud_esa20240910 import models as esa20240910_models
from alibabacloud_esa20240910.client import Client as ESA20240910Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models

logger = logging.getLogger(__name__)


class AliCloudESAClient:
    """阿里云ESA客户端"""

    def __init__(self, access_key_id: str, access_key_secret: str):
        """
        初始化阿里云ESA客户端

        :param access_key_id: 阿里云AccessKey ID
        :param access_key_secret: 阿里云AccessKey Secret
        :param region_id: 地域ID，默认为cn-hangzhou
        """
        config = open_api_models.Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
        )
        # ESA没有多区域endpoint，固定使用 cn-hangzhou
        config.endpoint = "esa.cn-hangzhou.aliyuncs.com"
        self.client = ESA20240910Client(config)
        # 单例化RuntimeOptions，避免重复创建
        self.runtime = util_models.RuntimeOptions()

    def get_site_records(
        self,
        site_id: int,
        record_name: str | None = None,
        record_type: str = "TXT",
        page_number: int = 1,
        page_size: int = 10,
        proxied: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        获取站点记录

        :param site_id: 站点ID
        :param record_name: 记录名称（域名）
        :param record_type: 记录类型（TXT)
        :param page_number: 分页页码
        :param page_size: 分页大小
        :param proxied: 是否代理加速
        :return: 记录列表
        """
        try:
            records = []
            current_page = page_number
            while True:
                request = esa20240910_models.ListRecordsRequest(
                    site_id=site_id,
                    record_name=record_name,
                    type=record_type,
                    page_number=current_page,
                    page_size=page_size,
                    proxied=proxied,
                )
                response = self.client.list_records_with_options(request, self.runtime)

                body = response.body
                list_records = body.records
                if not list_records:
                    break

                for record in list_records:
                    records.append(
                        {
                            "record_id": record.record_id,
                            "record_name": record.record_name,
                            "type": record.record_type,
                            "data": record.data,
                            "ttl": record.ttl,
                            "comment": record.comment,
                        }
                    )

                total_count = body.total_count
                if len(records) >= total_count or len(list_records) < page_size:
                    break

                current_page += 1

            if record_name:
                records = [r for r in records if r["record_name"] == record_name]

            return records
        except Exception as e:
            logger.error(f"获取站点记录失败: {e}")
            raise

    def add_txt_record(
        self,
        site_id: int,
        record_name: str,
        value: str,
        ttl: int = 600,
        comment: str = "Certbot DNS-01 challenge",
    ) -> str:
        """
        添加TXT记录

        :param site_id: 站点ID
        :param record_name: 记录名称
        :param value: 记录值
        :param ttl: TTL值
        :param comment: 备注
        :return: 记录ID
        """
        try:
            request = esa20240910_models.CreateRecordRequest(
                site_id=site_id,
                record_name=record_name,
                type="TXT",
                ttl=ttl,
                comment=comment,
                data=esa20240910_models.CreateRecordRequestData(value=value),
            )
            response = self.client.create_record_with_options(request, self.runtime)

            record_id = response.body.record_id

            if not record_id:
                raise Exception("添加记录失败，未返回记录ID")

            logger.info(f"成功添加ESA TXT记录: {record_name} -> {value}")
            return str(record_id)
        except Exception as e:
            logger.error(f"添加ESA TXT记录失败: {e}")
            raise

    def delete_record(self, record_id: int) -> bool:
        """
        删除记录

        :param record_id: 记录ID
        :return: 是否成功
        """
        try:
            request = esa20240910_models.DeleteRecordRequest(record_id=record_id)
            self.client.delete_record_with_options(request, self.runtime)
            logger.info(f"成功删除ESA记录: {record_id}")
            return True
        except Exception as e:
            logger.error(f"删除ESA记录失败: {e}")
            raise

    def update_record(
        self, record_id: int, value: str, ttl: int, comment: str | None = None
    ) -> bool:
        """
        更新记录

        :param record_id: 记录ID
        :param value: 记录值
        :param ttl: TTL值（可选）
        :param comment: 备注（可选）
        :return: 是否成功
        """
        try:
            request = esa20240910_models.UpdateRecordRequest(
                record_id=record_id,
                data=esa20240910_models.UpdateRecordRequestData(value=value),
                ttl=ttl,
                comment=comment,
            )
            self.client.update_record_with_options(request, self.runtime)
            logger.info(f"成功更新ESA记录: {record_id}")
            return True
        except Exception as e:
            logger.error(f"更新ESA记录失败: {e}")
            raise

    def get_sites(
        self,
        name: str | None = None,
        search_mode: str = "exact",
        page_number: int = 1,
        page_size: int = 50,
        sort_by: str | None = None,
    ) -> List[Dict[str, Any]]:
        """
        获取站点列表

        :param name: 站点名称搜索条件（可选）
        :param search_mode: 搜索模式（exact/like）
        :param page_number: 分页页码
        :param page_size: 分页大小
        :param sort_by: 排序字段
        :return: 站点列表
        """
        try:
            request = esa20240910_models.ListSitesRequest(
                site_name=name,
                site_search_type=search_mode,
                page_number=page_number,
                page_size=page_size,
                order_by=sort_by,
            )
            response = self.client.list_sites_with_options(request, self.runtime)

            sites_data = response.body.sites

            sites = []
            for site in sites_data:
                sites.append(
                    {
                        "site_id": site.site_id,
                        "site_name": site.site_name,
                        "status": site.status,
                        "coverage": site.coverage,
                        "access_type": site.access_type,
                    }
                )
            return sites
        except Exception as e:
            logger.error(f"获取站点列表失败: {e}")
            raise

    def get_site(self, site_id: int) -> Dict[str, Any]:
        """
        根据站点ID获取站点信息

        :param site_id: 站点ID
        :return: 站点信息
        """
        try:
            request = esa20240910_models.GetSiteRequest(site_id=site_id)
            response = self.client.get_site_with_options(request, self.runtime)

            site = response.body.site_model

            if not site:
                raise Exception(f"未找到站点ID: {site_id}")

            return {
                "site_id": site.site_id,
                "site_name": site.site_name,
                "status": site.status,
                "coverage": site.coverage,
                "access_type": site.access_type,
            }
        except Exception as e:
            logger.error(f"获取站点失败: {e}")
            raise

    def find_site_by_domain(self, domain: str) -> Dict[str, Any] | None:
        """
        根据域名查找站点

        :param domain: 域名
        :return: 站点信息或None
        """
        try:
            sites = self.get_sites()
            for site in sites:
                if site["site_name"] == domain:
                    return site
            return None
        except Exception as e:
            logger.error(f"查找站点失败: {e}")
            raise
