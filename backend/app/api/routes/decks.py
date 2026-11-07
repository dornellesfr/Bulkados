from uuid import UUID

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession, Prices
from app.schemas.copies import CopyRead
from app.schemas.decks import (
    CommandersUpdate,
    DeckBulkUpdate,
    DeckCopyCreate,
    DeckCreate,
    DeckDetail,
    DeckSummary,
    DeckUpdate,
    MoveCard,
    TakeCard,
)
from app.services import decks as deck_service
from app.services.access import require_accepted_group

router = APIRouter(tags=["decks"])


@router.post("/decks", response_model=DeckSummary, status_code=201)
async def create_deck(
    body: DeckCreate,
    user: CurrentUser,
    session: DbSession,
) -> DeckSummary:
    return await deck_service.create_deck(session, user, body)


@router.get("/decks", response_model=list[DeckSummary])
async def list_decks(user: CurrentUser, session: DbSession) -> list[DeckSummary]:
    return await deck_service.list_decks(session, user)


@router.post("/groups/{group_id}/decks", response_model=DeckSummary, status_code=201)
async def create_group_deck(
    group_id: UUID,
    body: DeckCreate,
    user: CurrentUser,
    session: DbSession,
) -> DeckSummary:
    """Compatibilidade: criar um deck dentro do bulk continua valendo, mas o deck é da pessoa."""
    await require_accepted_group(session, group_id, user.id)
    return await deck_service.create_deck(session, user, body)


@router.get("/groups/{group_id}/decks", response_model=list[DeckSummary])
async def list_group_decks(
    group_id: UUID,
    user: CurrentUser,
    session: DbSession,
) -> list[DeckSummary]:
    """Compatibilidade: a lista é sempre a dos decks da pessoa, em qualquer bulk."""
    await require_accepted_group(session, group_id, user.id)
    return await deck_service.list_decks(session, user)


@router.get("/decks/{deck_id}", response_model=DeckDetail)
async def get_deck(deck_id: UUID, user: CurrentUser, session: DbSession) -> DeckDetail:
    return await deck_service.get_deck(session, user, deck_id)


@router.patch("/decks/{deck_id}", response_model=DeckDetail)
async def update_deck(
    deck_id: UUID,
    body: DeckUpdate,
    user: CurrentUser,
    session: DbSession,
) -> DeckDetail:
    return await deck_service.update_deck(session, user, deck_id, body)


@router.delete("/decks/{deck_id}", status_code=204)
async def delete_deck(deck_id: UUID, user: CurrentUser, session: DbSession) -> None:
    await deck_service.delete_deck(session, user, deck_id)


@router.put("/decks/{deck_id}/bulk", response_model=DeckDetail)
async def replace_deck_cards(
    deck_id: UUID,
    body: DeckBulkUpdate,
    user: CurrentUser,
    session: DbSession,
    prices: Prices,
) -> DeckDetail:
    return await deck_service.replace_deck_cards(session, user, deck_id, body, prices)


@router.post("/decks/{deck_id}/commanders", response_model=DeckDetail)
async def set_commanders(
    deck_id: UUID,
    body: CommandersUpdate,
    user: CurrentUser,
    session: DbSession,
) -> DeckDetail:
    return await deck_service.set_commanders(session, user, deck_id, body)


@router.post("/decks/{deck_id}/take", response_model=CopyRead)
async def take_copy(
    deck_id: UUID,
    body: TakeCard,
    user: CurrentUser,
    session: DbSession,
) -> CopyRead:
    return await deck_service.take_copy(session, user, deck_id, body)


@router.post("/decks/{deck_id}/copies", response_model=list[CopyRead], status_code=201)
async def create_deck_copies(
    deck_id: UUID,
    body: DeckCopyCreate,
    user: CurrentUser,
    session: DbSession,
    prices: Prices,
) -> list[CopyRead]:
    return await deck_service.create_deck_copies(session, user, deck_id, body, prices)


@router.post("/decks/{deck_id}/cards/{card_copy_id}/move", response_model=CopyRead)
async def move_copy(
    deck_id: UUID,
    card_copy_id: UUID,
    body: MoveCard,
    user: CurrentUser,
    session: DbSession,
) -> CopyRead:
    return await deck_service.move_copy(session, user, deck_id, card_copy_id, body)


@router.post("/decks/{deck_id}/cards/{card_copy_id}/return", response_model=CopyRead)
async def return_copy(
    deck_id: UUID,
    card_copy_id: UUID,
    user: CurrentUser,
    session: DbSession,
) -> CopyRead:
    return await deck_service.return_copy(session, user, deck_id, card_copy_id)


@router.post("/decks/{deck_id}/cards/{card_copy_id}/lock", response_model=CopyRead)
async def lock_copy(
    deck_id: UUID,
    card_copy_id: UUID,
    user: CurrentUser,
    session: DbSession,
) -> CopyRead:
    return await deck_service.set_locked(session, user, deck_id, card_copy_id, locked=True)


@router.post("/decks/{deck_id}/cards/{card_copy_id}/unlock", response_model=CopyRead)
async def unlock_copy(
    deck_id: UUID,
    card_copy_id: UUID,
    user: CurrentUser,
    session: DbSession,
) -> CopyRead:
    return await deck_service.set_locked(session, user, deck_id, card_copy_id, locked=False)
