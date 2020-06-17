from datetime import datetime
import pytest

from broker.aws import alb as real_alb
from tests.lib.fake_aws import FakeAWS


class FakeALB(FakeAWS):
    def expect_get_listeners_for_alb(self, alb_arn, num_certificates: int = 1):
        certificates = [{"CertificateArn": "certificate-arn", "IsDefault": True}]
        for i in range(num_certificates - 1):
            certificates.append(
                {"CertificateArn": f"certificate-arn-{i}", "IsDefault": False}
            )
        self.stubber.add_response(
            "describe_listeners",
            {
                "Listeners": [
                    {
                        "ListenerArn": "httplistenerarn",
                        "LoadBalancerArn": alb_arn,
                        "Port": 80,
                        "Protocol": "HTTP",
                        "DefaultActions": [
                            {
                                "Type": "forward",
                                "TargetGroupArn": "arn",
                                "Order": 1,
                                "ForwardConfig": {
                                    "TargetGroups": [
                                        {"TargetGroupArn": "string", "Weight": 123}
                                    ],
                                    "TargetGroupStickinessConfig": {"Enabled": False},
                                },
                            }
                        ],
                    },
                    {
                        "ListenerArn": "httpslistenerarn",
                        "LoadBalancerArn": "string",
                        "Port": 123,
                        "Protocol": "HTTPS",
                        "Certificates": certificates,
                        "SslPolicy": "string",
                        "DefaultActions": [
                            {
                                "Type": "forward",
                                "TargetGroupArn": "string",
                                "Order": 1,
                                "ForwardConfig": {
                                    "TargetGroups": [
                                        {"TargetGroupArn": "string", "Weight": 1}
                                    ],
                                    "TargetGroupStickinessConfig": {"Enabled": False},
                                },
                            }
                        ],
                    },
                ],
                "NextMarker": "string",
            },
            {"LoadBalancerArn": alb_arn},
        )

    def expect_add_certificate_to_listener(self, alb_arn, iam_cert_arn):
        self.stubber.add_response(
            "add_listener_certificates",
            {
                "Certificates": [
                    {"CertificateArn": "arn:2", "IsDefault": True},
                    {"CertificateArn": iam_cert_arn, "IsDefault": False},
                ]
            },
            {
                "ListenerArn": "httpslistenerarn",
                "Certificates": [{"CertificateArn": iam_cert_arn, "IsDefault": False}],
            },
        )

    def expect_remove_certificate_from_listener(self, alb_arn, iam_cert_arn):
        self.stubber.add_response(
            "remove_listener_certificates",
            {},
            {
                "ListenerArn": "httpslistenerarn",
                "Certificates": [{"CertificateArn": iam_cert_arn, "IsDefault": False}],
            },
        )

    def expect_describe_alb(
        self, alb_arn, returned_domain: str = "somedomain.cloud.test"
    ):
        self.stubber.add_response(
            "describe_load_balancers",
            {
                "LoadBalancers": [
                    {
                        "LoadBalancerArn": "alb_arn",
                        "DNSName": returned_domain,
                        "CanonicalHostedZoneId": "string",
                        "CreatedTime": datetime(2015, 1, 1),
                        "LoadBalancerName": "string",
                        "Scheme": "internet-facing",
                        "VpcId": "string",
                        "State": {"Code": "active", "Reason": "string"},
                        "Type": "application",
                        "AvailabilityZones": [
                            {
                                "ZoneName": "string",
                                "SubnetId": "string",
                                "LoadBalancerAddresses": [
                                    {
                                        "IpAddress": "string",
                                        "AllocationId": "string",
                                        "PrivateIPv4Address": "string",
                                    }
                                ],
                            }
                        ],
                        "SecurityGroups": ["string"],
                        "IpAddressType": "ipv4",
                    }
                ],
                "NextMarker": "string",
            },
            {"LoadBalancerArns": [alb_arn]},
        )


@pytest.fixture(autouse=True)
def alb():
    with FakeALB.stubbing(real_alb) as alb_stubber:
        yield alb_stubber
