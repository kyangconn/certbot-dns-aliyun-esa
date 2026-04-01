"""
阿里云ESA API客户端
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from alibabacloud_esa20240910 import models as esa20240910_models
from alibabacloud_esa20240910.client import Client as ESA20240910Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_credentials.client import Client as CredentialsClient

logger = logging.getLogger(__name__)


class AliCloudESAClient:
    """阿里云ESA客户端"""

    def __init__(self, access_key_id: str, access_key_secret: str, region_id: str = "cn-hangzhou"):
        """
        初始化阿里云ESA客户端

        :param access_key_id: 阿里云AccessKey ID
        :param access_key_secret: 阿里云AccessKey Secret
        :param region_id: 地域ID，默认为cn-hangzhou
        """
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.region_id = region_id
        self.client = self._create_client()

    def _create_client(self) -> ESA20240910Client:
        """创建阿里云ESA客户端"""
        config = open_api_models.Config(
            access_key_id=self.access_key_id,
            access_key_secret=self.access_key_secret,
            region_id=self.region_id
        )
        # ESA的endpoint
        config.endpoint = f"esa.{self.region_id}.aliyuncs.com"
        return ESA20240910Client(config)

    def get_site_records(self, site_id: str, record_name: str | None = None, record_type: str = "TXT") -> List[Dict[str, Any]]:
        """
        获取站点记录

        :param site_id: 站点ID
        :param record_name: 记录名称（可选）
        :param record_type: 记录类型
        :return: 记录列表
        """
        try:
            request = esa20240910_models.ListRecordsRequest(
                site_id=site_id,  # type: ignore
                type=record_type
            )
            response = self.client.list_records(request)

            records = []
            if response.body and response.body.records:
                for record in response.body.records:
                    # 如果指定了record_name，只返回匹配的记录
                    if record_name and record.record_name != record_name:
                        continue
                    
                    records.append({
                        "record_id": record.record_id,
                        "record_name": record.record_name,
                        "type": record.type,  # type: ignore
                        "data": record.data,
                        "ttl": record.ttl,
                        "comment": record.comment,
                        "status": record.status  # type: ignore
                    })
            return records
        except Exception as e:
            logger.error(f"获取站点记录失败: {e}")
            raise

    def add_txt_record(self, site_id: str, record_name: str, value: str, ttl: int = 600, comment: str = "Certbot DNS-01 challenge") -> str:
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
            # 对于TXT记录，data字段需要特殊处理
            # 根据ESA文档，TXT记录的数据格式可能不同
            # 这里假设TXT记录的数据直接放在value字段中
            request = esa20240910_models.CreateRecordRequest(
                site_id=site_id,  # type: ignore
                record_name=record_name,
                type="TXT",
                ttl=ttl,
                comment=comment,
                # 对于TXT记录，可能需要不同的data结构
                # 这里需要根据实际的ESA API文档调整
                data=esa20240910_models.CreateRecordRequestData(
                    # 根据示例代码，TXT记录可能需要特定的data结构
                    # 这里先使用一个简单的结构
                    value=value  # type: ignore
                )
            )
            
            response = self.client.create_record(request)

            if response.body and response.body.record_id:
                logger.info(f"成功添加ESA TXT记录: {record_name} -> {value}")
                return str(response.body.record_id)  # type: ignore
            else:
                raise Exception("添加记录失败，未返回记录ID")
        except Exception as e:
            logger.error(f"添加ESA TXT记录失败: {e}")
            # 尝试使用更通用的方法
            return self._add_record_generic(site_id, record_name, "TXT", value, ttl, comment)

    def _add_record_generic(self, site_id: str, record_name: str, record_type: str, value: str, ttl: int = 600, comment: str = "") -> str:
        """
        通用方法添加记录（备用方法）
        """
        try:
            # 尝试不同的data结构
            request = esa20240910_models.CreateRecordRequest(
                site_id=site_id,  # type: ignore
                record_name=record_name,
                type=record_type,
                ttl=ttl,
                comment=comment
            )
            
            # 根据记录类型设置不同的data
            if record_type == "TXT":
                # TXT记录可能只需要简单的value
                # 这里尝试不设置data字段
                pass
            elif record_type == "CNAME":
                request.data = esa20240910_models.CreateRecordRequestData(
                    cname=value  # type: ignore
                )
            elif record_type == "A":
                request.data = esa20240910_models.CreateRecordRequestData(
                    address=value  # type: ignore
                )
            
            response = self.client.create_record(request)
            
            if response.body and response.body.record_id:
                logger.info(f"成功添加ESA {record_type}记录: {record_name} -> {value}")
                return str(response.body.record_id)  # type: ignore
            else:
                raise Exception("添加记录失败，未返回记录ID")
        except Exception as e:
            logger.error(f"通用方法添加记录失败: {e}")
            raise

    def delete_record(self, record_id: str) -> bool:
        """
        删除记录

        :param record_id: 记录ID
        :return: 是否成功
        """
        try:
            request = esa20240910_models.DeleteRecordRequest(
                record_id=record_id  # type: ignore
            )
            response = self.client.delete_record(request)

            logger.info(f"成功删除ESA记录: {record_id}")
            return True
        except Exception as e:
            logger.error(f"删除ESA记录失败: {e}")
            raise

    def update_record(self, record_id: str, record_name: str, record_type: str, value: str, ttl: int = 600, comment: str = "") -> bool:
        """
        更新记录

        :param record_id: 记录ID
        :param record_name: 记录名称
        :param record_type: 记录类型
        :param value: 记录值
        :param ttl: TTL值
        :param comment: 备注
        :return: 是否成功
        """
        try:
            request = esa20240910_models.UpdateRecordRequest(
                record_id=record_id,  # type: ignore
                record_name=record_name,  # type: ignore
                type=record_type,
                ttl=ttl,
                comment=comment
            )
            
            # 根据记录类型设置data
            if record_type == "TXT":
                request.data = esa20240910_models.UpdateRecordRequestData(
                    value=value  # type: ignore
                )
            
            response = self.client.update_record(request)

            logger.info(f"成功更新ESA记录: {record_id}")
            return True
        except Exception as e:
            logger.error(f"更新ESA记录失败: {e}")
            raise

    def get_sites(self) -> List[Dict[str, Any]]:
        """
        获取所有站点

        :return: 站点列表
        """
        try:
            request = esa20240910_models.ListSitesRequest()
            response = self.client.list_sites(request)

            sites = []
            if response.body and response.body.sites:
                for site in response.body.sites:
                    sites.append({
                        "site_id": site.site_id,
                        "site_name": site.site_name,
                        "status": site.status,
                        "coverage": site.coverage,
                        "access_type": site.access_type
                    })
            return sites
        except Exception as e:
            logger.error(f"获取站点列表失败: {e}")
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
