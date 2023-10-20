# flake8: noqa
# pylint: skip-file
# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

from google.protobuf import wrappers_pb2 as google_dot_protobuf_dot_wrappers__pb2
from upsf_client.protos import (
    messages_v1_pb2 as upsf__client_dot_protos_dot_messages__v1__pb2,
)
from upsf_client.protos import (
    service_v1_pb2 as upsf__client_dot_protos_dot_service__v1__pb2,
)


class upsfStub(object):
    """sssUpsf provides a set of services that will be exposed by the UPSF."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.CreateV1 = channel.unary_unary(
            "/wt474_upsf_service.v1.upsf/CreateV1",
            request_serializer=upsf__client_dot_protos_dot_messages__v1__pb2.Item.SerializeToString,
            response_deserializer=upsf__client_dot_protos_dot_messages__v1__pb2.Item.FromString,
        )
        self.ReadV1 = channel.unary_stream(
            "/wt474_upsf_service.v1.upsf/ReadV1",
            request_serializer=upsf__client_dot_protos_dot_service__v1__pb2.ReadReq.SerializeToString,
            response_deserializer=upsf__client_dot_protos_dot_messages__v1__pb2.Item.FromString,
        )
        self.UpdateV1 = channel.unary_unary(
            "/wt474_upsf_service.v1.upsf/UpdateV1",
            request_serializer=upsf__client_dot_protos_dot_service__v1__pb2.UpdateReq.SerializeToString,
            response_deserializer=upsf__client_dot_protos_dot_messages__v1__pb2.Item.FromString,
        )
        self.DeleteV1 = channel.unary_unary(
            "/wt474_upsf_service.v1.upsf/DeleteV1",
            request_serializer=google_dot_protobuf_dot_wrappers__pb2.StringValue.SerializeToString,
            response_deserializer=google_dot_protobuf_dot_wrappers__pb2.StringValue.FromString,
        )
        self.LookupV1 = channel.unary_unary(
            "/wt474_upsf_service.v1.upsf/LookupV1",
            request_serializer=upsf__client_dot_protos_dot_messages__v1__pb2.SessionContext.Spec.SerializeToString,
            response_deserializer=upsf__client_dot_protos_dot_messages__v1__pb2.SessionContext.FromString,
        )


class upsfServicer(object):
    """sssUpsf provides a set of services that will be exposed by the UPSF."""

    def CreateV1(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")

    def ReadV1(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")

    def UpdateV1(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")

    def DeleteV1(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")

    def LookupV1(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")


def add_upsfServicer_to_server(servicer, server):
    rpc_method_handlers = {
        "CreateV1": grpc.unary_unary_rpc_method_handler(
            servicer.CreateV1,
            request_deserializer=upsf__client_dot_protos_dot_messages__v1__pb2.Item.FromString,
            response_serializer=upsf__client_dot_protos_dot_messages__v1__pb2.Item.SerializeToString,
        ),
        "ReadV1": grpc.unary_stream_rpc_method_handler(
            servicer.ReadV1,
            request_deserializer=upsf__client_dot_protos_dot_service__v1__pb2.ReadReq.FromString,
            response_serializer=upsf__client_dot_protos_dot_messages__v1__pb2.Item.SerializeToString,
        ),
        "UpdateV1": grpc.unary_unary_rpc_method_handler(
            servicer.UpdateV1,
            request_deserializer=upsf__client_dot_protos_dot_service__v1__pb2.UpdateReq.FromString,
            response_serializer=upsf__client_dot_protos_dot_messages__v1__pb2.Item.SerializeToString,
        ),
        "DeleteV1": grpc.unary_unary_rpc_method_handler(
            servicer.DeleteV1,
            request_deserializer=google_dot_protobuf_dot_wrappers__pb2.StringValue.FromString,
            response_serializer=google_dot_protobuf_dot_wrappers__pb2.StringValue.SerializeToString,
        ),
        "LookupV1": grpc.unary_unary_rpc_method_handler(
            servicer.LookupV1,
            request_deserializer=upsf__client_dot_protos_dot_messages__v1__pb2.SessionContext.Spec.FromString,
            response_serializer=upsf__client_dot_protos_dot_messages__v1__pb2.SessionContext.SerializeToString,
        ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
        "wt474_upsf_service.v1.upsf", rpc_method_handlers
    )
    server.add_generic_rpc_handlers((generic_handler,))


# This class is part of an EXPERIMENTAL API.
class upsf(object):
    """sssUpsf provides a set of services that will be exposed by the UPSF."""

    @staticmethod
    def CreateV1(
        request,
        target,
        options=(),
        channel_credentials=None,
        call_credentials=None,
        insecure=False,
        compression=None,
        wait_for_ready=None,
        timeout=None,
        metadata=None,
    ):
        return grpc.experimental.unary_unary(
            request,
            target,
            "/wt474_upsf_service.v1.upsf/CreateV1",
            upsf__client_dot_protos_dot_messages__v1__pb2.Item.SerializeToString,
            upsf__client_dot_protos_dot_messages__v1__pb2.Item.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
        )

    @staticmethod
    def ReadV1(
        request,
        target,
        options=(),
        channel_credentials=None,
        call_credentials=None,
        insecure=False,
        compression=None,
        wait_for_ready=None,
        timeout=None,
        metadata=None,
    ):
        return grpc.experimental.unary_stream(
            request,
            target,
            "/wt474_upsf_service.v1.upsf/ReadV1",
            upsf__client_dot_protos_dot_service__v1__pb2.ReadReq.SerializeToString,
            upsf__client_dot_protos_dot_messages__v1__pb2.Item.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
        )

    @staticmethod
    def UpdateV1(
        request,
        target,
        options=(),
        channel_credentials=None,
        call_credentials=None,
        insecure=False,
        compression=None,
        wait_for_ready=None,
        timeout=None,
        metadata=None,
    ):
        return grpc.experimental.unary_unary(
            request,
            target,
            "/wt474_upsf_service.v1.upsf/UpdateV1",
            upsf__client_dot_protos_dot_service__v1__pb2.UpdateReq.SerializeToString,
            upsf__client_dot_protos_dot_messages__v1__pb2.Item.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
        )

    @staticmethod
    def DeleteV1(
        request,
        target,
        options=(),
        channel_credentials=None,
        call_credentials=None,
        insecure=False,
        compression=None,
        wait_for_ready=None,
        timeout=None,
        metadata=None,
    ):
        return grpc.experimental.unary_unary(
            request,
            target,
            "/wt474_upsf_service.v1.upsf/DeleteV1",
            google_dot_protobuf_dot_wrappers__pb2.StringValue.SerializeToString,
            google_dot_protobuf_dot_wrappers__pb2.StringValue.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
        )

    @staticmethod
    def LookupV1(
        request,
        target,
        options=(),
        channel_credentials=None,
        call_credentials=None,
        insecure=False,
        compression=None,
        wait_for_ready=None,
        timeout=None,
        metadata=None,
    ):
        return grpc.experimental.unary_unary(
            request,
            target,
            "/wt474_upsf_service.v1.upsf/LookupV1",
            upsf__client_dot_protos_dot_messages__v1__pb2.SessionContext.Spec.SerializeToString,
            upsf__client_dot_protos_dot_messages__v1__pb2.SessionContext.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
        )
