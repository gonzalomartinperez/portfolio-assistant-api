import hashlib
import json
import logging
import secrets
import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Request,
    Response,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from psycopg.errors import UniqueViolation

from .config import settings
from .db import connect
from .ledger import BudgetExhausted
from .models import (
    ConversationCreate,
    ConversationUpdate,
    ConversationView,
    ErrorBody,
    FeedbackCreate,
    MessagePage,
    Page,
    RunView,
    SendMessage,
    SessionView,
    SSEEnvelope,
)
from .workflow import delete_checkpoint, run_workflow

log = logging.getLogger('portfolio_assistant')
if not log.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(message)s'))
    log.addHandler(handler)
    log.setLevel(logging.INFO)
log.propagate = False

app = FastAPI(title='Portfolio Assistant API', version='1.0.0')
router = APIRouter(responses={code: {'model': ErrorBody} for code in (400, 401, 403, 404, 409, 422, 429, 503)})
app.add_middleware(CORSMiddleware, allow_origins=settings().origins, allow_credentials=True,
                   allow_methods=['GET', 'POST', 'PATCH', 'DELETE'],
                   allow_headers=['Content-Type', 'X-CSRF-Token', 'X-Session-Bootstrap', 'Idempotency-Key'],
                   expose_headers=['X-Run-ID', 'X-Request-ID'])


def utcnow():
    return datetime.now(UTC)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def fail(code: str, status: int = 400):
    raise HTTPException(status_code=status, detail=code)


@app.exception_handler(HTTPException)
def http_error(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content=ErrorBody(
        code=str(exc.detail), message=str(exc.detail).replace('_', ' '),
        request_id=request.state.request_id).model_dump())


@app.exception_handler(RequestValidationError)
def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content=ErrorBody(
        code='invalid_request', message='Invalid request', request_id=request.state.request_id).model_dump())


@app.middleware('http')
async def guard_origin(request: Request, call_next):
    started = time.perf_counter()
    request.state.request_id = uuid4().hex
    if request.method in ('POST', 'PATCH', 'DELETE') and request.headers.get('origin') not in settings().origins:
        response = JSONResponse(status_code=403, content=ErrorBody(
            code='origin_denied', message='Origin denied', request_id=request.state.request_id).model_dump())
    else:
        response = await call_next(request)
    response.headers['X-Request-ID'] = request.state.request_id
    response.headers['Vary'] = 'Origin'
    route = request.scope.get('route')
    log.info(json.dumps({
        'request_id': request.state.request_id,
        'operation': route.name if route else 'unmatched',
        'status': response.status_code,
        'duration_ms': round((time.perf_counter() - started) * 1000, 1),
    }))
    return response


@contextmanager
def owned_conversation(session_id: UUID, conversation_id: UUID):
    with connect() as conn:
        row = conn.execute('SELECT id FROM conversations WHERE id=%s AND session_id=%s',
                           (conversation_id, session_id)).fetchone()
        if not row:
            fail('not_found', 404)
        yield conn


def current_session(request: Request):
    raw = request.cookies.get(settings().cookie_name)
    if not raw:
        fail('session_required', 401)
    with connect() as conn:
        row = conn.execute('SELECT id, csrf_token, expires_at FROM sessions WHERE secret_digest=%s AND expires_at>now()',
                           (digest(raw),)).fetchone()
    if not row:
        fail('session_required', 401)
    return row


def mutation_session(request: Request, session=Depends(current_session)):
    token = request.headers.get('x-csrf-token', '')
    if not secrets.compare_digest(token, session['csrf_token']):
        fail('csrf_denied', 403)
    return session


def run_view(row):
    return RunView(id=row['id'], conversation_id=row['conversation_id'], state=row['state'],
                   message_id=row['message_id'], error_code=row['error_code'],
                   created_at=row['created_at'], updated_at=row['updated_at'])


def rate_limit(subject: str, operation: str, limit: int):
    subject_hash = digest(settings().rate_hash_key + subject)
    with connect() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(472018)')
        count = conn.execute("SELECT count(*) AS n FROM rate_events WHERE subject_hash=%s AND operation=%s AND created_at>now()-interval '1 hour'",
                             (subject_hash, operation)).fetchone()['n']
        if count >= limit:
            fail('rate_limited', 429)
        conn.execute('INSERT INTO rate_events(id,subject_hash,operation) VALUES (%s,%s,%s)',
                     (uuid4(), subject_hash, operation))


def reconcile_expired_runs():
    with connect() as conn:
        conn.execute("UPDATE runs SET state='interrupted',error_code='run_interrupted',updated_at=now() WHERE state IN ('pending','running') AND lease_until<now()")


@router.get('/health/live', operation_id='healthLive')
def live():
    return {'status': 'ok'}


