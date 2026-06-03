from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.stat import UserStat, ScoreEvent, ProgressionEvent
import logging

logger = logging.getLogger(__name__)

async def verify_ledger_consistency(db: AsyncSession, user_id: int) -> dict:
    """
    Replays all ScoreEvents and ProgressionEvents chronologically for a user
    to verify that the current UserStat values are fully consistent with the ledger.
    
    Returns a dict with verification details:
    {
        "success": bool,
        "total_xp_match": bool,
        "lifetime_xp_match": bool,
        "prestige_match": bool,
        "stat_total_xp": int,
        "replayed_total_xp": int,
        "stat_lifetime_xp": int,
        "replayed_lifetime_xp": int,
        "errors": list[str]
    }
    """
    errors = []
    
    # 1. Fetch current user stat state
    stat_q = select(UserStat).where(UserStat.user_id == user_id)
    user_stat = (await db.execute(stat_q)).scalars().first()
    if not user_stat:
        return {
            "success": False,
            "errors": [f"UserStat record not found for user {user_id}"]
        }
        
    # 2. Fetch all ScoreEvents ordered by created_at/date
    se_q = select(ScoreEvent).where(ScoreEvent.user_id == user_id).order_by(ScoreEvent.created_at)
    score_events = (await db.execute(se_q)).scalars().all()
    
    # 3. Fetch all ProgressionEvents ordered by created_at
    pe_q = select(ProgressionEvent).where(ProgressionEvent.user_id == user_id).order_by(ProgressionEvent.created_at)
    prog_events = (await db.execute(pe_q)).scalars().all()
    
    # 4. Chronological replay
    # Sort all events together by created_at. We will map them to a unified list.
    all_events = []
    for se in score_events:
        all_events.append({
            "type": "score",
            "created_at": se.created_at,
            "delta_xp": se.delta_xp,
            "event_type": se.event_type,
            "id": se.event_id
        })
    for pe in prog_events:
        all_events.append({
            "type": "progression",
            "created_at": pe.created_at,
            "event_type": pe.event_type,
            "payload": pe.payload,
            "id": pe.id
        })
        
    # Sort unified event log by created_at
    all_events.sort(key=lambda x: x["created_at"])
    
    replayed_total_xp = 0
    replayed_lifetime_xp = 0
    replayed_prestige = 0
    
    for evt in all_events:
        if evt["type"] == "score":
            delta = evt["delta_xp"]
            
            # Replay total XP with max(0, ...) floor
            old_total = replayed_total_xp
            replayed_total_xp = max(0, replayed_total_xp + delta)
            
            # Replay lifetime XP based on the positive growth in total XP
            actual_gain = replayed_total_xp - old_total
            if actual_gain > 0:
                replayed_lifetime_xp += actual_gain
                
        elif evt["type"] == "progression" and evt["event_type"] == "prestige_triggered":
            replayed_prestige += 1
            replayed_total_xp = 0  # reset total on prestige
            
    # Check consistency
    total_xp_match = (replayed_total_xp == user_stat.total_xp)
    lifetime_xp_match = (replayed_lifetime_xp == user_stat.lifetime_xp)
    prestige_match = (replayed_prestige == user_stat.prestige_level)
    
    if not total_xp_match:
        errors.append(f"Total XP mismatch! Stat: {user_stat.total_xp}, Replayed: {replayed_total_xp}")
    if not lifetime_xp_match:
        errors.append(f"Lifetime XP mismatch! Stat: {user_stat.lifetime_xp}, Replayed: {replayed_lifetime_xp}")
    if not prestige_match:
        errors.append(f"Prestige level mismatch! Stat: {user_stat.prestige_level}, Replayed: {replayed_prestige}")
        
    success = len(errors) == 0
    
    return {
        "success": success,
        "total_xp_match": total_xp_match,
        "lifetime_xp_match": lifetime_xp_match,
        "prestige_match": prestige_match,
        "stat_total_xp": user_stat.total_xp,
        "replayed_total_xp": replayed_total_xp,
        "stat_lifetime_xp": user_stat.lifetime_xp,
        "replayed_lifetime_xp": replayed_lifetime_xp,
        "stat_prestige": user_stat.prestige_level,
        "replayed_prestige": replayed_prestige,
        "errors": errors
    }
