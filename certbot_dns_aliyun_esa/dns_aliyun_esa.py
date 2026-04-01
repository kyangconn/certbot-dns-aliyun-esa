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
    def add_parser_arguments(
        cls, add: Callable[..., None], default_propagation_seconds: int = 30
    ) -> None:
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
                "access_key_id": "dns_aliyun_esa_access_id",
                "access_key_secret": "dns_aliyun_esa_access_secret",
                "site_id": "dns_aliyun_esa_site_id",
            },
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

        # 从凭证文件读取配置
        access_key_id = self.credentials.conf("access_key_id")
        access_key_secret = self.credentials.conf("access_key_secret")
        site_id = self.credentials.conf("site_id")

        # 验证必要的凭证
        if not access_key_id:
            raise errors.PluginError("凭证文件中缺少 access_key_id")
        if not access_key_secret:
            raise errors.PluginError("凭证文件中缺少 access_key_secret")
        if site_id:
            try:
                site_id = int(site_id)
            except ValueError:
                raise errors.PluginError(f"无效的ESA站点ID: {site_id}，必须是整数")

        logger.debug(f"使用配置: site_id={site_id or '自动查找'}")

        return _AliCloudESAHelper(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            site_id=site_id,
            ttl=self.ttl,
        )


class _AliCloudESAHelper:
    """阿里云ESA辅助类"""

    def __init__(
        self, access_key_id: str, access_key_secret: str, site_id: int, ttl: int = 600
    ):
        """
        初始化ESA辅助类

        :param access_key_id: 阿里云AccessKey ID
        :param access_key_secret: 阿里云AccessKey Secret
        :param site_id: ESA站点ID（可选）
        :param ttl: DNS记录TTL
        """
        self.client = AliCloudESAClient(access_key_id, access_key_secret)
        self.ttl = ttl
        self.site_id: int = site_id
        self._record_ids = {}  # 存储添加的记录ID，用于清理

    def _ensure_site_id(self, domain: str) -> int:
        """确保有站点ID，如果没有则尝试查找"""
        if self.site_id:
            # 已有 site_id 时优先调用 GetSite 验证
            try:
                site = self.client.get_site(self.site_id)
                self.site_id = site["site_id"]
                return self.site_id
            except Exception as e:
                raise errors.PluginError(
                    f"无效的ESA站点ID: {self.site_id}，GetSite失败: {e}"
                )

        # 尝试根据域名查找站点
        root_domain = self._get_root_domain(domain)
        logger.info(f"尝试查找域名 {root_domain} 对应的ESA站点...")

        site = self.client.find_site_by_domain(root_domain)

        if not site:
            # 尝试查找父域名
            parts = root_domain.split(".")
            if len(parts) > 2:
                parent_domain = ".".join(parts[1:])
                logger.info(f"尝试查找父域名 {parent_domain}...")
                site = self.client.find_site_by_domain(parent_domain)

        if not site:
            raise errors.PluginError(
                f"未找到域名 {domain} 对应的ESA站点。\n"
                f"请确保：\n"
                f"1. 域名已在阿里云ESA中配置站点\n"
                f"2. 或手动指定站点ID：--dns-aliyun-esa-site-id YOUR_SITE_ID\n"
                f"3. 或在凭证文件中配置 site_id"
            )

        self.site_id = site["site_id"]
        logger.info(f"找到站点: {site['site_name']} (ID: {self.site_id})")
        return self.site_id

    def add_txt_record(self, record_name: str, record_content: str) -> None:
        """
        添加TXT记录

        :param record_name: 记录名称
        :param record_content: 记录内容
        """
        logger.info(f"添加ESA TXT记录: {record_name} -> {record_content}")

        try:
            # 获取站点ID
            site_id = self._ensure_site_id(record_name)

            # 检查是否已存在相同的记录
            existing_records = self.client.get_site_records(site_id, record_name, "TXT")
            for record in existing_records:
                # 检查记录值是否匹配
                record_value = self._extract_txt_value(record)
                logger.debug(f"检查现有记录: {record_name} = {record_value}")
                if record_value == record_content:
                    logger.info(f"TXT记录已存在: {record_name}")
                    self._record_ids[record_name] = record["record_id"]
                    return

            # 添加新记录
            logger.info(f"正在添加新的TXT记录到站点 {site_id}...")
            record_id = self.client.add_txt_record(
                site_id=site_id,
                record_name=record_name,
                value=record_content,
                ttl=self.ttl,
                comment="Certbot DNS-01 challenge",
            )
            self._record_ids[record_name] = record_id
            logger.info(f"TXT记录添加成功，记录ID: {record_id}")

            # 等待DNS传播
            logger.info("等待DNS记录传播...")
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
        logger.info(f"删除ESA TXT记录: {record_name}")

        try:
            # 获取站点ID
            site_id = self._ensure_site_id(record_name)

            # 使用存储的记录ID删除
            if record_name in self._record_ids:
                record_id = self._record_ids[record_name]
                logger.info(f"使用缓存的记录ID删除: {record_id}")
                self.client.delete_record(record_id)
                del self._record_ids[record_name]
                logger.info(f"记录删除成功")
                return

            # 如果没有存储的记录ID，尝试查找并删除
            logger.info(f"查找要删除的记录: {record_name}")
            existing_records = self.client.get_site_records(site_id, record_name, "TXT")

            deleted = False
            for record in existing_records:
                record_value = self._extract_txt_value(record)
                logger.debug(f"检查记录: {record['record_id']} = {record_value}")
                if record_value == record_content:
                    logger.info(f"删除记录: {record['record_id']}")
                    self.client.delete_record(record["record_id"])
                    deleted = True
                    break

            if not deleted:
                logger.warning(f"未找到要删除的ESA TXT记录: {record_name}")
            else:
                logger.info(f"记录删除成功")

        except Exception as e:
            logger.error(f"删除ESA TXT记录失败: {e}")
            # 清理时的错误不应该导致程序失败
            logger.warning(f"清理ESA TXT记录时出错，但不影响证书获取: {e}")

    def _extract_txt_value(self, record: dict) -> str:
        """从ESA记录中提取TXT值"""
        logger.debug(f"提取TXT值，记录结构: {record}")

        # 首先检查是否有直接的value字段
        if "value" in record and record["value"]:
            return str(record["value"])

        # 检查data字段
        if "data" in record and record["data"]:
            data = record["data"]

            # 如果data是字符串，直接返回
            if isinstance(data, str):
                return data

            # 如果data是字典，尝试不同的键
            if isinstance(data, dict):
                # 尝试常见的键名
                for key in ["value", "txt", "data", "content", "text"]:
                    if key in data and data[key]:
                        return str(data[key])

                # 如果字典有值，尝试第一个值
                if data:
                    first_value = list(data.values())[0]
                    if first_value:
                        return str(first_value)

        # 检查其他可能的字段
        for field in ["content", "txt", "text", "record_value"]:
            if field in record and record[field]:
                return str(record[field])

        # 最后尝试整个记录转换为字符串
        logger.warning(f"无法从记录中提取TXT值，记录: {record}")
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
        parts = domain.split(".")
        if len(parts) >= 2:
            return ".".join(parts[-2:])
        return domain
