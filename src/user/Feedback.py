# Copyright (c) 2024.
"""Tools for handling user feedback"""

from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi import Response as FastAPIResponse
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from common.JWTValidator import get_jwt
from migrations.models import UserFeedback
from migrations.session import get_db
from user.GetAgent import check_uuid_format
from utils.response import Response, Responses

router = APIRouter()


class RatingData(BaseModel):
    """Database model for saving user feedback data"""

    thread_id: str
    rating: int
    message_id: str = ""
    comments: str = ""


@router.post("/rating")
def submit_rating(
    request: Request,
    response: FastAPIResponse,
    rating_data: RatingData,
    db: Annotated[Session, Depends(get_db)],
) -> Response[None]:
    """Gets the settings of an agent by its ID

    Args:
        request: The FastAPI request object
        response: The FastAPI response object
        rating_data: The rating to submit
        db: The database session

    Returns:
        OK if worked correctly, BAD_REQUEST otherwise

    """
    if not check_uuid_format(rating_data.thread_id):
        return Responses[None].response(
            response,
            False,
            status=HTTPStatus.BAD_REQUEST,
            message="Invalid UUID format",
        )
    user_jwt_content = get_jwt(request.state)

    try:
        rating_data.rating = int(rating_data.rating)

        if (rating_data.message_id and rating_data.rating in {0, 1}) or (
            not rating_data.message_id
            and rating_data.rating > 0
            and rating_data.rating <= 5  # noqa: PLR2004 This just means 5* rating, we can make this a constant if we want
        ):
            db.add(
                UserFeedback(
                    user_id=user_jwt_content["user_id"],
                    thread_id=rating_data.thread_id,
                    message_id=rating_data.message_id,
                    rating_format=2 if rating_data.message_id else 5,
                    rating=rating_data.rating,
                    comments=rating_data.comments,
                ),
            )
            db.commit()
            return Responses[None].response(response, True, status=HTTPStatus.OK)
        return Responses[None].response(
            response,
            False,
            status=HTTPStatus.BAD_REQUEST,
            message="Invalid rating value",
        )
    except ValueError:
        return Responses[None].response(
            response,
            False,
            status=HTTPStatus.BAD_REQUEST,
            message="Rating value was non-integer",
        )
    except IntegrityError:
        db.rollback()
        return Responses[None].response(
            response,
            False,
            status=HTTPStatus.BAD_REQUEST,
            message="Could not submit feedback",
        )
    except Exception as e:
        db.rollback()
        return Responses[None].response(
            response, False, status=HTTPStatus.BAD_REQUEST, message=str(e)
        )
