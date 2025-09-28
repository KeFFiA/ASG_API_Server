from uuid import UUID

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from API.Utils import create_or_update_subscription
from Config import setup_logger, MS_WEBHOOK_SECRET
from Schemas import SuccessResponse, ErrorResponse
from Schemas.Enums import service

logger = setup_logger(name="webhooks")

router = APIRouter(
    prefix="/webhooks",
    tags=[service.APITagsEnum.WEBHOOK],
)


MSGraphWebhookResponses = {
    200: {"model": SuccessResponse, "description": "Success"},
    510: {"model": ErrorResponse, "description": "Client state not authorized"},
    500: {"model": ErrorResponse, "description": "Server error"},
}


@router.post("/microsoft",
             status_code=status.HTTP_200_OK,
             responses=MSGraphWebhookResponses,
             summary="MicrosoftGraph",
             description="Receive webhook from Microsoft Graph",
             )
async def microsoft(request: Request):
    logger.info("[MicrosoftGraph] Webhook received")
    data = await request.json()

    # validationToken check
    validation_token = data.get("validationToken")
    if validation_token:
        logger.info("[MicrosoftGraph] Validation token received, responding with plain text")
        return JSONResponse(
            content=validation_token,
            media_type="text/plain",
            status_code=200
        )

    # clientState check
    for value in data.get("value", []):
        if value.get("clientState") != MS_WEBHOOK_SECRET:
            logger.info("[MicrosoftGraph] Webhook clientState({}) not recognised".format(value.get("clientState")))

            error_response = ErrorResponse(
                correlationId=request.state.correlation_id,
                description=f"{value.get('clientState')} code not authorized",
                code=str(status.HTTP_510_NOT_EXTENDED),
            )

            return JSONResponse(status_code=status.HTTP_510_NOT_EXTENDED, content=error_response.model_dump())

    for event in data.get("value", []):
        user_id = event["resourceData"]["id"]
    #     TODO: Final this shit

MSGraphWebhookResponses.pop(200)
MSGraphWebhookResponses[202] = {"model": SuccessResponse, "description": "Accepted"}

@router.post("/microsoft/lifecycle",
             status_code=status.HTTP_202_ACCEPTED,
             responses=MSGraphWebhookResponses,
             summary="MicrosoftGraph lifecycle",
             description="Receive lifecycle webhook from Microsoft Graph",
             )
async def microsoft_lifecycle(request: Request):
    logger.info("[MicrosoftGraph] Lifecycle webhook received")
    data = await request.json()

    # validationToken check
    validation_token = data.get("validationToken")
    if validation_token:
        logger.info("[MicrosoftGraph] Validation token received, responding with plain text")
        return JSONResponse(
            content=validation_token,
            media_type="text/plain",
            status_code=200
        )

    # clientState check

    for value in data.get("value", []):
        if value.get("clientState") != MS_WEBHOOK_SECRET:
            logger.info(
                "[MicrosoftGraph] Lifecycle webhook clientState({}) not recognised".format(value.get("clientState")))

            error_response = ErrorResponse(
                correlationId=request.state.correlation_id,
                description=f"{value.get('clientState')} code not authorized",
                code=str(status.HTTP_510_NOT_EXTENDED),
            )

            return JSONResponse(status_code=status.HTTP_510_NOT_EXTENDED, content=error_response.model_dump())
        if value.get("lifecycleEvent") == "reauthorizationRequired":
            subscription_id = value.get("subscriptionId")
            await create_or_update_subscription(subscription_id=subscription_id, db_proxy=request.state.db)
            success_response = SuccessResponse(
                correlationId=request.state.correlation_id,
                detail="Subscription reauthorized",
            )
            return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=success_response.model_dump())
