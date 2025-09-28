import asyncio
import inspect
import sys
from datetime import datetime, timezone, timedelta, date

from msgraph.generated.models.invited_user_message_info import InvitedUserMessageInfo
from msgraph.generated.models.user import User
from msgraph.generated.models.user_collection_response import UserCollectionResponse
from msgraph.generated.users.get_by_ids.get_by_ids_post_request_body import GetByIdsPostRequestBody
from msgraph.generated.models.invitation import Invitation

from Database import DatabaseClient
from Database.Models import Guests
from API.Clients import MSGraphClient
from API.Exceptions.MSGraphErrors import InvalidUserFilterError


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
                            email: str,
                            inviter: str,
                            display_name: str,
                            user_type: str = "Guest",
                            reset_redemption: bool = False,
                            custom_message: str | None = None,
                            expires_at: str | date = datetime.now(timezone.utc) + timedelta(days=30),
                            redirect_url: str = "https://myaccount.microsoft.com/organizations") -> Invitation:
    """
    Returns all the users in the system.

    :param user_type: User type(Guest or Member)
    :param _dbClient: Database client object
    :param display_name: The display name of the user being invited
    :param reset_redemption: Reset the user's redemption status and reinvite a user
    :param custom_message: Custom message which user will receive
    :param inviter: Email who send the invite
    :param expires_at: When the user's access expires
    :param _client: MSGraphClient object
    :param email: The email address of the user being invited
    :param redirect_url: The URL the user should be redirected to after the invitation is redeemed

    :return: Invitation object
    """
    if user_type.lower() not in ["guest", "member"]:
        raise ValueError("Invalid user type. Must be 'guest' or 'member'")

    client = _client.client

    invite = Invitation(
        invited_user_display_name=display_name,
        invited_user_email_address=email,
        invite_redirect_url=redirect_url,
        send_invitation_message=True,
        invited_user_type=user_type.capitalize(),
        reset_redemption=reset_redemption,
        invited_user_message_info=InvitedUserMessageInfo(
            customized_message_body=custom_message
        )
    )

    response = await client.invitations.post(invite)


    if response and response.invited_user.id is not None:
        async with _dbClient.session("main") as session:
            row = Guests(
                guest_email=email,
                guest_name=display_name,
                guest_upn=response.invited_user.user_principal_name,
                inviter_email=inviter,
                is_guest=True,
                expires_at=expires_at if
                isinstance(expires_at, datetime) else
                datetime.fromisoformat(expires_at) if
                "T" in expires_at else
                datetime.strptime(expires_at, "%Y-%m-%d"),
            )
            session.add(row)
    return response



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