from typing import Annotated
from fastapi import APIRouter, Depends, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from common.JWTValidator import getJWT
from migrations.models import UserFeedback
from utils.response import response
from user.GetAgent import check_uuid_format

from migrations.session import get_db

router = APIRouter()


@router.get("/{thread_id}")
def get_agent_by_id(
    request: Request, thread_id: str, db: Annotated[Session, Depends(get_db)]
):
    """
    This function gets the settings of an agent by its ID
    :param agent_id: The ID of the agent
    :param db: The database session
    :return: The settings of the agent
    """
    if not check_uuid_format(thread_id):
        return response(False, status_code=400, message="Invalid UUID format")
    user_jwt_content = getJWT(request.state)
    message_id = request.query_params.get("message_id", "")

    try:
        rating = int(request.query_params.get("rating", -1))
        comments = request.query_params.get("comments", "")
        if (message_id and rating in [0, 1]) or (
            not message_id and rating > 0 and rating <= 5
        ):
            db.add(
                UserFeedback(
                    user_id=user_jwt_content["user_id"],
                    thread_id=thread_id,
                    message_id=message_id,
                    rating_format=2 if message_id else 5,
                    rating=rating,
                    comments=comments,
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
