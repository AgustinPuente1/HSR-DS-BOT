from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, Boolean, DateTime, func

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
    tickets: Mapped[int] = mapped_column(Integer, default=0)
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
    character_id: Mapped[str] = mapped_column(String)
    copies: Mapped[int] = mapped_column(Integer, default=1)
    obtained_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())

class PullHistory(Base):
    __tablename__ = "pull_history"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    player_id: Mapped[str] = mapped_column(ForeignKey("players.user_id"), index=True, nullable=False)
    banner_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    rarity: Mapped[int] = mapped_column(Integer, nullable=False)
    character_id: Mapped[str] = mapped_column(String, nullable=False)
    ts: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
