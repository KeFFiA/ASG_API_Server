import asyncio
import inspect
import sys
from datetime import datetime

from msgraph.generated.models.invited_user_message_info import InvitedUserMessageInfo
from msgraph.generated.models.user import User
from msgraph.generated.models.user_collection_response import UserCollectionResponse
from msgraph.generated.users.get_by_ids.get_by_ids_post_request_body import GetByIdsPostRequestBody
from msgraph.generated.models.invitation import Invitation

from Database import DatabaseClient
from Database.Models import Guests
from API.Clients import MSGraphClient
from API.Exceptions.MSGraphErrors import InvalidUserFilterError
from Schemas import InviteUserSchema
from Schemas.Enums.MSGraphAPI import UserTypesEnum


async def get_users(_client: MSGraphClient = MSGraphClient()) -> UserCollectionResponse:
    """
    Returns all the users in the system.

    :param _client: MSGraphClient object
    :return: Users collection object
    """

    client = _client.client

    try:
        users = await client.users.get()
        if users and users.value:
            print(users)
            return users
        else:
            raise LookupError("Users not found")
    except Exception as _ex:
        raise Exception(_ex)


async def get_user(_client: MSGraphClient = MSGraphClient().client, **kwargs) -> User:
    """
    Returns one user by ONE filter

    :param _client: MSGraphClient object
    :param kwargs: Any of user information field
    :return: User object
    """

    if len(kwargs) != 1:
        raise InvalidUserFilterError()

    client = _client.client

    key, value = next(iter(kwargs.items()))

    try:
        if "id" in key:
            try:
                response = await client.users.get_by_ids.post(body=GetByIdsPostRequestBody(ids=[value], types=["user"]))
            except Exception as _ex:
                raise LookupError(f"User with {key}={value} not found")
        else:
            response = await client.users.get()

        if response and response.value:
            for user in response.value:
                if getattr(user, key) == value:
                    print(user)
                    return user

        raise LookupError(f"User with {key}={value} not found")

    except Exception as _ex:
        raise Exception(_ex)


async def invite_guest_user(_client: MSGraphClient = MSGraphClient(),
                            _dbClient: DatabaseClient = DatabaseClient(),
                            *,
                            data: InviteUserSchema) -> Invitation:
    """
    Returns all the users in the system.

    :param data: InviteUserSchema
    :param _dbClient: Database client object
    :param _client: MSGraphClient object

    :return: Invitation object
    """
    if data.user_type.lower() not in ["guest", "member"]:
        raise ValueError("Invalid user type. Must be 'guest' or 'member'")

    client = _client.client

    invite = Invitation(
        invited_user_display_name=data.user_displayName,
        invited_user_email_address=str(data.user_email),
        invite_redirect_url=str(data.redirect_url),
        send_invitation_message=True,
        invited_user_type=data.user_type,
        reset_redemption=data.reset_redemption,
        invited_user_message_info=InvitedUserMessageInfo(
            customized_message_body=data.custom_message
        )
    )
    try:
        response = await client.invitations.post(invite)

        if response and response.invited_user.id is not None:
            async with _dbClient.session("main") as session:
                row = Guests(
                    guest_email=str(data.user_email),
                    guest_name=data.user_displayName,
                    guest_upn=response.invited_user.user_principal_name,
                    inviter_email=str(data.inviter_email),
                    is_guest=data.user_type == UserTypesEnum.GUEST,
                    expires_at=data.expires_at,
                )
                session.add(row)
        return response

    except Exception as _ex:
        raise _ex




_current_module = sys.modules[__name__]

__all__ = [
    name
    for name, obj in globals().items()
    if inspect.isfunction(obj) and obj.__module__ == __name__
]

if __name__ == '__main__':
    asyncio.run(invite_guest_user(
        email="ogienko.12003@gmail.com",
        inviter="alexander.ogienko@formagiclife.com",
        display_name="Alexander TestUser",
        custom_message="Test invite user message",
        user_type='guest'
    )
    )