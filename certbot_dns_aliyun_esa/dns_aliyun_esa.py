"""
阿里云ESA DNS认证器插件
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable

import zope.interface
from certbot import errors, interfaces
from certbot.plugins import dns_common

from .esa_client import AliCloudESAClient

logger = logging.getLogger(__name__)


@zope.interface.implementer(interfaces.IAuthenticator)
@zope.interface.provider(interfaces.IPluginFactory)
class Authenticator(dns_common.DNSAuthenticator):
    """阿里云ESA DNS认证器"""

    description = "通过阿里云ESA API获取证书，使用DNS-01验证"
    ttl = 600  # DNS记录TTL

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.credentials: dns_common.CredentialsConfiguration | None = None

    @classmethod
    def add_parser_arguments(cls, add: Callable[..., None], default_propagation_seconds: int = 30) -> None:
        """添加命令行参数"""
        super().add_parser_arguments(add, default_propagation_seconds)
        add("credentials", help="阿里云API凭证文件路径")
        add("site-id", help="ESA站点ID（可选，如果不提供会自动查找）")

    def more_info(self) -> str:
        """返回插件的更多信息"""
        return (
            "此插件通过阿里云ESA API配置DNS记录来完成DNS-01验证。"
            "需要在凭证文件中配置阿里云AccessKey ID和AccessKey Secret。"
            "还需要指定ESA站点ID或让插件自动查找。"
        )

    def _setup_credentials(self) -> None:
        """设置API凭证"""
        self.credentials = self._configure_credentials(
            "credentials",
            "阿里云API凭证文件路径",
            {
                "access_key_id": "阿里云 AccessKey ID",
                "access_key_secret": "阿里云 AccessKey Secret",
                "region_id": "阿里云地域ID (可选，默认为cn-hangzhou)"
            }
        )

    def _perform(self, domain: str, validation_name: str, validation: str) -> None:
        """
        添加DNS TXT记录进行验证

        :param domain: 要验证的域名
        :param validation_name: 验证记录名称
        :param validation: 验证值
        """
        self._get_esa_helper().add_txt_record(validation_name, validation)

    def _cleanup(self, domain: str, validation_name: str, validation: str) -> None:
        """
        清理DNS TXT记录

        :param domain: 要验证的域名
        :param validation_name: 验证记录名称
        :param validation: 验证值
        """
        self._get_esa_helper().del_txt_record(validation_name, validation)

    def _get_esa_helper(self) -> "_AliCloudESAHelper":
        """获取阿里云ESA辅助类"""
        if not self.credentials:
            raise errors.Error("凭证未配置")

        access_key_id: str = self.credentials.conf("access_key_id") or ""
        access_key_secret: str = self.credentials.conf("access_key_secret") or ""
        region_id = self.credentials.conf("region_id") or "cn-hangzhou"
        
        # 获取站点ID（从命令行参数或自动查找）
        site_id = self.conf("site-id")
        
        return _AliCloudESAHelper(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            region_id=region_id,
            site_id=site_id,
            ttl=self.ttl
        )


class _AliCloudESAHelper:
    """阿里云ESA辅助类"""

    def __init__(self, access_key_id: str, access_key_secret: str, region_id: str, site_id: str | None = None, ttl: int = 600):
        """
        初始化ESA辅助类

        :param access_key_id: 阿里云AccessKey ID
        :param access_key_secret: 阿里云AccessKey Secret
        :param region_id: 地域ID
        :param site_id: ESA站点ID（可选）
        :param ttl: DNS记录TTL
        """
        self.client = AliCloudESAClient(access_key_id, access_key_secret, region_id)
        self.ttl = ttl
        self.site_id = site_id
        self._record_ids = {}  # 存储添加的记录ID，用于清理
        
        # 如果没有提供site_id，尝试自动查找
        if not self.site_id:
            logger.warning("未提供站点ID，将尝试自动查找")

    def _ensure_site_id(self, domain: str) -> str:
        """确保有站点ID，如果没有则尝试查找"""
        if self.site_id:
            return self.site_id
        
        # 尝试根据域名查找站点
        root_domain = self._get_root_domain(domain)
        site = self.client.find_site_by_domain(root_domain)
        
        if not site:
            # 尝试查找父域名
            parts = root_domain.split('.')
            if len(parts) > 2:
                parent_domain = '.'.join(parts[1:])
                site = self.client.find_site_by_domain(parent_domain)
        
        if not site:
            raise errors.PluginError(f"未找到域名 {domain} 对应的ESA站点，请手动指定站点ID")
        
        self.site_id = site["site_id"]
        logger.info(f"找到站点: {site['site_name']} (ID: {self.site_id})")
        return self.site_id

    def add_txt_record(self, record_name: str, record_content: str) -> None:
        """
        添加TXT记录

        :param record_name: 记录名称
        :param record_content: 记录内容
        """
        logger.debug(f"添加ESA TXT记录: {record_name} -> {record_content}")

        try:
            # 获取站点ID
            site_id = self._ensure_site_id(record_name)
            
            # 检查是否已存在相同的记录
            existing_records = self.client.get_site_records(site_id, record_name, "TXT")
            for record in existing_records:
                # 检查记录值是否匹配
                # 注意：ESA中TXT记录的值可能在data字段中
                record_value = self._extract_txt_value(record)
                if record_value == record_content:
                    logger.info(f"TXT记录已存在: {record_name}")
                    self._record_ids[record_name] = record["record_id"]
                    return

            # 添加新记录
            record_id = self.client.add_txt_record(
                site_id=site_id,
                record_name=record_name,
                value=record_content,
                ttl=self.ttl,
                comment="Certbot DNS-01 challenge"
            )
            self._record_ids[record_name] = record_id

            # 等待DNS传播
            logger.info(f"等待DNS记录传播...")
            time.sleep(10)

        except Exception as e:
            logger.error(f"添加ESA TXT记录失败: {e}")
            raise errors.PluginError(f"添加ESA TXT记录失败: {e}")

    def del_txt_record(self, record_name: str, record_content: str) -> None:
        """
        删除TXT记录

        :param record_name: 记录名称
        :param record_content: 记录内容
        """
        logger.debug(f"删除ESA TXT记录: {record_name}")

        try:
            # 获取站点ID
            site_id = self._ensure_site_id(record_name)
            
            # 使用存储的记录ID删除
            if record_name in self._record_ids:
                record_id = self._record_ids[record_name]
                self.client.delete_record(record_id)
                del self._record_ids[record_name]
                return

            # 如果没有存储的记录ID，尝试查找并删除
            existing_records = self.client.get_site_records(site_id, record_name, "TXT")
            for record in existing_records:
                record_value = self._extract_txt_value(record)
                if record_value == record_content:
                    self.client.delete_record(record["record_id"])
                    break
            else:
                logger.warning(f"未找到要删除的ESA TXT记录: {record_name}")

        except Exception as e:
            logger.error(f"删除ESA TXT记录失败: {e}")
            # 清理时的错误不应该导致程序失败
            logger.warning(f"清理ESA TXT记录时出错，但不影响证书获取: {e}")

    def _extract_txt_value(self, record: dict) -> str:
        """从ESA记录中提取TXT值"""
        # ESA中TXT记录的值可能在data字段中
        if "data" in record and record["data"]:
            # 根据ESA API的实际结构调整
            if isinstance(record["data"], dict):
                # 尝试从data字典中提取值
                if "value" in record["data"]:
                    return record["data"]["value"]
                elif "txt" in record["data"]:
                    return record["data"]["txt"]
                elif "data" in record["data"]:
                    return record["data"]["data"]
        
        # 如果data字段是字符串，直接返回
        if isinstance(record["data"], str):
            return record["data"]
        
        # 如果data字段不存在，尝试其他字段
        if "value" in record:
            return record["value"]
        
        # 最后返回空字符串
        return ""

    @staticmethod
    def _get_root_domain(domain: str) -> str:
        """
        获取根域名

        :param domain: 完整域名
        :return: 根域名
        """
        # 移除可能的_acme-challenge前缀
        if domain.startswith("_acme-challenge."):
            domain = domain[16:]  # 移除 "_acme-challenge." 前缀
        
        # 简单的根域名提取逻辑
        parts = domain.split('.')
        if len(parts) >= 2:
            return '.'.join(parts[-2:])
        return domain
