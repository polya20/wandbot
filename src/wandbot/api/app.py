import logging

from fastapi import FastAPI, Response, status
from wandbot.api.schemas import (
    APICreateChatThreadRequest,
    APIFeedbackRequest,
    APIFeedbackResponse,
    APIGetChatThreadResponse,
    APIQueryRequest,
    APIQueryResponse,
    APIQuestionAnswerRequest,
    APIQuestionAnswerResponse,
)
from wandbot.chat.chat import Chat
from wandbot.chat.config import ChatConfig
from wandbot.chat.schemas import ChatRequest
from wandbot.database.client import DatabaseClient
from wandbot.database.database import engine
from wandbot.database.models import Base

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)
chat: Chat | None = None
app = FastAPI(name="wandbot", version="0.0.1")
db_client: DatabaseClient | None = None


@app.on_event("startup")
def startup_event():
    global chat, db_client
    chat = Chat(ChatConfig())
    db_client = DatabaseClient()


@app.post(
    "/question_answer",
    response_model=APIQuestionAnswerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_question_answer(
    request: APIQuestionAnswerRequest, response: Response
) -> APIQuestionAnswerResponse | None:
    question_answer = db_client.create_question_answer(request)
    if question_answer is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
    return question_answer


@app.get(
    "/chat_thread/{application}/{thread_id}",
    response_model=APIGetChatThreadResponse | None,
    status_code=status.HTTP_200_OK,
)
async def get_chat_thread(
    application: str, thread_id: str, response: Response
) -> APIGetChatThreadResponse:
    chat_thread = db_client.get_chat_thread(
        application=application,
        thread_id=thread_id,
    )
    if chat_thread is None:
        chat_thread = db_client.create_chat_thread(
            APICreateChatThreadRequest(
                application=application,
                thread_id=thread_id,
            )
        )
        response.status_code = status.HTTP_201_CREATED
    if chat_thread is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
    return chat_thread


@app.post("/query", response_model=APIQueryResponse, status_code=status.HTTP_200_OK)
async def query(
    request: APIQueryRequest,
) -> APIQueryResponse:
    result = chat(
        ChatRequest(question=request.question, chat_history=request.chat_history),
    )
    result = APIQueryResponse(**result.dict())

    return result


@app.post(
    "/feedback",
    response_model=APIFeedbackResponse | None,
    status_code=status.HTTP_201_CREATED,
)
async def feedback(
    request: APIFeedbackRequest, response: Response
) -> APIFeedbackResponse:
    feedback_response = db_client.create_feedback(request)
    if feedback_response is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
    return feedback_response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="localhost",
        port=8000,
    )