import pytest  # noqa F401

from broker.extensions import db
from broker.models import Operation, CdnServiceInstance
from tests.lib import factories


@pytest.fixture
def service_instance():
    service_instance = factories.CdnServiceInstanceFactory.create(
        id="1234",
        domain_names=["example.com", "foo.com"],
        iam_server_certificate_id="certificate_id",
        iam_server_certificate_name="certificate_name",
        cloudfront_distribution_url="fake1234.cloudfront.net",
        cloudfront_distribution_id="FakeDistributionId",
        cloudfront_origin_hostname="origin_hostname",
        cloudfront_origin_path="origin_path",
        private_key_pem="SOMEPRIVATEKEY",
    )
    factories.ChallengeFactory.create(
        domain="example.com",
        validation_contents="example txt",
        service_instance=service_instance,
    )
    factories.ChallengeFactory.create(
        domain="foo.com",
        validation_contents="foo txt",
        service_instance=service_instance,
    )
    db.session.refresh(service_instance)
    return service_instance


def test_refuses_to_deprovision_synchronously(client, service_instance):
    client.deprovision_cdn_instance(service_instance.id, accepts_incomplete="false")

    assert "AsyncRequired" in client.response.body
    assert client.response.status_code == 422


def test_refuses_to_deprovision_synchronously_by_default(client, service_instance):
    client.deprovision_cdn_instance(service_instance.id, accepts_incomplete="")

    assert "AsyncRequired" in client.response.body
    assert client.response.status_code == 422


def test_deprovision_continues_when_resources_dont_exist(
    client, service_instance, dns, tasks, route53, iam, simple_regex, cloudfront
):
    subtest_deprovision_creates_deprovision_operation(client, service_instance)
    subtest_deprovision_removes_ALIAS_records(tasks, route53)
    subtest_deprovision_removes_TXT_records(tasks, route53)

    subtest_deprovision_disables_cloudfront_distribution_when_missing(
        tasks, service_instance, cloudfront
    )
    subtest_deprovision_waits_for_cloudfront_distribution_disabled_when_missing(
        tasks, service_instance, cloudfront
    )
    subtest_deprovision_removes_cloudfront_distribution_when_missing(
        tasks, service_instance, cloudfront
    )
    subtest_deprovision_removes_certificate_from_iam_when_missing(
        tasks, service_instance, iam
    )


def test_deprovision_happy_path(
    client, service_instance, dns, tasks, route53, iam, simple_regex, cloudfront
):
    subtest_deprovision_creates_deprovision_operation(client, service_instance)
    subtest_deprovision_removes_ALIAS_records(tasks, route53)
    subtest_deprovision_removes_TXT_records(tasks, route53)
    subtest_deprovision_disables_cloudfront_distribution(
        tasks, service_instance, cloudfront
    )
    subtest_deprovision_waits_for_cloudfront_distribution_disabled(
        tasks, service_instance, cloudfront
    )
    subtest_deprovision_removes_cloudfront_distribution(
        tasks, service_instance, cloudfront
    )
    subtest_deprovision_removes_certificate_from_iam(tasks, service_instance, iam)
    subtest_deprovision_marks_operation_as_succeeded(tasks)


def subtest_deprovision_creates_deprovision_operation(client, service_instance):
    client.deprovision_cdn_instance(service_instance.id, accepts_incomplete="true")

    assert client.response.status_code == 202, client.response.body
    assert "operation" in client.response.json

    operation_id = client.response.json["operation"]
    operation = Operation.query.get(operation_id)

    assert operation is not None
    assert operation.state == Operation.States.IN_PROGRESS.value
    assert operation.action == Operation.Actions.DEPROVISION.value
    assert operation.service_instance_id == service_instance.id


def subtest_deprovision_removes_ALIAS_records(tasks, route53):
    route53.expect_remove_ALIAS(
        "example.com.domains.cloud.test", "fake1234.cloudfront.net"
    )
    route53.expect_remove_ALIAS("foo.com.domains.cloud.test", "fake1234.cloudfront.net")

    tasks.run_queued_tasks_and_enqueue_dependents()

    route53.assert_no_pending_responses()


def subtest_deprovision_removes_TXT_records(tasks, route53):
    route53.expect_remove_TXT(
        "_acme-challenge.example.com.domains.cloud.test", "example txt"
    )
    route53.expect_remove_TXT("_acme-challenge.foo.com.domains.cloud.test", "foo txt")

    tasks.run_queued_tasks_and_enqueue_dependents()

    route53.assert_no_pending_responses()


