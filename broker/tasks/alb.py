import logging
import time

from broker.aws import alb
from broker.extensions import config, db
from broker.models import ALBServiceInstance, Operation
from broker.tasks import huey

logger = logging.getLogger(__name__)


def get_lowest_used_alb(listener_arns):
    https_listeners = []
    for listener_arn in listener_arns:
        certificates = alb.describe_listener_certificates(ListenerArn=listener_arn)
        https_listeners.append(
            dict(listener_arn=listener_arn, certificates=certificates["Certificates"])
        )
    https_listeners.sort(key=lambda x: len(x["certificates"]))
    selected_arn = https_listeners[0]["listener_arn"]
    listener_data = alb.describe_listeners(ListenerArns=[selected_arn])
    listener_data = listener_data["Listeners"][0]
    return listener_data["LoadBalancerArn"], listener_data["ListenerArn"]


@huey.retriable_task
def select_alb(operation_id, **kwargs):
    operation = Operation.query.get(operation_id)
    service_instance = operation.service_instance

    operation.step_description = "Selecting load balancer"
    db.session.add(operation)
    db.session.commit()

    if (
        service_instance.alb_arn
        and operation.action == Operation.Actions.PROVISION.value
    ):
        return
    service_instance.previous_alb_listener_arn = service_instance.alb_listener_arn
    service_instance.previous_alb_arn = service_instance.alb_arn

    service_instance.alb_arn, service_instance.alb_listener_arn = get_lowest_used_alb(
        config.ALB_LISTENER_ARNS
    )
    db.session.add(service_instance)
    db.session.commit()


@huey.retriable_task
def add_certificate_to_alb(operation_id, **kwargs):
    operation = Operation.query.get(operation_id)
    service_instance = operation.service_instance
    certificate = service_instance.new_certificate

    operation.step_description = "Adding SSL certificate to load balancer"
    db.session.add(operation)
    db.session.commit()

    alb.add_listener_certificates(
        ListenerArn=service_instance.alb_listener_arn,
        Certificates=[{"CertificateArn": certificate.iam_server_certificate_arn}],
    )
    alb_config = alb.describe_load_balancers(
        LoadBalancerArns=[service_instance.alb_arn]
    )
    service_instance.domain_internal = alb_config["LoadBalancers"][0]["DNSName"]
    service_instance.route53_alias_hosted_zone = alb_config["LoadBalancers"][0][
        "CanonicalHostedZoneId"
    ]
    service_instance.current_certificate = certificate
    service_instance.new_certificate = None
    db.session.add(service_instance)
    db.session.commit()


@huey.retriable_task
def remove_certificate_from_alb(operation_id, **kwargs):
    operation = Operation.query.get(operation_id)
    service_instance = operation.service_instance

    operation.step_description = "Removing SSL certificate from load balancer"
    db.session.add(operation)
    db.session.commit()

    if service_instance.alb_listener_arn is not None:
        alb.remove_listener_certificates(
            ListenerArn=service_instance.alb_listener_arn,
            Certificates=[
                {
                    "CertificateArn": service_instance.current_certificate.iam_server_certificate_arn
                }
            ],
        )
    db.session.add(service_instance)
    db.session.commit()


@huey.retriable_task
def remove_certificate_from_previous_alb(operation_id, **kwargs):
    operation = Operation.query.get(operation_id)
    service_instance = operation.service_instance
    for certificate in service_instance.certificates:
        if certificate.id != service_instance.current_certificate_id:
            remove_certificate = certificate

    operation.step_description = "Removing SSL certificate from load balancer"
    db.session.add(operation)
    db.session.commit()

    time.sleep(int(config.DNS_PROPAGATION_SLEEP_TIME))

    if service_instance.previous_alb_listener_arn is not None:
        alb.remove_listener_certificates(
            ListenerArn=service_instance.previous_alb_listener_arn,
            Certificates=[
                {"CertificateArn": remove_certificate.iam_server_certificate_arn}
            ],
        )

    service_instance.previous_alb_arn = None
    service_instance.previous_alb_listener_arn = None
    db.session.add(service_instance)
    db.session.commit()