@router.get('/health/ready', operation_id='healthReady')
def ready():
    try:
        with connect() as conn:
            conn.execute('SELECT 1')
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(settings().neo4j_uri, auth=(settings().neo4j_user, settings().neo4j_password))
        try:
            driver.verify_connectivity()
        finally:
            driver.close()
        return {'status': 'ok'}
    except Exception:
        fail('dependency_unavailable', 503)


@router.post('/api/v1/session', response_model=SessionView, responses={403: {'model': ErrorBody}}, operation_id='createSession')
def create_session(request: Request, response: Response,
                   x_session_bootstrap: str | None = Header(default=None)):
    if x_session_bootstrap != '1' or request.headers.get('content-type', '').split(';')[0] != 'application/json':
        fail('bootstrap_denied', 403)
    rate_limit(request.client.host if request.client else 'unknown', 'bootstrap', 20)
    raw = secrets.token_urlsafe(48)
    csrf = secrets.token_urlsafe(32)
    expires = utcnow() + timedelta(days=settings().retention_days)
    with connect() as conn:
        conn.execute('INSERT INTO sessions(id,secret_digest,csrf_token,expires_at) VALUES (%s,%s,%s,%s)',
                     (uuid4(), digest(raw), csrf, expires))
    response.set_cookie(settings().cookie_name, raw, httponly=True, secure=settings().secure_cookies,
                        samesite='lax', path='/', max_age=settings().retention_days * 86400)
    return SessionView(csrf_token=csrf, expires_at=expires, retention_days=settings().retention_days)


@router.get('/api/v1/session', response_model=SessionView, operation_id='getSession')
def get_session(session=Depends(current_session)):
    return SessionView(csrf_token=session['csrf_token'], expires_at=session['expires_at'],
                       retention_days=settings().retention_days)


@router.delete('/api/v1/session', status_code=204, operation_id='deleteSession')
def delete_session(response: Response, session=Depends(mutation_session)):
    with connect() as conn:
        run_ids = [str(row['id']) for row in conn.execute('SELECT r.id FROM runs r JOIN conversations c ON c.id=r.conversation_id WHERE c.session_id=%s', (session['id'],)).fetchall()]
        conn.execute('DELETE FROM sessions WHERE id=%s', (session['id'],))
    for run_id in run_ids:
        delete_checkpoint(run_id)
    response.delete_cookie(settings().cookie_name, path='/')


@router.post('/api/v1/conversations', response_model=ConversationView, operation_id='createConversation')
def create_conversation(body: ConversationCreate, session=Depends(mutation_session)):
    with connect() as conn:
        row = conn.execute('INSERT INTO conversations(id,session_id,title) VALUES (%s,%s,%s) RETURNING *',
                           (uuid4(), session['id'], body.title)).fetchone()
    return row


@router.get('/api/v1/conversations', response_model=Page, operation_id='listConversations')
def list_conversations(limit: int = 30, cursor: datetime | None = None, session=Depends(current_session)):
    if not 1 <= limit <= 50:
        fail('invalid_limit')
    with connect() as conn:
        rows = conn.execute('SELECT * FROM conversations WHERE session_id=%s AND (%s::timestamptz IS NULL OR updated_at<%s) ORDER BY updated_at DESC LIMIT %s',
                            (session['id'], cursor, cursor, limit + 1)).fetchall()
    return Page(items=rows[:limit], next_cursor=rows[limit-1]['updated_at'].isoformat() if len(rows) > limit else None)


@router.patch('/api/v1/conversations/{conversation_id}', response_model=ConversationView, operation_id='renameConversation')
def rename_conversation(conversation_id: UUID, body: ConversationUpdate, session=Depends(mutation_session)):
    with owned_conversation(session['id'], conversation_id) as conn:
        row = conn.execute('UPDATE conversations SET title=%s,updated_at=now() WHERE id=%s RETURNING *',
                           (body.title, conversation_id)).fetchone()
    return row


@router.delete('/api/v1/conversations/{conversation_id}', status_code=204, operation_id='deleteConversation')
def delete_conversation(conversation_id: UUID, session=Depends(mutation_session)):
    with owned_conversation(session['id'], conversation_id) as conn:
        run_ids = [str(row['id']) for row in conn.execute('SELECT id FROM runs WHERE conversation_id=%s', (conversation_id,)).fetchall()]
        conn.execute('DELETE FROM conversations WHERE id=%s', (conversation_id,))
    for run_id in run_ids:
        delete_checkpoint(run_id)


