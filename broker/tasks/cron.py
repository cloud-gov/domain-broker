import datetime

from huey import crontab

from broker.extensions import config, db
from broker.models import ServiceInstance, Operation
from broker.tasks import huey, pipelines


@huey.huey.periodic_task(
    crontab(month="*", hour="*", day="*", minute="13"),
    context=huey.huey.flask_app.app_context(),
)
def scan_for_expiring_certs():
    # TODO: skip SIs with active operations
    instances = ServiceInstance.query.filter(
        ServiceInstance.cert_expires_at - datetime.timedelta(days=10)
        < datetime.datetime.now()
    ).all()
    cdn_renewals = []
    alb_renewals = []
    for instance in instances:
        renewal = Operation(
            state=Operation.States.IN_PROGRESS.value,
            service_instance=instance,
            action=Operation.Actions.RENEW.value,
            step_description="Queuing tasks",
        )
        db.session.add(renewal)
        if instance.instance_type == "cdn_service_instance":
            cdn_renewals.append(renewal)
        else:
            alb_renewals.append(renewal)
    db.session.commit()
    for renewal in cdn_renewals:
        pipelines.queue_all_cdn_renewal_tasks_for_service_instance(renewal.id)
    for renewal in alb_renewals:
        pipelines.queue_all_alb_renewal_tasks_for_service_instance(renewal.id)

    # n.b. this return is only for testing - huey ignores it.
    return [instance.id for instance in instances]


@huey.huey.periodic_task(
    crontab(month="*", hour="*", day="*", minute="13"),
    context=huey.huey.flask_app.app_context(),
)
def restart_stalled_pipelines():
    for operation in scan_for_stalled_pipelines():
        reschedule_operation(operation)


def scan_for_stalled_pipelines():
    two_hours_ago = datetime.datetime.now() - datetime.timedelta(hours=2)
    operations = Operation.query.filter(
        Operation.state == Operation.States.IN_PROGRESS.value,
        Operation.updated_at <= two_hours_ago,
        Operation.canceled_at.is_(None),
    )
    return [operation.id for operation in operations]


def reschedule_operation(operation):
    service_instance = operation.service_instance
    if service_instance.instance_type == "cdn_service_instance":
        if operation.action == Operation.Actions.PROVISION.value:
            pipelines.queue_all_cdn_provision_tasks_for_operation(operation.id, "recovered pipeline")
        elif operation.action == Operation.Actions.DEPROVISION.value:
            pipelines.queue_all_cdn_deprovision_tasks_for_operation(operation.id, "recovered pipeline")
        elif operation.action == Operation.Actions.RENEW.value:
            pipelines.queue_all_cdn_renewal_tasks_for_service_instance(operation.id, "recovered pipeline")
    elif service_instance.instance_type == "alb_service_instance":
        if operation.action == Operation.Actions.PROVISION.value:
            pipelines.queue_all_alb_provision_tasks_for_operation(operation.id, "recovered pipeline")
        elif operation.action == Operation.Actions.DEPROVISION.value:
            pipelines.queue_all_alb_deprovision_tasks_for_operation(operation.id, "recovered pipeline")
        elif operation.action == Operation.Actions.RENEW.value:
            pipelines.queue_all_alb_renewal_tasks_for_service_instance(operation.id, "recovered pipeline")