def subtest_deprovision_disables_cloudfront_distribution(
    tasks, service_instance, cloudfront
):
    cloudfront.expect_get_distribution_config(
        caller_reference=service_instance.id,
        domains=service_instance.domain_names,
        certificate_id=service_instance.iam_server_certificate_id,
        origin_hostname=service_instance.cloudfront_origin_hostname,
        origin_path=service_instance.cloudfront_origin_path,
        distribution_id=service_instance.cloudfront_distribution_id,
    )
    cloudfront.expect_disable_distribution(
        caller_reference=service_instance.id,
        domains=service_instance.domain_names,
        certificate_id=service_instance.iam_server_certificate_id,
        origin_hostname=service_instance.cloudfront_origin_hostname,
        origin_path=service_instance.cloudfront_origin_path,
        distribution_id=service_instance.cloudfront_distribution_id,
        distribution_hostname=service_instance.cloudfront_distribution_url,
    )
    tasks.run_queued_tasks_and_enqueue_dependents()
    cloudfront.assert_no_pending_responses()


def subtest_deprovision_waits_for_cloudfront_distribution_disabled(
    tasks, service_instance, cloudfront
):
    cloudfront.expect_get_distribution(
        caller_reference=service_instance.id,
        domains=service_instance.domain_names,
        certificate_id=service_instance.iam_server_certificate_id,
        origin_hostname=service_instance.cloudfront_origin_hostname,
        origin_path=service_instance.cloudfront_origin_path,
        distribution_id=service_instance.cloudfront_distribution_id,
        status="Deployed",
        enabled=True,
    )
    cloudfront.expect_get_distribution(
        caller_reference=service_instance.id,
        domains=service_instance.domain_names,
        certificate_id=service_instance.iam_server_certificate_id,
        origin_hostname=service_instance.cloudfront_origin_hostname,
        origin_path=service_instance.cloudfront_origin_path,
        distribution_id=service_instance.cloudfront_distribution_id,
        status="Deployed",
        enabled=False,
    )
    tasks.run_queued_tasks_and_enqueue_dependents()

    cloudfront.assert_no_pending_responses()


def subtest_deprovision_removes_cloudfront_distribution(
    tasks, service_instance, cloudfront
):
    cloudfront.expect_delete_distribution(
        distribution_id=service_instance.cloudfront_distribution_id
    )
    tasks.run_queued_tasks_and_enqueue_dependents()
    cloudfront.assert_no_pending_responses()


def subtest_deprovision_disables_cloudfront_distribution_when_missing(
    tasks, service_instance, cloudfront
):
    cloudfront.expect_get_distribution_config_returning_no_such_distribution(
        distribution_id=service_instance.cloudfront_distribution_id
    )
    tasks.run_queued_tasks_and_enqueue_dependents()
    cloudfront.assert_no_pending_responses()


def subtest_deprovision_waits_for_cloudfront_distribution_disabled_when_missing(
    tasks, service_instance, cloudfront
):
    cloudfront.expect_get_distribution_returning_no_such_distribution(
        distribution_id=service_instance.cloudfront_distribution_id
    )
    tasks.run_queued_tasks_and_enqueue_dependents()

    cloudfront.assert_no_pending_responses()


def subtest_deprovision_removes_cloudfront_distribution_when_missing(
    tasks, service_instance, cloudfront
):
    cloudfront.expect_delete_distribution_returning_no_such_distribution(
        distribution_id=service_instance.cloudfront_distribution_id
    )
    tasks.run_queued_tasks_and_enqueue_dependents()
    cloudfront.assert_no_pending_responses()


def subtest_deprovision_removes_certificate_from_iam(tasks, service_instance, iam):
    iam.expects_delete_server_certificate(service_instance.iam_server_certificate_name)
    tasks.run_queued_tasks_and_enqueue_dependents()
    iam.assert_no_pending_responses()


def subtest_deprovision_removes_certificate_from_iam_when_missing(
    tasks, service_instance, iam
):
    iam.expects_delete_server_certificate_returning_no_such_entity(
        name=service_instance.iam_server_certificate_name
    )
    tasks.run_queued_tasks_and_enqueue_dependents()
    iam.assert_no_pending_responses()


def subtest_deprovision_marks_operation_as_succeeded(tasks):
    db.session.expunge_all()
    service_instance = CdnServiceInstance.query.get("1234")
    assert not service_instance.deactivated_at

    tasks.run_queued_tasks_and_enqueue_dependents()

    db.session.expunge_all()
    service_instance = CdnServiceInstance.query.get("1234")
    assert service_instance.deactivated_at
    assert not service_instance.private_key_pem

    operation = service_instance.operations.first()
    assert operation.state == "succeeded"
