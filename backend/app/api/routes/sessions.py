"""مسار الجلسات — دورة إنشاء/قراءة/حذف عبر HTTP، محميّة بمفتاح API (القاعدة Q5)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import DbDep, require_api_key
from app.repositories import SessionRepository
from app.schemas.session import SessionCreate, SessionRead

#: كل نقاط هذا المسار تتطلب مصادقة؛ التوثيق في ``docs/API.md`` يقول «نعم»،
#: واختبار العقد يستدعي كل صف «نعم» بلا بيانات اعتماد ويتوقع 401.
router = APIRouter(
    prefix="/sessions",
    tags=["sessions"],
    dependencies=[Depends(require_api_key)],
)


@router.post(
    "",
    response_model=SessionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a worker session",
    operation_id="createSession",
)
async def create_session(payload: SessionCreate, session: DbDep) -> SessionRead:
    """``201`` نجاح؛ ``409`` إذا كانت المهمة مرتبطة بجلسة؛ ``422`` لخلل تحقّق."""
    record = SessionRepository(session).create(
        task_id=payload.task_id,
        employee_id=payload.employee_id,
        branch=payload.branch,
        worktree=payload.worktree,
    )
    return SessionRead.model_validate(record)


@router.get(
    "/{session_id}",
    response_model=SessionRead,
    summary="Read one session",
    operation_id="getSession",
)
async def get_session(session_id: str, session: DbDep) -> SessionRead:
    """``200`` نجاح؛ ``404`` بمعرّف غير معروف (``not_found`` في القالب الموحد)."""
    return SessionRead.model_validate(SessionRepository(session).get(session_id))


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete one session",
    operation_id="deleteSession",
)
async def delete_session(session_id: str, session: DbDep) -> Response:
    """``204`` بلا جسم؛ ``404`` عند عدم الوجود. حذف مرّتين ⇒ الثاني ``404``."""
    SessionRepository(session).delete(session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "",
    response_model=list[SessionRead],
    summary="List sessions of one employee",
    operation_id="listSessions",
)
async def list_sessions(
    session: DbDep,
    employee_id: Annotated[str, Query(min_length=1, max_length=64)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[SessionRead]:
    """``200`` بقائمة قد تكون فارغة؛ ``422`` عند ``limit`` خارج ``1..100``."""
    records = SessionRepository(session).list_for_employee(employee_id, limit=limit)
    return [SessionRead.model_validate(record) for record in records]
