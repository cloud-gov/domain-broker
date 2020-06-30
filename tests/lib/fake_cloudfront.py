from datetime import datetime
from typing import Any, Dict, List

import pytest

from broker.aws import cloudfront as real_cloudfront
from tests.lib.fake_aws import FakeAWS


class FakeCloudFront(FakeAWS):
    def expect_create_distribution(
        self,
        caller_reference: str,
        domains: List[str],
        certificate_id: str,
        origin_hostname: str,
        origin_path: str,
        distribution_id: str,
        distribution_hostname: str,
        forward_cookie_policy: str = "all",
        forwarded_cookies: list = None,
        forwarded_headers: list = None,
        origin_protocol_policy: str = "https-only",
    ):
        if forwarded_headers is None:
            forwarded_headers = ["HOST"]
        self.stubber.add_response(
            "create_distribution",
            self._distribution_response(
                caller_reference,
                domains,
                certificate_id,
                origin_hostname,
                origin_path,
                distribution_id,
                distribution_hostname,
                forward_cookie_policy=forward_cookie_policy,
                forwarded_cookies=forwarded_cookies,
                forwarded_headers=forwarded_headers,
                origin_protocol_policy=origin_protocol_policy,
            ),
            {
                "DistributionConfig": self._distribution_config(
                    caller_reference,
                    domains,
                    certificate_id,
                    origin_hostname,
                    origin_path,
                    forward_cookie_policy=forward_cookie_policy,
                    forwarded_cookies=forwarded_cookies,
                    forwarded_headers=forwarded_headers,
                    origin_protocol_policy=origin_protocol_policy,
                )
            },
        )

    def expect_get_distribution_config(
        self,
        caller_reference: str,
        domains: List[str],
        certificate_id: str,
        origin_hostname: str,
        origin_path: str,
        distribution_id: str,
        forward_cookie_policy: str = "all",
        forwarded_cookies: list = None,
        forwarded_headers: list = None,
        origin_protocol_policy: str = "https-only",
    ):
        if forwarded_headers is None:
            forwarded_headers = ["HOST"]
        self.etag = str(datetime.now().timestamp())
        self.stubber.add_response(
            "get_distribution_config",
            {
                "DistributionConfig": self._distribution_config(
                    caller_reference,
                    domains,
                    certificate_id,
                    origin_hostname,
                    origin_path,
                    forward_cookie_policy=forward_cookie_policy,
                    forwarded_cookies=forwarded_cookies,
                    forwarded_headers=forwarded_headers,
                    origin_protocol_policy=origin_protocol_policy,
                ),
                "ETag": self.etag,
            },
            {"Id": distribution_id},
        )

    def expect_get_distribution_config_returning_no_such_distribution(
        self, distribution_id: str
    ):
        self.stubber.add_client_error(
            "get_distribution_config",
            service_error_code="NoSuchDistribution",
            service_message="'Ain't there.",
            http_status_code=404,
            expected_params={"Id": distribution_id},
        )

    def expect_disable_distribution(
        self,
        caller_reference: str,
        domains: List[str],
        certificate_id: str,
        origin_hostname: str,
        origin_path: str,
        distribution_id: str,
        distribution_hostname: str,
    ):
        self.stubber.add_response(
            "update_distribution",
            self._distribution_response(
                caller_reference,
                domains,
                certificate_id,
                origin_hostname,
                origin_path,
                distribution_id,
                distribution_hostname,
            ),
            {
                "DistributionConfig": self._distribution_config(
                    caller_reference,
                    domains,
                    certificate_id,
                    origin_hostname,
                    origin_path,
                    enabled=False,
                ),
                "Id": distribution_id,
                "IfMatch": self.etag,
            },
        )

    def expect_delete_distribution(self, distribution_id: str):
        self.stubber.add_response(
            "delete_distribution", {}, {"Id": distribution_id, "IfMatch": self.etag}
        )

    def expect_delete_distribution_returning_no_such_distribution(
        self, distribution_id: str
    ):
        self.stubber.add_client_error(
            "delete_distribution",
            service_error_code="NoSuchDistribution",
            service_message="'Ain't there.",
            http_status_code=404,
            expected_params={"Id": distribution_id, "IfMatch": "No-ETag"},
        )

    def expect_get_distribution(
        self,
        caller_reference: str,
        domains: List[str],
        certificate_id: str,
        origin_hostname: str,
        origin_path: str,
        distribution_id: str,
        status: str,
        enabled: bool = True,
        forward_cookie_policy: str = "all",
        forwarded_cookies: list = None,
        forwarded_headers: list = None,
        origin_protocol_policy: str = "https-only",
    ):
        if forwarded_headers is None:
            forwarded_headers = ["HOST"]
        self.etag = str(datetime.now().timestamp())
        distribution = self._distribution_response(
            caller_reference,
            domains,
            certificate_id,
            origin_hostname,
            origin_path,
            distribution_id,
            "ignored",
            status,
            enabled,
            forward_cookie_policy=forward_cookie_policy,
            forwarded_cookies=forwarded_cookies,
            forwarded_headers=forwarded_headers,
            origin_protocol_policy=origin_protocol_policy,
        )
        distribution["ETag"] = self.etag
        self.stubber.add_response(
            "get_distribution", distribution, {"Id": distribution_id}
        )

    def expect_get_distribution_returning_no_such_distribution(
        self, distribution_id: str
    ):
        self.stubber.add_client_error(
            "get_distribution",
            service_error_code="NoSuchDistribution",
            service_message="'Ain't there.",
            http_status_code=404,
            expected_params={"Id": distribution_id},
        )

    def expect_update_distribution(
        self,
        caller_reference: str,
        domains: List[str],
        certificate_id: str,
        origin_hostname: str,
        origin_path: str,
        distribution_id: str,
        distribution_hostname: str,
        forward_cookie_policy: str = "all",
        forwarded_cookies: list = None,
        forwarded_headers: list = None,
        origin_protocol_policy: str = "https-only",
    ):
        if forwarded_headers is None:
            forwarded_headers = ["HOST"]
        self.stubber.add_response(
            "update_distribution",
            self._distribution_response(
                caller_reference,
                domains,
                certificate_id,
                origin_hostname,
                origin_path,
                distribution_id,
                distribution_hostname,
                forward_cookie_policy=forward_cookie_policy,
                forwarded_cookies=forwarded_cookies,
                forwarded_headers=forwarded_headers,
                origin_protocol_policy=origin_protocol_policy,
            ),
            {
                "DistributionConfig": self._distribution_config(
                    caller_reference,
                    domains,
                    certificate_id,
                    origin_hostname,
                    origin_path,
                    forward_cookie_policy=forward_cookie_policy,
                    forwarded_cookies=forwarded_cookies,
                    forwarded_headers=forwarded_headers,
                    origin_protocol_policy=origin_protocol_policy,
                ),
                "Id": distribution_id,
                "IfMatch": self.etag,
            },
        )

    def _distribution_config(
        self,
        caller_reference: str,
        domains: List[str],
        iam_server_certificate_id: str,
        origin_hostname: str,
        origin_path: str,
        enabled: bool = True,
        forward_cookie_policy: str = "all",
        forwarded_cookies: list = None,
        forwarded_headers: list = None,
        origin_protocol_policy: str = "https-only",
    ) -> Dict[str, Any]:
        if forwarded_headers is None:
            forwarded_headers = ["HOST"]
        cookies = {"Forward": forward_cookie_policy}
        if forward_cookie_policy == "whitelist":
            cookies["WhitelistedNames"] = {
                "Quantity": len(forwarded_cookies),
                "Items": forwarded_cookies,
            }
        return {
            "CallerReference": caller_reference,
            "Aliases": {"Quantity": len(domains), "Items": domains},
            "DefaultRootObject": "",
            "Origins": {
                "Quantity": 1,
                "Items": [
                    {
                        "Id": "default-origin",
                        "DomainName": origin_hostname,
                        "OriginPath": origin_path,
                        "CustomOriginConfig": {
                            "HTTPPort": 80,
                            "HTTPSPort": 443,
                            "OriginProtocolPolicy": origin_protocol_policy,
                            "OriginSslProtocols": {"Quantity": 1, "Items": ["TLSv1.2"]},
                            "OriginReadTimeout": 30,
                            "OriginKeepaliveTimeout": 5,
                        },
                    }
                ],
            },
            "OriginGroups": {"Quantity": 0},
            "DefaultCacheBehavior": {
                "TargetOriginId": "default-origin",
                "ForwardedValues": {
                    "QueryString": True,
                    "Cookies": cookies,
                    "Headers": {
                        "Quantity": len(forwarded_headers),
                        "Items": forwarded_headers,
                    },
                    "QueryStringCacheKeys": {"Quantity": 0},
                },
                "TrustedSigners": {"Enabled": False, "Quantity": 0},
                "ViewerProtocolPolicy": "redirect-to-https",
                "MinTTL": 0,
                "AllowedMethods": {
                    "Quantity": 7,
                    "Items": [
                        "GET",
                        "HEAD",
                        "POST",
                        "PUT",
                        "PATCH",
                        "OPTIONS",
                        "DELETE",
                    ],
                    "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
                },
                "SmoothStreaming": False,
                "DefaultTTL": 86400,
                "MaxTTL": 31536000,
                "Compress": False,
                "LambdaFunctionAssociations": {"Quantity": 0},
            },
            "CacheBehaviors": {"Quantity": 0},
            "CustomErrorResponses": {"Quantity": 0},
            "Comment": "external domain service https://cloud-gov/external-domain-broker",
            "Logging": {
                "Enabled": False,
                "IncludeCookies": False,
                "Bucket": "",
                "Prefix": "",
            },
            "PriceClass": "PriceClass_100",
            "Enabled": enabled,
            "ViewerCertificate": {
                "CloudFrontDefaultCertificate": False,
                "IAMCertificateId": iam_server_certificate_id,
                "SSLSupportMethod": "sni-only",
                "MinimumProtocolVersion": "TLSv1.2_2018",
            },
            "IsIPV6Enabled": True,
        }

    def _distribution_response(
        self,
        caller_reference: str,
        domains: List[str],
        iam_server_certificate_id: str,
        origin_hostname: str,
        origin_path: str,
        distribution_id: str,
        distribution_hostname: str,
        status: str = "InProgress",
        enabled: bool = True,
        forward_cookie_policy: str = "all",
        forwarded_cookies: list = None,
        forwarded_headers: list = None,
        origin_protocol_policy: str = "https-only",
    ) -> Dict[str, Any]:
        if forwarded_headers is None:
            forwarded_headers = ["HOST"]
        cookies = {"Forward": forward_cookie_policy}
        if forward_cookie_policy == "whitelist":
            cookies["WhitelistedNames"] = {
                "Quantity": len(forwarded_cookies),
                "Items": forwarded_cookies,
            }
        return {
            "Distribution": {
                "Id": distribution_id,
                "ARN": f"arn:aws:cloudfront::000000000000:distribution/{distribution_id}",
                "Status": status,
                "LastModifiedTime": datetime.utcnow(),
                "InProgressInvalidationBatches": 0,
                "DomainName": distribution_hostname,
                "ActiveTrustedSigners": {"Enabled": False, "Quantity": 0, "Items": []},
                "DistributionConfig": self._distribution_config(
                    caller_reference,
                    domains,
                    iam_server_certificate_id,
                    origin_hostname,
                    origin_path,
                    enabled,
                    forward_cookie_policy,
                    forwarded_cookies,
                    forwarded_headers,
                    origin_protocol_policy,
                ),
            }
        }


@pytest.fixture(autouse=True)
def cloudfront():
    with FakeCloudFront.stubbing(real_cloudfront) as cloudfront_stubber:
        yield cloudfront_stubber
