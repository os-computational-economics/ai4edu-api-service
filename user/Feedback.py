from typing import Annotated
from fastapi import APIRouter, Depends, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from common.JWTValidator import getJWT
from migrations.models import UserFeedback
from utils.response import response
from user.GetAgent import check_uuid_format
from pydantic import BaseModel

from migrations.session import get_db

router = APIRouter()


class RatingData(BaseModel):
    thread_id: str
    rating: int
    message_id: str = ""
    comments: str = ""


@router.post("/rating")
def submit_rating(
    request: Request, rating_data: RatingData, db: Annotated[Session, Depends(get_db)]
):
    """
    This function gets the settings of an agent by its ID
    :param agent_id: The ID of the agent
    :param db: The database session
    :return: The settings of the agent
    """
    if not check_uuid_format(rating_data.thread_id):
        return response(False, status_code=400, message="Invalid UUID format")
    user_jwt_content = getJWT(request.state)

    try:
        rating_data.rating = int(rating_data.rating)

        if (rating_data.message_id and rating_data.rating in [0, 1]) or (
            not rating_data.message_id
            and rating_data.rating > 0
            and rating_data.rating <= 5
        ):
            db.add(
                UserFeedback(
                    user_id=user_jwt_content["user_id"],
                    thread_id=rating_data.thread_id,
                    message_id=rating_data.message_id,
                    rating_format=2 if rating_data.message_id else 5,
                    rating=rating_data.rating,
                    comments=rating_data.comments,
                )
            )
            db.commit()
            return response(True)
        return response(False, message="Invalid rating value")
    except ValueError:
        return response(False, message="Rating value was non-integer")
    except IntegrityError:
        db.rollback()
        return response(False, message="Could not submit feedback")
    except Exception as e:
        db.rollback()
        return response(False, message=str(e))
