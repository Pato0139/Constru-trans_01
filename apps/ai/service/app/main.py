import uuid
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.db.models import Conversation, Message
from app.db.postgres import get_db, init_db
from app.llm.factory import get_llm_provider
from app.memory.embeddings import embedding_service
from app.memory.retriever import semantic_retriever
from app.memory.short_term import short_term_memory
from app.schemas.chat import ChatRequest, ChatResponse

# Initialize services
llm = get_llm_provider()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        debug=settings.DEBUG,
    )

    # Set up CORS (configure properly in production!)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8000", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def startup():
        init_db()
        logger.info("AI Service started successfully")

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "AI Service"}

    # Chat endpoint
    @app.post(f"{settings.API_V1_STR}/chat", response_model=ChatResponse)
    async def chat(payload: ChatRequest, request: Request, db: Session = Depends(get_db)):
        # Validate internal token
        internal_token = request.headers.get("X-Internal-Token")
        if internal_token != settings.AI_INTERNAL_TOKEN:
            raise HTTPException(status_code=403, detail="Forbidden")

        # Generate session ID if not provided
        session_id = payload.session_id or str(uuid.uuid4())

        # Get or create conversation
        conversation: Optional[Conversation] = None
        if payload.session_id:
            try:
                conversation_id = int(payload.session_id)
                conversation = (
                    db.query(Conversation).filter(Conversation.id == conversation_id).first()
                )
            except (ValueError, TypeError):
                pass  # If invalid session_id, create new

        if not conversation:
            conversation = Conversation(user_id=payload.user_id)
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
            session_id = str(conversation.id)

        # Add user message to DB
        user_msg = Message(conversation_id=conversation.id, role="user", content=payload.message)
        db.add(user_msg)
        db.commit()

        # Build system prompt with business context and user info
        system_prompt = f"""Eres el asistente inteligente de ConstruTrans.
Responde siempre en español.

Tu trabajo es ayudar tanto con:
- preguntas del sistema ConstruTrans
- preguntas generales o cotidianas del usuario

Reglas:
- Si la pregunta requiere datos del sistema, usa business_context.
- Si no requiere datos del sistema, responde como asistente general.
- Mantén el contexto conversacional.
- Si el usuario escribe algo como "y en Bogotá", entiende que continúa la consulta anterior.
- No inventes datos internos.
- Usa punto como separador de miles y coma para decimales.
- Si Estados Unidos es mencionado sin ciudad concreta, explica que hay varias zonas horarias y muestra las principales.

Rol del usuario: {payload.user_role or "desconocido"}
Usuario: {payload.user_name or "No identificado"}

Contexto actual del negocio:
{payload.business_context}
""".strip()

        llm_messages = [{"role": "system", "content": system_prompt}]

        # Retrieve relevant memories if RAG is enabled
        if payload.use_rag:
            query_embedding = embedding_service.embed_text(payload.message)
            retrieved_memories = semantic_retriever.search(
                collection_name="conversation_memory", query_embedding=query_embedding, n_results=3
            )
            if retrieved_memories:
                memory_context = "\n".join([f"- {mem['document']}" for mem in retrieved_memories])
                llm_messages.append(
                    {"role": "system", "content": f"Memoria relevante:\n{memory_context}"}
                )

        # Add conversation history
        for h in payload.history[-10:]:
            llm_messages.append({"role": h.role, "content": h.content})

        # Add current user message
        llm_messages.append({"role": "user", "content": payload.message})

        # Generate response
        try:
            response_text = llm.chat(llm_messages, temperature=0.2)
        except Exception as e:
            logger.error(f"LLM error: {str(e)}")
            raise HTTPException(status_code=500, detail="Error al generar respuesta")

        # Add assistant message to DB
        assistant_msg = Message(
            conversation_id=conversation.id, role="assistant", content=response_text
        )
        db.add(assistant_msg)
        db.commit()

        # Store in short-term memory
        short_term_memory.add_message(session_id, {"role": "user", "content": payload.message})
        short_term_memory.add_message(session_id, {"role": "assistant", "content": response_text})

        # Store conversation in semantic memory
        conv_text = f"Usuario: {payload.message}\nAsistente: {response_text}"
        conv_embedding = embedding_service.embed_text(conv_text)

        # Get current history count for unique ID
        history_count = db.query(Message).filter(Message.conversation_id == conversation.id).count()

        semantic_retriever.add(
            collection_name="conversation_memory",
            ids=[f"conv-{conversation.id}-{history_count}"],
            documents=[conv_text],
            embeddings=[conv_embedding],
            metadatas=[{"conversation_id": conversation.id, "user_id": payload.user_id}],
        )

        # Update conversation
        conversation.updated_at = assistant_msg.created_at
        db.commit()

        return ChatResponse(
            response=response_text,
            session_id=session_id,
            model_used=getattr(llm, "name", settings.LLM_PROVIDER),
            tool_calls=[],
            status="ok",
        )

    return app


app = create_app()
