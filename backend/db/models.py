from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Organe(Base):
    """Groupe parlementaire ou commission."""

    __tablename__ = "organes"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # ex: PO800520
    sigle: Mapped[str] = mapped_column(String(20))
    libelle: Mapped[str] = mapped_column(String(200))
    couleur: Mapped[Optional[str]] = mapped_column(String(7))  # hex #rrggbb
    legislature: Mapped[int] = mapped_column(Integer, default=17)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    deputes: Mapped[list["Depute"]] = relationship(back_populates="groupe")


class Depute(Base):
    """Député en exercice ou ancien député."""

    __tablename__ = "deputes"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # ex: PA1234
    nom: Mapped[str] = mapped_column(String(200))
    prenom: Mapped[str] = mapped_column(String(100))
    nom_de_famille: Mapped[str] = mapped_column(String(100))
    sexe: Mapped[Optional[str]] = mapped_column(String(1))
    date_naissance: Mapped[Optional[date]] = mapped_column(Date)
    profession: Mapped[Optional[str]] = mapped_column(String(200))
    num_departement: Mapped[Optional[str]] = mapped_column(String(3))
    nom_circonscription: Mapped[Optional[str]] = mapped_column(String(200))
    num_circonscription: Mapped[Optional[int]] = mapped_column(Integer)
    place_hemicycle: Mapped[Optional[int]] = mapped_column(Integer)
    url_photo: Mapped[Optional[str]] = mapped_column(String(500))
    url_an: Mapped[Optional[str]] = mapped_column(String(500))
    twitter: Mapped[Optional[str]] = mapped_column(String(100))
    facebook_url: Mapped[Optional[str]] = mapped_column(String(500))
    instagram_url: Mapped[Optional[str]] = mapped_column(String(500))
    bluesky_url: Mapped[Optional[str]] = mapped_column(String(500))
    mandat_debut: Mapped[Optional[date]] = mapped_column(Date)
    mandat_fin: Mapped[Optional[date]] = mapped_column(Date)
    legislature: Mapped[int] = mapped_column(Integer, default=17)
    groupe_id: Mapped[Optional[str]] = mapped_column(ForeignKey("organes.id"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    groupe: Mapped[Optional["Organe"]] = relationship(back_populates="deputes")
    votes: Mapped[list["VoteDepute"]] = relationship(back_populates="depute")
    amendements: Mapped[list["Amendement"]] = relationship(back_populates="depute")


class Scrutin(Base):
    """Scrutin (vote solennel ou ordinaire)."""

    __tablename__ = "scrutins"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # ex: VTANR5L17V1234
    numero: Mapped[int] = mapped_column(Integer)
    titre: Mapped[str] = mapped_column(Text)
    date_seance: Mapped[date] = mapped_column(Date, index=True)
    type_vote: Mapped[Optional[str]] = mapped_column(String(50))
    sort: Mapped[Optional[str]] = mapped_column(String(20))  # adopté / rejeté
    nombre_votants: Mapped[Optional[int]] = mapped_column(Integer)
    nombre_pours: Mapped[Optional[int]] = mapped_column(Integer)
    nombre_contres: Mapped[Optional[int]] = mapped_column(Integer)
    nombre_abstentions: Mapped[Optional[int]] = mapped_column(Integer)
    url_an: Mapped[Optional[str]] = mapped_column(String(500))
    legislature: Mapped[int] = mapped_column(Integer, default=17)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    votes: Mapped[list["VoteDepute"]] = relationship(back_populates="scrutin")


class VoteDepute(Base):
    """Vote d'un député sur un scrutin."""

    __tablename__ = "votes_deputes"

    scrutin_id: Mapped[str] = mapped_column(ForeignKey("scrutins.id"), primary_key=True)
    depute_id: Mapped[str] = mapped_column(ForeignKey("deputes.id"), primary_key=True)
    position: Mapped[str] = mapped_column(
        String(20)
    )  # pour / contre / abstention / nonVotant

    scrutin: Mapped["Scrutin"] = relationship(back_populates="votes")
    depute: Mapped["Depute"] = relationship(back_populates="votes")


class Amendement(Base):
    """Amendement déposé par un député."""

    __tablename__ = "amendements"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    numero: Mapped[Optional[str]] = mapped_column(String(20))
    titre: Mapped[Optional[str]] = mapped_column(Text)
    texte_legislature: Mapped[Optional[str]] = mapped_column(String(50))
    date_depot: Mapped[Optional[date]] = mapped_column(Date, index=True)
    sort: Mapped[Optional[str]] = mapped_column(String(50))
    url_an: Mapped[Optional[str]] = mapped_column(String(500))
    depute_id: Mapped[Optional[str]] = mapped_column(ForeignKey("deputes.id"))
    legislature: Mapped[int] = mapped_column(Integer, default=17)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    depute: Mapped[Optional["Depute"]] = relationship(back_populates="amendements")
