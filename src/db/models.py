from datetime import datetime, timezone
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, Boolean, DateTime, UniqueConstraint, func

class Base(DeclarativeBase): pass

class Player(Base):
    __tablename__ = "players"
    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    created_at: Mapped["DateTime"] = mapped_column(DateTime, server_default=func.now())
    last_daily_at: Mapped["DateTime | None"] = mapped_column(DateTime(timezone=True), nullable=True)

    currencies: Mapped["Currency"] = relationship(back_populates="player", uselist=False)
    gacha: Mapped["GachaState"] = relationship(back_populates="player", uselist=False)

class Currency(Base):
    __tablename__ = "currencies"
    player_id: Mapped[str] = mapped_column(ForeignKey("players.user_id"), primary_key=True)
    tickets_standard: Mapped[int] = mapped_column(Integer, default=0)  # Star Rail Pass
    tickets_special:  Mapped[int] = mapped_column(Integer, default=0)  # Star Rail Special Pass
    credits: Mapped[int] = mapped_column(Integer, default=0)
    player: Mapped[Player] = relationship(back_populates="currencies")

class GachaState(Base):
    __tablename__ = "gacha_state"
    player_id: Mapped[str] = mapped_column(ForeignKey("players.user_id"), primary_key=True)
    banner_id: Mapped[str] = mapped_column(String, default="stellar_warp")
    pity4: Mapped[int] = mapped_column(Integer, default=0)
    pity5: Mapped[int] = mapped_column(Integer, default=0)
    last_5_was_featured: Mapped[bool] = mapped_column(Boolean, default=True)  # en estándar da igual
    player: Mapped[Player] = relationship(back_populates="gacha")

class InventoryItem(Base):
    __tablename__ = "inventory"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    player_id: Mapped[str] = mapped_column(ForeignKey("players.user_id"))
    item_id: Mapped[str] = mapped_column(String)         # id genérico (char o LC)
    item_type: Mapped[str] = mapped_column(String)       # "character" | "light_cone"
    copies: Mapped[int] = mapped_column(Integer, default=1)
    obtained_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

class PullHistory(Base):
    __tablename__ = "pull_history"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    player_id: Mapped[str] = mapped_column(ForeignKey("players.user_id"), index=True, nullable=False)
    banner_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    rarity: Mapped[int] = mapped_column(Integer, nullable=False)
    item_id: Mapped[str] = mapped_column(String, nullable=False)
    item_type: Mapped[str] = mapped_column(String, nullable=False)  # "character" | "light_cone"
    ts: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True),
        index=True,
        default=lambda: datetime.now(timezone.utc)
    )

class Equipment(Base):
    __tablename__ = "equipment"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    player_id: Mapped[str] = mapped_column(ForeignKey("players.user_id"), index=True, nullable=False)
    character_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    light_cone_id: Mapped[str] = mapped_column(String, index=True, nullable=False)

    __table_args__ = (
        # Un LC por PJ
        UniqueConstraint("player_id", "character_id", name="uq_equipment_player_character"),
        # Un PJ por LC 
        UniqueConstraint("player_id", "light_cone_id", name="uq_equipment_player_lightcone"),
    )