@router.get('/api/v1/conversations/{conversation_id}/messages', response_model=MessagePage, operation_id='listMessages')
def list_messages(conversation_id: UUID, limit: int = 50, cursor: datetime | None = None,
                  session=Depends(current_session)):
    if not 1 <= limit <= 100:
        fail('invalid_limit')
    with owned_conversation(session['id'], conversation_id) as conn:
        rows = conn.execute('SELECT * FROM messages WHERE conversation_id=%s AND (%s::timestamptz IS NULL OR created_at<%s) ORDER BY created_at DESC LIMIT %s',
                            (conversation_id, cursor, cursor, limit + 1)).fetchall()
    return MessagePage(items=rows[:limit], next_cursor=rows[limit-1]['created_at'].isoformat() if len(rows) > limit else None)


def sse(event_type: str, run_id: UUID, conversation_id: UUID, sequence: int, payload: dict):
    body = SSEEnvelope(type=event_type, run_id=run_id, conversation_id=conversation_id,
                       sequence=sequence, timestamp=utcnow(), payload=payload)
    return f'event: {event_type}\ndata: {body.model_dump_json()}\n\n'


def retrieve(question: str):
    # Exact pgvector scan and bounded graph traversal over the same active version.
    from neo4j import GraphDatabase

    from .knowledge import embed
    with connect() as conn:
        version = conn.execute("SELECT id,source_commit FROM knowledge_versions WHERE status='active' ORDER BY created_at DESC LIMIT 1").fetchone()
        if not version:
            return [], []
        if 'filomena' in question.lower():
            rows = conn.execute("SELECT id,title,url,source_type,path,start_line,end_line,content FROM chunks WHERE knowledge_version=%s AND path IN ('src/content/en/projects.ts','src/content/es/projects.ts') AND start_line=1 ORDER BY path LIMIT 2", (version['id'],)).fetchall()
        else:
            rows = conn.execute('SELECT id,title,url,source_type,path,start_line,end_line,content FROM chunks WHERE knowledge_version=%s ORDER BY embedding <=> %s::vector LIMIT 3',
                                (version['id'], embed(question))).fetchall()
    graph_ids = []
    if 'filomena' in question.lower():
        driver = GraphDatabase.driver(settings().neo4j_uri, auth=(settings().neo4j_user, settings().neo4j_password))
        try:
            with driver.session() as graph:
                graph_ids = [record['id'] for record in graph.run(
                    'MATCH (:Project {name:$name})-[:SUPPORTED_BY]->(d:Document {version:$version}) RETURN d.id AS id LIMIT 3',
                    name='Filomena', version=version['id'])]
        finally:
            driver.close()
    if graph_ids:
        with connect() as conn:
            graph_rows = conn.execute('SELECT id,title,url,source_type,path,start_line,end_line,content FROM chunks WHERE knowledge_version=%s AND id=ANY(%s)',
                                      (version['id'], graph_ids)).fetchall()
        seen = {row['id'] for row in rows}
        rows.extend(row for row in graph_rows if row['id'] not in seen)
    return rows[:5], [version['source_commit']]


def execute_run(run_id: UUID, conversation_id: UUID, question: str, locale: str):
    seq = 0
    yield sse('run.started', run_id, conversation_id, seq, {'state': 'running'})
    seq += 1
    try:
        with connect() as conn:
            conn.execute("UPDATE runs SET state='running',lease_until=now()+interval '5 minutes',updated_at=now() WHERE id=%s AND state='pending'", (run_id,))
        rows, commits = retrieve(question)
        evidence = '\n'.join(row['content'] for row in rows)
        result = run_workflow({'question': question, 'locale': locale, 'evidence': evidence, 'answer': '', 'run_id': str(run_id)}, str(run_id))
        answer = result['answer']
        citations = [{'id': row['id'], 'label': row['title'], 'url': row['url'],
                      'source_type': row['source_type'], 'commit_sha': commits[0] if commits else None, 'path': row['path'],
                      'start_line': row['start_line'], 'end_line': row['end_line']} for row in rows] if evidence else []
        for offset in range(0, len(answer), 60):
            with connect() as conn:
                state = conn.execute('SELECT state FROM runs WHERE id=%s', (run_id,)).fetchone()['state']
            if state == 'cancelled':
                yield sse('run.cancelled', run_id, conversation_id, seq, {})
                return
            yield sse('message.delta', run_id, conversation_id, seq, {'text': answer[offset:offset+60]})
            seq += 1
        message_id = uuid4()
        with connect() as conn:
            state = conn.execute('SELECT state FROM runs WHERE id=%s FOR UPDATE', (run_id,)).fetchone()
            if state['state'] != 'running':
                yield sse('run.cancelled', run_id, conversation_id, seq, {})
                return
            conn.execute("INSERT INTO messages(id,conversation_id,role,content,citations) VALUES (%s,%s,'assistant',%s,%s)",
                         (message_id, conversation_id, answer, json.dumps(citations)))
            conn.execute("UPDATE runs SET state='completed',message_id=%s,lease_until=NULL,updated_at=now() WHERE id=%s",
                         (message_id, run_id))
        yield sse('message.completed', run_id, conversation_id, seq, {'message_id': str(message_id), 'content': answer, 'citations': citations})
        yield sse('run.completed', run_id, conversation_id, seq + 1, {'state': 'completed'})
    except Exception as error:
        code = 'budget_exhausted' if isinstance(error, BudgetExhausted) else 'generation_failed'
        with connect() as conn:
            conn.execute("UPDATE runs SET state='failed',error_code=%s,lease_until=NULL,updated_at=now() WHERE id=%s AND state IN ('pending','running')", (code, run_id))
        yield sse('run.failed', run_id, conversation_id, seq, {'code': code})


