from enum import StrEnum


class MembershipStatus(StrEnum):
    invited = "invited"
    accepted = "accepted"


class CommanderLegal(StrEnum):
    legal = "legal"
    banned = "banned"
    not_legal = "not_legal"


class PartnerKind(StrEnum):
    partner = "partner"
    partner_with = "partner_with"
    friends_forever = "friends_forever"
    background = "background"
    choose_a_background = "choose_a_background"
    doctors_companion = "doctors_companion"


class CopyState(StrEnum):
    available = "available"
    reserved = "reserved"
    in_deck = "in_deck"


class DeckFormat(StrEnum):
    commander_10 = "commander_10"
    commander_100 = "commander_100"
    commander_200 = "commander_200"
    commander_500 = "commander_500"
    competitive = "competitive"


class DeckRole(StrEnum):
    commander = "commander"
    main = "main"


class RequestSource(StrEnum):
    bulk = "bulk"
    deck = "deck"


class RequestStatus(StrEnum):
    pending_acceptance = "pending_acceptance"
    awaiting_handoff = "awaiting_handoff"
    completed = "completed"
    cancelled = "cancelled"
    rejected = "rejected"


OPEN_REQUEST_STATUSES: frozenset[RequestStatus] = frozenset(
    {RequestStatus.pending_acceptance, RequestStatus.awaiting_handoff}
)
