from enum import Enum
from sqlalchemy.dialects import postgresql

from openbrokerapi.service_broker import OperationState
from sqlalchemy_utils.types.encrypted.encrypted_type import (
    AesGcmEngine,
    StringEncryptedType,
)

from broker.extensions import config, db


def db_encryption_key():
    return config.DATABASE_ENCRYPTION_KEY


class Base(db.Model):
    __abstract__ = True

    created_at = db.Column(db.TIMESTAMP(timezone=True), server_default=db.func.now())
    updated_at = db.Column(db.TIMESTAMP(timezone=True), onupdate=db.func.now())


class ACMEUser(Base):
    __tablename__ = "acme_user"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, nullable=False)
    uri = db.Column(db.String, nullable=False)
    private_key_pem = db.Column(
        StringEncryptedType(db.Text, db_encryption_key, AesGcmEngine, "pkcs5"),
        nullable=False,
    )

    registration_json = db.Column(db.Text)
    service_instances = db.relation(
        "ServiceInstance", backref="acme_user", lazy="dynamic"
    )


class ServiceInstance(Base):
    __tablename__ = "service_instance"
    id = db.Column(db.String(36), primary_key=True)
    operations = db.relation("Operation", backref="service_instance", lazy="dynamic")
    challenges = db.relation("Challenge", backref="service_instance", lazy="dynamic")
    acme_user_id = db.Column(db.Integer, db.ForeignKey("acme_user.id"))
    domain_names = db.Column(postgresql.JSONB, default=[])
    order_json = db.Column(db.Text)
    instance_type = db.Column(db.Text)

    csr_pem = db.Column(db.Text)
    cert_pem = db.Column(db.Text)
    cert_expires_at = db.Column(db.TIMESTAMP(timezone=True))
    private_key_pem = db.Column(
        StringEncryptedType(db.Text, db_encryption_key, AesGcmEngine, "pkcs5")
    )
    fullchain_pem = db.Column(db.Text)
    domain_internal = db.Column(db.String)

    iam_server_certificate_id = db.Column(db.String)
    iam_server_certificate_name = db.Column(db.String)
    iam_server_certificate_arn = db.Column(db.String)
    route53_alias_hosted_zone = db.Column(db.String)
    route53_change_ids = db.Column(postgresql.JSONB, default=[])

    deactivated_at = db.Column(db.TIMESTAMP(timezone=True))

    __mapper_args__ = {
        "polymorphic_identity": "service_instance",
        "polymorphic_on": instance_type,
    }

    def __repr__(self):
        return f"<ServiceInstance {self.id} {self.domain_names}>"


class CDNServiceInstance(ServiceInstance):
    class ForwardCookiePolicy(Enum):
        ALL = "all"
        NONE = "none"
        WHITELIST = "whitelist"

    cloudfront_distribution_arn = db.Column(db.String)
    cloudfront_distribution_id = db.Column(db.String)
    cloudfront_origin_hostname = db.Column(db.String)
    cloudfront_origin_path = db.Column(db.String)
    forward_cookie_policy = db.Column(db.String, default=ForwardCookiePolicy.ALL.value)
    forwarded_cookies = db.Column(postgresql.JSONB, default=[])
    forwarded_headers = db.Column(postgresql.JSONB, default=[])

    __mapper_args__ = {"polymorphic_identity": "cdn_service_instance"}

    def __repr__(self):
        return f"<CDNServiceInstance {self.id} {self.domain_names}>"


class ALBServiceInstance(ServiceInstance):
    alb_arn = db.Column(db.String)
    alb_listener_arn = db.Column(db.String)

    __mapper_args__ = {"polymorphic_identity": "alb_service_instance"}

    def __repr__(self):
        return f"<ALBServiceInstance {self.id} {self.domain_names}>"


class Operation(Base):
    # operation.state = Operation.States.IN_PROGRESS.value
    States = OperationState

    # operation.action = Operation.Actions.PROVISION.value
    class Actions(Enum):
        PROVISION = "Provision"
        DEPROVISION = "Deprovision"
        RENEW = "Renew"

    id = db.Column(db.Integer, primary_key=True)
    service_instance_id = db.Column(
        db.String, db.ForeignKey("service_instance.id"), nullable=False
    )
    state = db.Column(
        db.String,
        default=States.IN_PROGRESS.value,
        server_default=States.IN_PROGRESS.value,
        nullable=False,
    )
    action = db.Column(db.String, nullable=False)
    canceled_at = db.Column(db.TIMESTAMP(timezone=True))
    step_description = db.Column(db.String)

    def __repr__(self):
        return f"<Operation {self.id} {self.state}>"


class Challenge(Base):
    id = db.Column(db.Integer, primary_key=True)
    service_instance_id = db.Column(
        db.String, db.ForeignKey("service_instance.id"), nullable=False
    )
    domain = db.Column(db.String, nullable=False)
    validation_domain = db.Column(db.String, nullable=False)
    validation_contents = db.Column(db.Text, nullable=False)
    body_json = db.Column(db.Text)
    answered = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<Challenge {self.id} {self.domain}>"