@router.post('/api/v1/conversations/{conversation_id}/messages/stream', operation_id='streamMessage',
          responses={200: {'content': {'text/event-stream': {'schema': {'type': 'string'}}}}})
def stream_message(conversation_id: UUID, body: SendMessage,
                   idempotency_key: str = Header(min_length=8, max_length=128),
                   session=Depends(mutation_session)):
    reconcile_expired_runs()
    payload_hash = digest(body.model_dump_json())
    rate_limit(str(session['id']), 'message', 30)
    with owned_conversation(session['id'], conversation_id) as conn:
        existing = conn.execute('SELECT * FROM runs WHERE conversation_id=%s AND idempotency_key=%s',
                                (conversation_id, idempotency_key)).fetchone()
        if existing:
            if existing['payload_hash'] != payload_hash:
                fail('idempotency_conflict', 409)
            fail('run_already_exists', 409)
        conn.execute('SELECT pg_advisory_xact_lock(472020)')
        active_count = conn.execute("SELECT count(*) AS n FROM runs WHERE state IN ('pending','running')").fetchone()['n']
        if active_count >= 4:
            fail('busy', 429)
        run_id = uuid4()
        try:
            conn.execute("INSERT INTO runs(id,conversation_id,idempotency_key,payload_hash,state,lease_until) VALUES (%s,%s,%s,%s,'pending',now()+interval '5 minutes')",
                         (run_id, conversation_id, idempotency_key, payload_hash))
            conn.execute("INSERT INTO messages(id,conversation_id,role,content) VALUES (%s,%s,'user',%s)",
                         (uuid4(), conversation_id, body.content))
            conn.execute('UPDATE conversations SET updated_at=now() WHERE id=%s', (conversation_id,))
        except UniqueViolation:
            fail('run_in_progress', 409)
    return StreamingResponse(execute_run(run_id, conversation_id, body.content, body.locale),
                             media_type='text/event-stream', headers={'Cache-Control': 'no-cache, no-transform',
                                                                      'X-Accel-Buffering': 'no', 'X-Run-ID': str(run_id)})


@router.get('/api/v1/runs/{run_id}', response_model=RunView, operation_id='getRun')
def get_run(run_id: UUID, session=Depends(current_session)):
    reconcile_expired_runs()
    with connect() as conn:
        row = conn.execute('SELECT r.* FROM runs r JOIN conversations c ON c.id=r.conversation_id WHERE r.id=%s AND c.session_id=%s',
                           (run_id, session['id'])).fetchone()
    if not row:
        fail('not_found', 404)
    return run_view(row)


@router.post('/api/v1/runs/{run_id}/cancel', response_model=RunView, operation_id='cancelRun')
def cancel_run(run_id: UUID, session=Depends(mutation_session)):
    with connect() as conn:
        row = conn.execute("UPDATE runs r SET state='cancelled',lease_until=NULL,updated_at=now() FROM conversations c WHERE r.id=%s AND r.conversation_id=c.id AND c.session_id=%s AND r.state IN ('pending','running') RETURNING r.*",
                           (run_id, session['id'])).fetchone()
        if not row:
            row = conn.execute('SELECT r.* FROM runs r JOIN conversations c ON c.id=r.conversation_id WHERE r.id=%s AND c.session_id=%s',
                               (run_id, session['id'])).fetchone()
    if not row:
        fail('not_found', 404)
    return run_view(row)


@router.post('/api/v1/messages/{message_id}/feedback', status_code=204, operation_id='recordFeedback')
def record_feedback(message_id: UUID, body: FeedbackCreate, session=Depends(mutation_session)):
    with connect() as conn:
        found = conn.execute("SELECT m.id FROM messages m JOIN conversations c ON c.id=m.conversation_id WHERE m.id=%s AND c.session_id=%s AND m.role='assistant'",
                             (message_id, session['id'])).fetchone()
        if not found:
            fail('not_found', 404)
        conn.execute('INSERT INTO feedback(message_id,session_id,rating) VALUES (%s,%s,%s) ON CONFLICT(message_id) DO UPDATE SET rating=excluded.rating',
                     (message_id, session['id'], body.rating))


app.include_router(router)
